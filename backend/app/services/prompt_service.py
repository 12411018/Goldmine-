"""
Goldmine AI — Prompt Service

Provides context-aware prompt normalization and AI-powered prompt improvement.
"""

from typing import Optional
from app.adapters.base import GenerateRequest
from app.services.model_registry import model_registry


class PromptService:
    async def improve_prompt(self, user_prompt: str) -> str:
        """
        Use an available reasoning model to improve a user's prompt.
        """
        system_instruction = (
            "You are an expert prompt engineer. Your task is to rewrite the "
            "user's prompt to be more specific, clear, and structured for AI models. "
            "Keep the intent exactly the same, but improve the wording. "
            "Do NOT answer the prompt. ONLY output the improved prompt itself. "
            "Do NOT include conversational filler like 'Here is the improved prompt:'."
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ]

        # Pick best available reasoning model from model registry
        candidates = await model_registry.get_models_for_capability("reasoning")
        if not candidates:
            candidates = await model_registry.list_available_models()

        if not candidates:
            return user_prompt

        target_model = candidates[0]
        adapter = model_registry.get_adapter_for_model(target_model.id)

        try:
            request = GenerateRequest(
                messages=messages,
                model_id=target_model.id,
                max_tokens=1000,
                temperature=0.3,
            )

            response = await adapter.generate(request)
            return response.content.strip()

        except Exception as e:
            # Fallback to original if improvement fails
            print(f"Prompt improvement failed: {e}")
            return user_prompt


prompt_service = PromptService()
