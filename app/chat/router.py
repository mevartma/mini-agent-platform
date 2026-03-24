from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Permission, require_permission
from app.chat import service
from app.chat.schemas import MessageCreate, MessageResponse, SessionCreate, SessionResponse
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    user: User = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    session = await service.create_session(db, user.tenant_id, data.name)
    return SessionResponse.model_validate(session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    user: User = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[SessionResponse]:
    sessions = await service.list_sessions(db, user.tenant_id)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    session = await service.get_session(db, user.tenant_id, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    messages = await service.list_messages(db, user.tenant_id, session_id, limit, offset)
    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    session_id: str,
    data: MessageCreate,
    user: User = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    session = await service.get_session(db, user.tenant_id, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if data.role not in ("user", "agent"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="role must be 'user' or 'agent'.")
    msg = await service.add_message(
        db,
        tenant_id=user.tenant_id,
        session_id=session_id,
        role=data.role,
        content=data.content,
        agent_name=data.agent_name,
        execution_id=data.execution_id,
    )
    return MessageResponse.model_validate(msg)
