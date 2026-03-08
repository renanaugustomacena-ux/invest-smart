"""Tests for algo_engine.math.stochastic — GBM, MertonJumpDiffusion, HestonStochasticVolatility."""

from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pytest

from moneymaker_common.decimal_utils import ZERO

from algo_engine.math.stochastic import (
    GeometricBrownianMotion,
    HestonStochasticVolatility,
    MertonJumpDiffusion,
)

ONE = Decimal("1")
GBM = GeometricBrownianMotion
MJD = MertonJumpDiffusion
HSV = HestonStochasticVolatility


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normal_returns(n: int = 100, mu: float = 0.0005, sigma: float = 0.01, seed: int = 42) -> list[Decimal]:
    """Generate normal log returns."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(mu, sigma, n)
    return [Decimal(str(round(v, 10))) for v in returns]


def _fat_tailed_returns(n: int = 100, seed: int = 42) -> list[Decimal]:
    """Normal returns with injected outliers for jump detection."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0, 0.01, n)
    # Inject large jumps
    for idx in [10, 30, 50, 70, 90]:
        returns[idx] = rng.choice([-1, 1]) * 0.08
    return [Decimal(str(round(v, 10))) for v in returns]


# ---------------------------------------------------------------------------
# TestGeometricBrownianMotion
# ---------------------------------------------------------------------------


class TestGeometricBrownianMotion:
    """Tests for the GeometricBrownianMotion class."""

    # --- fit tests ---

    def test_fit_empty_returns_zeros(self) -> None:
        mu, sigma = GBM.fit([])
        assert mu == ZERO
        assert sigma == ZERO

    def test_fit_insufficient_returns_zeros(self) -> None:
        mu, sigma = GBM.fit([Decimal("0.01")] * 5)
        assert mu == ZERO
        assert sigma == ZERO

    def test_fit_constant_returns_zeros(self) -> None:
        mu, sigma = GBM.fit([Decimal("0.01")] * 20)
        assert mu == ZERO
        assert sigma == ZERO

    def test_fit_positive_returns_positive_sigma(self) -> None:
        returns = _normal_returns(100)
        mu, sigma = GBM.fit(returns)
        assert sigma > ZERO

    def test_fit_result_is_decimal(self) -> None:
        returns = _normal_returns(50)
        mu, sigma = GBM.fit(returns)
        assert isinstance(mu, Decimal)
        assert isinstance(sigma, Decimal)

    # --- simulate_paths tests ---

    def test_simulate_shape(self) -> None:
        paths = GBM.simulate_paths(s0=100.0, mu=0.05, sigma=0.2, t=1.0, dt=1 / 252, n_paths=10, seed=42)
        n_steps = int(round(1.0 / (1 / 252)))
        assert paths.shape == (n_steps + 1, 10)

    def test_simulate_first_row_is_s0(self) -> None:
        paths = GBM.simulate_paths(s0=50.0, mu=0.05, sigma=0.2, t=1.0, dt=1 / 252, n_paths=5, seed=42)
        np.testing.assert_allclose(paths[0], 50.0)

    def test_simulate_all_positive(self) -> None:
        paths = GBM.simulate_paths(s0=100.0, mu=0.05, sigma=0.2, t=1.0, dt=1 / 252, n_paths=20, seed=42)
        assert np.all(paths > 0)

    def test_simulate_s0_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            GBM.simulate_paths(s0=0.0, mu=0.05, sigma=0.2, t=1.0, dt=1 / 252, n_paths=1)

    def test_simulate_negative_sigma_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            GBM.simulate_paths(s0=100.0, mu=0.05, sigma=-0.1, t=1.0, dt=1 / 252, n_paths=1)

    def test_simulate_dt_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            GBM.simulate_paths(s0=100.0, mu=0.05, sigma=0.2, t=1.0, dt=0.0, n_paths=1)

    def test_simulate_deterministic_seed(self) -> None:
        p1 = GBM.simulate_paths(s0=100.0, mu=0.05, sigma=0.2, t=0.1, dt=1 / 252, n_paths=5, seed=99)
        p2 = GBM.simulate_paths(s0=100.0, mu=0.05, sigma=0.2, t=0.1, dt=1 / 252, n_paths=5, seed=99)
        np.testing.assert_array_equal(p1, p2)

    def test_simulate_zero_sigma_pure_drift(self) -> None:
        # With sigma=0, S(t) = S0 * exp(mu * t)
        paths = GBM.simulate_paths(s0=100.0, mu=0.1, sigma=0.0, t=1.0, dt=1 / 252, n_paths=1, seed=42)
        expected_final = 100.0 * math.exp(0.1 * 1.0)
        assert abs(paths[-1, 0] - expected_final) < 0.01


