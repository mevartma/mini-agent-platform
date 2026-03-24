"""Tool CRUD service — all operations are scoped to a tenant_id."""

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import tool_key
from app.cache.ops import get_cached, invalidate, set_cached
from app.db.base import new_uuid
from app.db.models import Agent, AgentTool, Tool
from app.tools.schemas import ToolCreate, ToolResponse, ToolUpdate


class ToolNotFoundError(Exception):
    pass


class ToolNameConflictError(Exception):
    pass


async def create_tool(
    db: AsyncSession, tenant_id: str, data: ToolCreate
) -> Tool:
    existing = await db.scalar(
        select(Tool).where(Tool.tenant_id == tenant_id, Tool.name == data.name)
    )
    if existing:
        raise ToolNameConflictError(f"Tool '{data.name}' already exists.")

    tool = Tool(id=new_uuid(), tenant_id=tenant_id, **data.model_dump())
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return tool


async def list_tools(
    db: AsyncSession,
    tenant_id: str,
    agent_name: str | None = None,
) -> list[Tool]:
    query = select(Tool).where(Tool.tenant_id == tenant_id)

    if agent_name:
        query = (
            query.join(AgentTool, AgentTool.tool_id == Tool.id)
            .join(Agent, Agent.id == AgentTool.agent_id)
            .where(Agent.tenant_id == tenant_id, Agent.name == agent_name)
        )

    result = await db.execute(query.order_by(Tool.name))
    return list(result.scalars().all())


async def get_tool(
    db: AsyncSession,
    tenant_id: str,
    tool_id: str,
    redis: Redis | None = None,
) -> Tool | dict:
    if redis is not None:
        cached = await get_cached(redis, tool_key(tenant_id, tool_id))
        if cached is not None:
            return cached
    tool = await db.scalar(
        select(Tool).where(Tool.tenant_id == tenant_id, Tool.id == tool_id)
    )
    if not tool:
        raise ToolNotFoundError(f"Tool '{tool_id}' not found.")
    if redis is not None:
        data = ToolResponse.model_validate(tool).model_dump(mode="json")
        await set_cached(redis, tool_key(tenant_id, tool_id), data)
    return tool


async def update_tool(
    db: AsyncSession,
    tenant_id: str,
    tool_id: str,
    data: ToolUpdate,
    redis: Redis | None = None,
) -> Tool:
    tool = await get_tool(db, tenant_id, tool_id)

    updates = data.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] != tool.name:
        conflict = await db.scalar(
            select(Tool).where(
                Tool.tenant_id == tenant_id, Tool.name == updates["name"]
            )
        )
        if conflict:
            raise ToolNameConflictError(f"Tool '{updates['name']}' already exists.")

    for field, value in updates.items():
        setattr(tool, field, value)

    await db.commit()
    await db.refresh(tool)
    if redis is not None:
        await invalidate(redis, tool_key(tenant_id, tool_id))
    return tool


async def delete_tool(
    db: AsyncSession,
    tenant_id: str,
    tool_id: str,
    redis: Redis | None = None,
) -> None:
    tool = await get_tool(db, tenant_id, tool_id)
    await db.delete(tool)
    await db.commit()
    if redis is not None:
        await invalidate(redis, tool_key(tenant_id, tool_id))
