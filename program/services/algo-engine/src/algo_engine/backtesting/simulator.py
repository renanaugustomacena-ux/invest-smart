"""TradeSimulator — simulates order fills with realistic market frictions.

Tracks open positions, checks SL/TP hits per bar, applies configurable
spread, slippage, and commission costs. Maintains a complete equity curve
and trade log for post-run analysis.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

from algo_engine.features.pipeline import OHLCVBar

logger = get_logger(__name__)


@dataclass
class OpenPosition:
    """Represents an active simulated position."""

    position_id: str
    signal_id: str
    symbol: str
    direction: str
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    lots: Decimal
    entry_timestamp: int
    commission: Decimal


class TradeSimulator:
    """Simulates trade execution with realistic market frictions.

    Models spread (default 1.5 pips), slippage (0.5 pips), and commission
    ($7/lot) to produce realistic fill prices and P&L. Checks each bar's
    high/low against open positions' SL/TP levels.

    Usage:
        sim = TradeSimulator(initial_equity=Decimal("10000"))
        sim.open_position(signal_dict, bar)
        sim.process_bar(next_bar)  # checks SL/TP hits
        sim.close_all_positions(final_bar)
    """

    def __init__(
        self,
        *,
        initial_equity: Decimal = Decimal("10000"),
        spread_pips: Decimal = Decimal("1.5"),
        slippage_pips: Decimal = Decimal("0.5"),
        commission_per_lot: Decimal = Decimal("7"),
        pip_value: Decimal = Decimal("0.0001"),
    ) -> None:
        self._initial_equity = initial_equity
        self._spread_pips = spread_pips
        self._slippage_pips = slippage_pips
        self._commission_per_lot = commission_per_lot
        self._pip_value = pip_value

        self._equity = initial_equity
        self._open_positions: list[OpenPosition] = []
        self._equity_curve: list[Decimal] = [initial_equity]
        self._trade_log: list[dict[str, Any]] = []

    @property
    def equity(self) -> Decimal:
        """Current account equity."""
        return self._equity

    @property
    def equity_curve(self) -> list[Decimal]:
        """Complete equity curve (one entry per bar processed plus initial)."""
        return self._equity_curve

    @property
    def trade_log(self) -> list[dict[str, Any]]:
        """List of all completed trades with full details."""
        return self._trade_log

    @property
    def open_position_count(self) -> int:
        """Number of currently open positions."""
        return len(self._open_positions)

    def _spread_cost(self) -> Decimal:
        """Total spread in price units."""
        return self._spread_pips * self._pip_value

    def _slippage_cost(self) -> Decimal:
        """Total slippage in price units."""
        return self._slippage_pips * self._pip_value

    def _fill_price(self, signal_price: Decimal, direction: str) -> Decimal:
        """Calculate the realistic fill price including spread and slippage.

        For BUY orders: fill above market (price + half_spread + slippage).
        For SELL orders: fill below market (price - half_spread - slippage).
        """
        half_spread = (self._spread_cost() / Decimal("2")).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_EVEN
        )
        slippage = self._slippage_cost()

        if direction == "BUY" or direction == "Direction.BUY":
            return signal_price + half_spread + slippage
        else:
            return signal_price - half_spread - slippage

    def open_position(self, signal: dict[str, Any], bar: OHLCVBar) -> None:
        """Open a new simulated position from a trading signal.

        Args:
            signal: Trading signal dict from AlgoEngine.process_bar().
            bar: The bar on which the signal was generated.
        """
        direction = str(signal.get("direction", ""))
        entry_price = Decimal(str(signal["entry_price"]))
        fill = self._fill_price(entry_price, direction)
        lots = Decimal(str(signal.get("suggested_lots", "0.01")))
        commission = (self._commission_per_lot * lots).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )

        position = OpenPosition(
            position_id=str(uuid.uuid4()),
            signal_id=str(signal.get("signal_id", "")),
            symbol=str(signal.get("symbol", "")),
            direction=direction,
            entry_price=fill,
            stop_loss=Decimal(str(signal.get("stop_loss", "0"))),
            take_profit=Decimal(str(signal.get("take_profit", "0"))),
            lots=lots,
            entry_timestamp=bar.timestamp,
            commission=commission,
        )

        self._equity -= commission
        self._open_positions.append(position)

        logger.debug(
            "Position opened",
            position_id=position.position_id,
            direction=direction,
            fill_price=str(fill),
            signal_price=str(entry_price),
            lots=str(lots),
            commission=str(commission),
        )

    def process_bar(self, bar: OHLCVBar) -> None:
        """Check all open positions for SL/TP hits on this bar.

        For each open position, checks if the bar's high/low would have
        triggered the stop-loss or take-profit. If both would trigger on
        the same bar, stop-loss takes priority (conservative assumption).

        After processing exits, records the current equity to the curve.

        Args:
            bar: The current OHLCV bar to check against open positions.
        """
        closed_indices: list[int] = []

        for i, pos in enumerate(self._open_positions):
            exit_price: Decimal | None = None
            exit_reason: str = ""

            if self._is_buy(pos.direction):
                # BUY: SL hit if bar low <= stop_loss, TP hit if bar high >= take_profit
                if pos.stop_loss > ZERO and bar.low <= pos.stop_loss:
                    exit_price = pos.stop_loss
                    exit_reason = "stop_loss"
                elif pos.take_profit > ZERO and bar.high >= pos.take_profit:
                    exit_price = pos.take_profit
                    exit_reason = "take_profit"
            else:
                # SELL: SL hit if bar high >= stop_loss, TP hit if bar low <= take_profit
                if pos.stop_loss > ZERO and bar.high >= pos.stop_loss:
                    exit_price = pos.stop_loss
                    exit_reason = "stop_loss"
                elif pos.take_profit > ZERO and bar.low <= pos.take_profit:
                    exit_price = pos.take_profit
                    exit_reason = "take_profit"

            if exit_price is not None:
                self._close_position(pos, exit_price, exit_reason, bar.timestamp)
                closed_indices.append(i)

        # Remove closed positions in reverse order to preserve indices
        for i in sorted(closed_indices, reverse=True):
            self._open_positions.pop(i)

        self._equity_curve.append(self._equity)

    def close_all_positions(self, bar: OHLCVBar) -> None:
        """Close all remaining open positions at the bar's close price.

        Called at the end of a backtest to ensure no positions remain open.

        Args:
            bar: The final bar whose close price is used for exits.
        """
        for pos in self._open_positions:
            exit_price = self._fill_price(bar.close, self._opposite_direction(pos.direction))
            self._close_position(pos, exit_price, "end_of_backtest", bar.timestamp)

        self._open_positions.clear()

    def _close_position(
        self,
        pos: OpenPosition,
        exit_price: Decimal,
        reason: str,
        exit_timestamp: int,
    ) -> None:
        """Record a closed trade and update equity."""
        pnl = self._calculate_pnl(pos, exit_price)
        self._equity += pnl

        trade_record = {
            "position_id": pos.position_id,
            "signal_id": pos.signal_id,
            "symbol": pos.symbol,
            "direction": pos.direction,
            "entry_price": pos.entry_price,
            "exit_price": exit_price,
            "stop_loss": pos.stop_loss,
            "take_profit": pos.take_profit,
            "lots": pos.lots,
            "pnl": pnl,
            "commission": pos.commission,
            "entry_timestamp": pos.entry_timestamp,
            "exit_timestamp": exit_timestamp,
            "exit_reason": reason,
        }
        self._trade_log.append(trade_record)

        logger.debug(
            "Position closed",
            position_id=pos.position_id,
            direction=pos.direction,
            entry_price=str(pos.entry_price),
            exit_price=str(exit_price),
            pnl=str(pnl),
            reason=reason,
        )

    def _calculate_pnl(self, pos: OpenPosition, exit_price: Decimal) -> Decimal:
        """Calculate profit/loss in account currency for a position.

        P&L = (exit - entry) * lots * lot_size for BUY
        P&L = (entry - exit) * lots * lot_size for SELL

        The lot_size is derived from pip_value. For standard forex:
        1 pip = $10 per standard lot, so lot_size = pip_value_per_lot / pip_value.
        We use a simplified model: P&L in price points * lots / pip_value * 10.
        """
        if self._is_buy(pos.direction):
            price_diff = exit_price - pos.entry_price
        else:
            price_diff = pos.entry_price - exit_price

        # Convert price difference to pips, then to currency
        pips = price_diff / self._pip_value
        # Standard lot: 1 pip = $10, so PnL = pips * $10 * lots
        pip_value_per_lot = Decimal("10")
        pnl = (pips * pip_value_per_lot * pos.lots).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )
        return pnl

    @staticmethod
    def _is_buy(direction: str) -> bool:
        """Check if a direction string represents a BUY."""
        d = direction.upper()
        return "BUY" in d

    @staticmethod
    def _opposite_direction(direction: str) -> str:
        """Return the opposite direction for closing fills."""
        if TradeSimulator._is_buy(direction):
            return "SELL"
        return "BUY"
