# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Volatility-Scaled Time-Series Momentum strategy.

Based on Moskowitz, Ooi & Pedersen (2012) — "Time Series Momentum".

Core signal: position = sign(lookback_return) x (target_vol / realized_vol)

Scales momentum exposure inversely to recent volatility so that the
strategy takes larger positions in calm markets and smaller positions
when volatility spikes.  ATR-percent is used as the realized-volatility
proxy and annualized via sqrt(trading-days).

Filters:
- ADX must exceed a threshold to confirm a trend is present.
- Hurst exponent (when available) boosts confidence for persistent series.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import Direction
from moneymaker_common.logging import get_logger

from algo_engine.strategies.base import SignalSuggestion, TradingStrategy

logger = get_logger(__name__)

_ADX_TREND_THRESHOLD = Decimal("20")
_ADX_HOLD_THRESHOLD = Decimal("15")
_MAX_VOL_SCALAR = Decimal("2.0")
_CONFIDENCE_BASE = Decimal("0.50")
_CONFIDENCE_CAP = Decimal("0.85")
_CONFIDENCE_DIVISOR = Decimal("20")
_HURST_BOOST_THRESHOLD = Decimal("0.55")
_HURST_BOOST = Decimal("0.05")


class VolScaledMomentumStrategy(TradingStrategy):
    """Volatility-scaled time-series momentum strategy."""

    def __init__(
        self,
        lookback_period: int = 20,
        vol_window: int = 20,
        target_vol: Decimal = Decimal("0.15"),
        annualization_factor: int = 252,
        min_vol: Decimal = Decimal("0.05"),
    ) -> None:
        self._lookback_period = lookback_period
        self._vol_window = vol_window
        self._target_vol = target_vol
        self._annualization_factor = annualization_factor
        self._min_vol = min_vol
        self._sqrt_ann = Decimal(str(math.sqrt(annualization_factor)))

    @property
    def name(self) -> str:
        return "vol_scaled_momentum_v1"

    def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
        """Analyze features and produce a volatility-scaled momentum signal.

        Args:
            features: Indicator dictionary from the FeaturePipeline.

        Returns:
            SignalSuggestion with direction, confidence and reasoning.
        """
        roc = features.get("roc", ZERO)
        atr_pct = features.get("atr_pct", ZERO)
        adx = features.get("adx", ZERO)

        # --- Realized volatility from ATR-percent, annualized ---------------
        realized_vol = atr_pct * self._sqrt_ann / Decimal("100")
        realized_vol = max(realized_vol, self._min_vol)

        # --- Vol scalar (capped) --------------------------------------------
        vol_scalar = min(self._target_vol / realized_vol, _MAX_VOL_SCALAR)

        # --- HOLD conditions -------------------------------------------------
        if roc == ZERO or adx < _ADX_HOLD_THRESHOLD:
            return SignalSuggestion(
                direction=Direction.HOLD,
                confidence=Decimal("0.20"),
                reasoning=(
                    "No momentum signal: " f"roc={roc}, adx={adx} (threshold={_ADX_HOLD_THRESHOLD})"
                ),
                metadata={
                    "strategy": self.name,
                    "vol_scalar": str(vol_scalar),
                    "realized_vol": str(realized_vol),
                },
            )

        # --- Direction -------------------------------------------------------
        direction = Direction.BUY if roc > ZERO else Direction.SELL

        # --- ADX trend filter ------------------------------------------------
        if adx < _ADX_TREND_THRESHOLD:
            return SignalSuggestion(
                direction=Direction.HOLD,
                confidence=Decimal("0.25"),
                reasoning=(f"Weak trend: adx={adx} below {_ADX_TREND_THRESHOLD}"),
                metadata={
                    "strategy": self.name,
                    "vol_scalar": str(vol_scalar),
                    "realized_vol": str(realized_vol),
                },
            )

        # --- Confidence ------------------------------------------------------
        confidence = min(
            _CONFIDENCE_BASE + abs(roc) * vol_scalar / _CONFIDENCE_DIVISOR,
            _CONFIDENCE_CAP,
        )

        # Hurst exponent boost for persistent series
        hurst = features.get("hurst")
        if hurst is not None and Decimal(str(hurst)) > _HURST_BOOST_THRESHOLD:
            confidence = min(confidence + _HURST_BOOST, _CONFIDENCE_CAP)

        reasoning_parts = [
            f"{'Bullish' if direction == Direction.BUY else 'Bearish'} momentum",
            f"roc={roc}",
            f"vol_scalar={vol_scalar:.4f}",
            f"realized_vol={realized_vol:.4f}",
            f"adx={adx}",
        ]

        return SignalSuggestion(
            direction=direction,
            confidence=confidence,
            reasoning=" | ".join(reasoning_parts),
            metadata={
                "strategy": self.name,
                "vol_scalar": str(vol_scalar),
                "realized_vol": str(realized_vol),
            },
        )
