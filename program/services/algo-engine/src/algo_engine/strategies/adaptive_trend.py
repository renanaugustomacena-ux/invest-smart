# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Cycle-adaptive trend following strategy.

Uses detected market cycles to dynamically adjust indicator periods.
When a dominant cycle is present, RSI and EMA periods scale to match
the cycle length, improving signal accuracy across different market
conditions. Falls back to sensible defaults when no cycle is detected.

Confirmation logic mirrors TrendFollowingStrategy but adds:
- Adaptive period scaling based on dominant cycle
- RSI directional confirmation
- Hurst exponent filter (trend persistence gate)
- Cycle-detection confidence bonus
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import Direction
from moneymaker_common.logging import get_logger

from algo_engine.strategies.base import SignalSuggestion, TradingStrategy

logger = get_logger(__name__)

_ADX_THRESHOLD = Decimal("25")
_RSI_MIDPOINT = Decimal("50")
_HURST_TREND_THRESHOLD = Decimal("0.55")
_HURST_MEAN_REVERT_THRESHOLD = Decimal("0.45")
_CYCLE_BONUS = Decimal("0.05")


def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp an integer to [lo, hi]."""
    return max(lo, min(value, hi))


class AdaptiveTrendStrategy(TradingStrategy):
    """Trend following with cycle-adaptive indicator periods."""

    def __init__(
        self,
        *,
        default_cycle: int = 20,
        min_rsi: int = 7,
        max_rsi: int = 28,
        min_ema_fast: int = 5,
        max_ema_fast: int = 25,
        min_ema_slow: int = 12,
        max_ema_slow: int = 60,
        min_confirmations: int = 3,
    ) -> None:
        self._default_cycle = default_cycle
        self._min_rsi = min_rsi
        self._max_rsi = max_rsi
        self._min_ema_fast = min_ema_fast
        self._max_ema_fast = max_ema_fast
        self._min_ema_slow = min_ema_slow
        self._max_ema_slow = max_ema_slow
        self._min_confirmations = min_confirmations

    @property
    def name(self) -> str:
        return "adaptive_trend_v1"

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
        """Analyze indicators with cycle-adaptive periods.

        Args:
            features: Indicator dictionary from the FeaturePipeline.

        Returns:
            SignalSuggestion with direction, confidence, and reasoning.
        """
        # --- 1. Resolve dominant cycle --------------------------------
        dominant_cycle = features.get("dominant_cycle")
        cycle_detected = dominant_cycle is not None
        cycle = int(dominant_cycle) if dominant_cycle is not None else self._default_cycle

        # --- 2. Compute adaptive periods ------------------------------
        rsi_period = _clamp(round(cycle / 2), self._min_rsi, self._max_rsi)
        ema_fast_period = _clamp(round(cycle / 4), self._min_ema_fast, self._max_ema_fast)
        ema_slow_period = _clamp(round(cycle / 2), self._min_ema_slow, self._max_ema_slow)

        if ema_fast_period >= ema_slow_period:
            ema_slow_period = ema_fast_period + 2

        # --- 3. Gather indicator values (prefer pre-computed) ---------
        adx: Decimal = features.get("adx", ZERO)
        macd_histogram: Decimal = features.get("macd_histogram", ZERO)
        sma_200: Decimal = features.get("sma_200", ZERO)
        latest_close: Decimal = features.get("latest_close", ZERO)
        rsi: Decimal = features.get("rsi", ZERO)
        ema_fast: Decimal = features.get("ema_fast", ZERO)
        ema_slow: Decimal = features.get("ema_slow", ZERO)

        # --- 4. Count confirmations -----------------------------------
        buy_confirmations: list[str] = []
        sell_confirmations: list[str] = []

        # EMA crossover
        if ema_fast > ZERO and ema_slow > ZERO:
            if ema_fast > ema_slow:
                buy_confirmations.append("EMA fast > slow")
            elif ema_fast < ema_slow:
                sell_confirmations.append("EMA fast < slow")

        # Price vs SMA(200)
        if sma_200 > ZERO and latest_close > ZERO:
            if latest_close > sma_200:
                buy_confirmations.append("Price > SMA(200)")
            elif latest_close < sma_200:
                sell_confirmations.append("Price < SMA(200)")

        # MACD histogram
        if macd_histogram > ZERO:
            buy_confirmations.append("MACD histogram positive")
        elif macd_histogram < ZERO:
            sell_confirmations.append("MACD histogram negative")

        # ADX strength (non-directional — reinforces dominant side)
        adx_strong = adx > _ADX_THRESHOLD
        if adx_strong:
            if len(buy_confirmations) > len(sell_confirmations):
                buy_confirmations.append("ADX > 25")
            elif len(sell_confirmations) > len(buy_confirmations):
                sell_confirmations.append("ADX > 25")

        # RSI directional bias
        if rsi > _RSI_MIDPOINT:
            buy_confirmations.append("RSI > 50 (bullish)")
        elif rsi < _RSI_MIDPOINT:
            sell_confirmations.append("RSI < 50 (bearish)")

        buy_count = len(buy_confirmations)
        sell_count = len(sell_confirmations)

        # --- 5. Minimum confirmations gate ----------------------------
        if buy_count < self._min_confirmations and sell_count < self._min_confirmations:
            return SignalSuggestion(
                direction=Direction.HOLD,
                confidence=Decimal("0.30"),
                reasoning=(
                    f"Insufficient confirmations: BUY={buy_count}, SELL={sell_count}, "
                    f"need >= {self._min_confirmations}"
                ),
            )

        # Determine dominant direction
        if buy_count >= self._min_confirmations and buy_count > sell_count:
            direction = Direction.BUY
            confirmations = buy_confirmations
            conf_count = buy_count
        elif sell_count >= self._min_confirmations and sell_count > buy_count:
            direction = Direction.SELL
            confirmations = sell_confirmations
            conf_count = sell_count
        else:
            return SignalSuggestion(
                direction=Direction.HOLD,
                confidence=Decimal("0.30"),
                reasoning=(f"Conflicting confirmations: BUY={buy_count}, SELL={sell_count}"),
            )

        # --- 6. Hurst exponent filter ---------------------------------
        hurst = features.get("hurst")
        if hurst is not None:
            hurst = Decimal(str(hurst))
            if hurst < _HURST_MEAN_REVERT_THRESHOLD:
                return SignalSuggestion(
                    direction=Direction.HOLD,
                    confidence=Decimal("0.25"),
                    reasoning=(
                        f"Hurst {hurst} < {_HURST_MEAN_REVERT_THRESHOLD} — "
                        "mean-reverting regime, trend signal suppressed"
                    ),
                )
            if hurst < _HURST_TREND_THRESHOLD:
                return SignalSuggestion(
                    direction=Direction.HOLD,
                    confidence=Decimal("0.30"),
                    reasoning=(
                        f"Hurst {hurst} < {_HURST_TREND_THRESHOLD} — "
                        "insufficient trend persistence"
                    ),
                )

        # --- 7. Confidence calculation --------------------------------
        cycle_bonus = _CYCLE_BONUS if cycle_detected else ZERO
        confidence = min(
            Decimal("0.50") + adx / Decimal("100") + cycle_bonus,
            Decimal("0.90"),
        )

        # --- 8. Build metadata ----------------------------------------
        metadata: dict[str, Any] = {
            "strategy": self.name,
            "cycle": cycle,
            "adaptive_rsi": rsi_period,
            "adaptive_ema_fast": ema_fast_period,
            "adaptive_ema_slow": ema_slow_period,
        }

        return SignalSuggestion(
            direction=direction,
            confidence=confidence,
            reasoning=(
                f"Adaptive trend {direction.value}: {conf_count} confirmations "
                f"(cycle={cycle}) — {', '.join(confirmations)}"
            ),
            metadata=metadata,
        )
