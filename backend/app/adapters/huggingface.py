"""
Goldmine AI — Hugging Face Adapter

Implements the AIModelAdapter interface for Hugging Face Inference Providers.
Uses the OpenAI-compatible endpoint for chat completions.
"""

import time
import httpx
import json
from typing import AsyncGenerator, Optional

from app.adapters.base import AIModelAdapter, ModelInfo, GenerateRequest, GenerateResponse
from app.core.config import settings
from app.core.cache import cache


# Default model registry — configurable via environment or database
DEFAULT_MODELS: list[dict] = [
    {
        "id": "deepseek-ai/DeepSeek-R1-0528",
        "display_name": "DeepSeek R1",
        "provider": "huggingface",
        "capabilities": ["reasoning", "coding"],
        "supports_vision": False,
        "supports_reasoning": True,
        "supports_coding": True,
        "supports_streaming": True,
        "enabled": True,
        "priority": 1,
        "max_tokens": 8192,
    },
    {
        "id": "Qwen/Qwen3-235B-A22B",
        "display_name": "Qwen3 235B",
        "provider": "huggingface",
        "capabilities": ["reasoning", "coding", "general"],
        "supports_vision": False,
        "supports_reasoning": True,
        "supports_coding": True,
        "supports_streaming": True,
        "enabled": True,
        "priority": 2,
        "max_tokens": 8192,
    },
    {
        "id": "meta-llama/Llama-3.3-70B-Instruct",
        "display_name": "Llama 3.3 70B",
        "provider": "huggingface",
        "capabilities": ["general", "coding"],
        "supports_vision": False,
        "supports_reasoning": False,
        "supports_coding": True,
        "supports_streaming": True,
        "enabled": True,
        "priority": 3,
        "max_tokens": 4096,
    },
    {
        "id": "microsoft/phi-4",
        "display_name": "Phi-4",
        "provider": "huggingface",
        "capabilities": ["general", "reasoning"],
        "supports_vision": False,
        "supports_reasoning": True,
        "supports_coding": True,
        "supports_streaming": True,
        "enabled": True,
        "priority": 4,
        "max_tokens": 4096,
    },
    {
        "id": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "display_name": "Qwen2.5 Coder",
        "provider": "huggingface",
        "capabilities": ["coding"],
        "supports_vision": False,
        "supports_reasoning": False,
        "supports_coding": True,
        "supports_streaming": True,
        "enabled": True,
        "priority": 5,
        "max_tokens": 8192,
    },
    {
        "id": "Qwen/Qwen2.5-VL-72B-Instruct",
        "display_name": "Qwen2.5 VL",
        "provider": "huggingface",
        "capabilities": ["general"],
        "supports_vision": False,
        "supports_reasoning": False,
        "supports_coding": False,
        "supports_streaming": True,
        "enabled": True,
        "priority": 6,
        "max_tokens": 4096,
    },
]

# HF OpenAI-compatible base URL
HF_API_BASE = "https://router.huggingface.co/v1"


class HuggingFaceAdapter(AIModelAdapter):
    """
    Hugging Face adapter using the OpenAI-compatible chat/completions API.
    Supports multiple models through one authentication setup.
    """

    def __init__(self):
        self._models: dict[str, ModelInfo] = {}
        self._availability_cache: dict[str, bool] = {}
        self._load_models()

    def _load_models(self):
        """Load model registry from defaults. Can be extended to load from DB."""
        for model_data in DEFAULT_MODELS:
            model_info = ModelInfo(**model_data)
            self._models[model_info.id] = model_info

    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        if not settings.is_hf_configured:
            return None
        model = self._models.get(model_id)
        return model if model and model.enabled else None

    async def list_models(self) -> list[ModelInfo]:
        """List all registered models, checking availability."""
        if not settings.is_hf_configured:
            return []
        models = []
        for model in self._models.values():
            if model.enabled:
                models.append(model)
        return sorted(models, key=lambda m: m.priority)

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate a response using the HF OpenAI-compatible endpoint."""
        if not settings.is_hf_configured:
            raise RuntimeError("Hugging Face token is not configured")

        start_time = time.time()

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{HF_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.hf_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": request.model_id,
                    "messages": request.messages,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": False,
                },
            )

            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                error_text = response.text
                raise RuntimeError(
                    f"HF API error ({response.status_code}): {error_text[:500]}"
                )

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            finish_reason = data["choices"][0].get("finish_reason")
            usage = data.get("usage")

            return GenerateResponse(
                content=content,
                model_id=request.model_id,
                provider="huggingface",
                latency_ms=latency_ms,
                finish_reason=finish_reason,
                usage=usage,
            )

    async def stream(self, request: GenerateRequest) -> AsyncGenerator[str, None]:
        """Stream a response chunk by chunk using SSE."""
        if not settings.is_hf_configured:
            raise RuntimeError("Hugging Face token is not configured")

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{HF_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.hf_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": request.model_id,
                    "messages": request.messages,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": True,
                },
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(
                        f"HF API error ({response.status_code}): {error_text[:500]}"
                    )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def supports_capability(self, model_id: str, capability: str) -> bool:
        model = self._models.get(model_id)
        if model is None:
            return False
        return capability in model.capabilities

    async def is_available(self, model_id: str) -> bool:
        """
        Check model availability by making a lightweight API call.
        Caches results for 5 minutes to avoid excessive API calls.
        """
        cache_key = f"hf_available:{model_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        model = self._models.get(model_id)
        if model is None or not model.enabled:
            return False

        if not settings.is_hf_configured:
            return False

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{HF_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.hf_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 1,
                    },
                )
                available = response.status_code == 200
                cache.set(cache_key, available, ttl=300)
                return available
        except Exception:
            cache.set(cache_key, False, ttl=60)
            return False


# Singleton adapter instance
hf_adapter = HuggingFaceAdapter()
