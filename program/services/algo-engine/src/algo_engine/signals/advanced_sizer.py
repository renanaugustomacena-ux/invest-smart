# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""CVaR-based position sizing with Half-Kelly criterion.

Extends the basic risk-per-trade sizer with two additional layers:

1. **CVaR adjustment** — If a Conditional Value-at-Risk estimate is
   provided, the position is scaled so the expected tail loss stays
   within the per-trade risk budget.

2. **Half-Kelly cap** — When enough trade history is available, the
   Kelly-optimal fraction (halved for safety) acts as a ceiling on
   the base size, preventing over-leverage when the edge is thin.

A tiered DrawdownScaler further reduces exposure as account drawdown
deepens, providing circuit-breaker-style protection.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

from algo_engine.signals.position_sizer import infer_pip_size, infer_pip_value

logger = get_logger(__name__)

_TWO_PLACES = Decimal("0.01")
_HUNDRED = Decimal("100")
_MIN_KELLY_TRADES = 10


@dataclass(frozen=True, slots=True)
class TradeRecord:
    """Immutable record of a completed trade."""

    pnl: Decimal
    direction: str  # "BUY" or "SELL"
    symbol: str


class DrawdownScaler:
    """Tiered drawdown scaling — reduces size as drawdown worsens."""

    def __init__(
        self,
        tier1_dd: Decimal = Decimal("3"),
        tier1_scale: Decimal = Decimal("0.50"),
        tier2_dd: Decimal = Decimal("5"),
        tier2_scale: Decimal = Decimal("0.25"),
    ) -> None:
        self._tier1_dd = tier1_dd
        self._tier1_scale = tier1_scale
        self._tier2_dd = tier2_dd
        self._tier2_scale = tier2_scale

    def scale(self, drawdown_pct: Decimal) -> Decimal:
        """Return a scaling factor in (0, 1] based on current drawdown.

        - dd < tier1  → 1.0 (full size)
        - tier1 <= dd < tier2  → tier1_scale
        - dd >= tier2  → tier2_scale
        """
        if drawdown_pct < self._tier1_dd:
            return Decimal("1.0")
        if drawdown_pct < self._tier2_dd:
            return self._tier1_scale
        return self._tier2_scale


