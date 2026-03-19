"""Agent CRUD service — all operations are scoped to a tenant_id."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import new_uuid
from app.db.models import Agent, AgentTool, Tool
from app.agents.schemas import AgentCreate, AgentUpdate


class AgentNotFoundError(Exception):
    pass


class AgentNameConflictError(Exception):
    pass


class ToolNotFoundError(Exception):
    pass


async def _resolve_tools(
    db: AsyncSession, tenant_id: str, tool_ids: list[str]
) -> list[Tool]:
    """Fetch tools by IDs, ensuring they belong to the tenant."""
    if not tool_ids:
        return []
    result = await db.execute(
        select(Tool).where(
            Tool.tenant_id == tenant_id,
            Tool.id.in_(tool_ids),
        )
    )
    tools = list(result.scalars().all())
    found_ids = {t.id for t in tools}
    missing = set(tool_ids) - found_ids
    if missing:
        raise ToolNotFoundError(f"Tools not found: {', '.join(sorted(missing))}")
    return tools


async def _load_agent(db: AsyncSession, tenant_id: str, agent_id: str) -> Agent:
    agent = await db.scalar(
        select(Agent)
        .options(selectinload(Agent.agent_tools).selectinload(AgentTool.tool))
        .where(Agent.tenant_id == tenant_id, Agent.id == agent_id)
    )
    if not agent:
        raise AgentNotFoundError(f"Agent '{agent_id}' not found.")
    return agent


async def create_agent(
    db: AsyncSession, tenant_id: str, data: AgentCreate
) -> Agent:
    existing = await db.scalar(
        select(Agent).where(Agent.tenant_id == tenant_id, Agent.name == data.name)
    )
    if existing:
        raise AgentNameConflictError(f"Agent '{data.name}' already exists.")

    tools = await _resolve_tools(db, tenant_id, data.tool_ids)

    agent = Agent(
        id=new_uuid(),
        tenant_id=tenant_id,
        name=data.name,
        role=data.role,
        description=data.description,
    )
    db.add(agent)
    await db.flush()  # get agent.id before creating join rows

    for tool in tools:
        db.add(AgentTool(agent_id=agent.id, tool_id=tool.id))

    await db.commit()
    return await _load_agent(db, tenant_id, agent.id)


async def list_agents(
    db: AsyncSession,
    tenant_id: str,
    tool_name: str | None = None,
) -> list[Agent]:
    query = (
        select(Agent)
        .options(selectinload(Agent.agent_tools).selectinload(AgentTool.tool))
        .where(Agent.tenant_id == tenant_id)
    )

    if tool_name:
        query = (
            query.join(AgentTool, AgentTool.agent_id == Agent.id)
            .join(Tool, Tool.id == AgentTool.tool_id)
            .where(Tool.tenant_id == tenant_id, Tool.name == tool_name)
        )

    result = await db.execute(query.order_by(Agent.name))
    return list(result.scalars().unique().all())


async def get_agent(db: AsyncSession, tenant_id: str, agent_id: str) -> Agent:
    return await _load_agent(db, tenant_id, agent_id)


async def update_agent(
    db: AsyncSession, tenant_id: str, agent_id: str, data: AgentUpdate
) -> Agent:
    agent = await _load_agent(db, tenant_id, agent_id)

    updates = data.model_dump(exclude_unset=True)

    if "name" in updates and updates["name"] != agent.name:
        conflict = await db.scalar(
            select(Agent).where(
                Agent.tenant_id == tenant_id, Agent.name == updates["name"]
            )
        )
        if conflict:
            raise AgentNameConflictError(f"Agent '{updates['name']}' already exists.")
        agent.name = updates["name"]

    if "role" in updates:
        agent.role = updates["role"]

    if "description" in updates:
        agent.description = updates["description"]

    if "tool_ids" in updates:
        new_tools = await _resolve_tools(db, tenant_id, updates["tool_ids"])
        # Replace all existing AgentTool rows
        for at in list(agent.agent_tools):
            await db.delete(at)
        await db.flush()
        for tool in new_tools:
            db.add(AgentTool(agent_id=agent.id, tool_id=tool.id))

    await db.commit()
    return await _load_agent(db, tenant_id, agent.id)


async def delete_agent(db: AsyncSession, tenant_id: str, agent_id: str) -> None:
    agent = await _load_agent(db, tenant_id, agent_id)
    await db.delete(agent)
    await db.commit()
