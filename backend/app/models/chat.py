"""
Goldmine AI — Pydantic Models for Chat
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional
from uuid import UUID
from datetime import datetime


# === Request Models ===

class ChatModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class ChatCreateRequest(ChatModel):
    title: Optional[str] = "New Chat"


class ChatUpdateRequest(ChatModel):
    title: Optional[str] = Field(None, min_length=1, max_length=120)


class MessageCreateRequest(ChatModel):
    content: str = Field(..., min_length=1, max_length=32000)
    chat_id: Optional[str] = None
    image_urls: Optional[list[str]] = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=8)
    model_id: Optional[str] = None  # None = AUTO mode
    mode: str = Field(default="goldmine", pattern="^(goldmine|single)$")
    experience_mode: Literal["normal", "study", "research"] = "normal"
    web_research: bool = False
    request_id: Optional[UUID] = None


class StreamChatRequest(ChatModel):
    content: str = Field(..., min_length=1, max_length=32000)
    chat_id: Optional[str] = None
    image_urls: Optional[list[str]] = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=8)
    model_id: Optional[str] = None
    mode: str = Field(default="goldmine", pattern="^(goldmine|single)$")
    experience_mode: Literal["normal", "study", "research"] = "normal"
    web_research: bool = False
    request_id: Optional[UUID] = None


# === Response Models ===

class ChatResponse(ChatModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(ChatModel):
    id: str
    chat_id: str
    user_id: str
    role: str
    content: str
    image_urls: Optional[list[str]] = None
    created_at: str


class EvaluationSignals(ChatModel):
    cross_model_agreement: Optional[float] = None
    evidence_support: Optional[float] = None
    completeness: Optional[float] = None
    relevance: Optional[float] = None
    consistency: Optional[float] = None


class ModelResponseData(ChatModel):
    id: str
    message_id: str
    model_id: str
    provider: str
    content: str
    goldmine_score: Optional[float] = None
    evaluation_signals: Optional[EvaluationSignals] = None
    selected: bool = False
    latency_ms: Optional[int] = None
    web_verified: bool = False
    response_type: str = "model"
    selection_explanation: Optional[str] = None
    created_at: str


class AttachmentData(ChatModel):
    id: str
    file_name: str
    mime_type: str
    size_bytes: int


class SourceData(ChatModel):
    id: str
    message_id: str
    title: str
    url: str
    domain: str
    relevance_score: Optional[float] = None
    support_type: str  # "supporting" | "contradicting" | "neutral"
    created_at: str


class GoldmineResult(ChatModel):
    """The full result returned after Goldmine evaluation."""
    chat_id: str
    message_id: str
    selected_response: ModelResponseData
    all_responses: list[ModelResponseData]
    sources: list[SourceData] = []
    goldmine_score: float
    selection_explanation: str
    web_verified: bool = False
    synthesis_model_id: Optional[str] = None
    synthesis_status: str = "not_requested"
    provider_failures: list[dict] = Field(default_factory=list)
