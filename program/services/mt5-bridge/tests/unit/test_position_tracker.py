"""Tests for PositionTracker state management and build_trade_result."""

from __future__ import annotations

import time
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from mt5_bridge.position_tracker import PositionTracker


@pytest.fixture()
def connector():
    mock = MagicMock()
    mock.get_open_positions.return_value = []
    mock.modify_position_sl.return_value = None
    return mock


@pytest.fixture()
def tracker(connector):
    return PositionTracker(
        connector=connector,
        trailing_stop_enabled=True,
        trailing_stop_pips=Decimal("50"),
        trailing_activation_pips=Decimal("30"),
    )


class TestStateAccessors:
    def test_starts_empty(self, tracker):
        assert tracker.position_count == 0
        assert tracker.get_open_positions() == []

    def test_get_recently_closed_empty(self, tracker):
        assert tracker.get_recently_closed() == []


class TestBuildTradeResult:
    def test_builds_complete_result(self, tracker):
        closed = {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": Decimal("0.10"),
            "price_open": Decimal("1.0800"),
            "price_current": Decimal("1.0850"),
            "sl": Decimal("1.0750"),
            "tp": Decimal("1.1000"),
            "profit": Decimal("50.00"),
            "swap": Decimal("-1.20"),
            "commission": Decimal("-0.50"),
            "time": 1700000000,
            "closed_at": 1700003600,
            "magic": 123456,
            "comment": "MONEYMAKER:abc12345",
        }
        result = tracker.build_trade_result(closed)

        assert result["ticket"] == 12345
        assert result["symbol"] == "EURUSD"
        assert result["direction"] == "BUY"
        assert result["volume"] == "0.10"
        assert result["price_open"] == "1.0800"
        assert result["price_close"] == "1.0850"
        assert result["profit"] == "50.00"
        assert result["open_time"] == 1700000000
        assert result["close_time"] == 1700003600

    def test_handles_missing_fields(self, tracker):
        closed = {"ticket": 1, "symbol": "GBPUSD", "type": "SELL"}
        result = tracker.build_trade_result(closed)
        assert result["ticket"] == 1
        assert result["volume"] == "0"
        assert result["profit"] == "0"