# ---------------------------------------------------------------------------
# TestMertonJumpDiffusion
# ---------------------------------------------------------------------------


class TestMertonJumpDiffusion:
    """Tests for the MertonJumpDiffusion class."""

    # --- fit tests ---

    def test_fit_empty_returns_zeros(self) -> None:
        result = MJD.fit([])
        assert result["mu"] == ZERO
        assert result["lam"] == ZERO

    def test_fit_insufficient_returns_zeros(self) -> None:
        result = MJD.fit([Decimal("0.01")] * 5)
        assert result["sigma"] == ZERO

    def test_fit_constant_returns_zeros(self) -> None:
        result = MJD.fit([Decimal("0.01")] * 20)
        assert result["sigma"] == ZERO

    def test_fit_all_keys_present(self) -> None:
        returns = _normal_returns(100)
        result = MJD.fit(returns)
        assert set(result.keys()) == {"mu", "sigma", "lam", "mu_j", "sigma_j"}

    def test_fit_normal_returns_low_lambda(self) -> None:
        # Normal returns have near-zero excess kurtosis -> lam should be 0
        returns = _normal_returns(200, sigma=0.01, seed=42)
        result = MJD.fit(returns)
        # Either lam is zero (no kurtosis) or small
        # Normal data can have some sample kurtosis, so just check it's not huge
        assert result["lam"] < Decimal("100")

    def test_fit_fat_tailed_positive_lambda(self) -> None:
        returns = _fat_tailed_returns(200, seed=42)
        result = MJD.fit(returns)
        assert result["lam"] > ZERO

    # --- jump_probability tests ---

    def test_jump_probability_insufficient_returns_zero(self) -> None:
        result = MJD.jump_probability([Decimal("0.01")] * 5, window=20)
        assert result == ZERO

    def test_jump_probability_no_jumps_zero(self) -> None:
        # Constant returns: no jumps
        returns = [Decimal("0.001")] * 50
        result = MJD.jump_probability(returns, window=20)
        assert result == ZERO

    def test_jump_probability_in_range(self) -> None:
        returns = _fat_tailed_returns(100, seed=42)
        result = MJD.jump_probability(returns, window=20)
        assert ZERO <= result <= ONE

    def test_jump_probability_extreme_detected(self) -> None:
        # Insert massive outlier in recent window
        returns = _normal_returns(100, sigma=0.01, seed=42)
        returns[-5] = Decimal("0.5")  # 50x sigma
        result = MJD.jump_probability(returns, window=20, threshold_sigma=Decimal("3"))
        assert result > ZERO

    # --- simulate_paths tests ---

    def test_simulate_shape(self) -> None:
        params = {"mu": 0.05, "sigma": 0.2, "lam": 5.0, "mu_j": -0.01, "sigma_j": 0.03}
        paths = MJD.simulate_paths(params, s0=100.0, t=1.0, dt=1 / 252, n_paths=5, seed=42)
        n_steps = int(round(1.0 / (1 / 252)))
        assert paths.shape == (n_steps + 1, 5)

    def test_simulate_s0_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            MJD.simulate_paths({}, s0=0.0, t=1.0, dt=1 / 252, n_paths=1)

    def test_simulate_deterministic_seed(self) -> None:
        params = {"mu": 0.05, "sigma": 0.2, "lam": 5.0, "mu_j": 0.0, "sigma_j": 0.02}
        p1 = MJD.simulate_paths(params, s0=100.0, t=0.1, dt=1 / 252, n_paths=3, seed=99)
        p2 = MJD.simulate_paths(params, s0=100.0, t=0.1, dt=1 / 252, n_paths=3, seed=99)
        np.testing.assert_array_equal(p1, p2)

    def test_simulate_first_row_is_s0(self) -> None:
        params = {"mu": 0.05, "sigma": 0.2, "lam": 1.0, "mu_j": 0.0, "sigma_j": 0.01}
        paths = MJD.simulate_paths(params, s0=42.0, t=0.5, dt=1 / 252, n_paths=3, seed=42)
        np.testing.assert_allclose(paths[0], 42.0)


