"""Process-local saved memories used only while Postgres is unavailable."""

import uuid
from datetime import datetime, timezone


_memories: dict[str, dict[str, dict]] = {}


def list_memories(user_id: str, enabled_only: bool = False) -> list[dict]:
    rows = list(_memories.get(user_id, {}).values())
    if enabled_only:
        rows = [row for row in rows if row["enabled"]]
    return sorted(rows, key=lambda row: (-row["importance"], row["created_at"]))


def create_memory(user_id: str, content: str, category: str, importance: int) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "content": content,
        "category": category,
        "importance": importance,
        "source": "user",
        "enabled": True,
        "temporary": True,
        "created_at": now,
        "updated_at": now,
    }
    _memories.setdefault(user_id, {})[row["id"]] = row
    return row


def update_memory(user_id: str, memory_id: str, changes: dict) -> dict | None:
    row = _memories.get(user_id, {}).get(memory_id)
    if not row:
        return None
    row.update(changes)
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    return row


def delete_memory(user_id: str, memory_id: str) -> bool:
    return _memories.get(user_id, {}).pop(memory_id, None) is not None
