"""Tests for /api/economic/* endpoints."""

from __future__ import annotations

import pytest

from backend.tests.conftest import MockPool


@pytest.mark.asyncio
async def test_upcoming_events_empty(client, mock_pool: MockPool):
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/economic/upcoming")
    assert resp.status_code == 200
    assert resp.json()["events"] == []


@pytest.mark.asyncio
async def test_upcoming_events_with_days(client, mock_pool: MockPool):
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/economic/upcoming?days=14")
    assert resp.status_code == 200
    assert resp.json()["events"] == []


@pytest.mark.asyncio
async def test_blackouts_empty(client, mock_pool: MockPool):
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/economic/blackouts")
    assert resp.status_code == 200
    assert resp.json()["blackouts"] == []


@pytest.mark.asyncio
async def test_recent_events_empty(client, mock_pool: MockPool):
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/economic/recent")
    assert resp.status_code == 200
    assert resp.json()["events"] == []


@pytest.mark.asyncio
async def test_days_validation(client):
    """days param must be within bounds."""
    resp = await client.get("/api/economic/upcoming?days=0")
    assert resp.status_code == 422

    resp = await client.get("/api/economic/upcoming?days=31")
    assert resp.status_code == 422
