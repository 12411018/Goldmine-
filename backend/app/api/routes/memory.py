"""
Goldmine AI — Memory API Routes

CRUD operations for user-controlled permanent memory.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.deps import get_current_user
from app.db.prisma import prisma
from app.models.memory import MemoryCreateRequest, MemoryUpdateRequest
from app.services.memory_fallback import (
    create_memory as create_fallback_memory,
    delete_memory as delete_fallback_memory,
    list_memories as list_fallback_memories,
    update_memory as update_fallback_memory,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def list_memories(request: Request, user=Depends(get_current_user)):
    """List all memories for the current user."""
    user_id = user["user_id"]
    if not getattr(request.app.state, "database_ready", False):
        return list_fallback_memories(user_id)
    try:
        memories = await prisma.memory.find_many(
            where={"user_id": user_id},
            order={"importance": "desc"},
        )
    except Exception as exc:
        logger.warning("Memory read deferred while database is unavailable (%s)", type(exc).__name__)
        return list_fallback_memories(user_id)
    return [
        {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "content": m.content,
            "category": m.category or "general",
            "importance": m.importance or 5,
            "source": m.source or "user",
            "enabled": m.enabled if m.enabled is not None else True,
            "created_at": m.created_at.isoformat(),
            "updated_at": m.updated_at.isoformat(),
        }
        for m in memories
    ]


@router.post("")
async def create_memory(body: MemoryCreateRequest, request: Request, user=Depends(get_current_user)):
    """Add a new memory."""
    user_id = user["user_id"]
    if not getattr(request.app.state, "database_ready", False):
        return create_fallback_memory(user_id, body.content, body.category, body.importance)
    try:
        memory = await prisma.memory.create(
            data={
                "user_id": user_id,
                "content": body.content,
                "category": body.category,
                "importance": body.importance,
                "source": "user",
            }
        )
    except Exception as exc:
        logger.warning("Memory save deferred while database is unavailable (%s)", type(exc).__name__)
        return create_fallback_memory(user_id, body.content, body.category, body.importance)
    return {
        "id": str(memory.id),
        "user_id": str(memory.user_id),
        "content": memory.content,
        "category": memory.category,
        "importance": memory.importance,
        "source": memory.source,
        "enabled": memory.enabled,
        "created_at": memory.created_at.isoformat(),
        "updated_at": memory.updated_at.isoformat(),
    }


@router.patch("/{memory_id}")
async def update_memory(
    memory_id: str, body: MemoryUpdateRequest, request: Request, user=Depends(get_current_user)
):
    """Update a memory."""
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return {"status": "no changes"}
    user_id = user["user_id"]
    if not getattr(request.app.state, "database_ready", False):
        updated = update_fallback_memory(user_id, memory_id, update_data)
        if not updated:
            raise HTTPException(status_code=404, detail="Memory not found in temporary storage")
        return updated
    try:
        existing = await prisma.memory.find_first(
            where={"id": memory_id, "user_id": user_id},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Memory not found")
        memory = await prisma.memory.update(
            where={"id": memory_id},
            data=update_data,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Memory update deferred while database is unavailable (%s)", type(exc).__name__)
        updated = update_fallback_memory(user_id, memory_id, update_data)
        if not updated:
            raise HTTPException(status_code=404, detail="Memory not found") from exc
        return updated
    return {
        "id": str(memory.id),
        "content": memory.content,
        "category": memory.category,
        "importance": memory.importance,
        "enabled": memory.enabled,
        "updated_at": memory.updated_at.isoformat(),
    }


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, request: Request, user=Depends(get_current_user)):
    """Delete a memory."""
    user_id = user["user_id"]
    if not getattr(request.app.state, "database_ready", False):
        if not delete_fallback_memory(user_id, memory_id):
            raise HTTPException(status_code=404, detail="Memory not found in temporary storage")
        return {"status": "deleted", "temporary": True}
    try:
        existing = await prisma.memory.find_first(
            where={"id": memory_id, "user_id": user_id},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Memory not found")
        await prisma.memory.delete(where={"id": memory_id})
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Memory deletion deferred while database is unavailable (%s)", type(exc).__name__)
        if not delete_fallback_memory(user_id, memory_id):
            raise HTTPException(status_code=404, detail="Memory not found") from exc
    return {"status": "deleted"}
