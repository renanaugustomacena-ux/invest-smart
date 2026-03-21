"""Tests for MultiTimeframeAnalyzer — multi-TF bar accumulation and feature enrichment.

No unittest.mock — uses real FeaturePipeline with deterministic OHLCV bars.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.features.mtf_analyzer import MIN_BARS, WINDOW_SIZES, MultiTimeframeAnalyzer
from algo_engine.features.pipeline import OHLCVBar

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bar(close: Decimal, ts: int = 0) -> OHLCVBar:
    """Create a simple OHLCV bar with given close price."""
    return OHLCVBar(
        timestamp=ts,
        open=close - Decimal("0.0001"),
        high=close + Decimal("0.0005"),
        low=close - Decimal("0.0005"),
        close=close,
        volume=Decimal("100"),
    )


def _generate_bars(n: int, base_price: Decimal = Decimal("1.10000")) -> list[OHLCVBar]:
    """Generate n bars with slightly varying prices for realistic feature computation."""
    bars = []
    price = base_price
    for i in range(n):
        # Small sine-like variation to produce meaningful indicators
        delta = Decimal(str(0.0001 * (i % 7 - 3)))
        price = base_price + delta
        bars.append(_make_bar(price, ts=i * 60000))
    return bars


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestMultiTimeframeAnalyzerInit:
    def test_default_timeframes(self):
        mtf = MultiTimeframeAnalyzer()
        assert mtf._primary_tf == "M5"
        assert "M5" in mtf._timeframes
        assert "M15" in mtf._timeframes
        assert "H1" in mtf._timeframes

    def test_custom_timeframes(self):
        mtf = MultiTimeframeAnalyzer(primary_tf="M15", timeframes=["M15", "H1", "H4"])
        assert mtf._primary_tf == "M15"
        assert "H4" in mtf._timeframes


# ---------------------------------------------------------------------------
# Bar accumulation
# ---------------------------------------------------------------------------


class TestBarAccumulation:
    def test_bar_count_starts_at_zero(self):
        mtf = MultiTimeframeAnalyzer()
        assert mtf.bar_count("EURUSD", "M5") == 0

    def test_add_bar_increments_count(self):
        mtf = MultiTimeframeAnalyzer()
        bar = _make_bar(Decimal("1.10000"))
        mtf.add_bar("EURUSD", "M5", bar)
        assert mtf.bar_count("EURUSD", "M5") == 1

    def test_add_multiple_bars(self):
        mtf = MultiTimeframeAnalyzer()
        bars = _generate_bars(10)
        for b in bars:
            mtf.add_bar("EURUSD", "M5", b)
        assert mtf.bar_count("EURUSD", "M5") == 10

    def test_unknown_timeframe_ignored(self):
        mtf = MultiTimeframeAnalyzer(timeframes=["M5", "H1"])
        bar = _make_bar(Decimal("1.10000"))
        result = mtf.add_bar("EURUSD", "M1", bar)
        assert result is None
        assert mtf.bar_count("EURUSD", "M1") == 0

    def test_separate_buffers_per_symbol(self):
        mtf = MultiTimeframeAnalyzer()
        bar = _make_bar(Decimal("1.10000"))
        mtf.add_bar("EURUSD", "M5", bar)
        mtf.add_bar("GBPUSD", "M5", bar)
        assert mtf.bar_count("EURUSD", "M5") == 1
        assert mtf.bar_count("GBPUSD", "M5") == 1

    def test_window_size_limits_buffer(self):
        mtf = MultiTimeframeAnalyzer(timeframes=["M5"])
        max_window = WINDOW_SIZES.get("M5", 250)
        bars = _generate_bars(max_window + 50)
        for b in bars:
            mtf.add_bar("EURUSD", "M5", b)
        assert mtf.bar_count("EURUSD", "M5") == max_window


# ---------------------------------------------------------------------------
# Feature computation
# ---------------------------------------------------------------------------


class TestFeatureComputation:
    def test_returns_none_before_min_bars(self):
        """Need MIN_BARS[M5] bars before features are computed."""
        mtf = MultiTimeframeAnalyzer(timeframes=["M5"])
        min_needed = MIN_BARS.get("M5", 50)
        bars = _generate_bars(min_needed - 1)
        result = None
        for b in bars:
            result = mtf.add_bar("EURUSD", "M5", b)
        assert result is None

    def test_returns_features_at_min_bars(self):
        """At MIN_BARS, should return feature dict."""
        mtf = MultiTimeframeAnalyzer(timeframes=["M5"])
        min_needed = MIN_BARS.get("M5", 50)
        bars = _generate_bars(min_needed)
        result = None
        for b in bars:
            result = mtf.add_bar("EURUSD", "M5", b)
        assert result is not None
        assert isinstance(result, dict)

    def test_features_include_standard_indicators(self):
        """Feature dict should contain RSI, EMA, ATR etc."""
        mtf = MultiTimeframeAnalyzer(timeframes=["M5"])
        min_needed = MIN_BARS.get("M5", 50)
        bars = _generate_bars(min_needed)
        result = None
        for b in bars:
            result = mtf.add_bar("EURUSD", "M5", b)
        assert result is not None
        # Standard indicators from FeaturePipeline
        assert "rsi" in result
        assert "atr" in result
        assert "ema_fast" in result
        assert "ema_slow" in result

    def test_htf_bar_returns_none(self):
        """Non-primary TF bars should return None (no combined features)."""
        mtf = MultiTimeframeAnalyzer(timeframes=["M5", "H1"])
        bar = _make_bar(Decimal("1.10000"))
        result = mtf.add_bar("EURUSD", "H1", bar)
        assert result is None


# ---------------------------------------------------------------------------
# HTF enrichment
# ---------------------------------------------------------------------------


class TestHTFEnrichment:
    def test_enrichment_adds_htf_prefix(self):
        """When HTF has features, primary features get enriched with h1_trend etc."""
        mtf = MultiTimeframeAnalyzer(timeframes=["M5", "H1"])
        m5_min = MIN_BARS.get("M5", 50)
        h1_min = MIN_BARS.get("H1", 20)

        # Feed H1 bars first
        h1_bars = _generate_bars(h1_min)
        for b in h1_bars:
            mtf.add_bar("EURUSD", "H1", b)

        # Feed M5 bars
        m5_bars = _generate_bars(m5_min)
        result = None
        for b in m5_bars:
            result = mtf.add_bar("EURUSD", "M5", b)

        assert result is not None
        assert "h1_trend" in result
        assert result["h1_trend"] in ("bullish", "bearish", "neutral")
        assert "h1_rsi" in result
        assert "h1_atr" in result
        assert "h1_adx" in result

    def test_mtf_aligned_flag(self):
        """Result should include mtf_aligned boolean."""
        mtf = MultiTimeframeAnalyzer(timeframes=["M5", "H1"])
        m5_min = MIN_BARS.get("M5", 50)
        h1_min = MIN_BARS.get("H1", 20)

        h1_bars = _generate_bars(h1_min)
        for b in h1_bars:
            mtf.add_bar("EURUSD", "H1", b)

        m5_bars = _generate_bars(m5_min)
        result = None
        for b in m5_bars:
            result = mtf.add_bar("EURUSD", "M5", b)

        assert result is not None
        assert "mtf_aligned" in result
        assert isinstance(result["mtf_aligned"], bool)

    def test_primary_timeframe_in_result(self):
        """Result should include primary_timeframe field."""
        mtf = MultiTimeframeAnalyzer(timeframes=["M5"])
        bars = _generate_bars(MIN_BARS.get("M5", 50))
        result = None
        for b in bars:
            result = mtf.add_bar("EURUSD", "M5", b)
        assert result is not None
        assert result["primary_timeframe"] == "M5"

    def test_no_htf_features_still_works(self):
        """Without HTF data, primary features still computed."""
        mtf = MultiTimeframeAnalyzer(timeframes=["M5", "H1"])
        bars = _generate_bars(MIN_BARS.get("M5", 50))
        result = None
        for b in bars:
            result = mtf.add_bar("EURUSD", "M5", b)
        assert result is not None
        # Without H1 data, h1_trend should not be present
        # mtf_aligned still present (compares with neutral h1_trend)
        assert "mtf_aligned" in result
