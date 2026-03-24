import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Permission, require_permission
from app.db.models import User
from app.db.session import get_db
from app.runner import history_service
from app.runner.history_schemas import ExecutionListResponse
from app.runner.schemas import RunResponse

router = APIRouter(prefix="/agents", tags=["history"])


@router.get("/{agent_id}/executions", response_model=ExecutionListResponse)
async def list_executions(
    agent_id: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    user: User = Depends(require_permission(Permission.EXECUTIONS_READ)),
    db: AsyncSession = Depends(get_db),
) -> ExecutionListResponse:
    try:
        executions, total = await history_service.list_executions(
            db, user.tenant_id, agent_id, page, limit
        )
    except history_service.AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return ExecutionListResponse(
        items=[RunResponse.model_validate(e) for e in executions],
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total else 0,
    )
