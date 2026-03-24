"""Async Redis client — singleton managed via FastAPI lifespan."""

from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.config import settings

_redis: Redis | None = None


async def startup() -> None:
    global _redis
    _redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def shutdown() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency that yields the shared Redis client."""
    if _redis is None:
        raise RuntimeError("Redis not initialised — check lifespan setup.")
    yield _redis
