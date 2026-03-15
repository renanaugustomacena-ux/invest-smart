"""Composite Confidence — multi-factor calibrated confidence scoring.

Extracted from GOLIATH V1 vision (Chapter 10.6). Replaces per-strategy
ad-hoc confidence with a unified formula:

  confidence = 0.40 * indicator_agreement
             + 0.35 * historical_edge
             + 0.25 * signal_quality

Each sub-score is bounded [0, 1]. The composite is also bounded [0, 1].

- indicator_agreement: fraction of indicators aligned with the proposed direction
- historical_edge: rolling win rate from beliefs (or provided directly)
- signal_quality: distance from decision thresholds (how decisive is the signal?)
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

ONE = Decimal("1")
FIFTY = Decimal("50")


def _clamp_01(value: Decimal) -> Decimal:
    """Clamp to [0, 1]."""
    if value < ZERO:
        return ZERO
    if value > ONE:
        return ONE
    return value


class CompositeConfidence:
    """Compute calibrated confidence from multiple independent factors.

    Usage:
        cc = CompositeConfidence()
        confidence = cc.compute(
            features=features_dict,
            direction="BUY",
            belief_edge=Decimal("0.3"),
        )
    """

    def __init__(
        self,
        weight_agreement: Decimal = Decimal("0.40"),
        weight_edge: Decimal = Decimal("0.35"),
        weight_quality: Decimal = Decimal("0.25"),
    ) -> None:
        self._w_agreement = weight_agreement
        self._w_edge = weight_edge
        self._w_quality = weight_quality

    def compute(
        self,
        features: dict[str, Any],
        direction: str,
        belief_edge: Decimal = ZERO,
        win_rate: Decimal | None = None,
    ) -> Decimal:
        """Compute composite confidence score.

        Args:
            features: Feature dict from FeaturePipeline.
            direction: Proposed trade direction ("BUY" or "SELL").
            belief_edge: Edge belief from BeliefState [-1, +1].
            win_rate: Optional explicit win rate [0, 1].

        Returns:
            Calibrated confidence in [0, 1].
        """
        agreement = self._indicator_agreement(features, direction)
        edge = self._historical_edge(belief_edge, win_rate)
        quality = self._signal_quality(features, direction)

        composite = self._w_agreement * agreement + self._w_edge * edge + self._w_quality * quality

        result = _clamp_01(composite).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        logger.debug(
            "Composite confidence computed",
            agreement=str(agreement),
            edge=str(edge),
            quality=str(quality),
            composite=str(result),
        )

        return result

    def _indicator_agreement(self, features: dict[str, Any], direction: str) -> Decimal:
        """Fraction of indicators agreeing with the proposed direction.

        Checks: EMA cross, RSI bias, MACD histogram, Stochastic, ADX trend.
        """
        is_buy = direction == "BUY"
        votes = 0
        total = 0

        # EMA fast vs slow
        ema_fast = features.get("ema_fast", ZERO)
        ema_slow = features.get("ema_slow", ZERO)
        if ema_fast != ZERO and ema_slow != ZERO:
            total += 1
            if (is_buy and ema_fast > ema_slow) or (not is_buy and ema_fast < ema_slow):
                votes += 1

        # RSI bias (above 50 = bullish, below = bearish)
        rsi = features.get("rsi", FIFTY)
        total += 1
        if (is_buy and rsi > FIFTY) or (not is_buy and rsi < FIFTY):
            votes += 1

        # MACD histogram direction
        macd_hist = features.get("macd_histogram", ZERO)
        total += 1
        if (is_buy and macd_hist > ZERO) or (not is_buy and macd_hist < ZERO):
            votes += 1

        # Stochastic direction
        stoch_k = features.get("stoch_k", FIFTY)
        total += 1
        if (is_buy and stoch_k > FIFTY) or (not is_buy and stoch_k < FIFTY):
            votes += 1

        # +DI vs -DI (directional indicators)
        plus_di = features.get("plus_di", ZERO)
        minus_di = features.get("minus_di", ZERO)
        if plus_di != ZERO or minus_di != ZERO:
            total += 1
            if (is_buy and plus_di > minus_di) or (not is_buy and minus_di > plus_di):
                votes += 1

        if total == 0:
            return Decimal("0.5")

        return Decimal(str(votes)) / Decimal(str(total))

    def _historical_edge(self, belief_edge: Decimal, win_rate: Decimal | None) -> Decimal:
        """Convert edge evidence into a [0, 1] score.

        If explicit win_rate is provided, use it directly.
        Otherwise, convert belief_edge from [-1, +1] to [0, 1].
        """
        if win_rate is not None:
            return _clamp_01(win_rate)

        # Transform [-1, +1] → [0, 1]
        return _clamp_01((belief_edge + ONE) / Decimal("2"))

    def _signal_quality(self, features: dict[str, Any], direction: str) -> Decimal:
        """How decisive is the signal? Distance from decision thresholds.

        A signal where RSI is at 80 (strong overbought for SELL) is higher
        quality than RSI at 52 (barely above neutral for BUY).
        """
        is_buy = direction == "BUY"
        quality_sum = ZERO
        count = 0

        # RSI distance from 50 (neutral), normalized to [0, 1]
        rsi = features.get("rsi", FIFTY)
        rsi_dist = abs(rsi - FIFTY) / FIFTY
        # Only count if RSI agrees with direction
        if (is_buy and rsi > FIFTY) or (not is_buy and rsi < FIFTY):
            quality_sum += rsi_dist
        count += 1

        # Feature composite score distance from 0 (neutral)
        composite = features.get("feature_composite_score", ZERO)
        if composite != ZERO:
            composite_dist = abs(composite)
            if (is_buy and composite > ZERO) or (not is_buy and composite < ZERO):
                quality_sum += composite_dist
            count += 1

        # Bollinger %B: extreme values indicate clearer signals
        bb_pct_b = features.get("bb_pct_b", Decimal("0.5"))
        bb_dist = abs(bb_pct_b - Decimal("0.5")) * Decimal("2")
        if (is_buy and bb_pct_b > Decimal("0.5")) or (not is_buy and bb_pct_b < Decimal("0.5")):
            quality_sum += bb_dist
        count += 1

        if count == 0:
            return Decimal("0.5")

        return _clamp_01(quality_sum / Decimal(str(count)))
