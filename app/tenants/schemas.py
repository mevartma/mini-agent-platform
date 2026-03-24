from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.db.models import UserRole


class TenantRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime


class TenantRegisterResponse(BaseModel):
    tenant: TenantResponse
    user: UserResponse
    api_key: str = Field(..., description="Raw API key — shown once, store it securely.")
    key_label: str


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key_prefix: str
    label: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime


class ApiKeyCreateResponse(BaseModel):
    api_key: str = Field(..., description="Raw API key — shown once, store it securely.")
    key: ApiKeyResponse
