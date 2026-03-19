from fastapi import FastAPI

from app.agents.router import router as agents_router
from app.runner.history_router import router as history_router
from app.runner.router import router as runner_router
from app.tools.router import router as tools_router

app = FastAPI(
    title="Mini Agent Platform",
    description="Multi-tenant API for managing and running AI agents.",
    version="0.1.0",
)

app.include_router(tools_router)
app.include_router(agents_router)
app.include_router(runner_router)
app.include_router(history_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
