"""User-controlled Goldmine personalization settings."""

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
import logging

from app.api.deps import get_current_user
from app.db.prisma import prisma
from app.services.personalization_service import cache_preference, get_cached_preference

logger = logging.getLogger(__name__)
router = APIRouter()
PREFERENCE_CATEGORY = "goldmine_personalization"


class PreferencesUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    tone: Literal["friendly", "professional", "balanced"] = "friendly"


def _memory_content(display_name: str, tone: str) -> str:
    return f"The user's preferred name is {display_name}. Preferred assistant tone: {tone}."


@router.get("")
async def get_preferences(request: Request, user=Depends(get_current_user)):
    user_id = user["user_id"]
    cached = get_cached_preference(user_id)
    if not getattr(request.app.state, "database_ready", False):
        if cached:
            return {**cached, "temporary": True}
        return {"display_name": user.get("email", "").split("@")[0] or "User", "tone": "friendly", "temporary": True}
    try:
        profile = await prisma.profile.find_unique(where={"id": user_id})
        preference = await prisma.memory.find_first(
            where={"user_id": user_id, "category": PREFERENCE_CATEGORY},
            order={"updated_at": "desc"},
        )
        tone = "friendly"
        if preference and "tone:" in preference.content.lower():
            value = preference.content.lower().split("tone:", 1)[1].strip().rstrip(".")
            if value in {"friendly", "professional", "balanced"}:
                tone = value
        display_name = profile.display_name if profile and profile.display_name else (user.get("email", "").split("@")[0] or "User")
        return {"display_name": display_name, "tone": tone, "temporary": False}
    except Exception as exc:
        logger.warning("Preference read deferred while database is unavailable (%s)", type(exc).__name__)
        if cached:
            return {**cached, "temporary": True}
        return {"display_name": user.get("email", "").split("@")[0] or "User", "tone": "friendly", "temporary": True}


@router.patch("")
async def update_preferences(body: PreferencesUpdate, request: Request, user=Depends(get_current_user)):
    name = body.display_name.strip()
    user_id = user["user_id"]
    cache_preference(user_id, name, body.tone)
    if not getattr(request.app.state, "database_ready", False):
        return {"display_name": name, "tone": body.tone, "temporary": True}
    try:
        await prisma.profile.update(where={"id": user_id}, data={"display_name": name})
        data = {"content": _memory_content(name, body.tone), "importance": 10, "enabled": True, "source": "user"}
        existing = await prisma.memory.find_first(
            where={"user_id": user_id, "category": PREFERENCE_CATEGORY},
            order={"updated_at": "desc"},
        )
        if existing:
            await prisma.memory.update(where={"id": str(existing.id)}, data=data)
        else:
            await prisma.memory.create(data={"user_id": user_id, "category": PREFERENCE_CATEGORY, **data})
        return {"display_name": name, "tone": body.tone, "temporary": False}
    except Exception as exc:
        logger.warning("Preference save deferred while database is unavailable (%s)", type(exc).__name__)
        return {"display_name": name, "tone": body.tone, "temporary": True}
