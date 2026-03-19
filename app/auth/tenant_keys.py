"""Tenant API key registry.

Keys are loaded from the TENANT_KEYS environment variable (see .env.example).
Format: "api-key:tenant-id,api-key2:tenant-id2"

Hardcoded defaults are used when the env var is not set, making local
development possible without any configuration.
"""

from app.config import settings


def _load_keys(raw: str) -> dict[str, str]:
    """Parse "key:tenant,key2:tenant2" into {key: tenant_id}."""
    result: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        parts = pair.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid TENANT_KEYS entry: {pair!r}")
        api_key, tenant_id = parts[0].strip(), parts[1].strip()
        result[api_key] = tenant_id
    return result


# Resolved at import time — immutable for the lifetime of the process.
TENANT_KEY_MAP: dict[str, str] = _load_keys(settings.tenant_keys)


def resolve_tenant(api_key: str) -> str | None:
    """Return the tenant_id for the given API key, or None if invalid."""
    return TENANT_KEY_MAP.get(api_key)
