from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.router import router as agents_router
from app.auth.router import router as auth_router
from app.cache import client as redis_client
from app.chat.router import router as chat_router
from app.runner.history_router import router as history_router
from app.runner.router import router as runner_router
from app.tenants.router import router as tenants_router
from app.tools.router import router as tools_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.startup()
    yield
    await redis_client.shutdown()


app = FastAPI(
    title="Mini Agent Platform",
    description="Multi-tenant API for managing and running AI agents.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(tools_router)
app.include_router(agents_router)
app.include_router(runner_router)
app.include_router(history_router)
app.include_router(chat_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
