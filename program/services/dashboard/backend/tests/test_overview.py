"""Tests for /api/overview endpoint."""

from __future__ import annotations

import pytest

from backend.tests.conftest import MockPool, _REDIS_STORE


@pytest.mark.asyncio
async def test_overview_empty_state(client, mock_pool: MockPool):
    """With no data, overview returns zero KPIs."""
    # get_signals_today_count returns row with cnt=0
    mock_pool.fetchrow.return_value = {"cnt": 0}
    # get_daily_pnl returns row
    mock_pool.fetchrow.side_effect = [
        {"cnt": 0},  # signals count
        {"total_pnl": 0, "total_trades": 0, "wins": 0, "losses": 0},  # daily pnl
    ]
    mock_pool.fetch.return_value = []  # recent signals

    resp = await client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()

    assert "kpis" in data
    assert data["kpis"]["signals_today"] == 0
    assert data["kpis"]["open_positions"] == 0
    assert data["kpis"]["kill_switch_active"] is False
    assert "services" in data
    assert "recent_signals" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_overview_with_brain_state(client, mock_pool: MockPool):
    """When brain state exists in Redis, KPIs reflect it."""
    _REDIS_STORE["moneymaker:brain:state"] = {
        "active_positions": 3,
        "drawdown_pct": "1.25",
        "kill_switch_active": True,
    }
    mock_pool.fetchrow.side_effect = [
        {"cnt": 5},
        {"total_pnl": 120.50, "total_trades": 10, "wins": 7, "losses": 3},
    ]
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()

    assert data["kpis"]["signals_today"] == 5
    assert data["kpis"]["open_positions"] == 3
    assert data["kpis"]["kill_switch_active"] is True
    assert data["kpis"]["win_rate"] == "70.00"


@pytest.mark.asyncio
async def test_overview_services_health(client, mock_pool: MockPool):
    """Service health section lists DB and Redis."""
    mock_pool.fetchrow.side_effect = [
        {"cnt": 0},
        {"total_pnl": 0, "total_trades": 0, "wins": 0, "losses": 0},
    ]
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/overview")
    data = resp.json()

    service_names = [s["name"] for s in data["services"]]
    assert "PostgreSQL" in service_names
    assert "Redis" in service_names
