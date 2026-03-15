"""Walk-Forward Optimization engine.

Splits historical bars into rolling in-sample / out-of-sample windows,
performs grid search on IS data, and validates on OOS data to detect
overfitting before it reaches live trading.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WFOWindow:
    """A single walk-forward window with IS and OOS index boundaries."""

    in_sample_start: int = 0
    in_sample_end: int = 0
    out_sample_start: int = 0
    out_sample_end: int = 0
    is_sharpe: Decimal = ZERO
    oos_sharpe: Decimal = ZERO


@dataclass
class WFOResult:
    """Aggregated walk-forward optimization result across all windows."""

    windows: list[WFOWindow] = field(default_factory=list)
    best_params_per_window: list[dict[str, Any]] = field(default_factory=list)
    avg_is_sharpe: Decimal = ZERO
    avg_oos_sharpe: Decimal = ZERO
    oos_degradation: Decimal = ZERO
    is_overfit: bool = False


class WalkForwardOptimizer:
    """Rolling walk-forward optimizer with grid search.

    Parameters
    ----------
    in_sample_days:
        Number of days for the in-sample training window.
    out_sample_days:
        Number of days for the out-of-sample validation window.
    step_days:
        Number of days to advance the window on each roll.
    bars_per_day:
        Number of bars per trading day (default 288 for 5-min bars).
    """

    def __init__(
        self,
        in_sample_days: int = 90,
        out_sample_days: int = 30,
        step_days: int = 30,
        bars_per_day: int = 288,
    ) -> None:
        self._is_bars = in_sample_days * bars_per_day
        self._oos_bars = out_sample_days * bars_per_day
        self._step_bars = step_days * bars_per_day
        self._window_bars = self._is_bars + self._oos_bars
        logger.info(
            "WalkForwardOptimizer initialised: IS=%d bars, OOS=%d bars, step=%d bars",
            self._is_bars,
            self._oos_bars,
            self._step_bars,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(
        self,
        bars: list,
        param_grid: dict[str, list],
        evaluate_fn: Callable[[list, dict], Decimal],
    ) -> WFOResult:
        """Run walk-forward optimization across all rolling windows.

        Parameters
        ----------
        bars:
            Full list of bar objects / dicts ordered chronologically.
        param_grid:
            Mapping of parameter name -> list of candidate values.
        evaluate_fn:
            ``evaluate_fn(bars_slice, params) -> Decimal`` returning the
            Sharpe ratio (or other objective) for the given slice/params.

        Returns
        -------
        WFOResult with per-window details and aggregate overfit metrics.
        """
        total_bars = len(bars)
        if total_bars < self._window_bars:
            logger.warning(
                "Not enough bars for WFO: need %d, have %d",
                self._window_bars,
                total_bars,
            )
            return WFOResult(is_overfit=True)

        param_names = list(param_grid.keys())
        param_combos = [
            dict(zip(param_names, combo)) for combo in itertools.product(*param_grid.values())
        ]
        logger.info("Grid search: %d parameter combinations", len(param_combos))

        windows: list[WFOWindow] = []
        best_params_per_window: list[dict[str, Any]] = []

        offset = 0
        while offset + self._window_bars <= total_bars:
            is_start = offset
            is_end = offset + self._is_bars
            oos_start = is_end
            oos_end = is_end + self._oos_bars

            # --- Grid search on IS data ---
            best_sharpe = Decimal("-9999")
            best_params: dict[str, Any] = {}
            is_slice = bars[is_start:is_end]

            for params in param_combos:
                sharpe = evaluate_fn(is_slice, params)
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = params

            # --- Validate on OOS data ---
            oos_slice = bars[oos_start:oos_end]
            oos_sharpe = evaluate_fn(oos_slice, best_params)

            window = WFOWindow(
                in_sample_start=is_start,
                in_sample_end=is_end,
                out_sample_start=oos_start,
                out_sample_end=oos_end,
                is_sharpe=best_sharpe,
                oos_sharpe=oos_sharpe,
            )
            windows.append(window)
            best_params_per_window.append(best_params)

            logger.info(
                "Window %d: IS Sharpe=%s, OOS Sharpe=%s, params=%s",
                len(windows),
                best_sharpe,
                oos_sharpe,
                best_params,
            )

            offset += self._step_bars

        return self._build_result(windows, best_params_per_window)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _build_result(
        windows: list[WFOWindow],
        best_params_per_window: list[dict[str, Any]],
    ) -> WFOResult:
        n = Decimal(str(len(windows))) if windows else Decimal("1")
        avg_is = sum(w.is_sharpe for w in windows) / n
        avg_oos = sum(w.oos_sharpe for w in windows) / n
        degradation = avg_oos / avg_is if avg_is != ZERO else ZERO
        is_overfit = degradation < Decimal("0.5")

        return WFOResult(
            windows=windows,
            best_params_per_window=best_params_per_window,
            avg_is_sharpe=avg_is,
            avg_oos_sharpe=avg_oos,
            oos_degradation=degradation,
            is_overfit=is_overfit,
        )
