"""Tests for StrategyAttribution and StrategyStats — per-strategy performance tracking.

All tests use REAL class instances — no MagicMock, no @patch, no unittest.mock.
Financial values use Decimal for precision.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from moneymaker_common.decimal_utils import ZERO
from algo_engine.analytics.attribution import StrategyAttribution, StrategyStats


# ---------------------------------------------------------------------------
# StrategyStats properties
# ---------------------------------------------------------------------------


class TestStrategyStatsProperties:
    """Test computed properties on StrategyStats directly."""

    def test_win_rate_no_trades(self):
        stats = StrategyStats()
        assert stats.win_rate == ZERO

    def test_win_rate_all_wins(self):
        stats = StrategyStats(wins=5, losses=0)
        assert stats.win_rate == Decimal("1")

    def test_win_rate_all_losses(self):
        stats = StrategyStats(wins=0, losses=4)
        assert stats.win_rate == ZERO

    def test_win_rate_mixed(self):
        stats = StrategyStats(wins=3, losses=7)
        assert stats.win_rate == Decimal("0.3")

    def test_profit_factor_no_loss(self):
        """When total_loss is zero and profit > 0, profit_factor is Infinity."""
        stats = StrategyStats(total_profit=Decimal("100"))
        assert stats.profit_factor == Decimal("Infinity")

    def test_profit_factor_no_loss_no_profit(self):
        """When both total_loss and total_profit are zero, profit_factor is ZERO."""
        stats = StrategyStats()
        assert stats.profit_factor == ZERO

    def test_profit_factor_normal(self):
        """profit_factor = abs(total_profit / total_loss)."""
        stats = StrategyStats(
            total_profit=Decimal("200"),
            total_loss=Decimal("-100"),
        )
        assert stats.profit_factor == Decimal("2")

    def test_net_profit_calculation(self):
        """net_profit = total_profit + total_loss (loss is already negative)."""
        stats = StrategyStats(
            total_profit=Decimal("300"),
            total_loss=Decimal("-120"),
        )
        assert stats.net_profit == Decimal("180")

    def test_net_profit_no_trades(self):
        stats = StrategyStats()
        assert stats.net_profit == ZERO

    def test_avg_confidence_no_signals(self):
        stats = StrategyStats()
        assert stats.avg_confidence == ZERO

    def test_avg_confidence_calculated(self):
        stats = StrategyStats(
            signals_count=4,
            confidence_sum=Decimal("3.0"),
        )
        assert stats.avg_confidence == Decimal("0.75")


# ---------------------------------------------------------------------------
# StrategyAttribution — record_signal / record_outcome
# ---------------------------------------------------------------------------


class TestStrategyAttributionRecording:
    """Test signal and outcome recording."""

    def test_record_signal_increments_count(self):
        attr = StrategyAttribution()
        attr.record_signal("trend", "BUY", Decimal("0.80"))
        attr.record_signal("trend", "SELL", Decimal("0.70"))
        stats = attr._stats["trend"]
        assert stats.signals_count == 2

    def test_record_signal_accumulates_confidence(self):
        attr = StrategyAttribution()
        attr.record_signal("scalp", "BUY", Decimal("0.60"))
        attr.record_signal("scalp", "BUY", Decimal("0.90"))
        stats = attr._stats["scalp"]
        assert stats.confidence_sum == Decimal("1.50")

    def test_record_outcome_win(self):
        attr = StrategyAttribution()
        attr.record_outcome("trend", Decimal("50.00"))
        stats = attr._stats["trend"]
        assert stats.wins == 1
        assert stats.losses == 0
        assert stats.total_profit == Decimal("50.00")
        assert stats.total_loss == ZERO

    def test_record_outcome_loss(self):
        attr = StrategyAttribution()
        attr.record_outcome("trend", Decimal("-30.00"))
        stats = attr._stats["trend"]
        assert stats.wins == 0
        assert stats.losses == 1
        assert stats.total_loss == Decimal("-30.00")
        assert stats.total_profit == ZERO

    def test_record_outcome_zero_profit_no_win_no_loss(self):
        """A zero-profit trade should count as neither win nor loss."""
        attr = StrategyAttribution()
        attr.record_outcome("breakeven", ZERO)
        stats = attr._stats["breakeven"]
        assert stats.wins == 0
        assert stats.losses == 0
        assert stats.total_profit == ZERO
        assert stats.total_loss == ZERO


# ---------------------------------------------------------------------------
# StrategyAttribution — get_report / get_strategy_names
# ---------------------------------------------------------------------------


class TestStrategyAttributionReporting:
    """Test report generation and strategy listing."""

    def test_get_strategy_names_empty(self):
        attr = StrategyAttribution()
        assert attr.get_strategy_names() == []

    def test_get_strategy_names_tracks_order(self):
        attr = StrategyAttribution()
        attr.record_signal("alpha", "BUY", Decimal("0.70"))
        attr.record_signal("beta", "SELL", Decimal("0.80"))
        names = attr.get_strategy_names()
        assert "alpha" in names
        assert "beta" in names
        assert len(names) == 2

    def test_get_report_format(self):
        attr = StrategyAttribution()
        attr.record_signal("trend", "BUY", Decimal("0.80"))
        attr.record_outcome("trend", Decimal("100.00"))
        report = attr.get_report()
        assert "trend" in report
        entry = report["trend"]
        assert entry["signals"] == 1
        assert entry["wins"] == 1
        assert entry["losses"] == 0
        expected_keys = {"signals", "wins", "losses", "win_rate", "net_profit",
                         "profit_factor", "avg_confidence"}
        assert set(entry.keys()) == expected_keys

    def test_get_report_values_are_strings_for_decimals(self):
        attr = StrategyAttribution()
        attr.record_signal("scalp", "BUY", Decimal("0.60"))
        attr.record_outcome("scalp", Decimal("25.00"))
        report = attr.get_report()
        entry = report["scalp"]
        assert isinstance(entry["win_rate"], str)
        assert isinstance(entry["net_profit"], str)
        assert isinstance(entry["profit_factor"], str)
        assert isinstance(entry["avg_confidence"], str)

    def test_multiple_strategies_tracked_independently(self):
        attr = StrategyAttribution()
        attr.record_signal("alpha", "BUY", Decimal("0.90"))
        attr.record_outcome("alpha", Decimal("100.00"))
        attr.record_signal("beta", "SELL", Decimal("0.50"))
        attr.record_outcome("beta", Decimal("-40.00"))

        report = attr.get_report()
        assert report["alpha"]["wins"] == 1
        assert report["alpha"]["losses"] == 0
        assert report["beta"]["wins"] == 0
        assert report["beta"]["losses"] == 1
        assert report["alpha"]["net_profit"] == str(Decimal("100.00"))
        assert report["beta"]["net_profit"] == str(Decimal("-40.00"))
