"""Generic cache-aside helpers."""

import json

from redis.asyncio import Redis

_MISS = object()


async def get_cached(redis: Redis, key: str) -> dict | None:
    raw = await redis.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_cached(redis: Redis, key: str, data: dict, ttl: int = 300) -> None:
    await redis.set(key, json.dumps(data), ex=ttl)


async def invalidate(redis: Redis, *keys: str) -> None:
    if keys:
        await redis.delete(*keys)
