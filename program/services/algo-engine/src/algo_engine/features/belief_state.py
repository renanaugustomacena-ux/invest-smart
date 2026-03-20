# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Belief State — EMA-smoothed temporal context accumulators.

Extracted from GOLIATH V1 vision (Chapter 10.3), replacing neural memory
layers with pure deterministic EMA math. Maintains four belief accumulators
that track the evolving market context over time:

- trend_belief: directional conviction built from feature scores
- momentum_belief: oscillator pressure accumulation
- regime_belief: confidence in the current regime classification
- edge_belief: accumulated evidence of strategy edge (win/loss outcomes)

Each belief is an EMA-smoothed Decimal in [-1, +1]. The alpha parameter
controls responsiveness: lower alpha = more memory, higher = more reactive.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

ONE = Decimal("1")
NEG_ONE = Decimal("-1")


def _clamp(value: Decimal) -> Decimal:
    if value < NEG_ONE:
        return NEG_ONE
    if value > ONE:
        return ONE
    return value


@dataclass(frozen=True)
class Beliefs:
    """Snapshot of current belief state."""

    trend: Decimal
    momentum: Decimal
    regime: Decimal
    edge: Decimal


class BeliefState:
    """EMA-smoothed belief accumulators for temporal market context.

    Usage:
        beliefs = BeliefState(alpha=Decimal("0.10"))
        beliefs.update(
            trend_score=Decimal("0.6"),
            momentum_score=Decimal("-0.3"),
            regime_confidence=Decimal("0.85"),
        )
        current = beliefs.get_beliefs()
        # current.trend ~ 0.06 after first update (from 0.0)
    """

    def __init__(self, alpha: Decimal = Decimal("0.10")) -> None:
        self._alpha = alpha
        self._one_minus_alpha = ONE - alpha
        self._trend: Decimal = ZERO
        self._momentum: Decimal = ZERO
        self._regime: Decimal = ZERO
        self._edge: Decimal = ZERO
        self._update_count: int = 0

    def update(
        self,
        trend_score: Decimal = ZERO,
        momentum_score: Decimal = ZERO,
        regime_confidence: Decimal = ZERO,
        trade_outcome: Decimal | None = None,
    ) -> Beliefs:
        """Update all belief accumulators with new observations.

        Args:
            trend_score: Current trend score from FeatureScorer [-1, +1].
            momentum_score: Current momentum score [-1, +1].
            regime_confidence: Confidence in the classified regime [0, 1].
            trade_outcome: Optional trade result — positive = win, negative = loss.
                           Pass None when no trade was closed this bar.

        Returns:
            Updated Beliefs snapshot.
        """
        self._trend = self._ema(self._trend, _clamp(trend_score))
        self._momentum = self._ema(self._momentum, _clamp(momentum_score))
        self._regime = self._ema(self._regime, _clamp(regime_confidence))

        if trade_outcome is not None:
            # Normalize trade outcome: win=+1, loss=-1, break-even=0
            outcome_signal = _clamp(trade_outcome)
            self._edge = self._ema(self._edge, outcome_signal)

        self._update_count += 1
        return self.get_beliefs()

    def get_beliefs(self) -> Beliefs:
        """Return current belief state snapshot."""
        return Beliefs(
            trend=self._trend.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN),
            momentum=self._momentum.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN),
            regime=self._regime.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN),
            edge=self._edge.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN),
        )

    @property
    def update_count(self) -> int:
        return self._update_count

    def _ema(self, prev: Decimal, new: Decimal) -> Decimal:
        """Exponential moving average: prev * (1 - alpha) + new * alpha."""
        return self._one_minus_alpha * prev + self._alpha * new
