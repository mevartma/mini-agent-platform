from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def set_tenant(db: AsyncSession, tenant_id: str) -> None:
    """Set the PostgreSQL session variable consumed by RLS policies.

    Called by require_permission() in rbac.py before every authenticated
    route handler. Uses set_config() with is_local=false (session-level)
    so it persists across commits within the same connection checkout.
    """
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, false)"),
        {"tid": tenant_id},
    )
