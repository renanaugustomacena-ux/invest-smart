"""Shared test fixtures for external-data service."""

from __future__ import annotations

import pytest

from external_data.config import ExternalDataSettings


@pytest.fixture()
def mock_settings(monkeypatch):
    """Return ExternalDataSettings with test defaults."""
    monkeypatch.setenv("FRED_API_KEY", "test-key")
    monkeypatch.setenv("MONEYMAKER_REDIS_HOST", "localhost")
    monkeypatch.setenv("MONEYMAKER_REDIS_PORT", "6379")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "test")
    monkeypatch.setenv("DB_PASSWORD", "test")
    monkeypatch.setenv("DB_NAME", "testdb")
    return ExternalDataSettings()
