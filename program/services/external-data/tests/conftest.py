"""Shared test fixtures for external-data service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from external_data.config import ExternalDataSettings


@pytest.fixture()
def mock_settings(monkeypatch):
    """Return ExternalDataSettings with test defaults."""
    monkeypatch.setenv("FRED_API_KEY", "test-key")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "test")
    monkeypatch.setenv("DB_PASSWORD", "test")
    monkeypatch.setenv("DB_NAME", "testdb")
    return ExternalDataSettings()


@pytest.fixture()
def mock_redis():
    """Return a mock async Redis client."""
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.ping = AsyncMock()
    redis.close = AsyncMock()
    return redis


@pytest.fixture()
def mock_db_pool():
    """Return a mock asyncpg Pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    conn.execute = AsyncMock()

    # Mock the async context manager for pool.acquire()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=ctx)
    pool.close = AsyncMock()

    return pool, conn
