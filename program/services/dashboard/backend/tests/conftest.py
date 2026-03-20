# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Shared fixtures for dashboard backend integration tests.

Sets environment variables BEFORE importing the app so that
pydantic-settings picks up real connection parameters.

NO MOCKS: uses a real httpx.AsyncClient with httpx.ASGITransport
talking to the real FastAPI app, which connects to real DB and Redis.
"""

from __future__ import annotations

import os

import httpx
import pytest


@pytest.fixture
async def async_client(monkeypatch):
    """Create a real httpx.AsyncClient connected to the FastAPI app.

    Environment variables are set via monkeypatch.setenv BEFORE the
    app module is imported so that DashboardSettings picks up the
    correct values.
    """
    # Set env vars for the test session -- uses real services if available,
    # otherwise falls back to localhost defaults.
    monkeypatch.setenv(
        "MONEYMAKER_DB_HOST",
        os.environ.get("MONEYMAKER_DB_HOST", "localhost"),
    )
    monkeypatch.setenv(
        "MONEYMAKER_DB_PORT",
        os.environ.get("MONEYMAKER_DB_PORT", "5432"),
    )
    monkeypatch.setenv(
        "MONEYMAKER_DB_NAME",
        os.environ.get("MONEYMAKER_DB_NAME", "moneymaker"),
    )
    monkeypatch.setenv(
        "MONEYMAKER_DB_USER",
        os.environ.get("MONEYMAKER_DB_USER", "moneymaker"),
    )
    monkeypatch.setenv(
        "MONEYMAKER_DB_PASSWORD",
        os.environ.get("MONEYMAKER_DB_PASSWORD", ""),
    )
    monkeypatch.setenv(
        "MONEYMAKER_REDIS_HOST",
        os.environ.get("MONEYMAKER_REDIS_HOST", "localhost"),
    )
    monkeypatch.setenv(
        "MONEYMAKER_REDIS_PORT",
        os.environ.get("MONEYMAKER_REDIS_PORT", "6379"),
    )
    monkeypatch.setenv(
        "MONEYMAKER_REDIS_PASSWORD",
        os.environ.get("MONEYMAKER_REDIS_PASSWORD", ""),
    )
    monkeypatch.setenv("MONEYMAKER_ENV", "development")

    # Import app AFTER env vars are set so settings pick them up.
    # We must reload modules to ensure fresh settings if tests are
    # run in the same process with different env configurations.
    from backend.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
