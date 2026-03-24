"""Tenant onboarding and API key management service."""

import secrets

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid
from app.db.models import ApiKey, Tenant, User, UserRole

# Key format: "map_<40 random url-safe chars>"
_KEY_PREFIX_LEN = 8
_KEY_BODY_LEN = 40


class TenantSlugConflictError(Exception):
    pass


class TenantNotFoundError(Exception):
    pass


class EmailConflictError(Exception):
    pass


class ApiKeyNotFoundError(Exception):
    pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_raw_key() -> str:
    """Return a cryptographically secure API key."""
    return "map_" + secrets.token_urlsafe(_KEY_BODY_LEN)


def _hash_secret(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def _verify_secret(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode(), hashed.encode())


# ── Tenant registration ───────────────────────────────────────────────────────

async def register_tenant(
    db: AsyncSession,
    name: str,
    slug: str,
    admin_email: str,
    admin_password: str,
) -> tuple[Tenant, User, ApiKey, str]:
    """Create a new tenant, admin user, and initial API key.

    Returns:
        (tenant, user, api_key_record, raw_key) — raw_key is returned once
        and never stored in plaintext.
    """
    # Check slug uniqueness
    if await db.scalar(select(Tenant).where(Tenant.slug == slug)):
        raise TenantSlugConflictError(f"Slug '{slug}' is already taken.")

    tenant = Tenant(id=new_uuid(), name=name, slug=slug)
    db.add(tenant)
    await db.flush()

    user = User(
        id=new_uuid(),
        tenant_id=tenant.id,
        email=admin_email,
        password_hash=_hash_secret(admin_password),
        role=UserRole.admin,
    )
    db.add(user)
    await db.flush()

    raw_key = _generate_raw_key()
    api_key = ApiKey(
        id=new_uuid(),
        tenant_id=tenant.id,
        user_id=user.id,
        key_prefix=raw_key[:_KEY_PREFIX_LEN],
        key_hash=_hash_secret(raw_key),
        label="Initial key",
    )
    db.add(api_key)
    await db.commit()

    await db.refresh(tenant)
    await db.refresh(user)
    await db.refresh(api_key)
    return tenant, user, api_key, raw_key


# ── API key management ────────────────────────────────────────────────────────

async def create_api_key(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    label: str,
) -> tuple[ApiKey, str]:
    """Generate a new API key for a tenant user.

    Returns:
        (api_key_record, raw_key)
    """
    raw_key = _generate_raw_key()
    api_key = ApiKey(
        id=new_uuid(),
        tenant_id=tenant_id,
        user_id=user_id,
        key_prefix=raw_key[:_KEY_PREFIX_LEN],
        key_hash=_hash_secret(raw_key),
        label=label,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, raw_key


async def list_api_keys(db: AsyncSession, tenant_id: str) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.tenant_id == tenant_id)
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_api_key(
    db: AsyncSession, tenant_id: str, key_id: str
) -> None:
    api_key = await db.scalar(
        select(ApiKey).where(
            ApiKey.tenant_id == tenant_id, ApiKey.id == key_id
        )
    )
    if not api_key:
        raise ApiKeyNotFoundError(f"API key '{key_id}' not found.")
    api_key.is_active = False
    await db.commit()


# ── Key verification (used by auth layer) ────────────────────────────────────

async def verify_api_key(
    db: AsyncSession, raw_key: str
) -> User | None:
    """Resolve a raw API key to its owner User, or return None if invalid.

    Strategy: match by key_prefix (first 8 chars) to narrow candidates,
    then bcrypt-verify each candidate hash.
    """
    prefix = raw_key[:_KEY_PREFIX_LEN]
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_prefix == prefix,
            ApiKey.is_active == True,  # noqa: E712
        )
    )
    candidates = list(result.scalars().all())

    for candidate in candidates:
        if _verify_secret(raw_key, candidate.key_hash):
            # Fetch the owning user
            user = await db.scalar(
                select(User).where(
                    User.id == candidate.user_id,
                    User.is_active == True,  # noqa: E712
                )
            )
            return user

    return None
