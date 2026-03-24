from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Permission, require_permission
from app.cache.client import get_redis
from app.db.models import User
from app.db.session import get_db
from app.tools import service
from app.tools.schemas import ToolCreate, ToolListResponse, ToolResponse, ToolUpdate

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    data: ToolCreate,
    user: User = Depends(require_permission(Permission.TOOLS_WRITE)),
    db: AsyncSession = Depends(get_db),
) -> ToolResponse:
    try:
        tool = await service.create_tool(db, user.tenant_id, data)
    except service.ToolNameConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ToolResponse.model_validate(tool)


@router.get("", response_model=ToolListResponse)
async def list_tools(
    agent_name: str | None = Query(None, description="Filter by agent name"),
    user: User = Depends(require_permission(Permission.TOOLS_READ)),
    db: AsyncSession = Depends(get_db),
) -> ToolListResponse:
    tools = await service.list_tools(db, user.tenant_id, agent_name=agent_name)
    items = [ToolResponse.model_validate(t) for t in tools]
    return ToolListResponse(items=items, total=len(items))


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    user: User = Depends(require_permission(Permission.TOOLS_READ)),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ToolResponse:
    try:
        tool = await service.get_tool(db, user.tenant_id, tool_id, redis=redis)
    except service.ToolNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ToolResponse.model_validate(tool)


@router.patch("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    data: ToolUpdate,
    user: User = Depends(require_permission(Permission.TOOLS_WRITE)),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ToolResponse:
    try:
        tool = await service.update_tool(db, user.tenant_id, tool_id, data, redis=redis)
    except service.ToolNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except service.ToolNameConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ToolResponse.model_validate(tool)


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: str,
    user: User = Depends(require_permission(Permission.TOOLS_WRITE)),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    try:
        await service.delete_tool(db, user.tenant_id, tool_id, redis=redis)
    except service.ToolNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
