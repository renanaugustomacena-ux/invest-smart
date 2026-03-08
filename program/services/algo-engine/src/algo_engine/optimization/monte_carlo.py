"""Monte Carlo robustness validation.

Three independent tests — return shuffling, bootstrap resampling, and
parameter perturbation — quantify how fragile a strategy's edge really is.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

import numpy as np

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

_TWO = Decimal("2")
_SQRT_252 = Decimal(str(math.sqrt(252)))


@dataclass
class MonteCarloResult:
    """Aggregate statistics from a Monte Carlo simulation batch."""

    n_simulations: int = 0
    median_sharpe: Decimal = ZERO
    pct_5_sharpe: Decimal = ZERO
    pct_95_sharpe: Decimal = ZERO
    pct_95_drawdown: Decimal = ZERO
    survival_rate: Decimal = ZERO
    is_robust: bool = False


class MonteCarloValidator:
    """Monte Carlo robustness testing for trading strategies.

    Parameters
    ----------
    n_simulations:
        Number of Monte Carlo iterations per test.
    seed:
        Random seed for reproducibility.
    """

    def __init__(self, n_simulations: int = 1000, seed: int = 42) -> None:
        self._n_simulations = n_simulations
        self._rng = np.random.default_rng(seed)
        logger.info(
            "MonteCarloValidator initialised: n=%d, seed=%d",
            n_simulations,
            seed,
        )

    # ------------------------------------------------------------------
    # Public tests
    # ------------------------------------------------------------------

    def return_shuffling(self, returns: list[Decimal]) -> MonteCarloResult:
        """Shuffle the order of returns to destroy serial correlation.

        If the strategy's edge relies on the *sequence* of returns rather
        than their overall distribution this test will show degradation.
        """
        arr = np.array([float(r) for r in returns])
        sharpes: list[float] = []
        drawdowns: list[float] = []

        for _ in range(self._n_simulations):
            shuffled = self._rng.permutation(arr)
            sharpes.append(self._sharpe(shuffled))
            drawdowns.append(self._max_drawdown(shuffled))

        return self._build_result(sharpes, drawdowns)

    def bootstrap_resampling(self, returns: list[Decimal]) -> MonteCarloResult:
        """Resample returns with replacement (classic bootstrap)."""
        arr = np.array([float(r) for r in returns])
        n = len(arr)
        sharpes: list[float] = []
        drawdowns: list[float] = []

        for _ in range(self._n_simulations):
            sample = self._rng.choice(arr, size=n, replace=True)
            sharpes.append(self._sharpe(sample))
            drawdowns.append(self._max_drawdown(sample))

        return self._build_result(sharpes, drawdowns)

    def parameter_perturbation(
        self,
        base_params: dict,
        param_ranges: dict,
        evaluate_fn: Callable,
    ) -> MonteCarloResult:
        """Perturb each parameter by +/-10% and evaluate stability.

        Parameters
        ----------
        base_params:
            Baseline parameter dictionary (name -> numeric value).
        param_ranges:
            Allowed (min, max) for each parameter.
        evaluate_fn:
            ``evaluate_fn(params) -> Decimal`` returning Sharpe ratio.
        """
        sharpes: list[float] = []

        for _ in range(self._n_simulations):
            perturbed: dict = {}
            for name, value in base_params.items():
                low = float(value) * 0.9
                high = float(value) * 1.1
                if name in param_ranges:
                    p_min, p_max = param_ranges[name]
                    low = max(low, float(p_min))
                    high = min(high, float(p_max))
                perturbed[name] = Decimal(
                    str(round(self._rng.uniform(low, high), 6))
                )
            sharpe = evaluate_fn(perturbed)
            sharpes.append(float(sharpe))

        return self._build_result(sharpes, [0.0] * len(sharpes))

    def validate_strategy(self, returns: list[Decimal]) -> dict:
        """Run all three return-based tests and produce a combined report.

        Returns a dict with keys ``shuffle``, ``bootstrap``,
        ``perturbation`` (None for perturbation since it requires extra
        inputs), plus overfitting flags.
        """
        shuffle_result = self.return_shuffling(returns)
        bootstrap_result = self.bootstrap_resampling(returns)

        # Compute raw strategy Sharpe for flag checks
        arr = np.array([float(r) for r in returns])
        raw_sharpe = Decimal(str(round(self._sharpe(arr), 6)))
        gross_profit = sum(r for r in returns if r > ZERO)
        gross_loss = abs(sum(r for r in returns if r < ZERO))
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss != ZERO
            else Decimal("999")
        )

        return {
            "shuffle": shuffle_result,
            "bootstrap": bootstrap_result,
            "perturbation": None,
            "raw_sharpe": raw_sharpe,
            "profit_factor": profit_factor,
            "overfitting_flags": {
                "sharpe_suspiciously_high": raw_sharpe > Decimal("3.0"),
                "profit_factor_suspiciously_high": profit_factor > Decimal("3.0"),
                "shuffle_robust": shuffle_result.is_robust,
                "bootstrap_robust": bootstrap_result.is_robust,
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sharpe(returns: np.ndarray) -> float:
        """Annualised Sharpe from an array of period returns."""
        if len(returns) < 2:
            return 0.0
        mean = float(np.mean(returns))
        std = float(np.std(returns, ddof=1))
        if std == 0.0:
            return 0.0
        return (mean / std) * math.sqrt(252)

    @staticmethod
    def _max_drawdown(returns: np.ndarray) -> float:
        """Maximum drawdown from a return series."""
        cumulative = np.cumprod(1.0 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (running_max - cumulative) / running_max
        return float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    def _build_result(
        self,
        sharpes: list[float],
        drawdowns: list[float],
    ) -> MonteCarloResult:
        s = np.array(sharpes)
        d = np.array(drawdowns)
        profitable = float(np.mean(s > 0.0))

        pct_5_sharpe = Decimal(str(round(float(np.percentile(s, 5)), 6)))

        return MonteCarloResult(
            n_simulations=self._n_simulations,
            median_sharpe=Decimal(str(round(float(np.median(s)), 6))),
            pct_5_sharpe=pct_5_sharpe,
            pct_95_sharpe=Decimal(str(round(float(np.percentile(s, 95)), 6))),
            pct_95_drawdown=Decimal(str(round(float(np.percentile(d, 95)), 6))),
            survival_rate=Decimal(str(round(profitable, 6))),
            is_robust=pct_5_sharpe > ZERO,
        )
