"""Safe initial document validation, text extraction, and excerpt ranking."""

from io import BytesIO
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_CHARS = 200_000
SUPPORTED_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
SUPPORTED_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


class DocumentError(ValueError):
    pass


def validate_image(filename: str, content_type: str, data: bytes) -> str:
    """Validate a small raster image and return its canonical MIME type."""
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise DocumentError("Images must be between 1 byte and 10 MB.")
    extension = Path(filename).suffix.lower()
    expected_type = SUPPORTED_IMAGE_TYPES.get(extension)
    if not expected_type or content_type not in (expected_type, "application/octet-stream"):
        raise DocumentError("Supported images are PNG, JPG, JPEG, and WebP.")
    signatures = {
        ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": data.startswith(b"\xff\xd8\xff"),
        ".jpeg": data.startswith(b"\xff\xd8\xff"),
        ".webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    }
    if not signatures[extension]:
        raise DocumentError("The image content does not match its file type.")
    return expected_type


def sanitize_filename(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name
    name = re.sub(r"[^\w.() -]", "_", name, flags=re.UNICODE).strip(" .")
    return (name or "upload")[:180]


def extract_text(filename: str, content_type: str, data: bytes) -> str:
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise DocumentError("Files must be between 1 byte and 10 MB.")
    extension = Path(filename).suffix.lower()
    expected_type = SUPPORTED_TYPES.get(extension)
    if not expected_type or content_type not in (expected_type, "application/octet-stream"):
        raise DocumentError("Supported document types are PDF, TXT, and Markdown.")

    try:
        if extension == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise DocumentError("Encrypted PDFs are not supported.")
            if len(reader.pages) > 120:
                raise DocumentError("PDFs are limited to 120 pages.")
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            if not text.strip():
                raise DocumentError("No selectable text was found in this PDF. Scanned PDFs need OCR, which is not supported yet.")
        elif extension == ".docx":
            with ZipFile(BytesIO(data)) as archive:
                document_xml = archive.read("word/document.xml")
            root = ElementTree.fromstring(document_xml)
            namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for paragraph in root.findall(".//w:p", namespace):
                value = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
                if value.strip():
                    paragraphs.append(value)
            text = "\n".join(paragraphs)
        else:
            text = data.decode("utf-8-sig")
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError("The file could not be read. Use a valid PDF, DOCX, TXT, or Markdown document.") from exc

    text = text.replace("\x00", "").strip()
    if not text:
        raise DocumentError("The document contains no readable text.")
    if len(text) > MAX_EXTRACTED_CHARS:
        text = text[:MAX_EXTRACTED_CHARS]
    return text


def select_relevant_text(document: str, query: str, max_chars: int = 12_000) -> str:
    """Rank overlapping chunks and return them in source order within a prompt budget."""
    chunks = [document[i:i + 1800] for i in range(0, len(document), 1600)]
    terms = set(re.findall(r"[a-z0-9]{3,}", query.lower()))
    ranked = []
    for index, chunk in enumerate(chunks):
        words = set(re.findall(r"[a-z0-9]{3,}", chunk.lower()))
        score = len(terms & words) / max(1, len(terms))
        ranked.append((score, index, chunk))
    ranked.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    chosen, used = [], 0
    for _, index, chunk in ranked:
        if used + len(chunk) > max_chars:
            continue
        chosen.append((index, chunk))
        used += len(chunk)
    return "\n\n".join(f"[Document section {index + 1}]\n{chunk}" for index, chunk in sorted(chosen))
