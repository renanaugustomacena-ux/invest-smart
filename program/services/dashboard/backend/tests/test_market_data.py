"""Tests for /api/market/* endpoints."""

from __future__ import annotations

import pytest

from backend.tests.conftest import MockPool


@pytest.mark.asyncio
async def test_symbols_empty(client, mock_pool: MockPool):
    """With no bars, symbols list is empty."""
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/market/symbols")
    assert resp.status_code == 200
    assert resp.json()["symbols"] == []


@pytest.mark.asyncio
async def test_bars_requires_symbol(client):
    """GET /api/market/bars without symbol returns 422."""
    resp = await client.get("/api/market/bars")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_bars_empty(client, mock_pool: MockPool):
    """With no data, bars returns empty list."""
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/market/bars?symbol=EURUSD")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "EURUSD"
    assert data["timeframe"] == "M5"
    assert data["bars"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_bars_with_custom_timeframe(client, mock_pool: MockPool):
    """Timeframe query param is forwarded."""
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/market/bars?symbol=EURUSD&timeframe=H1&limit=100")
    assert resp.status_code == 200
    data = resp.json()
    assert data["timeframe"] == "H1"


@pytest.mark.asyncio
async def test_tick_stats_empty(client, mock_pool: MockPool):
    """Tick stats returns empty when no ticks."""
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/market/tick-stats")
    assert resp.status_code == 200
    assert resp.json()["stats"] == []


@pytest.mark.asyncio
async def test_quality_empty(client, mock_pool: MockPool):
    """Quality endpoint returns zero counts."""
    mock_pool.fetchrow.side_effect = [
        {"total_bars": 0},
        {"total_ticks": 0},
    ]

    resp = await client.get("/api/market/quality")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_bars"] == 0
    assert data["total_ticks"] == 0
