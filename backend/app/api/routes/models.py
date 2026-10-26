"""
Goldmine AI — Models API Routes

Lists available AI models from the registry.
"""

from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.services.model_registry import model_registry

router = APIRouter()


@router.get("")
async def list_models(user=Depends(get_current_user)):
    """List all available models."""
    models = await model_registry.list_available_models()
    return [
        {
            "id": m.id,
            "display_name": m.display_name,
            "provider": m.provider,
            "capabilities": m.capabilities,
            "supports_vision": m.supports_vision,
            "supports_reasoning": m.supports_reasoning,
            "supports_coding": m.supports_coding,
            "supports_streaming": m.supports_streaming,
            "enabled": m.enabled,
        }
        for m in models
    ]
