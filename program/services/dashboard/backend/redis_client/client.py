"""Async Redis client for reading MONEYMAKER real-time state."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from backend.config import settings


_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return the shared Redis client, creating it if needed.

    Tries the configured redis_url first. If authentication fails
    (e.g. password set in .env but Redis has no password), retries
    without credentials on the same host/port.
    """
    global _client
    if _client is None:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            await client.ping()
            _client = client
        except aioredis.AuthenticationError:
            # Password in .env but Redis has none — retry without auth
            await client.aclose()
            fallback_url = f"redis://{settings.moneymaker_redis_host}:{settings.moneymaker_redis_port}/0"
            _client = aioredis.from_url(fallback_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    """Close the Redis connection."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def get_json_key(key: str) -> dict[str, Any] | None:
    """Read a JSON value from Redis."""
    client = await get_redis()
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except (aioredis.ConnectionError, aioredis.TimeoutError):
        return None


async def set_json_key(key: str, value: dict[str, Any]) -> bool:
    """Write a JSON value to Redis."""
    client = await get_redis()
    try:
        await client.set(key, json.dumps(value))
        return True
    except (aioredis.ConnectionError, aioredis.TimeoutError):
        return False


async def redis_health() -> dict[str, Any]:
    """Check Redis connectivity and return status."""
    client = await get_redis()
    try:
        pong = await client.ping()
        return {"status": "connected", "ping": pong}
    except (aioredis.ConnectionError, aioredis.TimeoutError) as e:
        return {"status": "disconnected", "error": str(e)}
