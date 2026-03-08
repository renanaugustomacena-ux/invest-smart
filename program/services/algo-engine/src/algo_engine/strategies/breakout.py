"""Donchian breakout strategy for reversal regimes.

Uses Donchian channels (already computed by FeaturePipeline via
calculate_donchian_channels() in algo_engine/features/technical.py)
to detect breakout entries with multi-confirmation scoring.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from moneymaker_common.enums import Direction
from moneymaker_common.logging import get_logger

from algo_engine.strategies.base import SignalSuggestion, TradingStrategy

logger = get_logger(__name__)


class BreakoutStrategy(TradingStrategy):
    """Donchian channel breakout strategy.

    Entry logic:
    - BUY: Close >= Donchian upper + confirmations
    - SELL: Close <= Donchian lower + confirmations

    Confirmations (each adds +0.10 confidence):
    1. ADX > 20 (directional strength)
    2. ATR expansion (current ATR > 1.2x SMA of ATR)
    3. Volume > 1.5x average

    Confidence: 0.50 base + (confirmations x 0.10), capped at 0.85
    """

    @property
    def name(self) -> str:
        return "breakout_donchian"

    def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
        close = features.get("latest_close", Decimal("0"))
        donchian_upper = features.get("donchian_upper", Decimal("0"))
        donchian_lower = features.get("donchian_lower", Decimal("0"))
        adx = features.get("adx", Decimal("0"))
        atr = features.get("atr", Decimal("0"))
        volume_ratio = features.get("volume_ratio", Decimal("1"))

        # Must have valid Donchian channels
        if donchian_upper == Decimal("0") or donchian_lower == Decimal("0"):
            return SignalSuggestion(
                direction=Direction.HOLD,
                confidence=Decimal("0.30"),
                reasoning="Donchian channels not yet computed",
            )

        # Determine breakout direction
        is_upper_break = close >= donchian_upper
        is_lower_break = close <= donchian_lower

        if not is_upper_break and not is_lower_break:
            return SignalSuggestion(
                direction=Direction.HOLD,
                confidence=Decimal("0.40"),
                reasoning=(
                    f"No breakout: price {close} within "
                    f"Donchian [{donchian_lower}, {donchian_upper}]"
                ),
            )

        # Count confirmations
        confirmations = 0
        reasons = []

        # Confirmation 1: ADX > 20 (directional strength)
        if adx > Decimal("20"):
            confirmations += 1
            reasons.append(f"ADX={adx:.1f}>20")

        # Confirmation 2: ATR expansion
        atr_sma = features.get("atr_sma", atr)
        if atr_sma > Decimal("0") and atr > atr_sma * Decimal("1.2"):
            confirmations += 1
            reasons.append(f"ATR expanding ({atr:.5f}>{atr_sma * Decimal('1.2'):.5f})")

        # Confirmation 3: Volume spike
        if volume_ratio > Decimal("1.5"):
            confirmations += 1
            reasons.append(f"Vol={volume_ratio:.2f}x>1.5x")

        # Calculate confidence: 0.50 base + 0.10 per confirmation, max 0.85
        confidence = min(
            Decimal("0.50") + Decimal(str(confirmations)) * Decimal("0.10"),
            Decimal("0.85"),
        )

        if is_upper_break:
            direction = Direction.BUY
            reasoning = (
                f"Donchian upper breakout ({close}>={donchian_upper}); "
                f"{'; '.join(reasons)}"
            )
        else:
            direction = Direction.SELL
            reasoning = (
                f"Donchian lower breakout ({close}<={donchian_lower}); "
                f"{'; '.join(reasons)}"
            )

        logger.debug(
            "Breakout signal",
            direction=direction.value,
            confidence=str(confidence),
            confirmations=confirmations,
        )

        return SignalSuggestion(
            direction=direction,
            confidence=confidence,
            reasoning=reasoning,
            metadata={"strategy": self.name, "confirmations": confirmations},
        )
