"""OpenRouter adapter restricted to explicitly free model endpoints."""

import json
import time
from typing import AsyncGenerator, Optional

import httpx

from app.adapters.base import AIModelAdapter, GenerateRequest, GenerateResponse, ModelInfo
from app.core.config import settings


OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

# These model IDs explicitly end in :free. Never substitute a paid model ID here.
FREE_MODELS: list[dict] = [
    {
        "id": "nvidia/nemotron-3.5-lightning:free",
        "display_name": "Nemotron 3.5 Lightning (Free)",
        "capabilities": ["general", "reasoning", "coding"],
        "supports_reasoning": True,
        "supports_coding": True,
        "priority": 1,
        "max_tokens": 4096,
    },
    {
        "id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "display_name": "Nemotron 3 Ultra (Free)",
        "capabilities": ["general", "reasoning", "coding"],
        "supports_reasoning": True,
        "supports_coding": True,
        "priority": 2,
        "max_tokens": 4096,
    },
    {
        "id": "nvidia/nemotron-3.5-super-vl:free",
        "display_name": "Nemotron 3.5 Super VL (Free)",
        "capabilities": ["general", "reasoning"],
        "supports_vision": True,
        "supports_reasoning": True,
        "priority": 3,
        "max_tokens": 4096,
    },
    {
        "id": "poolside/laguna-s-2.1:free",
        "display_name": "Laguna S 2.1 (Free backup)",
        "capabilities": ["general", "coding"],
        "supports_coding": True,
        "priority": 4,
        "max_tokens": 4096,
    },
]


class OpenRouterAdapter(AIModelAdapter):
    """OpenAI-compatible adapter with a hard allowlist of no-token-cost models."""

    def __init__(self):
        self._models = {
            item["id"]: ModelInfo(
                id=item["id"],
                display_name=item["display_name"],
                provider="openrouter",
                capabilities=item.get("capabilities", ["general"]),
                supports_vision=item.get("supports_vision", False),
                supports_reasoning=item.get("supports_reasoning", False),
                supports_coding=item.get("supports_coding", False),
                supports_streaming=True,
                enabled=True,
                priority=item["priority"],
                max_tokens=item["max_tokens"],
            )
            for item in FREE_MODELS
        }

    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        if not settings.is_openrouter_configured:
            return None
        return self._models.get(model_id)

    async def list_models(self) -> list[ModelInfo]:
        if not settings.is_openrouter_configured:
            return []
        return list(self._models.values())

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "Goldmine AI",
        }

    def _payload(self, request: GenerateRequest, stream: bool) -> dict:
        if request.model_id not in self._models:
            raise RuntimeError("Model is not in the free-model allowlist")
        messages = []
        for message in request.messages:
            images = message.get("image_urls") or []
            if images:
                content = [{"type": "text", "text": str(message.get("content", ""))}]
                content.extend(
                    {"type": "image_url", "image_url": {"url": image_url}}
                    for image_url in images
                )
                messages.append({**message, "content": content})
            else:
                messages.append(message)
        return {
            "model": request.model_id,
            "messages": messages,
            "max_tokens": min(request.max_tokens, self._models[request.model_id].max_tokens),
            "temperature": request.temperature,
            "stream": stream,
        }

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        if not settings.is_openrouter_configured:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OPENROUTER_API_BASE}/chat/completions",
                headers=self._headers(),
                json=self._payload(request, stream=False),
            )
        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter request failed with HTTP {response.status_code}")
        data = response.json()
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenRouter returned an empty response")
        return GenerateResponse(
            content=content,
            model_id=request.model_id,
            provider="openrouter",
            latency_ms=int((time.monotonic() - start) * 1000),
            finish_reason=choice.get("finish_reason"),
            usage=data.get("usage"),
        )

    async def stream(self, request: GenerateRequest) -> AsyncGenerator[str, None]:
        if not settings.is_openrouter_configured:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{OPENROUTER_API_BASE}/chat/completions",
                headers=self._headers(),
                json=self._payload(request, stream=True),
            ) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"OpenRouter stream failed with HTTP {response.status_code}")
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        event = json.loads(raw)
                        content = event.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    except (json.JSONDecodeError, IndexError, AttributeError):
                        continue
                    if isinstance(content, str) and content:
                        yield content

    async def supports_capability(self, model_id: str, capability: str) -> bool:
        model = self._models.get(model_id)
        return bool(model and capability in model.capabilities)

    async def is_available(self, model_id: str) -> bool:
        return bool(settings.is_openrouter_configured and model_id in self._models)


openrouter_adapter = OpenRouterAdapter()
