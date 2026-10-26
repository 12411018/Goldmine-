"""
Goldmine AI — Supabase Client

Server-side Supabase client using the service role key.
"""

from supabase import create_client, Client
from app.core.config import settings
from typing import Optional

_supabase_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Get or create the Supabase client. Returns None if not configured."""
    global _supabase_client

    if not settings.is_supabase_configured:
        return None

    if _supabase_client is None:
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )

    return _supabase_client
