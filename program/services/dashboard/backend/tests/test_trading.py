"""Tests for /api/trading endpoint."""

from __future__ import annotations

import pytest

from backend.tests.conftest import MockPool, _REDIS_STORE


@pytest.mark.asyncio
async def test_trading_empty(client, mock_pool: MockPool):
    """With no data, trading returns empty lists."""
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/trading")
    assert resp.status_code == 200
    data = resp.json()

    assert data["signals"] == []
    assert data["executions"] == []
    assert data["positions"] == []
    assert data["total_signals"] == 0
    assert data["total_executions"] == 0


@pytest.mark.asyncio
async def test_trading_with_symbol_filter(client, mock_pool: MockPool):
    """Query param symbol is accepted."""
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/trading?symbol=EURUSD&limit=10")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_trading_with_positions_in_redis(client, mock_pool: MockPool):
    """Positions come from Redis brain state."""
    _REDIS_STORE["moneymaker:brain:state"] = {
        "positions_detail": [{"symbol": "EURUSD", "direction": "BUY", "lots": "0.01"}]
    }
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/trading")
    data = resp.json()

    assert len(data["positions"]) == 1
    assert data["positions"][0]["symbol"] == "EURUSD"
