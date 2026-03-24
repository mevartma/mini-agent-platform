"""Tenant onboarding and API key management routes.

POST   /tenants/register           — public
POST   /tenants/api-keys           — admin only
GET    /tenants/api-keys           — admin only
DELETE /tenants/api-keys/{key_id}  — admin only
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Permission, require_permission
from app.db.models import User
from app.db.session import get_db
from app.tenants import service
from app.tenants.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    TenantRegisterRequest,
    TenantRegisterResponse,
    TenantResponse,
    UserResponse,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post(
    "/register",
    response_model=TenantRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_tenant(
    data: TenantRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantRegisterResponse:
    """Register a new tenant with an initial admin user and API key.

    The raw API key is returned **once** — store it securely.
    """
    try:
        tenant, user, api_key, raw_key = await service.register_tenant(
            db,
            name=data.name,
            slug=data.slug,
            admin_email=data.admin_email,
            admin_password=data.admin_password,
        )
    except service.TenantSlugConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return TenantRegisterResponse(
        tenant=TenantResponse.model_validate(tenant),
        user=UserResponse.model_validate(user),
        api_key=raw_key,
        key_label=api_key.label,
    )


@router.post(
    "/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    data: ApiKeyCreateRequest,
    user: User = Depends(require_permission(Permission.API_KEYS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreateResponse:
    """Generate an additional API key for the current tenant. Admin only."""
    api_key, raw_key = await service.create_api_key(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        label=data.label,
    )
    return ApiKeyCreateResponse(
        api_key=raw_key,
        key=ApiKeyResponse.model_validate(api_key),
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: User = Depends(require_permission(Permission.API_KEYS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    """List all API keys for the current tenant. Admin only."""
    keys = await service.list_api_keys(db, user.tenant_id)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    user: User = Depends(require_permission(Permission.API_KEYS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke (deactivate) an API key. Admin only."""
    try:
        await service.revoke_api_key(db, user.tenant_id, key_id)
    except service.ApiKeyNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
