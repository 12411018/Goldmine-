"""
Goldmine AI — Abstract AI Model Adapter

Defines the interface that all AI provider adapters must implement.
This allows Goldmine to interact with any provider uniformly.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from pydantic import BaseModel, ConfigDict


class AdapterModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class ModelInfo(AdapterModel):
    """Information about a specific model."""
    id: str
    display_name: str
    provider: str
    capabilities: list[str] = []
    supports_vision: bool = False
    supports_reasoning: bool = False
    supports_coding: bool = False
    supports_streaming: bool = True
    enabled: bool = True
    priority: int = 0
    max_tokens: int = 4096


class GenerateRequest(AdapterModel):
    """Request to generate a response from a model."""
    messages: list[dict]  # OpenAI-format messages
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = False


class GenerateResponse(AdapterModel):
    """Response from a model generation."""
    content: str
    model_id: str
    provider: str
    latency_ms: int
    finish_reason: Optional[str] = None
    usage: Optional[dict] = None


class AIModelAdapter(ABC):
    """
    Abstract adapter interface for AI model providers.
    
    The Goldmine engine interacts with adapters, not directly with provider APIs.
    This allows new providers to be added without rewriting Goldmine.
    """

    @abstractmethod
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model."""
        pass

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """List all available models from this provider."""
        pass

    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate a complete response from the model."""
        pass

    @abstractmethod
    async def stream(self, request: GenerateRequest) -> AsyncGenerator[str, None]:
        """Stream a response from the model, yielding chunks of text."""
        pass

    @abstractmethod
    async def supports_capability(self, model_id: str, capability: str) -> bool:
        """Check if a model supports a specific capability."""
        pass

    @abstractmethod
    async def is_available(self, model_id: str) -> bool:
        """Check if a model is currently available and accessible."""
        pass