# ---------------------------------------------------------------------------
# TestHestonStochasticVolatility
# ---------------------------------------------------------------------------


class TestHestonStochasticVolatility:
    """Tests for the HestonStochasticVolatility class."""

    # --- fit tests ---

    def _sample_data(self, n: int = 100, seed: int = 42) -> tuple[list[Decimal], list[Decimal]]:
        """Generate returns and realized vol series for Heston fit."""
        rng = np.random.default_rng(seed)
        returns = rng.normal(0.0005, 0.01, n)
        # Realized vol: abs returns smoothed
        vol = np.abs(returns) * np.sqrt(252)
        vol = np.maximum(vol, 0.001)  # Ensure positive
        return (
            [Decimal(str(round(v, 10))) for v in returns],
            [Decimal(str(round(v, 10))) for v in vol],
        )

    def test_fit_empty_returns_zeros(self) -> None:
        result = HSV.fit([], [])
        assert result["kappa"] == ZERO

    def test_fit_mismatched_returns_zeros(self) -> None:
        returns = _normal_returns(50)
        vol = [Decimal("0.01")] * 30
        result = HSV.fit(returns, vol)
        assert result["theta"] == ZERO

    def test_fit_all_keys_present(self) -> None:
        returns, vol = self._sample_data()
        result = HSV.fit(returns, vol)
        assert set(result.keys()) == {"mu", "kappa", "theta", "xi", "rho"}

    def test_fit_positive_kappa(self) -> None:
        returns, vol = self._sample_data()
        result = HSV.fit(returns, vol)
        assert result["kappa"] > ZERO

    def test_fit_positive_theta(self) -> None:
        returns, vol = self._sample_data()
        result = HSV.fit(returns, vol)
        assert result["theta"] > ZERO

    def test_fit_rho_in_range(self) -> None:
        returns, vol = self._sample_data()
        result = HSV.fit(returns, vol)
        assert Decimal("-1") <= result["rho"] <= ONE

    # --- simulate_paths tests ---

    def test_simulate_returns_tuple(self) -> None:
        params = {"mu": 0.05, "kappa": 2.0, "theta": 0.04, "xi": 0.3, "rho": -0.7}
        result = HSV.simulate_paths(params, s0=100.0, v0=0.04, t=0.5, dt=1 / 252, n_paths=3, seed=42)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_simulate_shapes_match(self) -> None:
        params = {"mu": 0.05, "kappa": 2.0, "theta": 0.04, "xi": 0.3, "rho": -0.7}
        prices, vols = HSV.simulate_paths(params, s0=100.0, v0=0.04, t=1.0, dt=1 / 252, n_paths=5, seed=42)
        assert prices.shape == vols.shape

    def test_simulate_s0_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            HSV.simulate_paths({}, s0=0.0, v0=0.04, t=1.0, dt=1 / 252, n_paths=1)

    def test_simulate_v0_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            HSV.simulate_paths({}, s0=100.0, v0=-0.01, t=1.0, dt=1 / 252, n_paths=1)

    def test_simulate_deterministic_seed(self) -> None:
        params = {"mu": 0.05, "kappa": 2.0, "theta": 0.04, "xi": 0.3, "rho": -0.7}
        p1, v1 = HSV.simulate_paths(params, s0=100.0, v0=0.04, t=0.1, dt=1 / 252, n_paths=3, seed=99)
        p2, v2 = HSV.simulate_paths(params, s0=100.0, v0=0.04, t=0.1, dt=1 / 252, n_paths=3, seed=99)
        np.testing.assert_array_equal(p1, p2)
        np.testing.assert_array_equal(v1, v2)

    def test_simulate_first_row_s0(self) -> None:
        params = {"mu": 0.05, "kappa": 2.0, "theta": 0.04, "xi": 0.3, "rho": -0.7}
        prices, vols = HSV.simulate_paths(params, s0=50.0, v0=0.04, t=0.5, dt=1 / 252, n_paths=3, seed=42)
        np.testing.assert_allclose(prices[0], 50.0)
        np.testing.assert_allclose(vols[0], 0.04)
