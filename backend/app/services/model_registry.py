"""
Goldmine AI — Model Registry Service

Manages the registry of available AI models across providers (Google Gemini, Hugging Face).
Provides model lookup, capability filtering, and intelligent routing.
"""

from typing import Optional, List
from app.adapters.base import ModelInfo
from app.adapters.huggingface import hf_adapter
from app.adapters.gemini import gemini_adapter
from app.adapters.openrouter import openrouter_adapter
from app.core.config import settings


class ModelRegistry:
    """
    Central model registry that aggregates models from all adapters.
    Supports multi-provider (Google Gemini, Hugging Face).
    """

    def __init__(self):
        self._adapters = {
            "openrouter": openrouter_adapter,
            "gemini": gemini_adapter,
            "huggingface": hf_adapter,
        }

    def _active_adapters(self):
        if settings.free_models_only:
            return {"openrouter": openrouter_adapter}
        return self._adapters

    async def list_available_models(self) -> List[ModelInfo]:
        """List all enabled models across all adapters."""
        all_models = []
        for adapter in self._active_adapters().values():
            try:
                models = await adapter.list_models()
                all_models.extend(models)
            except Exception:
                continue
        return sorted(all_models, key=lambda m: m.priority)

    async def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get info about a specific model."""
        for adapter in self._active_adapters().values():
            try:
                model = await adapter.get_model_info(model_id)
                if model:
                    return model
            except Exception:
                continue
        return None

    async def get_models_for_capability(self, capability: str) -> List[ModelInfo]:
        """Get all models that support a specific capability."""
        all_models = await self.list_available_models()
        return [m for m in all_models if capability in m.capabilities]

    async def get_vision_models(self) -> List[ModelInfo]:
        """Get all models that support vision/image input."""
        all_models = await self.list_available_models()
        return [m for m in all_models if m.supports_vision]

    async def select_models_for_prompt(
        self,
        has_image: bool = False,
        capability: Optional[str] = None,
        max_models: int = 3,
    ) -> List[ModelInfo]:
        """
        Automatically select the best models for a given prompt.
        Used in AUTO mode.
        """
        all_models = await self.list_available_models()

        if has_image:
            candidates = [m for m in all_models if m.supports_vision]
        elif capability:
            candidates = [m for m in all_models if capability in m.capabilities]
        else:
            candidates = all_models

        # Interleave providers so a single provider outage does not consume the
        # entire multi-model selection. Keep each provider's configured priority.
        provider_order = list(dict.fromkeys(model.provider for model in candidates))
        models_by_provider = {
            provider: [model for model in candidates if model.provider == provider]
            for provider in provider_order
        }
        diverse_candidates = []
        for index in range(max((len(items) for items in models_by_provider.values()), default=0)):
            for provider in provider_order:
                provider_models = models_by_provider[provider]
                if index < len(provider_models):
                    diverse_candidates.append(provider_models[index])
        return diverse_candidates[:max_models]

    def get_adapter_for_model(self, model_id: str):
        """Get the adapter instance for a given model."""
        if model_id in openrouter_adapter._models:
            return openrouter_adapter
        if settings.free_models_only:
            raise RuntimeError("Only allowlisted free models are enabled")
        if "gemini" in model_id.lower():
            return gemini_adapter
        return hf_adapter


# Singleton
model_registry = ModelRegistry()
