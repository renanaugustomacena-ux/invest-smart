"""Shared test fixtures for MT5 Bridge tests."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_mt5_connector():
    """Mock MT5 connector that doesn't require actual MT5 terminal."""
    connector = MagicMock()
    connector.is_connected = True
    connector.get_account_info.return_value = {
        "balance": Decimal("10000.00"),
        "equity": Decimal("10050.00"),
        "margin": Decimal("500.00"),
        "free_margin": Decimal("9550.00"),
        "profit": Decimal("50.00"),
        "leverage": 100,
        "currency": "USD",
    }
    connector.get_open_positions.return_value = []
    connector.get_symbol_info.return_value = {
        "name": "XAUUSD",
        "bid": Decimal("2045.50"),
        "ask": Decimal("2045.80"),
        "spread": 30,
        "digits": 2,
        "trade_contract_size": Decimal("100"),
        "volume_min": Decimal("0.01"),
        "volume_max": Decimal("100.0"),
        "volume_step": Decimal("0.01"),
        "trade_mode": 0,
    }
    return connector


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
