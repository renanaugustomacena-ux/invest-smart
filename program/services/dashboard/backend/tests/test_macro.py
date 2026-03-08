"""Tests for /api/macro/* endpoints."""

from __future__ import annotations

import pytest

from backend.tests.conftest import MockPool


@pytest.mark.asyncio
async def test_macro_snapshot_empty(client, mock_pool: MockPool):
    """With no macro data, snapshot is null."""
    mock_pool.fetchrow.return_value = None

    resp = await client.get("/api/macro/snapshot")
    assert resp.status_code == 200
    assert resp.json()["snapshot"] is None


@pytest.mark.asyncio
async def test_vix_history_empty(client, mock_pool: MockPool):
    """VIX history returns empty list when no data."""
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/macro/vix")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_yield_curve_empty(client, mock_pool: MockPool):
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/macro/yield-curve")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_dxy_empty(client, mock_pool: MockPool):
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/macro/dxy")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_cot_empty(client, mock_pool: MockPool):
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/macro/cot")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_recession_empty(client, mock_pool: MockPool):
    mock_pool.fetchrow.return_value = None

    resp = await client.get("/api/macro/recession")
    assert resp.status_code == 200
    assert resp.json()["data"] is None


@pytest.mark.asyncio
async def test_vix_limit_validation(client):
    """Limit param must be within bounds."""
    resp = await client.get("/api/macro/vix?limit=0")
    assert resp.status_code == 422

    resp = await client.get("/api/macro/vix?limit=2000")
    assert resp.status_code == 422
