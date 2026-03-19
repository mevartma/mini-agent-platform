"""Shared test fixtures and helpers."""

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock

import pytest


@dataclass
class MockTool:
    """Lightweight stand-in for the Tool ORM model."""

    id: str
    name: str
    description: str
    tenant_id: str = "tenant-test"


@dataclass
class MockAgentTool:
    tool: MockTool


@dataclass
class MockAgent:
    """Lightweight stand-in for the Agent ORM model."""

    id: str
    name: str
    role: str
    description: str
    tenant_id: str = "tenant-test"
    agent_tools: list[MockAgentTool] = field(default_factory=list)

    @property
    def tools(self) -> list[MockTool]:
        return [at.tool for at in self.agent_tools]


def make_agent(
    *,
    name: str = "Test Agent",
    role: str = "Analyst",
    description: str = "A test agent.",
    tool_names: list[str] | None = None,
) -> MockAgent:
    """Factory for creating MockAgent instances in tests."""
    tool_names = tool_names or []
    agent_tools = [
        MockAgentTool(
            tool=MockTool(
                id=f"tool-{n}",
                name=n,
                description=f"Description for {n}",
            )
        )
        for n in tool_names
    ]
    return MockAgent(
        id="agent-test-id",
        name=name,
        role=role,
        description=description,
        agent_tools=agent_tools,
    )


def make_db_session() -> AsyncMock:
    """Return a minimal mock of an AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session
