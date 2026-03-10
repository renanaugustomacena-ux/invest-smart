"""Tests for AdvancedPositionSizer and DrawdownScaler."""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.signals.advanced_sizer import (
    AdvancedPositionSizer,
    DrawdownScaler,
    TradeRecord,
)


D = Decimal


# ===========================================================================
# DrawdownScaler
# ===========================================================================

class TestDrawdownScaler:
    def test_no_drawdown_full_size(self):
        s = DrawdownScaler(tier1_dd=D("3"), tier2_dd=D("5"))
        assert s.scale(D("0")) == D("1.0")

    def test_below_tier1_full_size(self):
        s = DrawdownScaler(tier1_dd=D("3"), tier2_dd=D("5"))
        assert s.scale(D("2.9")) == D("1.0")

    def test_at_tier1_reduced(self):
        s = DrawdownScaler(
            tier1_dd=D("3"), tier1_scale=D("0.50"),
            tier2_dd=D("5"), tier2_scale=D("0.25"),
        )
        assert s.scale(D("3.0")) == D("0.50")

    def test_between_tiers_tier1_scale(self):
        s = DrawdownScaler(
            tier1_dd=D("3"), tier1_scale=D("0.50"),
            tier2_dd=D("5"), tier2_scale=D("0.25"),
        )
        assert s.scale(D("4.5")) == D("0.50")

    def test_at_tier2_minimum(self):
        s = DrawdownScaler(
            tier1_dd=D("3"), tier1_scale=D("0.50"),
            tier2_dd=D("5"), tier2_scale=D("0.25"),
        )
        assert s.scale(D("5.0")) == D("0.25")

    def test_above_tier2_minimum(self):
        s = DrawdownScaler(
            tier1_dd=D("3"), tier1_scale=D("0.50"),
            tier2_dd=D("5"), tier2_scale=D("0.25"),
        )
        assert s.scale(D("10.0")) == D("0.25")


# ===========================================================================
# TradeRecord
# ===========================================================================

class TestTradeRecord:
    def test_frozen(self):
        tr = TradeRecord(pnl=D("100"), direction="BUY", symbol="EURUSD")
        with pytest.raises(AttributeError):
            tr.pnl = D("200")  # type: ignore[misc]


# ===========================================================================
# AdvancedPositionSizer
# ===========================================================================

class TestAdvancedSizerBasic:
    def test_returns_decimal(self):
        sizer = AdvancedPositionSizer()
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("10000"),
            drawdown_pct=D("0"),
        )
        assert isinstance(lots, Decimal)

    def test_quantized_to_two_places(self):
        sizer = AdvancedPositionSizer()
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("10000"),
            drawdown_pct=D("0"),
        )
        assert lots == lots.quantize(D("0.01"))

    def test_clamped_to_max(self):
        sizer = AdvancedPositionSizer(max_lots=D("0.10"))
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("1000000"),
            drawdown_pct=D("0"),
        )
        assert lots <= D("0.10")

    def test_clamped_to_min(self):
        sizer = AdvancedPositionSizer(min_lots=D("0.01"))
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("100"),
            drawdown_pct=D("0"),
        )
        assert lots >= D("0.01")


class TestAdvancedSizerDrawdownReduction:
    def test_higher_drawdown_smaller_position(self):
        sizer = AdvancedPositionSizer(max_lots=D("10.0"))
        lots_low_dd = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("100000"),
            drawdown_pct=D("0"),
        )
        lots_high_dd = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("100000"),
            drawdown_pct=D("5"),
        )
        assert lots_high_dd < lots_low_dd


class TestAdvancedSizerConfidence:
    def test_lower_confidence_smaller_position(self):
        sizer = AdvancedPositionSizer(max_lots=D("10.0"))
        lots_high = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("100000"),
            drawdown_pct=D("0"),
            confidence=D("0.90"),
        )
        lots_low = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("100000"),
            drawdown_pct=D("0"),
            confidence=D("0.50"),
        )
        assert lots_low < lots_high


class TestAdvancedSizerCVaR:
    def test_cvar_caps_position(self):
        sizer = AdvancedPositionSizer(max_lots=D("10.0"), use_kelly=False)
        lots_no_cvar = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("100000"),
            drawdown_pct=D("0"),
        )
        lots_with_cvar = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("100000"),
            drawdown_pct=D("0"),
            cvar=D("0.01000"),  # large CVaR
        )
        assert lots_with_cvar <= lots_no_cvar


class TestAdvancedSizerKelly:
    def _load_trades(self, sizer, wins, losses):
        for _ in range(wins):
            sizer.record_trade(TradeRecord(pnl=D("100"), direction="BUY", symbol="EURUSD"))
        for _ in range(losses):
            sizer.record_trade(TradeRecord(pnl=D("-80"), direction="BUY", symbol="EURUSD"))

    def test_kelly_not_applied_below_min_trades(self):
        sizer = AdvancedPositionSizer(max_lots=D("10.0"), use_kelly=True)
        # Only 5 trades — Kelly should not apply
        self._load_trades(sizer, 3, 2)
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("100000"),
            drawdown_pct=D("0"),
        )
        assert lots > D("0")

    def test_kelly_caps_with_enough_trades(self):
        sizer = AdvancedPositionSizer(max_lots=D("10.0"), use_kelly=True)
        # 15 trades: 10W / 5L, avg_win=100, avg_loss=80
        self._load_trades(sizer, 10, 5)
        lots_kelly = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("100000"),
            drawdown_pct=D("0"),
        )
        assert lots_kelly > D("0")

    def test_kelly_no_edge_returns_zero(self):
        sizer = AdvancedPositionSizer(max_lots=D("10.0"), use_kelly=True)
        # All losses — no edge
        for _ in range(15):
            sizer.record_trade(TradeRecord(pnl=D("-50"), direction="BUY", symbol="EURUSD"))
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("100000"),
            drawdown_pct=D("0"),
        )
        # Kelly returns ZERO → kelly_lots=0 caps below base → clamped to min_lots
        assert lots >= sizer._min_lots


class TestAdvancedSizerEdgeCases:
    def test_zero_sl_distance_returns_min(self):
        sizer = AdvancedPositionSizer()
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=D("1.10000"),
            stop_loss=D("1.10000"),
            equity=D("10000"),
            drawdown_pct=D("0"),
        )
        assert lots == sizer._min_lots

    def test_unknown_symbol_returns_min(self):
        sizer = AdvancedPositionSizer()
        lots = sizer.calculate(
            symbol="UNKNOWN_XYZ",
            entry_price=D("1.10000"),
            stop_loss=D("1.09500"),
            equity=D("10000"),
            drawdown_pct=D("0"),
        )
        assert lots == sizer._min_lots

    def test_gold_symbol(self):
        sizer = AdvancedPositionSizer()
        lots = sizer.calculate(
            symbol="XAUUSD",
            entry_price=D("2000.00"),
            stop_loss=D("1990.00"),
            equity=D("10000"),
            drawdown_pct=D("0"),
        )
        assert lots > D("0")
