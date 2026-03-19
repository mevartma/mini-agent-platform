from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.tools.schemas import ToolResponse


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    tool_ids: list[str] = Field(default_factory=list)


class AgentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    role: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    tool_ids: list[str] | None = None  # None = don't change; [] = remove all


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    role: str
    description: str
    tools: list[ToolResponse]
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    total: int
