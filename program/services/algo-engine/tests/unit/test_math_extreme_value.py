"""Tests for algo_engine.math.extreme_value — GPD, TailRiskAnalyzer, ES."""

from __future__ import annotations

import math
from decimal import Decimal

import pytest

from moneymaker_common.decimal_utils import ZERO

from algo_engine.math.extreme_value import (
    GeneralizedParetoDistribution,
    TailRiskAnalyzer,
    expected_shortfall_historical,
)

ONE = Decimal("1")
GPD = GeneralizedParetoDistribution


# ---------------------------------------------------------------------------
# TestGeneralizedParetoDistribution
# ---------------------------------------------------------------------------


class TestGeneralizedParetoDistribution:
    """Tests for GPD fit, cdf, var, cvar."""

    # --- fit tests ---

    def test_fit_insufficient_data_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 20"):
            GPD.fit([Decimal("1")] * 10)

    def test_fit_degenerate_denominator_raises(self) -> None:
        # Exponential-like data causes degenerate PWM denominator or negative sigma
        exceedances = [Decimal(str(i + 1)) for i in range(30)]
        with pytest.raises(ValueError):
            GPD.fit(exceedances)

    def test_fit_single_point_raises(self) -> None:
        # Only 1 distinct value repeated
        with pytest.raises(ValueError):
            GPD.fit([Decimal("1")] * 20)

    # --- CDF tests ---

    def test_cdf_zero_at_zero(self) -> None:
        result = GPD.cdf(ZERO, Decimal("0.1"), ONE)
        assert result == ZERO

    def test_cdf_approaches_one_for_large_x(self) -> None:
        result = GPD.cdf(Decimal("100"), Decimal("0.1"), ONE)
        assert result > Decimal("0.99")

    def test_cdf_negative_x_returns_zero(self) -> None:
        result = GPD.cdf(Decimal("-1"), Decimal("0.1"), ONE)
        assert result == ZERO

    def test_cdf_negative_sigma_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            GPD.cdf(ONE, Decimal("0.1"), Decimal("-1"))

    def test_cdf_zero_sigma_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            GPD.cdf(ONE, Decimal("0.1"), ZERO)

    def test_cdf_near_zero_xi_exponential(self) -> None:
        # xi ~ 0 -> CDF(x) = 1 - exp(-x/sigma)
        result = GPD.cdf(ONE, ZERO, ONE)
        expected = Decimal(str(1 - math.exp(-1)))
        assert abs(result - expected) < Decimal("0.01")

    def test_cdf_in_valid_range(self) -> None:
        result = GPD.cdf(Decimal("5"), Decimal("0.2"), Decimal("2"))
        assert ZERO <= result <= ONE

    def test_cdf_monotonically_increasing(self) -> None:
        xi, sigma = Decimal("0.1"), ONE
        c1 = GPD.cdf(Decimal("1"), xi, sigma)
        c2 = GPD.cdf(Decimal("5"), xi, sigma)
        c3 = GPD.cdf(Decimal("20"), xi, sigma)
        assert c1 <= c2 <= c3

    def test_cdf_negative_xi_bounded_support(self) -> None:
        # For xi < 0, support is bounded at x = -sigma/xi
        xi = Decimal("-0.5")
        sigma = ONE
        # Upper bound = -sigma/xi = 2.0
        # Beyond support should return 1
        result = GPD.cdf(Decimal("3"), xi, sigma)
        assert result == ONE

    # --- VaR tests ---

    def test_var_invalid_alpha_raises(self) -> None:
        with pytest.raises(ValueError, match="alpha"):
            GPD.var(Decimal("1.5"), Decimal("0.1"), ONE, 1000, 50)

    def test_var_zero_alpha_raises(self) -> None:
        with pytest.raises(ValueError, match="alpha"):
            GPD.var(ZERO, Decimal("0.1"), ONE, 1000, 50)

    def test_var_zero_n_exceed_raises(self) -> None:
        with pytest.raises(ValueError, match="n_exceed"):
            GPD.var(Decimal("0.95"), Decimal("0.1"), ONE, 1000, 0)

    def test_var_returns_decimal(self) -> None:
        result = GPD.var(Decimal("0.95"), Decimal("0.1"), ONE, 1000, 50)
        assert isinstance(result, Decimal)

    def test_var_higher_alpha_larger(self) -> None:
        # Higher confidence = higher VaR
        var_95 = GPD.var(Decimal("0.95"), Decimal("0.1"), ONE, 1000, 50)
        var_99 = GPD.var(Decimal("0.99"), Decimal("0.1"), ONE, 1000, 50)
        assert var_99 > var_95

    # --- CVaR tests ---

    def test_cvar_xi_ge_one_raises(self) -> None:
        with pytest.raises(ValueError, match="xi >= 1"):
            GPD.cvar(Decimal("0.95"), Decimal("1.5"), ONE, ZERO, 1000, 50)

    def test_cvar_exceeds_or_equals_var(self) -> None:
        xi = Decimal("0.2")
        sigma = ONE
        alpha = Decimal("0.95")
        var_val = GPD.var(alpha, xi, sigma, 1000, 50)
        cvar_val = GPD.cvar(alpha, xi, sigma, Decimal("0.5"), 1000, 50)
        assert cvar_val >= var_val

    def test_cvar_returns_decimal(self) -> None:
        result = GPD.cvar(Decimal("0.95"), Decimal("0.2"), ONE, Decimal("0.5"), 1000, 50)
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# TestTailRiskAnalyzer
# ---------------------------------------------------------------------------


