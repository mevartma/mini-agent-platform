"""initial

Revision ID: ec44ba203b6c
Revises:
Create Date: 2026-03-18

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "ec44ba203b6c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tools",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "name", name="uq_tools_tenant_name"),
    )
    op.create_index("ix_tools_tenant_id", "tools", ["tenant_id"])

    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "name", name="uq_agents_tenant_name"),
    )
    op.create_index("ix_agents_tenant_id", "agents", ["tenant_id"])

    op.create_table(
        "agent_tools",
        sa.Column(
            "agent_id",
            sa.String(36),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tool_id",
            sa.String(36),
            sa.ForeignKey("tools.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column(
            "agent_id",
            sa.String(36),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("task", sa.Text, nullable=False),
        sa.Column("structured_prompt", sa.Text, nullable=False),
        sa.Column("final_response", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_executions_tenant_id", "executions", ["tenant_id"])
    op.create_index("ix_executions_agent_id", "executions", ["agent_id"])

    op.create_table(
        "execution_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "execution_id",
            sa.String(36),
            sa.ForeignKey("executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column("step_type", sa.String(32), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=True),
        sa.Column("tool_input", sa.Text, nullable=True),
        sa.Column("tool_output", sa.Text, nullable=True),
        sa.Column("llm_output", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_execution_steps_execution_id", "execution_steps", ["execution_id"]
    )


def downgrade() -> None:
    op.drop_table("execution_steps")
    op.drop_table("executions")
    op.drop_table("agent_tools")
    op.drop_table("agents")
    op.drop_table("tools")
