from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid
from app.db.models import ChatMessage, ChatSession


async def create_session(db: AsyncSession, tenant_id: str, name: str) -> ChatSession:
    session = ChatSession(id=new_uuid(), tenant_id=tenant_id, name=name)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_sessions(db: AsyncSession, tenant_id: str) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.tenant_id == tenant_id)
        .order_by(ChatSession.created_at.desc())
    )
    return list(result.scalars().all())


async def get_session(db: AsyncSession, tenant_id: str, session_id: str) -> ChatSession | None:
    return await db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.tenant_id == tenant_id
        )
    )


async def list_messages(
    db: AsyncSession,
    tenant_id: str,
    session_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.tenant_id == tenant_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def add_message(
    db: AsyncSession,
    tenant_id: str,
    session_id: str,
    role: str,
    content: str,
    agent_name: str | None = None,
    execution_id: str | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        id=new_uuid(),
        session_id=session_id,
        tenant_id=tenant_id,
        role=role,
        content=content,
        agent_name=agent_name,
        execution_id=execution_id,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
