"""Tests for /api/risk endpoints."""

from __future__ import annotations

import pytest

from backend.tests.conftest import _REDIS_STORE


@pytest.mark.asyncio
async def test_risk_empty(client):
    """With no brain state, returns safe defaults."""
    resp = await client.get("/api/risk")
    assert resp.status_code == 200
    data = resp.json()

    assert data["kill_switch_active"] is False
    assert data["open_positions"] == 0
    assert data["drawdown_pct"] == "0.00"


@pytest.mark.asyncio
async def test_risk_with_state(client):
    """Brain state in Redis is reflected in risk response."""
    _REDIS_STORE["moneymaker:brain:state"] = {
        "daily_loss_pct": "0.85",
        "drawdown_pct": "2.10",
        "kill_switch_active": False,
        "active_positions": 2,
        "symbols_exposed": ["EURUSD", "GBPUSD"],
        "maturity_state": "live",
        "current_regime": "trending_up",
    }

    resp = await client.get("/api/risk")
    data = resp.json()

    assert data["daily_loss_pct"] == "0.85"
    assert data["drawdown_pct"] == "2.10"
    assert data["open_positions"] == 2
    assert data["symbols_exposed"] == ["EURUSD", "GBPUSD"]
    assert data["regime"] == "trending_up"


@pytest.mark.asyncio
async def test_kill_switch_activate(client):
    """POST /api/risk/kill-switch activates kill switch."""
    resp = await client.post(
        "/api/risk/kill-switch",
        json={"active": True, "reason": "Testing"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["kill_switch_active"] is True
    assert data["reason"] == "Testing"

    # Verify Redis state was updated
    assert _REDIS_STORE["moneymaker:brain:state"]["kill_switch_active"] is True


@pytest.mark.asyncio
async def test_kill_switch_deactivate(client):
    """POST /api/risk/kill-switch deactivates kill switch."""
    _REDIS_STORE["moneymaker:brain:state"] = {"kill_switch_active": True}

    resp = await client.post(
        "/api/risk/kill-switch",
        json={"active": False},
    )
    data = resp.json()

    assert data["success"] is True
    assert data["kill_switch_active"] is False
    assert data["reason"] is None
