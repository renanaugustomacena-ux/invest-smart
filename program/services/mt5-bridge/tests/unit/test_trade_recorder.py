"""Tests for TradeRecorder pure logic (outcome, pips calculation)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from mt5_bridge.trade_recorder import TradeRecorder


@pytest.fixture()
def recorder():
    return TradeRecorder(
        database_url="postgresql://test:test@localhost/test",
        breakeven_threshold=Decimal("0.50"),
    )


class TestDetermineOutcome:
    def test_win(self, recorder):
        assert recorder._determine_outcome({"profit": "10.50"}) == "win"

    def test_loss(self, recorder):
        assert recorder._determine_outcome({"profit": "-5.00"}) == "loss"

    def test_breakeven_positive(self, recorder):
        assert recorder._determine_outcome({"profit": "0.30"}) == "breakeven"

    def test_breakeven_negative(self, recorder):
        assert recorder._determine_outcome({"profit": "-0.40"}) == "breakeven"

    def test_breakeven_zero(self, recorder):
        assert recorder._determine_outcome({"profit": "0"}) == "breakeven"

    def test_breakeven_exact_threshold(self, recorder):
        assert recorder._determine_outcome({"profit": "0.50"}) == "breakeven"

    def test_invalid_profit_string(self, recorder):
        assert recorder._determine_outcome({"profit": "invalid"}) == "breakeven"

    def test_missing_profit(self, recorder):
        assert recorder._determine_outcome({}) == "breakeven"


class TestCalculatePnlPips:
    def test_buy_forex_profit(self, recorder):
        result = recorder._calculate_pnl_pips(
            {
                "symbol": "EURUSD",
                "direction": "BUY",
                "price_open": "1.0800",
                "price_close": "1.0850",
            }
        )
        assert result == Decimal("50.00")

    def test_buy_forex_loss(self, recorder):
        result = recorder._calculate_pnl_pips(
            {
                "symbol": "EURUSD",
                "direction": "BUY",
                "price_open": "1.0800",
                "price_close": "1.0750",
            }
        )
        assert result == Decimal("-50.00")

    def test_sell_forex_profit(self, recorder):
        result = recorder._calculate_pnl_pips(
            {
                "symbol": "EURUSD",
                "direction": "SELL",
                "price_open": "1.0850",
                "price_close": "1.0800",
            }
        )
        assert result == Decimal("50.00")

    def test_jpy_pair_pip_size(self, recorder):
        result = recorder._calculate_pnl_pips(
            {
                "symbol": "USDJPY",
                "direction": "BUY",
                "price_open": "150.00",
                "price_close": "150.50",
            }
        )
        assert result == Decimal("50.00")

    def test_xauusd_pip_size(self, recorder):
        result = recorder._calculate_pnl_pips(
            {
                "symbol": "XAUUSD",
                "direction": "BUY",
                "price_open": "2000.00",
                "price_close": "2001.00",
            }
        )
        assert result == Decimal("100.00")

    def test_zero_open_price(self, recorder):
        result = recorder._calculate_pnl_pips(
            {
                "symbol": "EURUSD",
                "direction": "BUY",
                "price_open": "0",
                "price_close": "1.0800",
            }
        )
        assert result is None

    def test_missing_prices(self, recorder):
        result = recorder._calculate_pnl_pips({})
        assert result is None
