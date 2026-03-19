"""Execution history service — paginated retrieval scoped to a tenant."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Agent, Execution


class AgentNotFoundError(Exception):
    pass


async def list_executions(
    db: AsyncSession,
    tenant_id: str,
    agent_id: str,
    page: int,
    limit: int,
) -> tuple[list[Execution], int]:
    """Return a page of executions for an agent plus the total count.

    Args:
        db:        Async DB session.
        tenant_id: Caller's tenant — enforces isolation.
        agent_id:  Target agent ID.
        page:      1-based page number.
        limit:     Number of records per page (max 100).

    Returns:
        (items, total) tuple.

    Raises:
        AgentNotFoundError: If the agent doesn't exist for this tenant.
    """
    # Verify the agent belongs to the tenant before exposing its history.
    agent_exists = await db.scalar(
        select(Agent.id).where(
            Agent.tenant_id == tenant_id, Agent.id == agent_id
        )
    )
    if not agent_exists:
        raise AgentNotFoundError(f"Agent '{agent_id}' not found.")

    base_query = select(Execution).where(
        Execution.tenant_id == tenant_id,
        Execution.agent_id == agent_id,
    )

    total: int = await db.scalar(
        select(func.count()).select_from(base_query.subquery())
    ) or 0

    offset = (page - 1) * limit
    result = await db.execute(
        base_query.options(selectinload(Execution.steps))
        .order_by(Execution.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(result.scalars().all())

    return items, total
