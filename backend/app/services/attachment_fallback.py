"""Short-lived process-local uploads while Postgres is unavailable."""

import uuid
from datetime import datetime, timezone


MAX_TEMP_ATTACHMENT_BYTES = 24 * 1024 * 1024
_attachments: dict[str, dict[str, dict]] = {}


def store_attachment(user_id: str, file_name: str, mime_type: str, data: bytes, extracted_text: str | None) -> dict:
    current_size = sum(
        len(item.get("data") or b"")
        for rows in _attachments.values()
        for item in rows.values()
    )
    if current_size + len(data) > MAX_TEMP_ATTACHMENT_BYTES:
        raise ValueError("Temporary uploads are full. Send or remove pending files before uploading more.")
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "file_name": file_name,
        "mime_type": mime_type,
        "size_bytes": len(data),
        "extracted_text": extracted_text,
        "data": data,
        "message_id": None,
        "created_at": now,
    }
    _attachments.setdefault(user_id, {})[item["id"]] = item
    return item


def get_pending_attachments(user_id: str, attachment_ids: list[str]) -> list[dict] | None:
    rows = _attachments.get(user_id, {})
    result = [rows.get(attachment_id) for attachment_id in attachment_ids]
    if any(item is None or item["message_id"] is not None for item in result):
        return None
    return result


def claim_attachments(user_id: str, attachment_ids: list[str], message_id: str) -> None:
    rows = _attachments.get(user_id, {})
    for attachment_id in attachment_ids:
        item = rows.get(attachment_id)
        if item:
            item["message_id"] = message_id
            item["data"] = b""


def delete_pending_attachment(user_id: str, attachment_id: str) -> bool:
    rows = _attachments.get(user_id, {})
    item = rows.get(attachment_id)
    if not item or item["message_id"] is not None:
        return False
    del rows[attachment_id]
    return True


def public_attachment(item: dict) -> dict:
    return {key: item[key] for key in ("id", "file_name", "mime_type", "size_bytes")}
