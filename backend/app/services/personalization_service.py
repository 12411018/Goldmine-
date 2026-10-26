"""Process-local personalization fallback for database outages."""

from typing import TypedDict


class Personalization(TypedDict):
    display_name: str
    tone: str


_preferences: dict[str, Personalization] = {}


def get_cached_preference(user_id: str) -> Personalization | None:
    return _preferences.get(user_id)


def cache_preference(user_id: str, display_name: str, tone: str) -> Personalization:
    preference: Personalization = {"display_name": display_name, "tone": tone}
    _preferences[user_id] = preference
    return preference
