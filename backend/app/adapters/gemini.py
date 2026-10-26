"""
Goldmine AI — Google Gemini Adapter

Implements the AIModelAdapter interface for Google Gemini models using the
v1beta REST API with native support for Gemini 3.8 Flash, 3.5 Flash, and 3.1 Flash Lite.
"""

import time
import json
import httpx
from typing import AsyncGenerator, Optional, List, Dict, Any

from app.adapters.base import AIModelAdapter, ModelInfo, GenerateRequest, GenerateResponse
from app.core.config import settings


DEFAULT_GEMINI_MODELS: List[Dict[str, Any]] = [
    {
        "id": "gemini-3.8-flash",
        "display_name": "Gemini 3.8 Flash",
        "provider": "google",
        "capabilities": ["reasoning", "coding", "general"],
        "supports_vision": False,
        "supports_reasoning": True,
        "supports_coding": True,
        "supports_streaming": True,
        "enabled": True,
        "priority": 1,
        "max_tokens": 8192,
    },
    {
        "id": "gemini-3.6-flash",
        "display_name": "Gemini 3.6 Flash",
        "provider": "google",
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
        "id": "gemini-3.1-flash-lite",
        "display_name": "Gemini 3.1 Flash Lite",
        "provider": "google",
        "capabilities": ["general", "coding"],
        "supports_vision": False,
        "supports_reasoning": False,
        "supports_coding": True,
        "supports_streaming": True,
        "enabled": True,
        "priority": 3,
        "max_tokens": 4096,
    },
]

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiAdapter(AIModelAdapter):
    def __init__(self):
        self._models: Dict[str, ModelInfo] = {}
        for m in DEFAULT_GEMINI_MODELS:
            model_info = ModelInfo(**m)
            self._models[model_info.id] = model_info

    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        if not settings.is_gemini_configured:
            return None
        model = self._models.get(model_id)
        return model if model and model.enabled else None

    async def list_models(self) -> List[ModelInfo]:
        if not settings.is_gemini_configured:
            return []
        return sorted([m for m in self._models.values() if m.enabled], key=lambda m: m.priority)

    async def supports_capability(self, model_id: str, capability: str) -> bool:
        model = await self.get_model_info(model_id)
        return bool(model and capability in model.capabilities)

    async def is_available(self, model_id: str) -> bool:
        return bool(settings.is_gemini_configured and model_id in self._models)

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> tuple[Optional[Dict], List[Dict]]:
        """Converts OpenAI-formatted messages to Gemini payload format."""
        system_instruction = None
        contents: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_instruction = {"parts": [{"text": str(content)}]}
            else:
                gemini_role = "model" if role == "assistant" else "user"
                parts = [{"text": str(content)}]
                
                # Check for image_urls if present
                if "image_urls" in msg and msg["image_urls"]:
                    for url in msg["image_urls"]:
                        parts.append({"image_url": url})

                # Merge consecutive identical roles if necessary
                if contents and contents[-1]["role"] == gemini_role:
                    contents[-1]["parts"].extend(parts)
                else:
                    contents.append({"role": gemini_role, "parts": parts})

        # Ensure at least one content part exists
        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

        return system_instruction, contents

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate full response from Gemini."""
        if not settings.is_gemini_configured:
            raise RuntimeError("GOOGLE_API_KEY is not configured")

        start_time = time.time()
        system_instruction, contents = self._convert_messages(request.messages)

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens or 4096,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        model_id = request.model_id
        url = f"{GEMINI_BASE_URL}/{model_id}:generateContent"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": settings.google_api_key},
                json=payload,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                raise RuntimeError(
                    f"Gemini API error ({response.status_code}): {response.text[:400]}"
                )

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("No candidate response returned from Gemini")

            first_candidate = candidates[0]
            parts = first_candidate.get("content", {}).get("parts", [])
            content_text = "".join(part.get("text", "") for part in parts)
            finish_reason = first_candidate.get("finishReason")
            usage = data.get("usageMetadata")

            return GenerateResponse(
                content=content_text,
                model_id=model_id,
                provider="google",
                latency_ms=latency_ms,
                finish_reason=finish_reason,
                usage=usage,
            )

    async def stream(self, request: GenerateRequest) -> AsyncGenerator[str, None]:
        """Stream response chunks from Gemini via SSE."""
        if not settings.is_gemini_configured:
            raise RuntimeError("GOOGLE_API_KEY is not configured")

        system_instruction, contents = self._convert_messages(request.messages)
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens or 4096,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        model_id = request.model_id
        url = f"{GEMINI_BASE_URL}/{model_id}:streamGenerateContent?alt=sse"

        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST",
                url,
                headers={"x-goog-api-key": settings.google_api_key},
                json=payload,
            ) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    raise RuntimeError(f"Gemini stream error ({response.status_code}): {err_body[:300]}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if not data_str:
                            continue
                        try:
                            chunk_data = json.loads(data_str)
                            candidates = chunk_data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    text = part.get("text", "")
                                    if text:
                                        yield text
                        except Exception:
                            continue


gemini_adapter = GeminiAdapter()
