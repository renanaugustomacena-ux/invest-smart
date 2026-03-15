"""MTF Confirmation Matrix — unified cross-timeframe agreement ratio.

Evaluates how strongly multiple timeframes agree on direction,
momentum, and strength. Returns a single confirmation_ratio in [0, 1]
that can weight signal confidence.

Dimensions checked:
    1. Trend alignment  (0.40) — EMA direction agrees across TFs
    2. Momentum alignment (0.30) — RSI above/below 50 agrees across TFs
    3. Strength alignment (0.20) — ADX confirms trend on higher TFs
    4. Volatility context (0.10) — ATR expanding (favourable for entries)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from moneymaker_common.decimal_utils import ZERO

_ONE = Decimal("1")
_FIFTY = Decimal("50")
_TWENTY_FIVE = Decimal("25")


@dataclass(frozen=True)
class MTFConfirmationResult:
    """Snapshot of cross-timeframe agreement."""

    trend_agreement: Decimal  # [0, 1]
    momentum_agreement: Decimal  # [0, 1]
    strength_agreement: Decimal  # [0, 1]
    volatility_context: Decimal  # [0, 1]
    confirmation_ratio: Decimal  # [0, 1] weighted composite


class MTFConfirmation:
    """Compute multi-timeframe confirmation ratio from enriched features.

    Expects features dict already enriched by MultiTimeframeAnalyzer
    with keys like ``h1_trend``, ``m15_trend``, ``h1_rsi``, etc.
    """

    # Higher-timeframe prefixes to check (order: nearest → farthest)
    HTF_PREFIXES = ("m15", "h1")

    # Dimension weights (sum = 1.0)
    W_TREND = Decimal("0.40")
    W_MOMENTUM = Decimal("0.30")
    W_STRENGTH = Decimal("0.20")
    W_VOLATILITY = Decimal("0.10")

    def compute(
        self,
        features: dict,
        direction: str,
    ) -> MTFConfirmationResult:
        """Evaluate cross-timeframe agreement for the given direction.

        Args:
            features: Enriched feature dict (must include HTF keys).
            direction: "BUY" or "SELL".

        Returns:
            MTFConfirmationResult with per-dimension scores and composite.
        """
        trend = self._trend_alignment(features, direction)
        momentum = self._momentum_alignment(features, direction)
        strength = self._strength_alignment(features)
        volatility = self._volatility_context(features)

        composite = (
            self.W_TREND * trend
            + self.W_MOMENTUM * momentum
            + self.W_STRENGTH * strength
            + self.W_VOLATILITY * volatility
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        return MTFConfirmationResult(
            trend_agreement=trend,
            momentum_agreement=momentum,
            strength_agreement=strength,
            volatility_context=volatility,
            confirmation_ratio=composite,
        )

    # ------------------------------------------------------------------
    # Dimension 1: Trend alignment (0.40)
    # ------------------------------------------------------------------

    def _trend_alignment(self, features: dict, direction: str) -> Decimal:
        """Check how many timeframes agree on trend direction.

        Primary trend derived from ema_fast vs ema_slow.
        HTF trends from ``{prefix}_trend`` keys ("bullish"/"bearish").
        """
        expected = "bullish" if direction == "BUY" else "bearish"

        votes = 0
        total = 0

        # Primary timeframe
        ema_fast = features.get("ema_fast", ZERO)
        ema_slow = features.get("ema_slow", ZERO)
        if ema_fast > ZERO and ema_slow > ZERO:
            total += 1
            primary = "bullish" if ema_fast > ema_slow else "bearish"
            if primary == expected:
                votes += 1

        # Higher timeframes
        for prefix in self.HTF_PREFIXES:
            htf_trend = features.get(f"{prefix}_trend")
            if htf_trend is not None:
                total += 1
                if htf_trend == expected:
                    votes += 1

        if total == 0:
            return ZERO
        return Decimal(str(votes)) / Decimal(str(total))

    # ------------------------------------------------------------------
    # Dimension 2: Momentum alignment (0.30)
    # ------------------------------------------------------------------

    def _momentum_alignment(self, features: dict, direction: str) -> Decimal:
        """Check RSI agreement across timeframes.

        BUY: RSI > 50 is confirming.  SELL: RSI < 50 is confirming.
        """
        votes = 0
        total = 0

        # Primary RSI
        rsi = features.get("rsi")
        if rsi is not None:
            total += 1
            if direction == "BUY" and rsi > _FIFTY:
                votes += 1
            elif direction == "SELL" and rsi < _FIFTY:
                votes += 1

        # HTF RSI
        for prefix in self.HTF_PREFIXES:
            htf_rsi = features.get(f"{prefix}_rsi")
            if htf_rsi is not None and htf_rsi > ZERO:
                total += 1
                if direction == "BUY" and htf_rsi > _FIFTY:
                    votes += 1
                elif direction == "SELL" and htf_rsi < _FIFTY:
                    votes += 1

        if total == 0:
            return ZERO
        return Decimal(str(votes)) / Decimal(str(total))

    # ------------------------------------------------------------------
    # Dimension 3: Strength alignment (0.20)
    # ------------------------------------------------------------------

    def _strength_alignment(self, features: dict) -> Decimal:
        """Check ADX confirms trending conditions across timeframes.

        ADX > 25 indicates a strong trend (regardless of direction).
        """
        votes = 0
        total = 0

        # Primary ADX
        adx = features.get("adx")
        if adx is not None:
            total += 1
            if adx > _TWENTY_FIVE:
                votes += 1

        # HTF ADX
        for prefix in self.HTF_PREFIXES:
            htf_adx = features.get(f"{prefix}_adx")
            if htf_adx is not None and htf_adx > ZERO:
                total += 1
                if htf_adx > _TWENTY_FIVE:
                    votes += 1

        if total == 0:
            return ZERO
        return Decimal(str(votes)) / Decimal(str(total))

    # ------------------------------------------------------------------
    # Dimension 4: Volatility context (0.10)
    # ------------------------------------------------------------------

    def _volatility_context(self, features: dict) -> Decimal:
        """Check if ATR is expanding (favouring new entries).

        Uses primary ATR vs atr_sma. If ATR > SMA → expanding = 1.
        Falls back to 0.5 (neutral) if data missing.
        """
        atr = features.get("atr")
        atr_sma = features.get("atr_sma")

        if atr is None or atr_sma is None or atr_sma <= ZERO:
            return Decimal("0.5")

        if atr > atr_sma:
            return _ONE
        return ZERO
