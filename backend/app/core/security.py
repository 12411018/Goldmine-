"""
Goldmine AI — Security

JWT verification for Supabase Auth tokens.
"""

from typing import Optional
import logging
from app.core.config import settings
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)

async def verify_supabase_token(token: str) -> Optional[dict]:
    """
    Verify a Supabase JWT token.
    Returns the decoded payload if valid, None otherwise.
    """
    if not settings.is_supabase_configured:
        return None

    try:
        client = get_supabase()
        if not client:
            return None
        
        # Verify the token with Supabase directly
        response = client.auth.get_user(token)
        if response and response.user:
            return {
                "sub": response.user.id,
                "email": response.user.email
            }
        return None
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None

def get_user_id_from_token(payload: dict) -> Optional[str]:
    """Extract user ID from a decoded Supabase token payload."""
    return payload.get("sub")
