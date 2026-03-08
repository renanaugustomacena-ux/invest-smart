"""Tests for algo_engine.math.ou_process — OrnsteinUhlenbeck, SpreadAnalyzer."""

from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pytest

from moneymaker_common.decimal_utils import ZERO

from algo_engine.math.ou_process import (
    OUParams,
    OrnsteinUhlenbeck,
    SpreadAnalyzer,
)

ONE = Decimal("1")
OU = OrnsteinUhlenbeck


# ---------------------------------------------------------------------------
# Helper: generate a mean-reverting series via simulation
# ---------------------------------------------------------------------------


def _mean_reverting_series(
    theta: float = 0.3,
    mu: float = 100.0,
    sigma: float = 1.0,
    n: int = 200,
    seed: int = 42,
) -> list[Decimal]:
    """Generate an OU path for testing fit()."""
    rng = np.random.default_rng(seed)
    x = np.empty(n, dtype=np.float64)
    x[0] = mu
    for i in range(1, n):
        x[i] = x[i - 1] + theta * (mu - x[i - 1]) + sigma * rng.standard_normal()
    return [Decimal(str(round(v, 8))) for v in x]


# ---------------------------------------------------------------------------
# TestOrnsteinUhlenbeck
# ---------------------------------------------------------------------------


class TestOrnsteinUhlenbeck:
    """Tests for the OrnsteinUhlenbeck class."""

    # --- fit tests ---

    def test_fit_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 30"):
            OU.fit([Decimal("1")] * 10)

    def test_fit_mean_reverting_theta_positive(self) -> None:
        series = _mean_reverting_series(theta=0.3, mu=100.0)
        params = OU.fit(series)
        assert params.theta > ZERO
        assert params.is_valid is True

    def test_fit_recovers_mu(self) -> None:
        series = _mean_reverting_series(theta=0.3, mu=100.0)
        params = OU.fit(series)
        assert abs(params.mu - Decimal("100")) < Decimal("10")

    def test_fit_constant_series_not_valid(self) -> None:
        series = [Decimal("50")] * 50
        params = OU.fit(series)
        assert params.is_valid is False

    def test_fit_trend_not_valid(self) -> None:
        # Linear trend: no mean reversion
        series = [Decimal(str(i)) for i in range(50)]
        params = OU.fit(series)
        # A strong linear trend should produce theta <= 0
        assert params.is_valid is False or params.theta < Decimal("0.01")

    def test_fit_returns_ou_params(self) -> None:
        series = _mean_reverting_series()
        params = OU.fit(series)
        assert isinstance(params, OUParams)

    def test_fit_half_life_finite_when_valid(self) -> None:
        series = _mean_reverting_series()
        params = OU.fit(series)
        assert params.is_valid is True
        assert params.half_life != Decimal("Infinity")
        assert params.half_life > ZERO

    def test_fit_r_squared_non_negative(self) -> None:
        series = _mean_reverting_series()
        params = OU.fit(series)
        assert params.r_squared >= ZERO

    # --- half_life tests ---

    def test_half_life_known_value(self) -> None:
        theta = Decimal("0.5")
        expected = Decimal(str(math.log(2) / 0.5))
        result = OU.half_life(theta)
        assert abs(result - expected) < Decimal("0.001")

    def test_half_life_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            OU.half_life(ZERO)

    def test_half_life_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            OU.half_life(Decimal("-0.1"))

    # --- s_score tests ---

    def test_s_score_at_mean_is_zero(self) -> None:
        result = OU.s_score(Decimal("100"), Decimal("100"), ONE)
        assert result == ZERO

    def test_s_score_above_mean_positive(self) -> None:
        result = OU.s_score(Decimal("102"), Decimal("100"), ONE)
        assert result > ZERO

    def test_s_score_below_mean_negative(self) -> None:
        result = OU.s_score(Decimal("98"), Decimal("100"), ONE)
        assert result < ZERO

    def test_s_score_zero_sigma_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            OU.s_score(Decimal("100"), Decimal("100"), ZERO)

    # --- is_mean_reverting tests ---

    def test_is_mean_reverting_above_threshold(self) -> None:
        assert OU.is_mean_reverting(Decimal("0.05")) is True

    def test_is_mean_reverting_below_threshold(self) -> None:
        assert OU.is_mean_reverting(Decimal("0.005")) is False

    def test_is_mean_reverting_custom_threshold(self) -> None:
        assert OU.is_mean_reverting(Decimal("0.005"), min_theta=Decimal("0.001")) is True

    # --- simulate tests ---

    def test_simulate_length(self) -> None:
        params = OUParams(
            theta=Decimal("0.5"),
            mu=Decimal("100"),
            sigma=ONE,
            half_life=Decimal("1.386"),
            sigma_eq=ONE,
            r_squared=ONE,
            is_valid=True,
        )
        path = OU.simulate(params, Decimal("100"), n_steps=50, seed=42)
        assert len(path) == 51

    def test_simulate_first_element_is_x0(self) -> None:
        params = OUParams(
            theta=Decimal("0.5"),
            mu=Decimal("100"),
            sigma=ONE,
            half_life=Decimal("1.386"),
            sigma_eq=ONE,
            r_squared=ONE,
            is_valid=True,
        )
        path = OU.simulate(params, Decimal("42"), n_steps=10, seed=42)
        assert path[0] == Decimal("42")

    def test_simulate_deterministic_with_seed(self) -> None:
        params = OUParams(
            theta=Decimal("0.5"),
            mu=Decimal("100"),
            sigma=ONE,
            half_life=Decimal("1.386"),
            sigma_eq=ONE,
            r_squared=ONE,
            is_valid=True,
        )
        p1 = OU.simulate(params, Decimal("50"), n_steps=20, seed=99)
        p2 = OU.simulate(params, Decimal("50"), n_steps=20, seed=99)
        assert p1 == p2

    def test_simulate_reverts_toward_mu(self) -> None:
        params = OUParams(
            theta=Decimal("0.8"),
            mu=Decimal("100"),
            sigma=Decimal("0.1"),
            half_life=Decimal("0.866"),
            sigma_eq=Decimal("0.08"),
            r_squared=ONE,
            is_valid=True,
        )
        # Start far from mu
        path = OU.simulate(params, Decimal("50"), n_steps=100, seed=42)
        # Last values should be closer to mu than start
        assert abs(path[-1] - Decimal("100")) < abs(path[0] - Decimal("100"))


