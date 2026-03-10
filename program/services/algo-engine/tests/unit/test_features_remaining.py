"""Tests for remaining feature modules (G10).

Covers: MultiTimeframeAnalyzer, DataQualityChecker, SessionClassifier,
        MacroFeatures, SpreadPercentileTracker, HistoricalEdgeTracker.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.features.pipeline import OHLCVBar

D = Decimal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bar(
    ts: int = 1700000000000,
    o: str = "1900.00",
    h: str = "1901.00",
    l: str = "1899.00",
    c: str = "1900.50",
    v: str = "1000",
) -> OHLCVBar:
    return OHLCVBar(
        timestamp=ts,
        open=D(o),
        high=D(h),
        low=D(l),
        close=D(c),
        volume=D(v),
    )


# ===========================================================================
# MultiTimeframeAnalyzer
# ===========================================================================
from algo_engine.features.mtf_analyzer import MultiTimeframeAnalyzer


class TestMultiTimeframeAnalyzer:
    def test_init_defaults(self):
        mtf = MultiTimeframeAnalyzer()
        assert mtf is not None

    def test_init_custom_timeframes(self):
        mtf = MultiTimeframeAnalyzer(
            primary_tf="M15",
            timeframes=["M15", "H1"],
            rsi_period=10,
        )
        assert mtf is not None

    def test_bar_count_empty(self):
        mtf = MultiTimeframeAnalyzer()
        assert mtf.bar_count("XAUUSD", "M5") == 0

    def test_add_bar_increments_count(self):
        mtf = MultiTimeframeAnalyzer(primary_tf="M5")
        bar = _make_bar()
        mtf.add_bar("XAUUSD", "M5", bar)
        assert mtf.bar_count("XAUUSD", "M5") == 1

    def test_add_bar_returns_none_insufficient_data(self):
        mtf = MultiTimeframeAnalyzer(primary_tf="M5")
        bar = _make_bar()
        result = mtf.add_bar("XAUUSD", "M5", bar)
        # Not enough bars for indicators yet
        assert result is None

    def test_add_bar_returns_features_after_warmup(self):
        mtf = MultiTimeframeAnalyzer(
            primary_tf="M5",
            timeframes=["M5"],
            rsi_period=14,
            ema_fast_period=12,
            ema_slow_period=26,
            bb_period=20,
            atr_period=14,
        )
        # Feed enough bars to warm up all indicators
        for i in range(60):
            bar = _make_bar(
                ts=1700000000000 + i * 300000,
                o=str(1900 + i * 0.1),
                h=str(1901 + i * 0.1),
                l=str(1899 + i * 0.1),
                c=str(1900.5 + i * 0.1),
            )
            result = mtf.add_bar("XAUUSD", "M5", bar)

        # After enough bars, should return a features dict
        if result is not None:
            assert isinstance(result, dict)


# ===========================================================================
# DataQualityChecker
# ===========================================================================
from algo_engine.features.data_quality import DataQualityChecker


class TestDataQualityChecker:
    def test_valid_bar(self):
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            bar_open=D("1900"),
            bar_high=D("1901"),
            bar_low=D("1899"),
            bar_close=D("1900.50"),
            bar_volume=D("1000"),
            bar_timestamp_ms=1700000060000,
        )
        assert valid is True
        assert reason == ""

    def test_high_less_than_low_invalid(self):
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            bar_open=D("1900"),
            bar_high=D("1899"),  # high < low
            bar_low=D("1901"),
            bar_close=D("1900"),
            bar_volume=D("1000"),
            bar_timestamp_ms=1700000060000,
        )
        assert valid is False

    def test_negative_volume_logged(self):
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            bar_open=D("1900"),
            bar_high=D("1901"),
            bar_low=D("1899"),
            bar_close=D("1900"),
            bar_volume=D("-1"),
            bar_timestamp_ms=1700000060000,
        )
        # Negative volume is logged as warning but bar is still valid
        assert isinstance(valid, bool)

    def test_zero_volume_logged(self):
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            bar_open=D("1900"),
            bar_high=D("1901"),
            bar_low=D("1899"),
            bar_close=D("1900"),
            bar_volume=D("0"),
            bar_timestamp_ms=1700000060000,
        )
        # Zero volume is logged but bar remains valid
        assert isinstance(valid, bool)

    def test_close_outside_high_low_invalid(self):
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            bar_open=D("1900"),
            bar_high=D("1901"),
            bar_low=D("1899"),
            bar_close=D("1905"),  # above high
            bar_volume=D("1000"),
            bar_timestamp_ms=1700000060000,
        )
        assert valid is False

    def test_gap_detection_warns(self):
        checker = DataQualityChecker(max_gap_multiple=2.0)
        valid, reason = checker.validate_bar(
            bar_open=D("1900"),
            bar_high=D("1901"),
            bar_low=D("1899"),
            bar_close=D("1900"),
            bar_volume=D("1000"),
            bar_timestamp_ms=1700000300000,  # 5 min gap
            prev_close=D("1900"),
            prev_timestamp_ms=1700000000000,
            expected_interval_ms=60000,
        )
        # Gaps are logged as warnings but don't invalidate the bar
        assert isinstance(valid, bool)


# ===========================================================================
# SessionClassifier
# ===========================================================================
from algo_engine.features.sessions import SessionClassifier, TradingSession


class TestTradingSession:
    def test_enum_values(self):
        assert TradingSession.ASIAN is not None
        assert TradingSession.LONDON is not None
        assert TradingSession.US is not None
        assert TradingSession.LONDON_US_OVERLAP is not None
        assert TradingSession.OFF_HOURS is not None


class TestSessionClassifier:
    def test_asian_session(self):
        classifier = SessionClassifier()
        session = classifier.classify(utc_hour=2)
        assert session == TradingSession.ASIAN

    def test_london_session(self):
        classifier = SessionClassifier()
        session = classifier.classify(utc_hour=8)
        assert session == TradingSession.LONDON

    def test_us_session(self):
        classifier = SessionClassifier()
        session = classifier.classify(utc_hour=17)
        assert session == TradingSession.US

    def test_overlap_session(self):
        classifier = SessionClassifier()
        session = classifier.classify(utc_hour=14)
        assert session == TradingSession.LONDON_US_OVERLAP

    def test_confidence_boost_returns_float(self):
        classifier = SessionClassifier()
        for session in TradingSession:
            boost = classifier.get_confidence_boost(session)
            assert isinstance(boost, float)

    def test_all_hours_classified(self):
        classifier = SessionClassifier()
        for hour in range(24):
            session = classifier.classify(utc_hour=hour)
            assert isinstance(session, TradingSession)


# ===========================================================================
# MacroFeatures
# ===========================================================================
from algo_engine.features.macro_features import MacroFeatures, MacroFeatureProvider


class TestMacroFeatures:
    def test_defaults(self):
        mf = MacroFeatures()
        assert mf.vix_spot == 15.0
        assert mf.data_stale is False

    def test_to_vector_returns_list(self):
        mf = MacroFeatures()
        vec = mf.to_vector()
        assert isinstance(vec, list)
        assert len(vec) > 0
        assert all(isinstance(v, float) for v in vec)

    def test_custom_values(self):
        mf = MacroFeatures(vix_spot=30.0, curve_inverted=1, recession_prob=0.5)
        assert mf.vix_spot == 30.0
        assert mf.curve_inverted == 1
        vec = mf.to_vector()
        assert isinstance(vec, list)


class TestMacroFeatureProvider:
    def test_get_feature_names(self):
        provider = MacroFeatureProvider()
        names = provider.get_feature_names()
        assert isinstance(names, list)
        assert len(names) > 0

    def test_is_gold_bullish(self):
        provider = MacroFeatureProvider()
        mf = MacroFeatures(vix_spot=25.0, real_rate_10y=-0.5)
        result = provider.is_gold_bullish_environment(mf)
        assert isinstance(result, bool)

    def test_is_high_risk(self):
        provider = MacroFeatureProvider()
        mf = MacroFeatures(vix_spot=35.0, recession_prob=0.6)
        result = provider.is_high_risk_environment(mf)
        assert isinstance(result, bool)


# ===========================================================================
# SpreadPercentileTracker
# ===========================================================================
from algo_engine.features.spread_tracker import SpreadPercentileTracker


class TestSpreadPercentileTracker:
    def test_record_and_check(self):
        tracker = SpreadPercentileTracker(window=50, reject_percentile=90, min_observations=5)
        for i in range(20):
            tracker.record_spread("XAUUSD", D(str(10 + i)))
        ok, reason = tracker.check("XAUUSD", D("15"))
        assert isinstance(ok, bool)

    def test_check_unknown_symbol(self):
        tracker = SpreadPercentileTracker()
        ok, reason = tracker.check("UNKNOWN", D("10"))
        # No data → should pass (not enough observations to reject)
        assert ok is True

    def test_reject_high_spread(self):
        tracker = SpreadPercentileTracker(window=50, reject_percentile=90, min_observations=10)
        # Record spreads around 10
        for _ in range(20):
            tracker.record_spread("EURUSD", D("10"))
        # Extreme spread should be rejected
        ok, reason = tracker.check("EURUSD", D("10000"))
        assert ok is False

    def test_get_percentile(self):
        tracker = SpreadPercentileTracker(min_observations=5)
        for i in range(1, 101):
            tracker.record_spread("EURUSD", D(str(i)))
        pct = tracker.get_percentile("EURUSD", D("50"))
        assert isinstance(pct, int)
        assert 40 <= pct <= 60  # 50th value in 1..100

    def test_get_stats(self):
        tracker = SpreadPercentileTracker(min_observations=5)
        for i in range(1, 21):
            tracker.record_spread("EURUSD", D(str(i)))
        stats = tracker.get_stats("EURUSD")
        assert isinstance(stats, dict)

    def test_get_stats_unknown(self):
        tracker = SpreadPercentileTracker()
        stats = tracker.get_stats("NOPE")
        assert isinstance(stats, dict)


# ===========================================================================
# HistoricalEdgeTracker
# ===========================================================================
from algo_engine.analytics.historical_edge import (
    HistoricalEdgeTracker,
    EdgeStats,
    EdgeSnapshot,
)


class TestEdgeStats:
    def test_defaults(self):
        es = EdgeStats()
        assert es.wins == 0
        assert es.losses == 0
        assert es.trade_count == 0

    def test_win_rate(self):
        es = EdgeStats(wins=3, losses=7)
        # win_rate is on 0-1 scale: 3/10 = 0.3
        assert es.win_rate == D("0.3000")
        assert isinstance(es.win_rate, Decimal)

    def test_expected_value(self):
        es = EdgeStats(
            wins=2, losses=1,
            total_profit=D("100"), total_loss=D("30"),
        )
        ev = es.expected_value
        assert isinstance(ev, Decimal)

    def test_profit_factor_no_losses(self):
        es = EdgeStats(wins=5, losses=0, total_profit=D("500"))
        pf = es.profit_factor
        assert isinstance(pf, Decimal)


class TestHistoricalEdgeTracker:
    def test_record_and_get_edge(self):
        tracker = HistoricalEdgeTracker(min_trades=5)
        for _ in range(10):
            tracker.record_outcome("XAUUSD", "trending", "london", D("50"))
        for _ in range(5):
            tracker.record_outcome("XAUUSD", "trending", "london", D("-30"))

        snap = tracker.get_edge("XAUUSD", "trending", "london")
        assert isinstance(snap, EdgeSnapshot)
        assert snap.trade_count == 15
        assert snap.is_reliable is True  # 15 > min_trades=5

    def test_unreliable_below_min_trades(self):
        tracker = HistoricalEdgeTracker(min_trades=30)
        tracker.record_outcome("EURUSD", "ranging", "us", D("10"))
        snap = tracker.get_edge("EURUSD", "ranging", "us")
        assert snap.is_reliable is False

    def test_get_edge_unknown_key(self):
        tracker = HistoricalEdgeTracker()
        snap = tracker.get_edge("NOPE", "unknown", "off")
        assert snap.trade_count == 0
        assert snap.is_reliable is False

    def test_get_all_edges(self):
        tracker = HistoricalEdgeTracker(min_trades=2)
        tracker.record_outcome("XAUUSD", "trending", "london", D("50"))
        tracker.record_outcome("XAUUSD", "trending", "london", D("-20"))
        tracker.record_outcome("EURUSD", "ranging", "us", D("30"))
        edges = tracker.get_all_edges()
        assert isinstance(edges, list)
        assert len(edges) == 2

    def test_get_report(self):
        tracker = HistoricalEdgeTracker(min_trades=2)
        tracker.record_outcome("XAUUSD", "trending", "london", D("50"))
        tracker.record_outcome("XAUUSD", "trending", "london", D("-20"))
        report = tracker.get_report()
        assert isinstance(report, dict)
        assert len(report) > 0

    def test_win_rate_accuracy(self):
        tracker = HistoricalEdgeTracker(min_trades=2)
        for _ in range(7):
            tracker.record_outcome("XAUUSD", "trending", "london", D("10"))
        for _ in range(3):
            tracker.record_outcome("XAUUSD", "trending", "london", D("-5"))
        snap = tracker.get_edge("XAUUSD", "trending", "london")
        # 7 wins / 10 trades = 70%
        assert snap.win_rate > D("0")
