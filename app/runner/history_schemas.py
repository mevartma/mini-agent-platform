from pydantic import BaseModel, Field

from app.runner.schemas import RunResponse


class ExecutionListResponse(BaseModel):
    items: list[RunResponse]
    total: int
    page: int
    limit: int
    pages: int