class AdvancedPositionSizer:
    """CVaR-aware position sizer with optional Half-Kelly cap."""

    def __init__(
        self,
        max_lots: Decimal = Decimal("0.10"),
        min_lots: Decimal = Decimal("0.01"),
        risk_per_trade_pct: Decimal = Decimal("1.0"),
        max_risk_pct: Decimal = Decimal("2.0"),
        trade_history_size: int = 50,
        use_kelly: bool = True,
        kelly_fraction: Decimal = Decimal("0.5"),
    ) -> None:
        self._max_lots = max_lots
        self._min_lots = min_lots
        self._risk_pct = risk_per_trade_pct
        self._max_risk_pct = max_risk_pct
        self._use_kelly = use_kelly
        self._kelly_fraction = kelly_fraction
        self._trades: deque[TradeRecord] = deque(maxlen=trade_history_size)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_trade(self, trade: TradeRecord) -> None:
        """Append a completed trade to the rolling history window."""
        self._trades.append(trade)

    def calculate(
        self,
        symbol: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        equity: Decimal,
        drawdown_pct: Decimal,
        confidence: Decimal = Decimal("0.70"),
        cvar: Decimal | None = None,
    ) -> Decimal:
        """Compute position size in lots.

        Parameters
        ----------
        symbol:
            Instrument name (e.g. "EURUSD").
        entry_price:
            Planned entry price.
        stop_loss:
            Stop-loss price.
        equity:
            Current account equity.
        drawdown_pct:
            Current drawdown percentage (0-100 scale).
        confidence:
            Signal confidence in [0, 1].  Scales final size linearly.
        cvar:
            Conditional Value-at-Risk expressed in price-move (same unit
            as pip_size).  If provided and positive, the position is
            capped so expected tail loss <= risk budget.

        Returns
        -------
        Decimal
            Lot size quantized to 0.01, clamped to [min_lots, max_lots].
        """
        try:
            pip_size = infer_pip_size(symbol)
            pip_value = infer_pip_value(symbol)
        except ValueError:
            logger.critical(
                "advanced_sizer: unknown symbol, returning min lots",
                symbol=symbol,
            )
            return self._min_lots

        sl_distance = abs(entry_price - stop_loss)
        if sl_distance <= ZERO or pip_size <= ZERO or pip_value <= ZERO:
            logger.warning(
                "advanced_sizer: invalid parameters, returning min lots",
                symbol=symbol,
                sl_distance=str(sl_distance),
            )
            return self._min_lots

        sl_pips = sl_distance / pip_size

        # --- (a) Base risk, reduced by drawdown -----------------------
        dd_scale = max(Decimal("1") - drawdown_pct / Decimal("10"), Decimal("0.3"))
        base_risk = equity * self._risk_pct / _HUNDRED * dd_scale

        # Cap at max_risk_pct of equity
        max_risk = equity * self._max_risk_pct / _HUNDRED
        if base_risk > max_risk:
            base_risk = max_risk

        risk_per_pip = pip_value  # risk per pip per 1.0 lot

        lots = base_risk / (sl_pips * risk_per_pip)

        # --- (b) CVaR adjustment -------------------------------------
        if cvar is not None and cvar > ZERO:
            cvar_pips = cvar / pip_size
            if cvar_pips > ZERO:
                cvar_lots = base_risk / (cvar_pips * risk_per_pip)
                if cvar_lots < lots:
                    logger.debug(
                        "CVaR cap applied",
                        symbol=symbol,
                        base_lots=str(lots),
                        cvar_lots=str(cvar_lots),
                    )
                    lots = cvar_lots

        # --- (c) Half-Kelly cap --------------------------------------
        if self._use_kelly:
            kelly_f = self._kelly_criterion()
            if kelly_f is not None and kelly_f > ZERO:
                kelly_risk = equity * kelly_f * self._kelly_fraction
                kelly_lots = kelly_risk / (sl_pips * risk_per_pip)
                if kelly_lots < lots:
                    logger.debug(
                        "Kelly cap applied",
                        symbol=symbol,
                        kelly_f=str(kelly_f),
                        kelly_lots=str(kelly_lots),
                    )
                    lots = kelly_lots

        # --- (d) Confidence scaling -----------------------------------
        lots = lots * confidence

        # --- (e) Clamp ------------------------------------------------
        if lots < self._min_lots:
            lots = self._min_lots
        elif lots > self._max_lots:
            lots = self._max_lots

        # --- (f) Quantize ---------------------------------------------
        lots = lots.quantize(_TWO_PLACES, rounding=ROUND_HALF_EVEN)

        logger.debug(
            "advanced_sizer: position sized",
            symbol=symbol,
            equity=str(equity),
            drawdown_pct=str(drawdown_pct),
            confidence=str(confidence),
            lots=str(lots),
        )

        return lots

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _kelly_criterion(self) -> Decimal | None:
        """Compute optimal Kelly fraction from trade history.

        Formula: f* = (p * b - q) / b
            p = win rate
            q = 1 - p
            b = avg_win / avg_loss

        Returns
        -------
        Decimal or None
            The Kelly fraction, or ``None`` if fewer than
            ``_MIN_KELLY_TRADES`` trades are recorded.  Returns ZERO
            when the edge is non-positive.
        """
        if len(self._trades) < _MIN_KELLY_TRADES:
            return None

        wins: list[Decimal] = []
        losses: list[Decimal] = []
        for t in self._trades:
            if t.pnl > ZERO:
                wins.append(t.pnl)
            elif t.pnl < ZERO:
                losses.append(abs(t.pnl))

        total = len(wins) + len(losses)
        if total == 0:
            return None

        if not losses:
            # All wins, no losses — Kelly is theoretically 1.0 but
            # this is almost certainly a small-sample artefact.
            return Decimal("1")

        if not wins:
            return ZERO

        p = Decimal(len(wins)) / Decimal(total)
        q = Decimal("1") - p
        avg_win = sum(wins) / Decimal(len(wins))
        avg_loss = sum(losses) / Decimal(len(losses))

        if avg_loss <= ZERO:
            return None

        b = avg_win / avg_loss
        kelly = (p * b - q) / b

        if kelly <= ZERO:
            return ZERO

        return kelly