# ---------------------------------------------------------------------------
# TestSpreadAnalyzer
# ---------------------------------------------------------------------------


class TestSpreadAnalyzer:
    """Tests for the SpreadAnalyzer class."""

    def test_update_none_if_insufficient(self) -> None:
        analyzer = SpreadAnalyzer(lookback=100)
        for i in range(29):
            result = analyzer.update(Decimal(str(i)))
        assert result is None

    def test_update_returns_params_when_sufficient(self) -> None:
        analyzer = SpreadAnalyzer(lookback=100)
        series = _mean_reverting_series(n=50)
        result = None
        for v in series:
            result = analyzer.update(v)
        assert result is not None
        assert isinstance(result, OUParams)

    def test_get_signal_buy(self) -> None:
        analyzer = SpreadAnalyzer()
        params = OUParams(
            theta=Decimal("0.5"),
            mu=Decimal("100"),
            sigma=ONE,
            half_life=Decimal("1.386"),
            sigma_eq=ONE,
            r_squared=ONE,
            is_valid=True,
        )
        # s_score = (spread - mu) / sigma_eq = (97 - 100) / 1 = -3 < -1.5
        signal = analyzer.get_signal(Decimal("97"), params)
        assert signal["signal"] == "BUY"

    def test_get_signal_sell(self) -> None:
        analyzer = SpreadAnalyzer()
        params = OUParams(
            theta=Decimal("0.5"),
            mu=Decimal("100"),
            sigma=ONE,
            half_life=Decimal("1.386"),
            sigma_eq=ONE,
            r_squared=ONE,
            is_valid=True,
        )
        # s_score = (103 - 100) / 1 = 3 > 1.5
        signal = analyzer.get_signal(Decimal("103"), params)
        assert signal["signal"] == "SELL"

    def test_get_signal_close(self) -> None:
        analyzer = SpreadAnalyzer()
        params = OUParams(
            theta=Decimal("0.5"),
            mu=Decimal("100"),
            sigma=ONE,
            half_life=Decimal("1.386"),
            sigma_eq=ONE,
            r_squared=ONE,
            is_valid=True,
        )
        # s_score = (100.3 - 100) / 1 = 0.3, |0.3| < 0.5
        signal = analyzer.get_signal(Decimal("100.3"), params)
        assert signal["signal"] == "CLOSE"

    def test_get_signal_hold(self) -> None:
        analyzer = SpreadAnalyzer()
        params = OUParams(
            theta=Decimal("0.5"),
            mu=Decimal("100"),
            sigma=ONE,
            half_life=Decimal("1.386"),
            sigma_eq=ONE,
            r_squared=ONE,
            is_valid=True,
        )
        # s_score = (101 - 100) / 1 = 1.0, between 0.5 and 1.5
        signal = analyzer.get_signal(Decimal("101"), params)
        assert signal["signal"] == "HOLD"

    def test_get_signal_invalid_params_hold(self) -> None:
        analyzer = SpreadAnalyzer()
        params = OUParams(
            theta=ZERO,
            mu=Decimal("100"),
            sigma=ZERO,
            half_life=Decimal("Infinity"),
            sigma_eq=ZERO,
            r_squared=ZERO,
            is_valid=False,
        )
        signal = analyzer.get_signal(Decimal("50"), params)
        assert signal["signal"] == "HOLD"

    def test_get_signal_dict_keys(self) -> None:
        analyzer = SpreadAnalyzer()
        params = OUParams(
            theta=Decimal("0.5"),
            mu=Decimal("100"),
            sigma=ONE,
            half_life=Decimal("1.386"),
            sigma_eq=ONE,
            r_squared=ONE,
            is_valid=True,
        )
        signal = analyzer.get_signal(Decimal("100"), params)
        assert "s_score" in signal
        assert "half_life" in signal
        assert "signal" in signal
