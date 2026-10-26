"""
Goldmine AI — Pydantic Models for Memory
"""

from pydantic import BaseModel, Field
from typing import Optional


class MemoryCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    category: str = Field(default="general")
    importance: int = Field(default=5, ge=1, le=10)


class MemoryUpdateRequest(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=2000)
    category: Optional[str] = None
    importance: Optional[int] = Field(None, ge=1, le=10)
    enabled: Optional[bool] = None


class MemoryResponse(BaseModel):
    id: str
    user_id: str
    content: str
    category: str
    importance: int
    source: str
    enabled: bool
    created_at: str
    updated_at: str
