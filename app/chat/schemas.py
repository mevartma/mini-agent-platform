from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    name: str = "New Chat"


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    role: str  # user | agent
    content: str
    agent_name: str | None = None
    execution_id: str | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    tenant_id: str
    role: str
    content: str
    agent_name: str | None
    execution_id: str | None
    created_at: datetime
