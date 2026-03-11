"""Tests for /api/system/health endpoint."""

from __future__ import annotations

import pytest

from backend.tests.conftest import MockPool


@pytest.mark.asyncio
async def test_system_health(client, mock_pool: MockPool):
    """System health returns DB and Redis status."""
    # _check_database calls pool.fetchval("SELECT 1")
    mock_pool.fetchval.return_value = 1

    resp = await client.get("/api/system/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["database"]["name"] == "PostgreSQL"
    assert data["redis"]["name"] == "Redis"
    assert data["redis"]["status"] == "connected"
    assert "uptime_seconds" in data
    assert len(data["services"]) == 2
