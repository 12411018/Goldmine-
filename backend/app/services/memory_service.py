"""
Goldmine AI — Memory Service

Handles storage and retrieval of permanent memories using Supabase.
"""

from typing import Optional
from app.db.supabase import get_supabase
from app.models.memory import (
    MemoryCreateRequest,
    MemoryUpdateRequest,
    MemoryResponse,
)


class MemoryService:
    def __init__(self):
        self._supabase = get_supabase()

    async def get_memories(self, user_id: str, enabled_only: bool = True) -> list[MemoryResponse]:
        """Get all memories for a user."""
        if not self._supabase:
            return []

        query = self._supabase.table("memories").select("*").eq("user_id", user_id)
        if enabled_only:
            query = query.eq("enabled", True)

        response = query.order("importance", desc=True).execute()

        memories = []
        for row in response.data:
            memories.append(MemoryResponse(**row))

        return memories

    async def add_memory(self, user_id: str, memory_data: MemoryCreateRequest) -> MemoryResponse:
        """Add a new memory for a user."""
        if not self._supabase:
            raise RuntimeError("Database not configured")

        data = {
            "user_id": user_id,
            "content": memory_data.content,
            "category": memory_data.category,
            "importance": memory_data.importance,
            "source": "user",
        }

        response = self._supabase.table("memories").insert(data).execute()

        if not response.data:
            raise RuntimeError("Failed to insert memory")

        return MemoryResponse(**response.data[0])

    async def update_memory(
        self, user_id: str, memory_id: str, update_data: MemoryUpdateRequest
    ) -> Optional[MemoryResponse]:
        """Update an existing memory."""
        if not self._supabase:
            raise RuntimeError("Database not configured")

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return None

        # RLS will ensure user can only update their own memories
        response = (
            self._supabase.table("memories")
            .update(update_dict)
            .eq("id", memory_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not response.data:
            return None

        return MemoryResponse(**response.data[0])

    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete a memory."""
        if not self._supabase:
            raise RuntimeError("Database not configured")

        response = (
            self._supabase.table("memories")
            .delete()
            .eq("id", memory_id)
            .eq("user_id", user_id)
            .execute()
        )

        return len(response.data) > 0


# Singleton
memory_service = MemoryService()
