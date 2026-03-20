# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Feature Scorer — unified multi-dimensional market assessment.

Extracted from GOLIATH V1 vision (Chapter 10.2), implemented as pure
deterministic Decimal math. Scores four market dimensions:
- Trend: directional bias from EMA alignment and ADX strength
- Momentum: oscillator pressure from RSI, MACD, Stochastic
- Volatility: expansion/contraction from ATR and Bollinger width
- Volume: participation strength from volume vs its moving average

Each score is bounded to [-1, +1] where:
  +1 = strongly bullish / expanding / high participation
  -1 = strongly bearish / contracting / low participation
   0 = neutral / indeterminate
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

ONE = Decimal("1")
NEG_ONE = Decimal("-1")
HALF = Decimal("0.5")


def _clamp(value: Decimal, lo: Decimal = NEG_ONE, hi: Decimal = ONE) -> Decimal:
    """Clamp a Decimal to [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


@dataclass(frozen=True)
class FeatureAssessment:
    """Unified multi-dimensional market assessment."""

    trend: Decimal  # [-1, +1] bearish ← 0 → bullish
    momentum: Decimal  # [-1, +1] oversold ← 0 → overbought
    volatility: Decimal  # [-1, +1] contracting ← 0 → expanding
    volume: Decimal  # [-1, +1] low participation ← 0 → high participation

    @property
    def composite(self) -> Decimal:
        """Weighted composite score (trend-heavy for forex)."""
        return (
            self.trend * Decimal("0.35")
            + self.momentum * Decimal("0.30")
            + self.volatility * Decimal("0.20")
            + self.volume * Decimal("0.15")
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)


class FeatureScorer:
    """Scores raw indicator features into bounded [-1, +1] dimensions.

    Consumes the feature dict produced by FeaturePipeline and returns
    a FeatureAssessment with four independent scores. Strategies can
    use these scores for directional bias instead of raw indicator values.

    Usage:
        scorer = FeatureScorer()
        assessment = scorer.score(features)
        if assessment.trend > Decimal("0.5"):
            # Strong bullish trend bias
    """

    def score(self, features: dict[str, Any]) -> FeatureAssessment:
        """Score all four market dimensions from raw features."""
        return FeatureAssessment(
            trend=self._score_trend(features),
            momentum=self._score_momentum(features),
            volatility=self._score_volatility(features),
            volume=self._score_volume(features),
        )

    def _score_trend(self, features: dict[str, Any]) -> Decimal:
        """Score trend direction and strength.

        Components:
        - EMA alignment: fast above slow = bullish, below = bearish
        - ADX strength: amplifies the EMA signal when trend is strong
        - Price vs SMA200: above = bullish context, below = bearish
        """
        ema_fast = features.get("ema_fast", ZERO)
        ema_slow = features.get("ema_slow", ZERO)
        adx = features.get("adx", ZERO)
        sma_long = features.get("sma_long", ZERO)
        close = features.get("latest_close", ZERO)

        if ema_slow == ZERO or close == ZERO:
            return ZERO

        # EMA cross signal: normalized distance between fast and slow
        ema_diff = (ema_fast - ema_slow) / ema_slow * Decimal("100")
        # Scale: ±0.5% EMA difference maps to ±1.0 score
        ema_score = _clamp(ema_diff * Decimal("2"))

        # ADX amplifier: ADX > 25 strengthens signal, < 15 weakens it
        if adx > ZERO:
            adx_factor = _clamp(
                (adx - Decimal("20")) / Decimal("30"),
                lo=Decimal("-0.3"),
                hi=Decimal("0.5"),
            )
        else:
            adx_factor = ZERO

        # Long-term context: price above/below SMA200
        if sma_long > ZERO:
            sma_bias = _clamp(
                (close - sma_long) / sma_long * Decimal("50"),
                lo=Decimal("-0.3"),
                hi=Decimal("0.3"),
            )
        else:
            sma_bias = ZERO

        raw = ema_score * (ONE + adx_factor) + sma_bias
        return _clamp(raw).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

    def _score_momentum(self, features: dict[str, Any]) -> Decimal:
        """Score momentum pressure from oscillators.

        Components:
        - RSI: distance from 50 (neutral) normalized to [-1, +1]
        - MACD histogram: sign and magnitude
        - Stochastic: overbought/oversold pressure
        """
        rsi = features.get("rsi", Decimal("50"))
        macd_hist = features.get("macd_histogram", ZERO)
        stoch_k = features.get("stoch_k", Decimal("50"))
        close = features.get("latest_close", ONE)

        # RSI score: (RSI - 50) / 50 → [-1, +1]
        rsi_score = _clamp((rsi - Decimal("50")) / Decimal("50"))

        # MACD histogram: normalize relative to price
        if close > ZERO:
            macd_score = _clamp(
                (macd_hist / close) * Decimal("1000"),
            )
        else:
            macd_score = ZERO

        # Stochastic: similar to RSI normalization
        stoch_score = _clamp((stoch_k - Decimal("50")) / Decimal("50"))

        # Weighted combination: RSI 40%, MACD 35%, Stochastic 25%
        raw = (
            rsi_score * Decimal("0.40")
            + macd_score * Decimal("0.35")
            + stoch_score * Decimal("0.25")
        )
        return _clamp(raw).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

    def _score_volatility(self, features: dict[str, Any]) -> Decimal:
        """Score volatility expansion/contraction.

        Components:
        - ATR vs ATR SMA: expansion ratio
        - Bollinger width: absolute width relative to price
        """
        atr = features.get("atr", ZERO)
        atr_sma = features.get("atr_sma", ZERO)
        bb_width = features.get("bb_width", ZERO)

        # ATR expansion ratio: ATR/ATR_SMA - 1, clamped
        if atr_sma > ZERO:
            atr_ratio = _clamp(
                (atr / atr_sma - ONE) * Decimal("3"),
            )
        else:
            atr_ratio = ZERO

        # Bollinger width score: typical forex width ~0.005-0.02
        # Normalize: 0.01 = neutral, below = contracting, above = expanding
        bb_score = _clamp(
            (bb_width - Decimal("0.01")) * Decimal("100"),
        )

        raw = atr_ratio * Decimal("0.60") + bb_score * Decimal("0.40")
        return _clamp(raw).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

    def _score_volume(self, features: dict[str, Any]) -> Decimal:
        """Score volume participation relative to its average.

        Above-average volume = stronger conviction in the current move.
        Below-average = weak participation, potential false signal.
        """
        volume = features.get("volume_ratio", ZERO)

        if volume == ZERO:
            # Try raw volume vs SMA if ratio not computed
            vol = features.get("latest_volume", ZERO)
            vol_sma = features.get("volume_sma", ZERO)
            if vol_sma > ZERO:
                volume = vol / vol_sma
            else:
                return ZERO

        # volume_ratio: 1.0 = average. Score: (ratio - 1) clamped to [-1, +1]
        raw = _clamp((volume - ONE) * Decimal("2"))
        return raw.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
