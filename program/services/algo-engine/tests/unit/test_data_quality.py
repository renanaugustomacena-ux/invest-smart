"""Tests for DataQualityChecker.

All tests use real class instances and Decimal — no unittest.mock.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.features.data_quality import DataQualityChecker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ZERO = Decimal("0")


def _normal_bar(ts_ms: int = 0) -> tuple:
    """Return a valid, small-range bar for building up the 20-bar window.

    Range = 1.10050 - 1.09950 = 0.00100
    """
    return (
        Decimal("1.10000"),  # open
        Decimal("1.10050"),  # high
        Decimal("1.09950"),  # low
        Decimal("1.10020"),  # close
        Decimal("100"),      # volume
        ts_ms,               # timestamp_ms
    )


def _feed_normal_bars(checker: DataQualityChecker, count: int = 21) -> Decimal:
    """Feed count normal bars to the checker, returning the last close.

    Each bar is spaced 60_000ms apart starting at ts=0.
    """
    last_close = None
    prev_close = None
    prev_ts = None
    for i in range(count):
        o, h, l, c, v, _ = _normal_bar(ts_ms=i * 60_000)
        valid, reason = checker.validate_bar(
            o, h, l, c, v,
            bar_timestamp_ms=i * 60_000,
            prev_close=prev_close,
            prev_timestamp_ms=prev_ts,
        )
        assert valid, f"Normal bar {i} unexpectedly rejected: {reason}"
        prev_close = c
        prev_ts = i * 60_000
        last_close = c
    return last_close


# ---------------------------------------------------------------------------
# OHLC validity tests
# ---------------------------------------------------------------------------


class TestOHLCValidity:
    """Test OHLC relationship checks."""

    def test_valid_bar_passes(self) -> None:
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            Decimal("1.10000"),
            Decimal("1.10050"),
            Decimal("1.09950"),
            Decimal("1.10020"),
            Decimal("100"),
            bar_timestamp_ms=0,
        )
        assert valid is True
        assert reason == ""

    def test_high_less_than_open_rejected(self) -> None:
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            Decimal("1.10000"),  # open
            Decimal("1.09999"),  # high < open
            Decimal("1.09900"),  # low
            Decimal("1.09950"),  # close
            Decimal("100"),
            bar_timestamp_ms=0,
        )
        assert valid is False
        assert "OHLC" in reason

    def test_high_less_than_close_rejected(self) -> None:
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            Decimal("1.09900"),  # open (lower so high >= open)
            Decimal("1.09950"),  # high
            Decimal("1.09850"),  # low
            Decimal("1.09960"),  # close > high
            Decimal("100"),
            bar_timestamp_ms=0,
        )
        assert valid is False
        assert "OHLC" in reason

    def test_low_greater_than_open_rejected(self) -> None:
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            Decimal("1.10000"),  # open
            Decimal("1.10100"),  # high
            Decimal("1.10001"),  # low > open
            Decimal("1.10050"),  # close
            Decimal("100"),
            bar_timestamp_ms=0,
        )
        assert valid is False
        assert "OHLC" in reason

    def test_low_greater_than_close_rejected(self) -> None:
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            Decimal("1.10050"),  # open
            Decimal("1.10100"),  # high
            Decimal("1.10020"),  # low > close
            Decimal("1.10010"),  # close
            Decimal("100"),
            bar_timestamp_ms=0,
        )
        assert valid is False
        assert "OHLC" in reason

    def test_high_less_than_low_rejected(self) -> None:
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            Decimal("1.10000"),  # open
            Decimal("1.09900"),  # high < low
            Decimal("1.10000"),  # low (== open, so low <= open passes)
            Decimal("1.09900"),  # close (== high, so high >= close passes)
            Decimal("100"),
            bar_timestamp_ms=0,
        )
        # high (1.09900) < open (1.10000) triggers the first check
        assert valid is False
        assert "OHLC" in reason


# ---------------------------------------------------------------------------
# Volume zero — logged but not rejected
# ---------------------------------------------------------------------------


class TestVolumeZero:
    """Zero volume should pass (logged only)."""

    def test_zero_volume_passes(self) -> None:
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            Decimal("1.10000"),
            Decimal("1.10050"),
            Decimal("1.09950"),
            Decimal("1.10020"),
            Decimal("0"),  # zero volume
            bar_timestamp_ms=0,
        )
        assert valid is True
        assert reason == ""

    def test_negative_volume_passes(self) -> None:
        """Negative volume also triggers the <=ZERO branch but does not reject."""
        checker = DataQualityChecker()
        valid, reason = checker.validate_bar(
            Decimal("1.10000"),
            Decimal("1.10050"),
            Decimal("1.09950"),
            Decimal("1.10020"),
            Decimal("-1"),
            bar_timestamp_ms=0,
        )
        assert valid is True
        assert reason == ""


# ---------------------------------------------------------------------------
# Spike detection — needs >20 bars to activate
# ---------------------------------------------------------------------------


class TestSpikeDetection:
    """Spike detection only activates after 20 normal-range bars."""

    def test_within_20_bars_always_pass(self) -> None:
        """A large bar within the first 20 bars should still pass."""
        checker = DataQualityChecker()
        # Feed 19 normal bars
        _feed_normal_bars(checker, count=19)
        # Bar 20 (index 19) has a huge range but bar_count will be 20 (not > 20)
        valid, reason = checker.validate_bar(
            Decimal("1.10000"),
            Decimal("1.20000"),  # big spike: range = 0.10050 vs avg ~0.001
            Decimal("1.09950"),
            Decimal("1.15000"),
            Decimal("100"),
            bar_timestamp_ms=20 * 60_000,
        )
        assert valid is True

    def test_spike_detected_after_20_bars(self) -> None:
        """After 20+ normal bars, a huge range bar should be rejected."""
        checker = DataQualityChecker()
        _feed_normal_bars(checker, count=21)
        # Now bar_count = 21, avg_range ≈ 0.00100
        # Spike bar: range = 1.20000 - 1.09950 = 0.10050 → ratio ≈ 100x >> 5x
        valid, reason = checker.validate_bar(
            Decimal("1.10000"),
            Decimal("1.20000"),
            Decimal("1.09950"),
            Decimal("1.15000"),
            Decimal("100"),
            bar_timestamp_ms=21 * 60_000,
        )
        assert valid is False
        assert "Spike" in reason

    def test_normal_bar_after_20_passes(self) -> None:
        """A normal bar after 20+ bars should pass without issue."""
        checker = DataQualityChecker()
        _feed_normal_bars(checker, count=21)
        o, h, l, c, v, _ = _normal_bar()
        valid, reason = checker.validate_bar(
            o, h, l, c, v,
            bar_timestamp_ms=21 * 60_000,
        )
        assert valid is True
        assert reason == ""


# ---------------------------------------------------------------------------
# Gap detection — logged but NOT rejected
# ---------------------------------------------------------------------------


class TestGapDetection:
    """Time gaps are logged but should not cause rejection."""

    def test_large_time_gap_does_not_reject(self) -> None:
        """A gap > 3x expected interval is logged but bar still passes."""
        checker = DataQualityChecker()
        o, h, l, c, v, _ = _normal_bar()
        # First bar
        checker.validate_bar(o, h, l, c, v, bar_timestamp_ms=0)
        # Second bar with huge time gap (10x the expected 60s interval)
        valid, reason = checker.validate_bar(
            o, h, l, c, v,
            bar_timestamp_ms=600_000,  # 10 minutes later
            prev_close=c,
            prev_timestamp_ms=0,
            expected_interval_ms=60_000,
        )
        assert valid is True
        assert reason == ""

    def test_normal_time_gap_passes(self) -> None:
        checker = DataQualityChecker()
        o, h, l, c, v, _ = _normal_bar()
        checker.validate_bar(o, h, l, c, v, bar_timestamp_ms=0)
        valid, reason = checker.validate_bar(
            o, h, l, c, v,
            bar_timestamp_ms=60_000,
            prev_close=c,
            prev_timestamp_ms=0,
            expected_interval_ms=60_000,
        )
        assert valid is True
        assert reason == ""


# ---------------------------------------------------------------------------
# Price continuity — anomalous gap rejected after 20 bars
# ---------------------------------------------------------------------------


class TestPriceContinuity:
    """Price continuity check rejects gaps > max_spike * avg_range from prev_close."""

    def test_anomalous_price_gap_rejected(self) -> None:
        """After 20+ bars, a huge open vs prev_close gap is rejected."""
        checker = DataQualityChecker()
        last_close = _feed_normal_bars(checker, count=21)
        # avg_range ≈ 0.00100, max_spike = 5.0 → threshold ≈ 0.005
        # Open = last_close + 0.1 → gap = 0.1 >> 0.005
        far_open = last_close + Decimal("0.10000")
        valid, reason = checker.validate_bar(
            far_open,
            far_open + Decimal("0.00050"),
            far_open - Decimal("0.00050"),
            far_open,
            Decimal("100"),
            bar_timestamp_ms=21 * 60_000,
            prev_close=last_close,
            prev_timestamp_ms=20 * 60_000,
        )
        assert valid is False
        assert "Gap" in reason

    def test_normal_price_gap_passes(self) -> None:
        """After 20+ bars, a small open vs prev_close gap passes."""
        checker = DataQualityChecker()
        last_close = _feed_normal_bars(checker, count=21)
        # Open = last_close + 0.00010 → gap = 0.0001 < threshold ≈ 0.005
        small_open = last_close + Decimal("0.00010")
        valid, reason = checker.validate_bar(
            small_open,
            small_open + Decimal("0.00050"),
            small_open - Decimal("0.00050"),
            small_open,
            Decimal("100"),
            bar_timestamp_ms=21 * 60_000,
            prev_close=last_close,
            prev_timestamp_ms=20 * 60_000,
        )
        assert valid is True
        assert reason == ""

    def test_no_prev_close_skips_continuity_check(self) -> None:
        """Without prev_close, the continuity check is skipped."""
        checker = DataQualityChecker()
        _feed_normal_bars(checker, count=21)
        far_open = Decimal("2.00000")
        valid, reason = checker.validate_bar(
            far_open,
            far_open + Decimal("0.00050"),
            far_open - Decimal("0.00050"),
            far_open,
            Decimal("100"),
            bar_timestamp_ms=21 * 60_000,
            prev_close=None,  # no prev_close → skip continuity
        )
        assert valid is True
        assert reason == ""
