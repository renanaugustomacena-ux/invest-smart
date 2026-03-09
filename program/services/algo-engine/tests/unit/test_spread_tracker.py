"""Tests for SpreadPercentileTracker — dynamic spread rejection."""

from __future__ import annotations

from decimal import Decimal

from algo_engine.features.spread_tracker import SpreadPercentileTracker

ZERO = Decimal("0")


class TestRecording:
    def test_record_single(self):
        t = SpreadPercentileTracker()
        t.record_spread("XAUUSD", Decimal("2.5"))
        stats = t.get_stats("XAUUSD")
        assert stats["observations"] == "1"

    def test_case_insensitive(self):
        t = SpreadPercentileTracker()
        t.record_spread("xauusd", Decimal("2.5"))
        stats = t.get_stats("XAUUSD")
        assert stats["observations"] == "1"

    def test_window_limit(self):
        t = SpreadPercentileTracker(window=10)
        for i in range(20):
            t.record_spread("XAUUSD", Decimal(str(i)))
        stats = t.get_stats("XAUUSD")
        assert stats["observations"] == "10"

    def test_separate_symbols(self):
        t = SpreadPercentileTracker()
        t.record_spread("XAUUSD", Decimal("2.5"))
        t.record_spread("EURUSD", Decimal("0.8"))
        assert t.get_stats("XAUUSD")["observations"] == "1"
        assert t.get_stats("EURUSD")["observations"] == "1"


class TestCheck:
    def test_no_history_passes(self):
        t = SpreadPercentileTracker()
        ok, reason = t.check("XAUUSD", Decimal("100"))
        assert ok is True
        assert reason == ""

    def test_below_min_observations_passes(self):
        t = SpreadPercentileTracker(min_observations=20)
        for i in range(19):
            t.record_spread("XAUUSD", Decimal(str(i)))
        ok, reason = t.check("XAUUSD", Decimal("1000"))
        assert ok is True

    def test_normal_spread_passes(self):
        t = SpreadPercentileTracker(window=100, reject_percentile=90, min_observations=5)
        # Record 100 spreads between 1-10
        for i in range(100):
            t.record_spread("XAUUSD", Decimal(str(1 + (i % 10))))
        # Check with a spread of 5 (middle of range)
        ok, reason = t.check("XAUUSD", Decimal("5"))
        assert ok is True

    def test_extreme_spread_rejected(self):
        t = SpreadPercentileTracker(window=100, reject_percentile=90, min_observations=5)
        # Record 100 spreads between 1-10
        for i in range(100):
            t.record_spread("XAUUSD", Decimal(str(1 + (i % 10))))
        # Check with a spread of 100 (far above range)
        ok, reason = t.check("XAUUSD", Decimal("100"))
        assert ok is False
        assert "percentile" in reason

    def test_exactly_at_threshold(self):
        t = SpreadPercentileTracker(window=100, reject_percentile=90, min_observations=5)
        # Record 100 identical spreads
        for _ in range(100):
            t.record_spread("XAUUSD", Decimal("5"))
        # Same spread = 0th percentile (nothing below) → passes
        ok, _ = t.check("XAUUSD", Decimal("5"))
        assert ok is True


class TestPercentile:
    def test_percentile_lowest(self):
        t = SpreadPercentileTracker(window=100, min_observations=5)
        for i in range(1, 101):
            t.record_spread("XAUUSD", Decimal(str(i)))
        p = t.get_percentile("XAUUSD", Decimal("1"))
        assert p == 0  # nothing below 1

    def test_percentile_highest(self):
        t = SpreadPercentileTracker(window=100, min_observations=5)
        for i in range(1, 101):
            t.record_spread("XAUUSD", Decimal(str(i)))
        p = t.get_percentile("XAUUSD", Decimal("200"))
        assert p == 100  # everything below 200

    def test_percentile_middle(self):
        t = SpreadPercentileTracker(window=100, min_observations=5)
        for i in range(1, 101):
            t.record_spread("XAUUSD", Decimal(str(i)))
        p = t.get_percentile("XAUUSD", Decimal("50"))
        # 49 values below 50 out of 100 = 49th percentile
        assert 45 <= p <= 55

    def test_no_history_returns_zero(self):
        t = SpreadPercentileTracker()
        assert t.get_percentile("XAUUSD", Decimal("5")) == 0


class TestStats:
    def test_stats_empty(self):
        t = SpreadPercentileTracker()
        stats = t.get_stats("XAUUSD")
        assert stats == {"observations": "0"}

    def test_stats_with_data(self):
        t = SpreadPercentileTracker(window=50, min_observations=5)
        for i in range(1, 21):
            t.record_spread("XAUUSD", Decimal(str(i)))
        stats = t.get_stats("XAUUSD")
        assert stats["observations"] == "20"
        assert stats["min"] == "1"
        assert stats["max"] == "20"
        assert "median" in stats
        assert "p90" in stats
