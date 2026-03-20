# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Adaptive Parameter Tuner.

Dynamically adjusts indicator periods based on the dominant market cycle
detected from spectral analysis or other cycle-detection methods.
"""

from __future__ import annotations

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


def _clamp(value: int, bounds: tuple[int, int]) -> int:
    """Clamp an integer value to (min, max) bounds."""
    return max(bounds[0], min(value, bounds[1]))


class AdaptiveParameterTuner:
    """Cycle-adaptive indicator parameter tuner.

    Recalculates RSI and EMA periods from the dominant market cycle at
    fixed bar-count intervals.  Between updates the current parameters
    remain unchanged.

    Parameters
    ----------
    update_interval:
        Number of bars between automatic re-tuning checks.
    rsi_bounds:
        (min, max) allowed RSI period.
    ema_fast_bounds:
        (min, max) allowed fast EMA period.
    ema_slow_bounds:
        (min, max) allowed slow EMA period.
    """

    def __init__(
        self,
        update_interval: int = 100,
        rsi_bounds: tuple[int, int] = (7, 28),
        ema_fast_bounds: tuple[int, int] = (5, 25),
        ema_slow_bounds: tuple[int, int] = (12, 60),
    ) -> None:
        self._update_interval = update_interval
        self._rsi_bounds = rsi_bounds
        self._ema_fast_bounds = ema_fast_bounds
        self._ema_slow_bounds = ema_slow_bounds

        self._bar_count: int = 0
        self._current_params: dict = {
            "rsi_period": 14,
            "ema_fast": 12,
            "ema_slow": 26,
        }

        logger.info(
            "AdaptiveParameterTuner initialised: interval=%d, rsi=%s, " "ema_fast=%s, ema_slow=%s",
            update_interval,
            rsi_bounds,
            ema_fast_bounds,
            ema_slow_bounds,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, dominant_cycle: int | None = None) -> dict | None:
        """Process one new bar and optionally re-tune parameters.

        Parameters
        ----------
        dominant_cycle:
            Detected dominant cycle length in bars.  When ``None`` or
            when the bar count has not hit the update interval, no
            re-tuning occurs.

        Returns
        -------
        New parameter dict if an update was applied, otherwise ``None``.
        """
        self._bar_count += 1

        if self._bar_count % self._update_interval != 0:
            return None

        if dominant_cycle is None:
            return None

        rsi_period = _clamp(round(dominant_cycle / 2), self._rsi_bounds)
        ema_fast = _clamp(round(dominant_cycle / 4), self._ema_fast_bounds)
        ema_slow = _clamp(round(dominant_cycle / 2), self._ema_slow_bounds)

        # Guarantee ema_fast < ema_slow
        if ema_fast >= ema_slow:
            ema_fast = max(self._ema_fast_bounds[0], ema_slow - 1)

        self._current_params = {
            "rsi_period": rsi_period,
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
        }

        logger.info(
            "Parameters updated at bar %d (cycle=%d): %s",
            self._bar_count,
            dominant_cycle,
            self._current_params,
        )

        return dict(self._current_params)

    def get_current_params(self) -> dict:
        """Return a copy of the current parameter set."""
        return dict(self._current_params)
