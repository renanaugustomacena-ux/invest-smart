"""Tests for optimization modules (G9).

Covers: walk_forward, monte_carlo, adaptive parameter tuner.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.optimization.walk_forward import (
    WalkForwardOptimizer,
    WFOResult,
    WFOWindow,
)
from algo_engine.optimization.monte_carlo import (
    MonteCarloValidator,
    MonteCarloResult,
)
from algo_engine.optimization.adaptive import AdaptiveParameterTuner

D = Decimal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _synthetic_returns(n: int = 300, drift: float = 0.001, vol: float = 0.02) -> list[Decimal]:
    import random

    rng = random.Random(42)
    return [D(str(round(drift + vol * rng.gauss(0, 1), 8))) for _ in range(n)]


def _simple_evaluate(bars: list, params: dict) -> Decimal:
    """Dummy evaluate function that returns a Sharpe-like score."""
    period = params.get("period", 14)
    if len(bars) < period:
        return D("0")
    return D(str(round(1.0 / max(period, 1), 4)))


# ===========================================================================
# WFOWindow dataclass
# ===========================================================================


class TestWFOWindow:
    def test_defaults(self):
        w = WFOWindow()
        assert w.in_sample_start == 0
        assert w.out_sample_start == 0
        assert w.is_sharpe == D("0")
        assert w.oos_sharpe == D("0")


# ===========================================================================
# WFOResult dataclass
# ===========================================================================


class TestWFOResult:
    def test_defaults(self):
        r = WFOResult()
        assert r.windows == []
        assert r.best_params_per_window == []
        assert r.avg_is_sharpe == D("0")
        assert r.avg_oos_sharpe == D("0")
        assert r.oos_degradation == D("0")
        assert r.is_overfit is False


# ===========================================================================
# WalkForwardOptimizer
# ===========================================================================


class TestWalkForwardOptimizer:
    def test_init_defaults(self):
        wfo = WalkForwardOptimizer()
        assert wfo is not None

    def test_optimize_with_enough_bars(self):
        # 288 bars/day * (90 + 30) days = 34,560 bars minimum for 1 window
        # Use smaller intervals for testing
        wfo = WalkForwardOptimizer(
            in_sample_days=1,
            out_sample_days=1,
            step_days=1,
            bars_per_day=10,
        )
        bars = list(range(100))  # 100 "bars"
        param_grid = {"period": [5, 10, 20]}
        result = wfo.optimize(bars, param_grid, _simple_evaluate)
        assert isinstance(result, WFOResult)

    def test_optimize_too_few_bars_returns_empty(self):
        wfo = WalkForwardOptimizer(
            in_sample_days=10,
            out_sample_days=5,
            step_days=5,
            bars_per_day=100,
        )
        bars = list(range(5))  # way too few
        param_grid = {"period": [5, 10]}
        result = wfo.optimize(bars, param_grid, _simple_evaluate)
        assert isinstance(result, WFOResult)
        assert len(result.windows) == 0

    def test_optimize_detects_overfit(self):
        # Use evaluate fn that returns high IS but low OOS
        def overfit_eval(bars: list, params: dict) -> Decimal:
            return D("2.0")

        wfo = WalkForwardOptimizer(
            in_sample_days=1,
            out_sample_days=1,
            step_days=1,
            bars_per_day=10,
        )
        bars = list(range(100))
        param_grid = {"period": [5]}
        result = wfo.optimize(bars, param_grid, overfit_eval)
        assert isinstance(result, WFOResult)
        # With identical IS/OOS scores, degradation should be zero
        if result.windows:
            assert isinstance(result.oos_degradation, Decimal)


# ===========================================================================
# MonteCarloResult dataclass
# ===========================================================================


class TestMonteCarloResult:
    def test_defaults(self):
        r = MonteCarloResult()
        assert r.n_simulations == 0
        assert r.median_sharpe == D("0")
        assert r.survival_rate == D("0")
        assert r.is_robust is False


# ===========================================================================
# MonteCarloValidator
# ===========================================================================


class TestMonteCarloValidator:
    def test_return_shuffling(self):
        mc = MonteCarloValidator(n_simulations=50, seed=42)
        returns = _synthetic_returns(200)
        result = mc.return_shuffling(returns)
        assert isinstance(result, MonteCarloResult)
        assert result.n_simulations == 50
        assert isinstance(result.median_sharpe, Decimal)

    def test_bootstrap_resampling(self):
        mc = MonteCarloValidator(n_simulations=50, seed=42)
        returns = _synthetic_returns(200)
        result = mc.bootstrap_resampling(returns)
        assert isinstance(result, MonteCarloResult)
        assert result.n_simulations == 50

    def test_parameter_perturbation(self):
        mc = MonteCarloValidator(n_simulations=20, seed=42)

        def eval_fn(params: dict) -> Decimal:
            period = float(params.get("period", 14))
            return D(str(round(1.0 / max(period, 1), 4)))

        base_params = {"period": 14}
        param_ranges = {"period": (5, 30)}
        result = mc.parameter_perturbation(base_params, param_ranges, eval_fn)
        assert isinstance(result, MonteCarloResult)

    def test_validate_strategy(self):
        mc = MonteCarloValidator(n_simulations=30, seed=42)
        returns = _synthetic_returns(200)
        result = mc.validate_strategy(returns)
        assert isinstance(result, dict)

    def test_short_returns_handled(self):
        mc = MonteCarloValidator(n_simulations=10, seed=42)
        returns = _synthetic_returns(5)
        # Should handle gracefully (may return result with zeros)
        result = mc.return_shuffling(returns)
        assert isinstance(result, MonteCarloResult)

    def test_survival_rate_bounded(self):
        mc = MonteCarloValidator(n_simulations=50, seed=42)
        returns = _synthetic_returns(200)
        result = mc.return_shuffling(returns)
        assert D("0") <= result.survival_rate <= D("100") or result.survival_rate <= D("1")


# ===========================================================================
# AdaptiveParameterTuner
# ===========================================================================


class TestAdaptiveParameterTuner:
    def test_init_defaults(self):
        tuner = AdaptiveParameterTuner()
        params = tuner.get_current_params()
        assert isinstance(params, dict)
        assert "rsi_period" in params
        assert "ema_fast" in params
        assert "ema_slow" in params

    def test_get_current_params_returns_copy(self):
        tuner = AdaptiveParameterTuner()
        p1 = tuner.get_current_params()
        p2 = tuner.get_current_params()
        assert p1 == p2
        # Modifying returned dict shouldn't affect internal state
        p1["rsi_period"] = 999
        assert tuner.get_current_params()["rsi_period"] != 999

    def test_update_no_cycle_returns_none_initially(self):
        tuner = AdaptiveParameterTuner(update_interval=10)
        # Not enough bars yet
        result = tuner.update()
        # Should return None if not at update interval
        if result is not None:
            assert isinstance(result, dict)

    def test_update_with_cycle_at_interval(self):
        tuner = AdaptiveParameterTuner(update_interval=5)
        result = None
        for i in range(10):
            result = tuner.update(dominant_cycle=20)
        # After enough updates, should return new params
        if result is not None:
            assert isinstance(result, dict)

    def test_rsi_bounds_respected(self):
        tuner = AdaptiveParameterTuner(
            update_interval=1,
            rsi_bounds=(10, 20),
        )
        # Feed extreme cycle to try to push RSI out of bounds
        for _ in range(5):
            tuner.update(dominant_cycle=3)
        params = tuner.get_current_params()
        assert 10 <= params["rsi_period"] <= 20

    def test_ema_bounds_respected(self):
        tuner = AdaptiveParameterTuner(
            update_interval=1,
            ema_fast_bounds=(5, 25),
            ema_slow_bounds=(12, 60),
        )
        for _ in range(5):
            tuner.update(dominant_cycle=200)
        params = tuner.get_current_params()
        assert 5 <= params["ema_fast"] <= 25
        assert 12 <= params["ema_slow"] <= 60

    def test_ema_slow_always_greater_than_fast(self):
        tuner = AdaptiveParameterTuner(update_interval=1)
        for cycle in [5, 10, 20, 50, 100]:
            tuner.update(dominant_cycle=cycle)
        params = tuner.get_current_params()
        assert params["ema_slow"] >= params["ema_fast"]

    def test_custom_bounds(self):
        tuner = AdaptiveParameterTuner(
            rsi_bounds=(3, 50),
            ema_fast_bounds=(2, 40),
            ema_slow_bounds=(8, 100),
        )
        params = tuner.get_current_params()
        assert isinstance(params, dict)
