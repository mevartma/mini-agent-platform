"""SQLAlchemy ORM models for the Mini Agent Platform."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class Tool(Base, TimestampMixin):
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    agent_tools: Mapped[list["AgentTool"]] = relationship(
        back_populates="tool", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tools_tenant_name"),
    )

    def __repr__(self) -> str:
        return f"<Tool id={self.id} name={self.name}>"


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    agent_tools: Mapped[list["AgentTool"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    executions: Mapped[list["Execution"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_agents_tenant_name"),
    )

    @property
    def tools(self) -> list[Tool]:
        return [at.tool for at in self.agent_tools]

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name}>"


class AgentTool(Base):
    """Join table between Agent and Tool."""

    __tablename__ = "agent_tools"

    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    tool_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True
    )

    agent: Mapped["Agent"] = relationship(back_populates="agent_tools")
    tool: Mapped["Tool"] = relationship(back_populates="agent_tools", lazy="selectin")


class Execution(Base):
    """A single run of an agent."""

    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    structured_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    final_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="completed"
    )  # completed | failed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    agent: Mapped["Agent"] = relationship(back_populates="executions")
    steps: Mapped[list["ExecutionStep"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
        order_by="ExecutionStep.step_number",
    )

    def __repr__(self) -> str:
        return f"<Execution id={self.id} agent_id={self.agent_id} status={self.status}>"


class ExecutionStep(Base):
    """One step within an agent execution (LLM call or tool call)."""

    __tablename__ = "execution_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # llm_call | tool_call
    tool_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tool_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    execution: Mapped["Execution"] = relationship(back_populates="steps")
