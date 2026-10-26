"""Private uploads for chat documents and vision-model images."""

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.prisma import prisma
from app.db.supabase import get_supabase
from app.services.document_service import (
    DocumentError,
    MAX_UPLOAD_BYTES,
    extract_text,
    sanitize_filename,
    SUPPORTED_IMAGE_TYPES,
    SUPPORTED_TYPES,
    validate_image,
)
from app.services.attachment_fallback import public_attachment, store_attachment, delete_pending_attachment

router = APIRouter()
BUCKET = "chat-attachments"


@router.post("")
async def upload_attachment(request: Request, file: UploadFile = File(...), user=Depends(get_current_user)):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    filename = sanitize_filename(file.filename or "upload")
    extension = Path(filename).suffix.lower()
    try:
        if extension in SUPPORTED_IMAGE_TYPES:
            mime_type = validate_image(filename, file.content_type or "application/octet-stream", data)
            text = None
        else:
            text = extract_text(filename, file.content_type or "application/octet-stream", data)
            mime_type = SUPPORTED_TYPES[extension]
    except (DocumentError, KeyError) as exc:
        detail = str(exc) if isinstance(exc, DocumentError) else "Unsupported file type. Use PDF, DOCX, TXT, Markdown, PNG, JPG, or WebP."
        raise HTTPException(status_code=422, detail=detail) from exc

    if not getattr(request.app.state, "database_ready", False):
        try:
            attachment = store_attachment(user["user_id"], filename, mime_type, data, text)
        except ValueError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        return {**public_attachment(attachment), "temporary": True}

    if not settings.is_supabase_configured:
        raise HTTPException(status_code=503, detail="Private file storage is not configured")

    storage = get_supabase()
    if storage is None:
        raise HTTPException(status_code=503, detail="Private file storage is not configured")
    path = f"{user['user_id']}/{uuid.uuid4()}/{filename}"
    try:
        await asyncio.to_thread(
            storage.storage.from_(BUCKET).upload,
            path,
            data,
            {"content-type": mime_type, "upsert": "false"},
        )
        attachment = await prisma.attachment.create(
            data={
                "user_id": user["user_id"],
                "storage_path": path,
                "file_name": filename,
                "mime_type": mime_type,
                "size_bytes": len(data),
                "extracted_text": text,
            }
        )
    except Exception as exc:
        try:
            await asyncio.to_thread(storage.storage.from_(BUCKET).remove, [path])
        except Exception:
            pass
        raise HTTPException(status_code=502, detail="The document could not be saved to private storage") from exc

    return {
        "id": str(attachment.id),
        "file_name": attachment.file_name,
        "mime_type": attachment.mime_type,
        "size_bytes": attachment.size_bytes,
    }


@router.delete("/{attachment_id}")
async def delete_attachment(attachment_id: str, request: Request, user=Depends(get_current_user)):
    if not getattr(request.app.state, "database_ready", False):
        if not delete_pending_attachment(user["user_id"], attachment_id):
            raise HTTPException(status_code=404, detail="Pending upload not found")
        return {"status": "deleted", "temporary": True}
    attachment = await prisma.attachment.find_first(
        where={"id": attachment_id, "user_id": user["user_id"]},
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if attachment.message_id:
        raise HTTPException(status_code=409, detail="Attachments can only be removed before they are sent")

    storage = get_supabase()
    if storage is None:
        raise HTTPException(status_code=503, detail="Private file storage is not configured")
    try:
        await asyncio.to_thread(storage.storage.from_(BUCKET).remove, [attachment.storage_path])
        await prisma.attachment.delete(where={"id": attachment_id})
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The attachment could not be removed") from exc
    return {"status": "deleted"}
