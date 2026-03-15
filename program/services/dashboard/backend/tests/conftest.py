"""Shared fixtures for dashboard backend tests.

Provides mock DB pool, mock Redis client, and async HTTPX test client
so tests run without real infrastructure.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Mock DB pool — mimics asyncpg.Pool interface used by query functions
# ---------------------------------------------------------------------------


class MockPool:
    """In-memory asyncpg.Pool substitute."""

    def __init__(self) -> None:
        self.fetch = AsyncMock(return_value=[])
        self.fetchrow = AsyncMock(return_value=None)
        self.fetchval = AsyncMock(return_value=1)
        self.execute = AsyncMock(return_value="OK")


@pytest.fixture()
def mock_pool() -> MockPool:
    return MockPool()


# ---------------------------------------------------------------------------
# Mock Redis — mimics the dashboard redis_client helpers
# ---------------------------------------------------------------------------

_REDIS_STORE: dict[str, Any] = {}


async def _mock_get_json_key(key: str) -> dict | None:
    return _REDIS_STORE.get(key)


async def _mock_set_json_key(key: str, value: dict) -> bool:
    _REDIS_STORE[key] = value
    return True


async def _mock_redis_health() -> dict:
    return {"status": "connected", "ping": True}


@pytest.fixture(autouse=True)
def _reset_redis_store():
    _REDIS_STORE.clear()
    yield
    _REDIS_STORE.clear()


# ---------------------------------------------------------------------------
# All patch targets — applied via patch.start()/stop() to avoid nesting limit
# ---------------------------------------------------------------------------


def _build_patches(mock_pool: MockPool) -> list[Any]:
    """Return a list of patch objects for DB + Redis mocking."""
    pool_mock = AsyncMock(return_value=mock_pool)

    targets = [
        # Core modules
        ("backend.db.connection.get_pool", pool_mock),
        ("backend.db.connection.create_pool", pool_mock),
        ("backend.redis_client.client.get_json_key", _mock_get_json_key),
        ("backend.redis_client.client.set_json_key", _mock_set_json_key),
        ("backend.redis_client.client.redis_health", _mock_redis_health),
        # Route-level imports (already-resolved references)
        ("backend.api.routes.overview.get_pool", pool_mock),
        ("backend.api.routes.overview.get_json_key", _mock_get_json_key),
        ("backend.api.routes.overview.redis_health", _mock_redis_health),
        ("backend.api.routes.trading.get_pool", pool_mock),
        ("backend.api.routes.trading.get_json_key", _mock_get_json_key),
        ("backend.api.routes.risk.get_json_key", _mock_get_json_key),
        ("backend.api.routes.risk.set_json_key", _mock_set_json_key),
        ("backend.api.routes.market_data.get_pool", pool_mock),
        ("backend.api.routes.macro.get_pool", pool_mock),
        ("backend.api.routes.strategy.get_pool", pool_mock),
        ("backend.api.routes.economic.get_pool", pool_mock),
        ("backend.api.routes.system.get_pool", pool_mock),
        ("backend.api.routes.system.redis_health", _mock_redis_health),
        ("backend.ws.streams.get_pool", pool_mock),
        ("backend.ws.streams.get_json_key", _mock_get_json_key),
        ("backend.ws.streams.redis_health", _mock_redis_health),
    ]
    return [patch(target, new=mock) for target, mock in targets]


# ---------------------------------------------------------------------------
# Patched FastAPI app — replaces DB + Redis with mocks
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def client(mock_pool: MockPool):
    """Yield an async HTTPX client wired to the dashboard app with mocked deps."""
    patches = _build_patches(mock_pool)
    for p in patches:
        p.start()

    try:
        from backend.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        for p in patches:
            p.stop()
