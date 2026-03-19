from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

SUPPORTED_MODELS = ["gpt-4o", "claude-3-5-sonnet"]


class RunRequest(BaseModel):
    task: str = Field(..., min_length=1)
    model: str = Field(..., description=f"One of: {SUPPORTED_MODELS}")


class ExecutionStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    step_number: int
    step_type: str
    tool_name: str | None
    tool_input: str | None
    tool_output: str | None
    llm_output: str | None
    created_at: datetime


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    tenant_id: str
    model: str
    task: str
    structured_prompt: str
    final_response: str | None
    status: str
    steps: list[ExecutionStepResponse]
    created_at: datetime
