"""Role-Based Access Control — permissions and route guard dependency."""

import enum

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User, UserRole
from app.db.session import get_db, set_tenant


class Permission(str, enum.Enum):
    TOOLS_READ = "tools:read"
    TOOLS_WRITE = "tools:write"
    AGENTS_READ = "agents:read"
    AGENTS_WRITE = "agents:write"
    EXECUTIONS_RUN = "executions:run"
    EXECUTIONS_READ = "executions:read"
    API_KEYS_MANAGE = "api_keys:manage"


# Every permission granted to each role (additive, least-privilege).
ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.viewer: frozenset(
        [
            Permission.TOOLS_READ,
            Permission.AGENTS_READ,
            Permission.EXECUTIONS_READ,
        ]
    ),
    UserRole.operator: frozenset(
        [
            Permission.TOOLS_READ,
            Permission.TOOLS_WRITE,
            Permission.AGENTS_READ,
            Permission.AGENTS_WRITE,
            Permission.EXECUTIONS_RUN,
            Permission.EXECUTIONS_READ,
        ]
    ),
    UserRole.admin: frozenset(Permission),  # all permissions
}


def require_permission(permission: Permission):
    """FastAPI dependency factory — checks RBAC and configures RLS.

    Returns the authenticated User if the role has the required permission.
    Also sets the PostgreSQL session variable app.current_tenant_id so that
    RLS policies are enforced for the rest of the request.

    Because FastAPI deduplicates Depends(get_db) within a request, the same
    AsyncSession instance used here is the same one injected into the route
    handler — so the tenant context is already set when the handler runs.

    Usage:
        user: User = Depends(require_permission(Permission.AGENTS_WRITE))
    """

    async def _guard(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if permission not in ROLE_PERMISSIONS.get(user.role, frozenset()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' does not have permission '{permission}'.",
            )
        await set_tenant(db, user.tenant_id)
        return user

    # Give the inner function a unique name so FastAPI can distinguish
    # multiple require_permission() guards on the same endpoint.
    _guard.__name__ = f"require_{permission.value.replace(':', '_')}"
    return _guard
