from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_tenant_id
from app.db.session import get_db
from app.tools import service
from app.tools.schemas import ToolCreate, ToolListResponse, ToolResponse, ToolUpdate

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    data: ToolCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ToolResponse:
    try:
        tool = await service.create_tool(db, tenant_id, data)
    except service.ToolNameConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ToolResponse.model_validate(tool)


@router.get("", response_model=ToolListResponse)
async def list_tools(
    agent_name: str | None = Query(None, description="Filter by agent name"),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ToolListResponse:
    tools = await service.list_tools(db, tenant_id, agent_name=agent_name)
    items = [ToolResponse.model_validate(t) for t in tools]
    return ToolListResponse(items=items, total=len(items))


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ToolResponse:
    try:
        tool = await service.get_tool(db, tenant_id, tool_id)
    except service.ToolNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ToolResponse.model_validate(tool)


@router.patch("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    data: ToolUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ToolResponse:
    try:
        tool = await service.update_tool(db, tenant_id, tool_id, data)
    except service.ToolNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except service.ToolNameConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return ToolResponse.model_validate(tool)


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await service.delete_tool(db, tenant_id, tool_id)
    except service.ToolNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
