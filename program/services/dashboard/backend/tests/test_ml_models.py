"""Tests for /api/ml endpoints."""

from __future__ import annotations

import pytest

from backend.tests.conftest import MockPool


@pytest.mark.asyncio
async def test_ml_data_empty(client, mock_pool: MockPool):
    """With no models, returns empty lists and TB online."""
    mock_pool.fetch.return_value = []

    resp = await client.get("/api/ml")
    assert resp.status_code == 200
    data = resp.json()

    assert data["models"] == []
    assert data["recent_predictions"] == []
    assert data["training_metrics"] == []
    assert data["tensorboard_online"] is True  # mocked as True
    assert "tensorboard_url" in data


@pytest.mark.asyncio
async def test_tensorboard_status(client):
    """TensorBoard status endpoint returns online status."""
    resp = await client.get("/api/ml/tensorboard/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["online"] is True
    assert "url" in data
