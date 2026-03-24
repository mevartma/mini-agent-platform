"""Authentication routes — login and logout."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, get_auth_context
from app.auth.jwt import create_token, revoke_token
from app.cache.client import get_redis
from app.config import settings
from app.db.models import Tenant, User
from app.db.session import get_db
from app.tenants.service import _verify_secret

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    tenant_slug: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange email + password for a signed JWT."""

    # Resolve tenant
    tenant = await db.scalar(
        select(Tenant).where(Tenant.slug == data.tenant_slug, Tenant.is_active == True)  # noqa: E712
    )
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # Resolve user
    user = await db.scalar(
        select(User).where(
            User.tenant_id == tenant.id,
            User.email == data.email,
            User.is_active == True,  # noqa: E712
        )
    )
    if not user or not _verify_secret(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    token, _jti = create_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role.value,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    auth: AuthContext = Depends(get_auth_context),
    redis: Redis = Depends(get_redis),
) -> None:
    """Revoke the current JWT by blacklisting its jti in Redis.

    No-op when authenticated via API key (stateless — nothing to revoke).
    """
    if auth.jti is None or auth.token_exp is None:
        return  # API key auth — nothing to blacklist

    await revoke_token(redis, auth.jti, auth.token_exp)
