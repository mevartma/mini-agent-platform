"""JWT creation, decoding, and Redis-backed token blacklist."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from redis.asyncio import Redis

from app.config import settings

_ALGORITHM = "HS256"
_BLACKLIST_PREFIX = "jwt:blacklist:"


@dataclass(frozen=True)
class TokenClaims:
    user_id: str
    tenant_id: str
    role: str
    jti: str
    exp: datetime


def create_token(user_id: str, tenant_id: str, role: str) -> tuple[str, str]:
    """Sign and return a JWT plus its jti.

    Returns:
        (encoded_token, jti)
    """
    jti = str(uuid.uuid4())
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "jti": jti,
        "exp": exp,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)
    return token, jti


def decode_token(token: str) -> TokenClaims:
    """Decode and validate a JWT.

    Raises:
        jwt.ExpiredSignatureError: if the token has expired.
        jwt.InvalidTokenError: for any other validation failure.
    """
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    return TokenClaims(
        user_id=payload["sub"],
        tenant_id=payload["tenant_id"],
        role=payload["role"],
        jti=payload["jti"],
        exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )


async def revoke_token(redis: Redis, jti: str, exp: datetime) -> None:
    """Store the jti in Redis until it naturally expires."""
    ttl = int((exp - datetime.now(timezone.utc)).total_seconds())
    if ttl > 0:
        await redis.setex(f"{_BLACKLIST_PREFIX}{jti}", ttl, "1")


async def is_revoked(redis: Redis, jti: str) -> bool:
    return bool(await redis.exists(f"{_BLACKLIST_PREFIX}{jti}"))
