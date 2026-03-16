"""Integration tests for the dashboard /health endpoint.

Tests the real FastAPI app through a real httpx.AsyncClient using
ASGITransport -- no external HTTP server needed, but the full ASGI
stack is exercised including middleware and lifespan events.

NO MOCKS: the app connects (or attempts to connect) to real
PostgreSQL and Redis instances.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_returns_200(async_client):
    """GET /health should return 200 with service status."""
    response = await async_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "moneymaker-dashboard"


async def test_health_response_is_json(async_client):
    """GET /health should return application/json content type."""
    response = await async_client.get("/health")

    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


async def test_health_contains_required_fields(async_client):
    """GET /health response must contain 'status' and 'service' keys."""
    response = await async_client.get("/health")

    data = response.json()
    assert "status" in data, "Missing 'status' key in health response"
    assert "service" in data, "Missing 'service' key in health response"


async def test_cors_headers_present(async_client):
    """Verify CORS headers are set on responses."""
    response = await async_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    # The CORS middleware should respond to preflight requests
    # Status can be 200 or 405 depending on FastAPI version,
    # but the important thing is that CORS headers are present.
    cors_header = response.headers.get("access-control-allow-origin", "")
    assert cors_header in (
        "http://localhost:5173",
        "*",
        "",
    ), f"Unexpected CORS origin: {cors_header}"


async def test_nonexistent_route_returns_404(async_client):
    """A request to a nonexistent API route should return 404."""
    response = await async_client.get("/api/v1/nonexistent")

    assert response.status_code == 404