class TestTailRiskAnalyzer:
    """Tests for the TailRiskAnalyzer class."""

    def test_insufficient_returns_raises(self) -> None:
        analyzer = TailRiskAnalyzer()
        with pytest.raises(ValueError, match="at least 20"):
            analyzer.analyze([Decimal("0.01")] * 10)

    def test_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            TailRiskAnalyzer(confidence=Decimal("1.5"))

    def test_invalid_zero_confidence_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            TailRiskAnalyzer(confidence=ZERO)

    def test_invalid_threshold_pct_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold_percentile"):
            TailRiskAnalyzer(threshold_percentile=ZERO)

    def test_invalid_threshold_pct_one_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold_percentile"):
            TailRiskAnalyzer(threshold_percentile=ONE)

    def test_valid_construction(self) -> None:
        analyzer = TailRiskAnalyzer(
            confidence=Decimal("0.95"),
            threshold_percentile=Decimal("0.90"),
        )
        assert analyzer._confidence == Decimal("0.95")
        assert analyzer._threshold_pct == Decimal("0.90")

    def test_analyze_insufficient_exceedances_raises(self) -> None:
        # threshold_percentile=0.99 on 30 returns -> < 1 exceedance
        analyzer = TailRiskAnalyzer(
            confidence=Decimal("0.95"),
            threshold_percentile=Decimal("0.99"),
        )
        returns = [Decimal(str(i * 0.001)) for i in range(30)]
        with pytest.raises(ValueError, match="exceedances"):
            analyzer.analyze(returns)


# ---------------------------------------------------------------------------
# TestExpectedShortfallHistorical
# ---------------------------------------------------------------------------


class TestExpectedShortfallHistorical:
    """Tests for the expected_shortfall_historical function."""

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="not be empty"):
            expected_shortfall_historical([])

    def test_alpha_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="alpha"):
            expected_shortfall_historical([Decimal("1")], alpha=ZERO)

    def test_alpha_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="alpha"):
            expected_shortfall_historical([Decimal("1")], alpha=Decimal("-0.1"))

    def test_known_values(self) -> None:
        # [-5,-4,-3,-2,-1,0,1,2,3,4], worst 20% = [-5,-4], ES = -4.5
        returns = [Decimal(str(i)) for i in range(-5, 5)]
        result = expected_shortfall_historical(returns, alpha=Decimal("0.2"))
        assert result == Decimal("-4.5")

    def test_all_negative_returns(self) -> None:
        returns = [Decimal("-1")] * 20
        result = expected_shortfall_historical(returns, alpha=Decimal("0.05"))
        assert result == Decimal("-1")

    def test_alpha_one_is_mean(self) -> None:
        returns = [Decimal("1"), Decimal("2"), Decimal("3")]
        result = expected_shortfall_historical(returns, alpha=ONE)
        assert result == Decimal("2")

    def test_single_return(self) -> None:
        result = expected_shortfall_historical([Decimal("-3")], alpha=Decimal("0.05"))
        assert result == Decimal("-3")

    def test_result_is_decimal(self) -> None:
        returns = [Decimal(str(i)) for i in range(-10, 10)]
        result = expected_shortfall_historical(returns, alpha=Decimal("0.1"))
        assert isinstance(result, Decimal)

    def test_es_more_negative_than_var(self) -> None:
        # ES (average of tail) should be <= any individual tail quantile cutoff
        returns = [Decimal(str(i)) for i in range(-20, 20)]
        es = expected_shortfall_historical(returns, alpha=Decimal("0.1"))
        # Worst 10% of 40 values = 4 values = [-20, -19, -18, -17]
        assert es < Decimal("-15")
