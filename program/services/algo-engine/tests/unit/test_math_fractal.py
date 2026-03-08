"""Tests for algo_engine.math.fractal — Hurst, fractional differencing, DFA."""

from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from moneymaker_common.decimal_utils import ZERO

from algo_engine.math.fractal import (
    detrended_fluctuation_analysis,
    fractional_difference,
    hurst_exponent,
    optimal_d,
)

ONE = Decimal("1")


# ---------------------------------------------------------------------------
# Helper: generate deterministic random walk for testing
# ---------------------------------------------------------------------------


def _random_walk(n: int = 500, seed: int = 42) -> list[Decimal]:
    """IID standard normal returns -> H ~ 0.5 for R/S and DFA."""
    rng = np.random.default_rng(seed)
    returns = rng.standard_normal(n)
    return [Decimal(str(round(v, 8))) for v in returns]


def _linear_trend(n: int = 200) -> list[Decimal]:
    """Linear series 1, 2, ..., n -> strongly persistent (H > 0.5)."""
    return [Decimal(str(i)) for i in range(1, n + 1)]


# ---------------------------------------------------------------------------
# TestHurstExponent
# ---------------------------------------------------------------------------


class TestHurstExponent:
    """Tests for the hurst_exponent function."""

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="below the minimum"):
            hurst_exponent([Decimal("1")] * 30)

    def test_constant_series_raises(self) -> None:
        with pytest.raises(ValueError, match="constant series"):
            hurst_exponent([Decimal("100")] * 100)

    def test_random_walk_near_half(self) -> None:
        series = _random_walk(500)
        h = hurst_exponent(series)
        assert Decimal("0.3") < h < Decimal("0.7")

    def test_trending_series_above_half(self) -> None:
        series = _linear_trend(200)
        h = hurst_exponent(series)
        assert h > Decimal("0.5")

    def test_result_is_decimal(self) -> None:
        series = _linear_trend(200)
        result = hurst_exponent(series)
        assert isinstance(result, Decimal)

    def test_max_lag_parameter(self) -> None:
        series = _random_walk(200)
        # Both calls should succeed with different max_lag
        h1 = hurst_exponent(series, max_lag=20)
        h2 = hurst_exponent(series, max_lag=80)
        assert isinstance(h1, Decimal)
        assert isinstance(h2, Decimal)


# ---------------------------------------------------------------------------
# TestFractionalDifference
# ---------------------------------------------------------------------------


class TestFractionalDifference:
    """Tests for the fractional_difference function."""

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty series"):
            fractional_difference([], Decimal("0.5"))

    def test_negative_d_raises(self) -> None:
        with pytest.raises(ValueError, match="d must be >= 0"):
            fractional_difference([Decimal("1")] * 10, Decimal("-0.1"))

    def test_d_zero_identity(self) -> None:
        # d=0: weights = [1], so output = original series
        series = [Decimal(str(i)) for i in range(1, 21)]
        result = fractional_difference(series, ZERO)
        assert result == series

    def test_d_one_first_difference(self) -> None:
        # d=1: weights converge to [1, -1], so output ~ standard first difference
        series = [Decimal("10"), Decimal("13"), Decimal("18"), Decimal("25")]
        result = fractional_difference(series, ONE, threshold=Decimal("1e-5"))
        # First differences: 3, 5, 7. Result should be close.
        assert len(result) > 0
        # The last element should be close to 7 (25 - 18)
        assert abs(result[-1] - Decimal("7")) < Decimal("1")

    def test_output_shorter_than_input(self) -> None:
        # Use a higher threshold so weight count stays manageable
        series = [Decimal(str(i)) for i in range(200)]
        result = fractional_difference(series, Decimal("0.5"), threshold=Decimal("0.01"))
        assert len(result) <= len(series)
        assert len(result) > 0

    def test_result_contains_decimals(self) -> None:
        series = [Decimal(str(i)) for i in range(50)]
        result = fractional_difference(series, Decimal("0.4"))
        assert all(isinstance(v, Decimal) for v in result)

    def test_threshold_affects_output_length(self) -> None:
        series = [Decimal(str(i)) for i in range(100)]
        # Higher threshold -> fewer weights -> longer output
        result_high = fractional_difference(
            series, Decimal("0.5"), threshold=Decimal("0.01")
        )
        result_low = fractional_difference(
            series, Decimal("0.5"), threshold=Decimal("1e-8")
        )
        assert len(result_high) >= len(result_low)


# ---------------------------------------------------------------------------
# TestOptimalD
# ---------------------------------------------------------------------------


class TestOptimalD:
    """Tests for the optimal_d function."""

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty series"):
            optimal_d([])

    def test_stationary_series_d_zero(self) -> None:
        # Oscillating series is already stationary -> d=0
        series = [Decimal(str((-1) ** i)) for i in range(100)]
        result = optimal_d(series)
        assert result == ZERO

    def test_nonstationary_returns_positive_d(self) -> None:
        # Quadratic series is non-stationary
        series = [Decimal(str(i * i)) for i in range(100)]
        result = optimal_d(series)
        assert result > ZERO

    def test_result_in_range(self) -> None:
        series = [Decimal(str(i * i)) for i in range(100)]
        max_d = Decimal("1.0")
        result = optimal_d(series, max_d=max_d)
        assert ZERO <= result <= max_d

    def test_no_stationarity_raises(self) -> None:
        # Very small max_d with a step that overshoots -> only d=0 tested
        # For a highly persistent series, d=0 won't be stationary if
        # we demand a very strict threshold (p_value_threshold=1 means acf < 0).
        # That's impossible, so it must raise.
        series = [Decimal(str(i)) for i in range(100)]
        with pytest.raises(ValueError, match="No d in"):
            optimal_d(
                series,
                max_d=Decimal("0.0"),
                step=Decimal("0.05"),
                p_value_threshold=Decimal("1.0"),
            )


# ---------------------------------------------------------------------------
# TestDetrendedFluctuationAnalysis
# ---------------------------------------------------------------------------


class TestDetrendedFluctuationAnalysis:
    """Tests for the detrended_fluctuation_analysis function."""

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="below the minimum"):
            detrended_fluctuation_analysis([Decimal("1")] * 30)

    def test_constant_raises(self) -> None:
        with pytest.raises(ValueError, match="constant series"):
            detrended_fluctuation_analysis([Decimal("5")] * 100)

    def test_random_walk_near_half(self) -> None:
        series = _random_walk(500)
        alpha = detrended_fluctuation_analysis(series)
        assert Decimal("0.3") < alpha < Decimal("0.8")

    def test_result_is_decimal(self) -> None:
        series = _random_walk(200)
        result = detrended_fluctuation_analysis(series)
        assert isinstance(result, Decimal)
