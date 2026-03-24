"""FastAPI authentication dependencies.

Two auth strategies are supported, tried in order:
  1. Bearer JWT  — Authorization: Bearer <token>
  2. DB API key  — x-api-key: map_<...>

Both resolve to a User ORM object, preserving full context (tenant, role).
"""

from dataclasses import dataclass
from datetime import datetime

import jwt as pyjwt
from fastapi import Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import TokenClaims, decode_token, is_revoked
from app.cache.client import get_redis
from app.db.models import User
from app.db.session import get_db
from app.tenants.service import verify_api_key


@dataclass(frozen=True)
class AuthContext:
    """Carries the authenticated user and, when JWT was used, the jti + exp
    (needed by the logout endpoint to blacklist the token with the correct TTL)."""

    user: User
    jti: str | None = None       # None when authenticated via API key
    token_exp: datetime | None = None  # token expiry, set only for JWT auth


async def get_auth_context(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="x-api-key"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AuthContext:
    """Resolve either a Bearer JWT or an API key to an AuthContext."""

    # ── Strategy 1: Bearer JWT ────────────────────────────────────────────────
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
        try:
            claims: TokenClaims = decode_token(token)
        except pyjwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired.",
            )
        except pyjwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token.",
            )

        if await is_revoked(redis, claims.jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked.",
            )

        user = await db.scalar(
            select(User).where(User.id == claims.user_id, User.is_active == True)  # noqa: E712
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deactivated.",
            )
        return AuthContext(user=user, jti=claims.jti, token_exp=claims.exp)

    # ── Strategy 2: DB-backed API key ────────────────────────────────────────
    if x_api_key:
        user = await verify_api_key(db, x_api_key)
        if user:
            return AuthContext(user=user, jti=None)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide 'Authorization: Bearer <token>' or 'x-api-key'.",
    )


async def get_current_user(
    auth: AuthContext = Depends(get_auth_context),
) -> User:
    """Return only the authenticated User (for routes that don't need jti)."""
    return auth.user


async def get_tenant_id(
    auth: AuthContext = Depends(get_auth_context),
) -> str:
    """Backward-compatible dependency — returns tenant_id from auth context.

    All existing routes use this; Phase 4 will replace it with get_current_user.
    """
    return auth.user.tenant_id
