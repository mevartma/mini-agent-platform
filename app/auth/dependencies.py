"""FastAPI dependency for API key authentication."""

from fastapi import Header, HTTPException, status

from app.auth.tenant_keys import resolve_tenant


async def get_tenant_id(x_api_key: str = Header(..., alias="x-api-key")) -> str:
    """Resolve the x-api-key header to a tenant_id.

    Raises 401 if the key is missing or unrecognised.
    FastAPI automatically returns 422 if the header is entirely absent,
    so the Header(...) declaration covers that case.
    """
    tenant_id = resolve_tenant(x_api_key)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
    return tenant_id
