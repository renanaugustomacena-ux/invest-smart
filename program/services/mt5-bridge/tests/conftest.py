"""Shared test fixtures for MT5 Bridge tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_signal():
    """A valid trading signal for testing."""
    return {
        "signal_id": "test-signal-001",
        "symbol": "XAUUSD",
        "direction": "BUY",
        "confidence": "0.85",
        "suggested_lots": "0.10",
        "stop_loss": "2040.00",
        "take_profit": "2060.00",
        "timestamp": 1700000000000000000,
        "model_version": "test-v1",
        "regime": "trending_up",
    }
