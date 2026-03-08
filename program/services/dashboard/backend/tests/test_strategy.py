"""Tests for /api/strategy/* endpoints."""

from __future__ import annotations

import pytest

from backend.tests.conftest import MockPool


@pytest.mark.asyncio
async def test_strategy_summary_empty(client, mock_pool: MockPool):
    """Summary returns empty list when no strategies."""
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/strategy/summary")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_strategy_performance_empty(client, mock_pool: MockPool):
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/strategy/performance")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_strategy_performance_with_filter(client, mock_pool: MockPool):
    """Strategy filter query param is accepted."""
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/strategy/performance?strategy=COPER&limit=10")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_strategy_names_empty(client, mock_pool: MockPool):
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/strategy/names")
    assert resp.status_code == 200
    assert resp.json()["strategies"] == []
