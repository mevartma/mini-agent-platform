from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import service
from app.agents.schemas import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)
from app.auth.dependencies import get_tenant_id
from app.db.session import get_db

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentCreate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    try:
        agent = await service.create_agent(db, tenant_id, data)
    except service.AgentNameConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except service.ToolNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return AgentResponse.model_validate(agent)


@router.get("", response_model=AgentListResponse)
async def list_agents(
    tool_name: str | None = Query(None, description="Filter by tool name"),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AgentListResponse:
    agents = await service.list_agents(db, tenant_id, tool_name=tool_name)
    items = [AgentResponse.model_validate(a) for a in agents]
    return AgentListResponse(items=items, total=len(items))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    try:
        agent = await service.get_agent(db, tenant_id, agent_id)
    except service.AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    try:
        agent = await service.update_agent(db, tenant_id, agent_id, data)
    except service.AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except service.AgentNameConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except service.ToolNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await service.delete_agent(db, tenant_id, agent_id)
    except service.AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
