# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Spread Percentile Tracker — dynamic spread rejection based on history.

Replaces static spread thresholds (e.g., "reject if spread > 30 points")
with a percentile-based approach. Maintains a rolling window of observed
spreads per symbol and rejects signals when the current spread is in
an abnormally high percentile (e.g., > 90th percentile).

This adapts automatically to each instrument's typical spread behaviour:
- XAUUSD with normal spread 20-30 points won't reject at 25
- But XAUUSD with spread 80 during news will be flagged as >95th percentile

Utilizzo:
    tracker = SpreadPercentileTracker(window=200, reject_percentile=90)
    tracker.record_spread("XAUUSD", Decimal("2.5"))
    is_ok, reason = tracker.check("XAUUSD", Decimal("8.0"))
"""

from __future__ import annotations

from collections import deque
from decimal import ROUND_HALF_EVEN, Decimal

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


class SpreadPercentileTracker:
    """Track spread history per symbol and reject abnormal spreads.

    Uses a rolling window (default 200 observations) to build a
    distribution of spreads, then computes percentile rank of the
    current spread.
    """

    def __init__(
        self,
        window: int = 200,
        reject_percentile: int = 90,
        min_observations: int = 20,
    ) -> None:
        """Initialize tracker.

        Args:
            window: Rolling window size for spread history.
            reject_percentile: Reject if spread >= this percentile (0-100).
            min_observations: Minimum observations before percentile check activates.
                Below this threshold, check always passes.
        """
        self._window = window
        self._reject_percentile = reject_percentile
        self._min_observations = min_observations
        self._spreads: dict[str, deque[Decimal]] = {}

    def record_spread(self, symbol: str, spread: Decimal) -> None:
        """Record an observed spread value for the given symbol."""
        key = symbol.upper()
        if key not in self._spreads:
            self._spreads[key] = deque(maxlen=self._window)
        self._spreads[key].append(spread)

    def check(self, symbol: str, current_spread: Decimal) -> tuple[bool, str]:
        """Check if current spread is acceptable.

        Returns:
            (True, "") if acceptable.
            (False, reason) if spread is abnormally high.
        """
        key = symbol.upper()
        history = self._spreads.get(key)

        # No history or insufficient data — pass through
        if history is None or len(history) < self._min_observations:
            return True, ""

        percentile = self._compute_percentile(history, current_spread)

        if percentile >= self._reject_percentile:
            reason = (
                f"Spread {current_spread} at {percentile}th percentile "
                f"(threshold: {self._reject_percentile}th) for {symbol}"
            )
            logger.info(
                "Spread rejected: abnormally high",
                symbol=symbol,
                spread=str(current_spread),
                percentile=percentile,
                threshold=self._reject_percentile,
            )
            return False, reason

        return True, ""

    def get_percentile(self, symbol: str, spread: Decimal) -> int:
        """Get the percentile rank of a spread without rejecting.

        Returns 0 if no history available.
        """
        key = symbol.upper()
        history = self._spreads.get(key)
        if not history:
            return 0
        return self._compute_percentile(history, spread)

    def get_stats(self, symbol: str) -> dict[str, str]:
        """Get spread statistics for a symbol."""
        key = symbol.upper()
        history = self._spreads.get(key)
        if not history:
            return {"observations": "0"}

        sorted_h = sorted(history)
        n = len(sorted_h)
        median_idx = n // 2
        p90_idx = min(int(n * 0.9), n - 1)

        return {
            "observations": str(n),
            "min": str(sorted_h[0]),
            "max": str(sorted_h[-1]),
            "median": str(sorted_h[median_idx]),
            "p90": str(sorted_h[p90_idx]),
        }

    @staticmethod
    def _compute_percentile(history: deque[Decimal], value: Decimal) -> int:
        """Compute percentile rank of value in the history distribution.

        Returns integer 0-100.
        """
        count_below = sum(1 for v in history if v < value)
        percentile = (Decimal(str(count_below)) / Decimal(str(len(history)))) * Decimal("100")
        return int(percentile.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
