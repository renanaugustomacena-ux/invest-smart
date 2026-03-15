"""Multi-mode trailing stop manager for active position management.

Supports four trailing modes — ATR-based, Chandelier exit, break-even
promotion, and fixed-percentage — each updating the protective stop in
a single direction (tighter, never looser) as price moves in favour.

Usage:
    manager = TrailingStopManager()
    state = manager.open_position("EURUSD", "BUY", entry, initial_sl)
    state = manager.update(state, price, high, low, atr)
    if manager.is_stopped_out(state, price):
        # close position
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from enum import Enum
from typing import Any

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

_ONE_HUNDRED = Decimal("100")


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------


class TrailingMode(Enum):
    """Available trailing-stop algorithms."""

    ATR_TRAIL = "atr_trail"
    CHANDELIER = "chandelier"
    BREAK_EVEN = "break_even"
    PERCENTAGE = "percentage"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrailingStopState:
    """Immutable snapshot of a trailing stop for one position."""

    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: Decimal
    current_stop: Decimal
    highest_price: Decimal  # highest since entry (relevant for BUY)
    lowest_price: Decimal  # lowest since entry (relevant for SELL)
    mode: TrailingMode
    is_break_even: bool = False  # whether SL has been promoted to entry


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class TrailingStopManager:
    """Compute trailing-stop updates across multiple modes."""

    def __init__(
        self,
        atr_multiplier: Decimal = Decimal("2.5"),
        chandelier_multiplier: Decimal = Decimal("3.0"),
        break_even_atr_profit: Decimal = Decimal("2.0"),
        pct_trail: Decimal = Decimal("1.5"),
    ) -> None:
        self._atr_mult = atr_multiplier
        self._chan_mult = chandelier_multiplier
        self._be_atr = break_even_atr_profit
        self._pct = pct_trail

    # -- lifecycle -----------------------------------------------------------

    def open_position(
        self,
        symbol: str,
        direction: str,
        entry_price: Decimal,
        initial_stop: Decimal,
        mode: TrailingMode = TrailingMode.ATR_TRAIL,
    ) -> TrailingStopState:
        """Create a fresh trailing-stop state for a new position."""
        state = TrailingStopState(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            current_stop=initial_stop,
            highest_price=entry_price,
            lowest_price=entry_price,
            mode=mode,
        )
        logger.info(
            "trailing_stop_opened | symbol=%s dir=%s entry=%s stop=%s mode=%s",
            symbol,
            direction,
            entry_price,
            initial_stop,
            mode.value,
        )
        return state

    # -- update --------------------------------------------------------------

    def update(
        self,
        state: TrailingStopState,
        current_price: Decimal,
        current_high: Decimal,
        current_low: Decimal,
        atr: Decimal,
    ) -> TrailingStopState:
        """Return a new state with the trailing stop adjusted to *current_price*.

        The stop only ever moves in the protective direction (up for BUY,
        down for SELL).  It never widens.
        """
        highest = max(state.highest_price, current_high)
        lowest = min(state.lowest_price, current_low)

        mode = state.mode
        is_be = state.is_break_even
        new_stop = state.current_stop

        if mode is TrailingMode.ATR_TRAIL:
            new_stop = self._atr_trail(state, highest, lowest, atr)
        elif mode is TrailingMode.CHANDELIER:
            new_stop = self._chandelier(state, highest, lowest, atr)
        elif mode is TrailingMode.BREAK_EVEN:
            new_stop, mode, is_be = self._break_even(
                state,
                current_price,
                highest,
                lowest,
                atr,
            )
        elif mode is TrailingMode.PERCENTAGE:
            new_stop = self._percentage(state, highest, lowest)

        # Quantise to 5 decimal places (standard FX precision).
        new_stop = new_stop.quantize(Decimal("0.00001"), rounding=ROUND_HALF_EVEN)

        if new_stop != state.current_stop:
            logger.debug(
                "trailing_stop_moved | symbol=%s stop=%s->%s mode=%s",
                state.symbol,
                state.current_stop,
                new_stop,
                mode.value,
            )

        return TrailingStopState(
            symbol=state.symbol,
            direction=state.direction,
            entry_price=state.entry_price,
            current_stop=new_stop,
            highest_price=highest,
            lowest_price=lowest,
            mode=mode,
            is_break_even=is_be,
        )

    # -- stop-out check ------------------------------------------------------

    def is_stopped_out(
        self,
        state: TrailingStopState,
        current_price: Decimal,
    ) -> bool:
        """Return *True* when *current_price* has breached the stop."""
        if state.direction == "BUY":
            return current_price <= state.current_stop
        return current_price >= state.current_stop

    # -- private mode handlers -----------------------------------------------

    def _atr_trail(
        self,
        state: TrailingStopState,
        highest: Decimal,
        lowest: Decimal,
        atr: Decimal,
    ) -> Decimal:
        offset = self._atr_mult * atr
        if state.direction == "BUY":
            candidate = highest - offset
            return max(candidate, state.current_stop)
        candidate = lowest + offset
        return min(candidate, state.current_stop)

    def _chandelier(
        self,
        state: TrailingStopState,
        highest: Decimal,
        lowest: Decimal,
        atr: Decimal,
    ) -> Decimal:
        offset = self._chan_mult * atr
        if state.direction == "BUY":
            candidate = highest - offset
            return max(candidate, state.current_stop)
        candidate = lowest + offset
        return min(candidate, state.current_stop)

    def _break_even(
        self,
        state: TrailingStopState,
        current_price: Decimal,
        highest: Decimal,
        lowest: Decimal,
        atr: Decimal,
    ) -> tuple[Decimal, TrailingMode, bool]:
        threshold = self._be_atr * atr

        if state.direction == "BUY":
            profit = current_price - state.entry_price
        else:
            profit = state.entry_price - current_price

        if not state.is_break_even and profit > threshold:
            logger.info(
                "trailing_stop_break_even | symbol=%s entry=%s",
                state.symbol,
                state.entry_price,
            )
            # Promote stop to entry and switch to ATR trailing.
            new_stop = state.entry_price
            if state.direction == "BUY":
                new_stop = max(new_stop, state.current_stop)
            else:
                new_stop = min(new_stop, state.current_stop)
            return new_stop, TrailingMode.ATR_TRAIL, True

        return state.current_stop, state.mode, state.is_break_even

    def _percentage(
        self,
        state: TrailingStopState,
        highest: Decimal,
        lowest: Decimal,
    ) -> Decimal:
        factor = self._pct / _ONE_HUNDRED
        if state.direction == "BUY":
            candidate = highest * (1 - factor)
            return max(candidate, state.current_stop)
        candidate = lowest * (1 + factor)
        return min(candidate, state.current_stop)


# ---------------------------------------------------------------------------
# Position tracker
# ---------------------------------------------------------------------------


class PositionTracker:
    """Track multiple trailing-stop positions keyed by symbol."""

    def __init__(self, manager: TrailingStopManager) -> None:
        self._manager = manager
        self._positions: dict[str, TrailingStopState] = {}

    def open(
        self,
        symbol: str,
        direction: str,
        entry_price: Decimal,
        initial_stop: Decimal,
        mode: TrailingMode = TrailingMode.ATR_TRAIL,
    ) -> None:
        """Register a new position for trailing."""
        self._positions[symbol] = self._manager.open_position(
            symbol,
            direction,
            entry_price,
            initial_stop,
            mode,
        )

    def update_all(self, bars: dict[str, dict[str, Any]]) -> list[str]:
        """Update every tracked position and return symbols that got stopped out.

        *bars* maps symbol to a dict with keys ``price``, ``high``, ``low``,
        and ``atr`` — all as :class:`~decimal.Decimal`.
        """
        stopped: list[str] = []
        for symbol, state in list(self._positions.items()):
            bar = bars.get(symbol)
            if bar is None:
                continue

            new_state = self._manager.update(
                state,
                current_price=bar["price"],
                current_high=bar["high"],
                current_low=bar["low"],
                atr=bar["atr"],
            )
            self._positions[symbol] = new_state

            if self._manager.is_stopped_out(new_state, bar["price"]):
                logger.warning(
                    "trailing_stop_hit | symbol=%s stop=%s price=%s",
                    symbol,
                    new_state.current_stop,
                    bar["price"],
                )
                stopped.append(symbol)

        return stopped

    def close(self, symbol: str) -> None:
        """Remove a position from tracking."""
        self._positions.pop(symbol, None)

    def get_position(self, symbol: str) -> TrailingStopState | None:
        """Return the current state for *symbol*, or *None*."""
        return self._positions.get(symbol)
