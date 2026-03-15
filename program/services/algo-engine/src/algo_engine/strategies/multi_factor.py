"""Multi-Factor Scoring strategy — il "giudice composito".

Combina cinque fattori — momentum, mean-reversion, trend, volume e
multi-timeframe — in un punteggio ponderato complessivo.  Ogni fattore
produce un valore in [-1, +1] dove +1 = forte BUY, -1 = forte SELL,
0 = neutrale.  Il punteggio finale determina direzione e confidenza.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import Direction, TrendDirection
from moneymaker_common.logging import get_logger

from algo_engine.strategies.base import SignalSuggestion, TradingStrategy

logger = get_logger(__name__)

_ONE = Decimal("1")
_NEG_ONE = Decimal("-1")


def _clamp(value: Decimal, lo: Decimal = _NEG_ONE, hi: Decimal = _ONE) -> Decimal:
    """Clamp *value* between *lo* and *hi*."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


class MultiFactorStrategy(TradingStrategy):
    """Multi-factor scoring strategy — combines five orthogonal factors."""

    def __init__(
        self,
        momentum_weight: Decimal = Decimal("0.30"),
        mean_reversion_weight: Decimal = Decimal("0.20"),
        trend_weight: Decimal = Decimal("0.20"),
        volume_weight: Decimal = Decimal("0.15"),
        mtf_weight: Decimal = Decimal("0.15"),
    ) -> None:
        self._momentum_weight = momentum_weight
        self._mean_reversion_weight = mean_reversion_weight
        self._trend_weight = trend_weight
        self._volume_weight = volume_weight
        self._mtf_weight = mtf_weight

    @property
    def name(self) -> str:
        return "multi_factor_v1"

    # ------------------------------------------------------------------
    # Factor calculations
    # ------------------------------------------------------------------

    @staticmethod
    def _momentum_factor(features: dict[str, Any]) -> Decimal:
        """Momentum factor from ROC, RSI, and MACD histogram."""
        scores: list[Decimal] = []

        # Rate of change — normalise to [-1, 1] via roc / 5
        roc = features.get("roc")
        if roc is not None:
            scores.append(_clamp(Decimal(str(roc)) / Decimal("5")))

        # RSI — overbought/oversold with reversal bias
        rsi = features.get("rsi")
        if rsi is not None:
            rsi = Decimal(str(rsi))
            if rsi > Decimal("70"):
                scores.append(Decimal("-0.5"))
            elif rsi < Decimal("30"):
                scores.append(Decimal("0.5"))
            else:
                scores.append((rsi - Decimal("50")) / Decimal("50"))

        # MACD histogram — direction scaled by ATR
        macd_hist = features.get("macd_histogram")
        atr = features.get("atr")
        if macd_hist is not None:
            macd_hist = Decimal(str(macd_hist))
            if atr is not None and Decimal(str(atr)) > ZERO:
                magnitude = min(abs(macd_hist) / Decimal(str(atr)), _ONE)
            else:
                magnitude = min(abs(macd_hist), _ONE)
            sign = _ONE if macd_hist >= ZERO else _NEG_ONE
            scores.append(sign * magnitude)

        if not scores:
            return ZERO
        return sum(scores, ZERO) / Decimal(str(len(scores)))

    @staticmethod
    def _mean_reversion_factor(features: dict[str, Any]) -> Decimal:
        """Mean-reversion factor from Bollinger %B, Stochastic, Williams %R, O-U."""
        scores: list[Decimal] = []

        # Bollinger %B
        bb_pct_b = features.get("bb_pct_b")
        if bb_pct_b is not None:
            bb_pct_b = Decimal(str(bb_pct_b))
            if bb_pct_b < Decimal("0.2"):
                scores.append((Decimal("0.2") - bb_pct_b) * Decimal("5"))
            elif bb_pct_b > Decimal("0.8"):
                scores.append(-((bb_pct_b - Decimal("0.8")) * Decimal("5")))
            else:
                scores.append(ZERO)

        # Stochastic %K
        stoch_k = features.get("stoch_k")
        if stoch_k is not None:
            stoch_k = Decimal(str(stoch_k))
            if stoch_k < Decimal("20"):
                scores.append(_ONE)
            elif stoch_k > Decimal("80"):
                scores.append(_NEG_ONE)
            else:
                scores.append((Decimal("50") - stoch_k) / Decimal("50"))

        # Williams %R
        williams_r = features.get("williams_r")
        if williams_r is not None:
            williams_r = Decimal(str(williams_r))
            if williams_r > Decimal("-20"):
                scores.append(_NEG_ONE)
            elif williams_r < Decimal("-80"):
                scores.append(_ONE)
            else:
                scores.append(ZERO)

        # Ornstein-Uhlenbeck s-score
        ou_s_score = features.get("ou_s_score")
        if ou_s_score is not None:
            scores.append(_clamp(-Decimal(str(ou_s_score)) / Decimal("2")))

        if not scores:
            return ZERO
        return sum(scores, ZERO) / Decimal(str(len(scores)))

    @staticmethod
    def _trend_factor(features: dict[str, Any]) -> Decimal:
        """Trend factor from EMA trend, ADX direction, and price vs SMA-200."""
        scores: list[Decimal] = []

        # EMA trend direction
        ema_trend = features.get("ema_trend")
        if ema_trend is not None:
            if ema_trend == TrendDirection.BULLISH:
                scores.append(_ONE)
            elif ema_trend == TrendDirection.BEARISH:
                scores.append(_NEG_ONE)
            else:
                scores.append(ZERO)

        # ADX directional component
        adx = features.get("adx")
        plus_di = features.get("plus_di")
        minus_di = features.get("minus_di")
        if adx is not None and plus_di is not None and minus_di is not None:
            adx = Decimal(str(adx))
            plus_di = Decimal(str(plus_di))
            minus_di = Decimal(str(minus_di))
            direction = Decimal("0.5") if plus_di > minus_di else Decimal("-0.5")
            strength = min(adx / Decimal("50"), _ONE)
            scores.append(direction * strength)

        # Price vs SMA-200
        close = features.get("latest_close")
        sma_200 = features.get("sma_200")
        if close is not None and sma_200 is not None:
            close = Decimal(str(close))
            sma_200 = Decimal(str(sma_200))
            if sma_200 > ZERO:
                deviation = (close - sma_200) / sma_200
                scores.append(_clamp(deviation))

        if not scores:
            return ZERO
        return sum(scores, ZERO) / Decimal(str(len(scores)))

    @staticmethod
    def _volume_factor(features: dict[str, Any], other_factors_sign: Decimal) -> Decimal:
        """Volume factor — confirms or denies the prevailing directional bias."""
        volume_ratio = features.get("volume_ratio")
        if volume_ratio is None:
            return ZERO

        volume_ratio = Decimal(str(volume_ratio))
        if volume_ratio > Decimal("1.5"):
            if other_factors_sign > ZERO:
                return _ONE
            elif other_factors_sign < ZERO:
                return _NEG_ONE
        return ZERO

    @staticmethod
    def _mtf_factor(features: dict[str, Any], primary_trend: Decimal) -> Decimal:
        """Multi-timeframe alignment factor."""
        scores: list[Decimal] = []

        for key in ("mtf_h1_trend", "mtf_m15_trend"):
            mtf_trend = features.get(key)
            if mtf_trend is not None:
                if mtf_trend == TrendDirection.BULLISH:
                    mtf_dir = _ONE
                elif mtf_trend == TrendDirection.BEARISH:
                    mtf_dir = _NEG_ONE
                else:
                    mtf_dir = ZERO

                if primary_trend > ZERO and mtf_dir > ZERO:
                    scores.append(_ONE)
                elif primary_trend < ZERO and mtf_dir < ZERO:
                    scores.append(_ONE)
                elif mtf_dir != ZERO:
                    scores.append(_NEG_ONE)

        # Explicit conflict score override
        conflict = features.get("mtf_conflict_score")
        if conflict is not None:
            scores.append(_clamp(-Decimal(str(conflict))))

        if not scores:
            return ZERO
        return sum(scores, ZERO) / Decimal(str(len(scores)))

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
        """Compute multi-factor composite score and produce a signal suggestion."""
        momentum = self._momentum_factor(features)
        mean_reversion = self._mean_reversion_factor(features)
        trend = self._trend_factor(features)

        # Volume factor uses sign of non-volume factors as directional context
        directional_composite = (
            momentum * self._momentum_weight
            + mean_reversion * self._mean_reversion_weight
            + trend * self._trend_weight
        )
        other_sign = (
            _ONE
            if directional_composite > ZERO
            else (_NEG_ONE if directional_composite < ZERO else ZERO)
        )
        volume = self._volume_factor(features, other_sign)

        # MTF factor uses trend factor as primary trend proxy
        mtf = self._mtf_factor(features, trend)

        total_score = (
            momentum * self._momentum_weight
            + mean_reversion * self._mean_reversion_weight
            + trend * self._trend_weight
            + volume * self._volume_weight
            + mtf * self._mtf_weight
        )

        metadata = {
            "strategy": self.name,
            "total_score": str(total_score),
            "momentum": str(momentum),
            "mean_reversion": str(mean_reversion),
            "trend": str(trend),
            "volume": str(volume),
            "mtf": str(mtf),
        }

        # Threshold — no clear edge
        if abs(total_score) < Decimal("0.15"):
            return SignalSuggestion(
                direction=Direction.HOLD,
                confidence=Decimal("0.30"),
                reasoning=(
                    f"Multi-factor score {total_score:.4f} below threshold "
                    f"(mom={momentum:.3f} mr={mean_reversion:.3f} "
                    f"tr={trend:.3f} vol={volume:.3f} mtf={mtf:.3f})"
                ),
                metadata=metadata,
            )

        direction = Direction.BUY if total_score > ZERO else Direction.SELL
        confidence = min(
            Decimal("0.40") + abs(total_score) * Decimal("0.50"),
            Decimal("0.85"),
        )

        return SignalSuggestion(
            direction=direction,
            confidence=confidence,
            reasoning=(
                f"Multi-factor {direction.value}: score={total_score:.4f} "
                f"(mom={momentum:.3f} mr={mean_reversion:.3f} "
                f"tr={trend:.3f} vol={volume:.3f} mtf={mtf:.3f})"
            ),
            metadata=metadata,
        )
