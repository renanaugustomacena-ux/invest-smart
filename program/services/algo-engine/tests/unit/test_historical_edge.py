"""Tests for HistoricalEdgeTracker — per-context win rate and EV tracking."""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.analytics.historical_edge import (
    EdgeSnapshot,
    EdgeStats,
    HistoricalEdgeTracker,
)

ZERO = Decimal("0")


class TestEdgeStats:
    def test_empty_stats(self):
        s = EdgeStats()
        assert s.trade_count == 0
        assert s.win_rate == ZERO
        assert s.expected_value == ZERO
        assert s.avg_win == ZERO
        assert s.avg_loss == ZERO

    def test_all_wins(self):
        s = EdgeStats(wins=10, total_profit=Decimal("500"))
        assert s.win_rate == Decimal("1.0000")
        assert s.avg_win == Decimal("50")
        assert s.expected_value == Decimal("50.00")

    def test_all_losses(self):
        s = EdgeStats(losses=10, total_loss=Decimal("-300"))
        assert s.win_rate == ZERO
        assert s.avg_loss == Decimal("-30")
        assert s.expected_value == Decimal("-30.00")

    def test_mixed_outcomes(self):
        s = EdgeStats(wins=6, losses=4, total_profit=Decimal("600"), total_loss=Decimal("-200"))
        assert s.trade_count == 10
        assert s.win_rate == Decimal("0.6000")
        assert s.avg_win == Decimal("100")
        assert s.avg_loss == Decimal("-50")
        # EV = 0.6 * 100 + 0.4 * (-50) = 60 - 20 = 40
        assert s.expected_value == Decimal("40.00")

    def test_profit_factor(self):
        s = EdgeStats(wins=5, losses=5, total_profit=Decimal("500"), total_loss=Decimal("-250"))
        assert s.profit_factor == Decimal("2")

    def test_profit_factor_no_losses(self):
        s = EdgeStats(wins=5, total_profit=Decimal("500"))
        assert s.profit_factor == Decimal("Infinity")

    def test_profit_factor_no_trades(self):
        s = EdgeStats()
        assert s.profit_factor == ZERO


class TestTrackerRecording:
    def test_record_win(self):
        t = HistoricalEdgeTracker()
        t.record_outcome("XAUUSD", "trending", "london", Decimal("50"))
        edge = t.get_edge("XAUUSD", "trending", "london")
        assert edge.trade_count == 1
        assert edge.win_rate == Decimal("1.0000")

    def test_record_loss(self):
        t = HistoricalEdgeTracker()
        t.record_outcome("XAUUSD", "ranging", "tokyo", Decimal("-30"))
        edge = t.get_edge("XAUUSD", "ranging", "tokyo")
        assert edge.trade_count == 1
        assert edge.win_rate == ZERO

    def test_zero_profit_ignored(self):
        t = HistoricalEdgeTracker()
        t.record_outcome("XAUUSD", "trending", "london", ZERO)
        edge = t.get_edge("XAUUSD", "trending", "london")
        assert edge.trade_count == 0

    def test_case_normalization(self):
        t = HistoricalEdgeTracker()
        t.record_outcome("xauusd", "Trending", "LONDON", Decimal("50"))
        edge = t.get_edge("XAUUSD", "trending", "london")
        assert edge.trade_count == 1

    def test_separate_contexts(self):
        t = HistoricalEdgeTracker()
        t.record_outcome("XAUUSD", "trending", "london", Decimal("50"))
        t.record_outcome("EURUSD", "ranging", "newyork", Decimal("-20"))
        assert t.get_edge("XAUUSD", "trending", "london").trade_count == 1
        assert t.get_edge("EURUSD", "ranging", "newyork").trade_count == 1
        assert t.get_edge("XAUUSD", "ranging", "london").trade_count == 0


class TestReliability:
    def test_unreliable_below_threshold(self):
        t = HistoricalEdgeTracker(min_trades=30)
        for _ in range(29):
            t.record_outcome("XAUUSD", "trending", "london", Decimal("10"))
        edge = t.get_edge("XAUUSD", "trending", "london")
        assert not edge.is_reliable
        assert edge.trade_count == 29

    def test_reliable_at_threshold(self):
        t = HistoricalEdgeTracker(min_trades=30)
        for _ in range(30):
            t.record_outcome("XAUUSD", "trending", "london", Decimal("10"))
        edge = t.get_edge("XAUUSD", "trending", "london")
        assert edge.is_reliable

    def test_unknown_context_unreliable(self):
        t = HistoricalEdgeTracker()
        edge = t.get_edge("UNKNOWN", "unknown", "unknown")
        assert not edge.is_reliable
        assert edge.trade_count == 0


class TestSnapshot:
    def test_snapshot_is_frozen(self):
        t = HistoricalEdgeTracker()
        t.record_outcome("XAUUSD", "trending", "london", Decimal("50"))
        edge = t.get_edge("XAUUSD", "trending", "london")
        assert isinstance(edge, EdgeSnapshot)
        with pytest.raises(AttributeError):
            edge.win_rate = ZERO  # type: ignore[misc]

    def test_snapshot_fields(self):
        t = HistoricalEdgeTracker(min_trades=1)
        t.record_outcome("XAUUSD", "trending", "london", Decimal("100"))
        t.record_outcome("XAUUSD", "trending", "london", Decimal("-40"))
        edge = t.get_edge("XAUUSD", "trending", "london")
        assert edge.symbol == "XAUUSD"
        assert edge.regime == "trending"
        assert edge.session == "london"
        assert edge.is_reliable


class TestReport:
    def test_report_structure(self):
        t = HistoricalEdgeTracker(min_trades=1)
        t.record_outcome("XAUUSD", "trending", "london", Decimal("50"))
        report = t.get_report()
        assert "XAUUSD|trending|london" in report
        entry = report["XAUUSD|trending|london"]
        assert "trades" in entry
        assert "win_rate" in entry
        assert "expected_value" in entry
        assert entry["reliable"] is True

    def test_get_all_edges(self):
        t = HistoricalEdgeTracker()
        t.record_outcome("XAUUSD", "trending", "london", Decimal("50"))
        t.record_outcome("EURUSD", "ranging", "tokyo", Decimal("-20"))
        edges = t.get_all_edges()
        assert len(edges) == 2
