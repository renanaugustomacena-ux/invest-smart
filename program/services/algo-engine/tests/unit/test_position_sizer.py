"""Tests for algo_engine.signals.position_sizer — PositionSizer."""

from decimal import Decimal

from algo_engine.signals.position_sizer import PositionSizer


class TestPositionSizer:
    def test_basic_calculation_eurusd(self):
        """1% risk on $1000, 30 pip SL on EURUSD."""
        sizer = PositionSizer(
            risk_per_trade_pct=Decimal("1.0"),
            default_equity=Decimal("1000"),
        )
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
        )
        # Risk = $10, SL = 30 pips, pip_value = $10/lot
        # lots = 10 / (30 * 10) = 0.033 -> 0.03
        assert lots == Decimal("0.03")

    def test_min_lots_floor(self):
        """Should clamp to min_lots if calculated too small."""
        sizer = PositionSizer(
            risk_per_trade_pct=Decimal("0.5"),
            default_equity=Decimal("1000"),
            min_lots=Decimal("0.01"),
        )
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0500"),
        )
        # Risk = $5, SL = 500 pips, pip_value = $10
        # lots = 5 / (500 * 10) = 0.001 -> clamped to 0.01
        assert lots == Decimal("0.01")

    def test_max_lots_ceiling(self):
        """Should clamp to max_lots if calculated too large."""
        sizer = PositionSizer(
            risk_per_trade_pct=Decimal("5.0"),
            default_equity=Decimal("10000"),
            max_lots=Decimal("0.10"),
        )
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0845"),
        )
        assert lots == Decimal("0.10")

    def test_xauusd_calculation(self):
        """Gold has pip_size=0.01, pip_value=$1."""
        sizer = PositionSizer(
            risk_per_trade_pct=Decimal("1.0"),
            default_equity=Decimal("1000"),
        )
        lots = sizer.calculate(
            symbol="XAUUSD",
            entry_price=Decimal("2000"),
            stop_loss=Decimal("1990"),
        )
        # Risk = $10, SL = 1000 pips (10/0.01), pip_value = $1
        # lots = 10 / (1000 * 1) = 0.01
        assert lots == Decimal("0.01")

    def test_zero_sl_returns_min_lots(self):
        """Zero SL distance should return min_lots safely."""
        sizer = PositionSizer(default_equity=Decimal("1000"))
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0850"),
        )
        assert lots == Decimal("0.01")

    def test_equity_override(self):
        """Passing explicit equity should override default."""
        sizer = PositionSizer(
            risk_per_trade_pct=Decimal("1.0"),
            default_equity=Decimal("1000"),
        )
        lots_default = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
        )
        lots_higher = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            equity=Decimal("5000"),
        )
        assert lots_higher > lots_default

    def test_drawdown_scaling_mid(self):
        """3% drawdown should reduce sizing by 50%."""
        sizer = PositionSizer(
            risk_per_trade_pct=Decimal("1.0"),
            default_equity=Decimal("1000"),
        )
        lots_no_dd = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            drawdown_pct=Decimal("0"),
        )
        lots_mid_dd = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            drawdown_pct=Decimal("3.0"),
        )
        assert lots_mid_dd < lots_no_dd

    def test_drawdown_at_kill_switch_returns_min(self):
        """At 5%+ drawdown, should return minimum sizing."""
        sizer = PositionSizer(
            risk_per_trade_pct=Decimal("1.0"),
            default_equity=Decimal("1000"),
        )
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            drawdown_pct=Decimal("5.5"),
        )
        assert lots == Decimal("0.01")
