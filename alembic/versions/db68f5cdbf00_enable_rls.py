"""enable_rls

Enable PostgreSQL Row Level Security on all tenant-scoped tables.

All policies read the session-level parameter app.current_tenant_id,
which the application sets at the start of every authenticated request
via: SELECT set_config('app.current_tenant_id', <tenant_id>, false)

Tables with a direct tenant_id column use a simple equality check.
Join tables (agent_tools, execution_steps) use EXISTS subqueries.

FORCE ROW LEVEL SECURITY is set so that even the table owner (the app
DB user) cannot bypass policies. The DB user must NOT be a PostgreSQL
superuser — superusers always bypass RLS.

Revision ID: db68f5cdbf00
Revises: 3592e481e447
Create Date: 2026-03-19

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "db68f5cdbf00"
down_revision: Union[str, Sequence[str], None] = "3592e481e447"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Shorthand: setting with missing_ok=true returns NULL instead of raising.
_CURRENT_TENANT = "current_setting('app.current_tenant_id', true)"

# Tables with a direct tenant_id column.
_DIRECT_TABLES = ["tools", "agents", "executions"]


def upgrade() -> None:
    conn = op.get_bind()

    # ── Direct tenant_id tables ───────────────────────────────────────────────
    for table in _DIRECT_TABLES:
        conn.execute(
            _sql(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        )
        conn.execute(
            _sql(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        )
        conn.execute(
            _sql(
                f"CREATE POLICY {table}_tenant_isolation ON {table} "
                f"USING (tenant_id = {_CURRENT_TENANT}) "
                f"WITH CHECK (tenant_id = {_CURRENT_TENANT})"
            )
        )

    # ── agent_tools (join table — no direct tenant_id) ───────────────────────
    conn.execute(_sql("ALTER TABLE agent_tools ENABLE ROW LEVEL SECURITY"))
    conn.execute(_sql("ALTER TABLE agent_tools FORCE ROW LEVEL SECURITY"))
    conn.execute(
        _sql(
            "CREATE POLICY agent_tools_tenant_isolation ON agent_tools "
            "USING ("
            "  EXISTS ("
            "    SELECT 1 FROM agents "
            "    WHERE agents.id = agent_tools.agent_id "
            f"   AND agents.tenant_id = {_CURRENT_TENANT}"
            "  )"
            ") "
            "WITH CHECK ("
            "  EXISTS ("
            "    SELECT 1 FROM agents "
            "    WHERE agents.id = agent_tools.agent_id "
            f"   AND agents.tenant_id = {_CURRENT_TENANT}"
            "  )"
            ")"
        )
    )

    # ── execution_steps (join table — no direct tenant_id) ───────────────────
    conn.execute(
        _sql("ALTER TABLE execution_steps ENABLE ROW LEVEL SECURITY")
    )
    conn.execute(
        _sql("ALTER TABLE execution_steps FORCE ROW LEVEL SECURITY")
    )
    conn.execute(
        _sql(
            "CREATE POLICY execution_steps_tenant_isolation ON execution_steps "
            "USING ("
            "  EXISTS ("
            "    SELECT 1 FROM executions "
            "    WHERE executions.id = execution_steps.execution_id "
            f"   AND executions.tenant_id = {_CURRENT_TENANT}"
            "  )"
            ") "
            "WITH CHECK ("
            "  EXISTS ("
            "    SELECT 1 FROM executions "
            "    WHERE executions.id = execution_steps.execution_id "
            f"   AND executions.tenant_id = {_CURRENT_TENANT}"
            "  )"
            ")"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    for table in ["execution_steps", "agent_tools"] + _DIRECT_TABLES:
        conn.execute(
            _sql(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        )
        conn.execute(
            _sql(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        )
        conn.execute(
            _sql(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        )


def _sql(stmt: str):
    from sqlalchemy import text
    return text(stmt)
