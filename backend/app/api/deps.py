"""
Goldmine AI — API Dependencies

FastAPI dependency injection for authentication and database access.
"""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.security import verify_supabase_token, get_user_id_from_token
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate the Supabase JWT and return the user payload.
    Never trusts user_id from frontend — always extracts from verified token.
    """
    token = credentials.credentials
    payload = await verify_supabase_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = get_user_id_from_token(payload)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not extract user identity",
        )

    # Ensure profile exists in the DB (acts as the trigger fallback)
    from app.db.prisma import prisma
    email = payload.get("email", "")
    try:
        await prisma.profile.upsert(
            where={"id": user_id},
            data={
                "create": {
                    "id": user_id,
                    "email": email,
                    "display_name": email.split("@")[0] if email else "User",
                },
                "update": {"email": email},
            },
        )
    except Exception as exc:
        # Authentication is handled by Supabase HTTPS. Do not make a temporary
        # direct-Postgres outage prevent an authenticated user from using the
        # in-memory chat fallback.
        logger.warning("Profile sync deferred (%s)", type(exc).__name__)

    return {"user_id": user_id, "email": email, "payload": payload}


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[dict]:
    """Optional auth — returns None if no valid token provided."""
    if credentials is None:
        return None
    try:
        payload = await verify_supabase_token(credentials.credentials)
        if payload:
            return {
                "user_id": get_user_id_from_token(payload),
                "email": payload.get("email"),
                "payload": payload,
            }
    except Exception:
        pass
    return None


def get_db():
    """Get the Supabase client, raising if not configured."""
    client = get_supabase()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    return client
