"""Ornstein-Uhlenbeck Mean Reversion strategy -- statistically grounded mean reversion.

Uses the OU process to estimate mean reversion parameters (theta, mu, sigma)
from a rolling price window, then generates trading signals based on the
standardised s-score: how many equilibrium standard deviations the price
sits from the fitted long-run mean.

Entry signals fire when the s-score exceeds configurable thresholds,
with additional filtering on half-life bounds (reject too-slow or too-fast
reversion) and an optional Hurst exponent gate.

Ref: Doc 07, Section 5.2 -- OU Mean-Reversion Strategy.
"""

from __future__ import annotations

from collections import deque
from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import Direction
from moneymaker_common.logging import get_logger

from algo_engine.math.ou_process import OrnsteinUhlenbeck, OUParams
from algo_engine.strategies.base import SignalSuggestion, TradingStrategy

logger = get_logger(__name__)

_HURST_THRESHOLD = Decimal("0.45")
_BB_CONFIRM_LOW = Decimal("0.2")
_BB_CONFIRM_HIGH = Decimal("0.8")
_BB_CONFIDENCE_BOOST = Decimal("0.05")
_CONFIDENCE_BASE = Decimal("0.50")
_CONFIDENCE_PER_SIGMA = Decimal("0.10")
_CONFIDENCE_CAP = Decimal("0.85")


class OUMeanReversionStrategy(TradingStrategy):
    """OU-process mean reversion strategy with s-score signals."""

    def __init__(
        self,
        lookback: int = 100,
        entry_threshold: Decimal = Decimal("1.5"),
        exit_threshold: Decimal = Decimal("0.5"),
        max_half_life: int = 50,
        min_half_life: int = 3,
    ) -> None:
        self._lookback = lookback
        self._entry_threshold = entry_threshold
        self._exit_threshold = exit_threshold
        self._max_half_life = max_half_life
        self._min_half_life = min_half_life

        self._price_history: dict[str, deque[Decimal]] = {}
        self._ou = OrnsteinUhlenbeck()
        self._last_params: dict[str, OUParams] = {}

    @property
    def name(self) -> str:
        return "ou_mean_reversion_v1"

    def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
        """Analyze features and produce an OU-based mean reversion signal.

        Args:
            features: Dict of technical indicators. Required keys:
                ``symbol``, ``latest_close``. Optional: ``hurst``,
                ``bb_pct_b``.

        Returns:
            SignalSuggestion with direction, confidence, and reasoning.
        """
        symbol: str = features.get("symbol", "UNKNOWN")
        latest_close: Decimal | None = features.get("latest_close")

        if latest_close is None:
            return self._hold("Missing latest_close in features")

        # Maintain per-symbol rolling window
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=self._lookback)
        self._price_history[symbol].append(latest_close)

        history = self._price_history[symbol]
        if len(history) < self._lookback:
            return self._hold(
                f"Insufficient data for {symbol}: "
                f"{len(history)}/{self._lookback} observations"
            )

        # Fit OU process on price history
        try:
            params = self._ou.fit(list(history))
        except ValueError as exc:
            logger.warning("ou_fit_failed", symbol=symbol, error=str(exc))
            return self._hold(f"OU fit failed for {symbol}: {exc}")

        self._last_params[symbol] = params

        # Validate fitted parameters
        if not params.is_valid or params.theta <= ZERO:
            return self._hold(
                f"No mean reversion detected for {symbol}: theta={params.theta}"
            )

        half_life_f = float(params.half_life)
        if half_life_f < self._min_half_life:
            return self._hold(
                f"Half-life too short for {symbol}: {params.half_life} "
                f"< min {self._min_half_life} (likely noise)"
            )
        if half_life_f > self._max_half_life:
            return self._hold(
                f"Half-life too long for {symbol}: {params.half_life} "
                f"> max {self._max_half_life} (reversion too slow)"
            )

        # Compute s-score
        if params.sigma_eq <= ZERO:
            return self._hold(
                f"Degenerate sigma_eq for {symbol}: {params.sigma_eq}"
            )
        s_score = self._ou.s_score(latest_close, params.mu, params.sigma_eq)

        # Optional Hurst exponent filter
        hurst: Decimal | None = features.get("hurst")
        if hurst is not None and hurst >= _HURST_THRESHOLD:
            return self._hold(
                f"Hurst exponent {hurst} >= {_HURST_THRESHOLD} for {symbol} "
                f"(not anti-persistent, mean reversion unlikely)"
            )

        abs_s = abs(s_score)
        metadata = {
            "strategy": self.name,
            "s_score": str(s_score),
            "half_life": str(params.half_life),
            "theta": str(params.theta),
            "mu": str(params.mu),
        }

        # Signal logic
        bb_pct_b: Decimal | None = features.get("bb_pct_b")

        if s_score < -self._entry_threshold:
            confidence = min(
                _CONFIDENCE_BASE + abs_s * _CONFIDENCE_PER_SIGMA,
                _CONFIDENCE_CAP,
            )
            if bb_pct_b is not None and bb_pct_b < _BB_CONFIRM_LOW:
                confidence = min(confidence + _BB_CONFIDENCE_BOOST, _CONFIDENCE_CAP)
            return SignalSuggestion(
                direction=Direction.BUY,
                confidence=confidence,
                reasoning=(
                    f"OU mean reversion BUY for {symbol}: s-score={s_score:.4f} "
                    f"< -{self._entry_threshold} (price below equilibrium), "
                    f"half-life={params.half_life:.1f}"
                ),
                metadata=metadata,
            )

        if s_score > self._entry_threshold:
            confidence = min(
                _CONFIDENCE_BASE + abs_s * _CONFIDENCE_PER_SIGMA,
                _CONFIDENCE_CAP,
            )
            if bb_pct_b is not None and bb_pct_b > _BB_CONFIRM_HIGH:
                confidence = min(confidence + _BB_CONFIDENCE_BOOST, _CONFIDENCE_CAP)
            return SignalSuggestion(
                direction=Direction.SELL,
                confidence=confidence,
                reasoning=(
                    f"OU mean reversion SELL for {symbol}: s-score={s_score:.4f} "
                    f"> {self._entry_threshold} (price above equilibrium), "
                    f"half-life={params.half_life:.1f}"
                ),
                metadata=metadata,
            )

        if abs_s < self._exit_threshold:
            return SignalSuggestion(
                direction=Direction.HOLD,
                confidence=Decimal("0.40"),
                reasoning=(
                    f"OU mean reversion HOLD (exit zone) for {symbol}: "
                    f"|s-score|={abs_s:.4f} < {self._exit_threshold} "
                    f"(price near equilibrium, close positions)"
                ),
                metadata=metadata,
            )

        return SignalSuggestion(
            direction=Direction.HOLD,
            confidence=Decimal("0.35"),
            reasoning=(
                f"OU mean reversion HOLD for {symbol}: s-score={s_score:.4f} "
                f"in neutral zone [{-self._entry_threshold}, {self._entry_threshold}]"
            ),
            metadata=metadata,
        )

    @staticmethod
    def _hold(reason: str) -> SignalSuggestion:
        """Return a low-confidence HOLD signal with the given reason."""
        return SignalSuggestion(
            direction=Direction.HOLD,
            confidence=Decimal("0.30"),
            reasoning=reason,
        )
