# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""BacktestMetrics and BacktestResult — comprehensive performance analytics.

All financial calculations use Decimal with ROUND_HALF_EVEN to maintain
precision. Metrics are annualized assuming 252 trading days per year.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

# Annualization factor for daily returns
_TRADING_DAYS_PER_YEAR = Decimal("252")
_SQRT_252 = Decimal(str(math.sqrt(252)))


@dataclass
class BacktestResult:
    """Complete results from a backtest run.

    Contains the full equity curve, trade log, and all computed metrics
    needed to evaluate strategy performance.
    """

    # Equity tracking
    equity_curve: list[Decimal] = field(default_factory=list)
    initial_equity: Decimal = ZERO
    final_equity: Decimal = ZERO

    # Trade log
    trade_log: list[dict[str, Any]] = field(default_factory=list)
    total_trades: int = 0
    bars_processed: int = 0

    # Return metrics
    total_return_pct: Decimal = ZERO
    annualized_return_pct: Decimal = ZERO

    # Risk metrics
    sharpe_ratio: Decimal = ZERO
    sortino_ratio: Decimal = ZERO
    calmar_ratio: Decimal = ZERO
    max_drawdown_pct: Decimal = ZERO
    max_drawdown_value: Decimal = ZERO

    # Trade metrics
    win_rate: Decimal = ZERO
    profit_factor: Decimal = ZERO
    avg_trade_pnl: Decimal = ZERO
    avg_trade_duration_bars: Decimal = ZERO
    winning_trades: int = 0
    losing_trades: int = 0
    gross_profit: Decimal = ZERO
    gross_loss: Decimal = ZERO


def _quantize(value: Decimal, precision: str = "0.0001") -> Decimal:
    """Quantize a Decimal to the given precision with banker's rounding."""
    return value.quantize(Decimal(precision), rounding=ROUND_HALF_EVEN)


class BacktestMetrics:
    """Computes performance metrics from equity curve and trade log.

    All ratios use Decimal arithmetic. The risk-free rate is annualized
    and converted to a daily rate for Sharpe/Sortino calculations.

    Usage:
        metrics = BacktestMetrics(risk_free_rate=Decimal("0.02"))
        result = metrics.compute(equity_curve, trade_log, bars_processed, initial_equity)
    """

    def __init__(self, *, risk_free_rate: Decimal = Decimal("0.02")) -> None:
        self._risk_free_rate = risk_free_rate
        self._daily_risk_free = _quantize(risk_free_rate / _TRADING_DAYS_PER_YEAR, "0.00000001")

    def compute(
        self,
        equity_curve: list[Decimal],
        trade_log: list[dict[str, Any]],
        bars_processed: int,
        initial_equity: Decimal,
    ) -> BacktestResult:
        """Compute all metrics and return a BacktestResult.

        Args:
            equity_curve: List of equity values (one per bar plus initial).
            trade_log: List of completed trade dicts from TradeSimulator.
            bars_processed: Total number of bars fed through the engine.
            initial_equity: Starting account balance.

        Returns:
            BacktestResult with all fields populated.
        """
        result = BacktestResult(
            equity_curve=equity_curve,
            initial_equity=initial_equity,
            final_equity=equity_curve[-1] if equity_curve else initial_equity,
            trade_log=trade_log,
            total_trades=len(trade_log),
            bars_processed=bars_processed,
        )

        if not equity_curve or len(equity_curve) < 2:
            return result

        # Daily returns from equity curve
        returns = self._compute_returns(equity_curve)

        # Total and annualized return
        result.total_return_pct = self._total_return_pct(initial_equity, result.final_equity)
        result.annualized_return_pct = self._annualized_return(
            result.total_return_pct, len(returns)
        )

        # Drawdown
        result.max_drawdown_pct, result.max_drawdown_value = self._max_drawdown(equity_curve)

        # Risk-adjusted ratios
        if returns:
            result.sharpe_ratio = self._sharpe_ratio(returns)
            result.sortino_ratio = self._sortino_ratio(returns)

        if result.max_drawdown_pct > ZERO:
            result.calmar_ratio = _quantize(result.annualized_return_pct / result.max_drawdown_pct)

        # Trade-level metrics
        self._compute_trade_metrics(trade_log, result)

        logger.info(
            "Backtest metrics computed",
            total_return=str(result.total_return_pct),
            sharpe=str(result.sharpe_ratio),
            sortino=str(result.sortino_ratio),
            calmar=str(result.calmar_ratio),
            max_drawdown=str(result.max_drawdown_pct),
            win_rate=str(result.win_rate),
            profit_factor=str(result.profit_factor),
            total_trades=result.total_trades,
        )

        return result

    @staticmethod
    def _compute_returns(equity_curve: list[Decimal]) -> list[Decimal]:
        """Compute period-over-period returns from an equity curve."""
        returns: list[Decimal] = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1]
            if prev == ZERO:
                returns.append(ZERO)
            else:
                ret = _quantize((equity_curve[i] - prev) / prev, "0.00000001")
                returns.append(ret)
        return returns

    @staticmethod
    def _total_return_pct(initial_equity: Decimal, final_equity: Decimal) -> Decimal:
        """Calculate total return as a percentage."""
        if initial_equity == ZERO:
            return ZERO
        return _quantize(((final_equity - initial_equity) / initial_equity) * Decimal("100"))

    @staticmethod
    def _annualized_return(total_return_pct: Decimal, num_periods: int) -> Decimal:
        """Annualize the total return assuming daily periods.

        Uses: (1 + total_return)^(252/n) - 1, expressed as percentage.
        """
        if num_periods == 0:
            return ZERO

        total_return_decimal = total_return_pct / Decimal("100")
        growth = Decimal("1") + total_return_decimal

        if growth <= ZERO:
            return Decimal("-100")

        exponent = float(_TRADING_DAYS_PER_YEAR) / num_periods
        annualized = Decimal(str(float(growth) ** exponent)) - Decimal("1")
        return _quantize(annualized * Decimal("100"))

    def _sharpe_ratio(self, returns: list[Decimal]) -> Decimal:
        """Sharpe ratio: (mean_return - risk_free) / std_return * sqrt(252).

        Annualized for daily returns.
        """
        if len(returns) < 2:
            return ZERO

        mean_return = self._mean(returns)
        std_return = self._std(returns)

        if std_return == ZERO:
            return ZERO

        excess_return = mean_return - self._daily_risk_free
        sharpe = _quantize(excess_return / std_return * _SQRT_252)
        return sharpe

    def _sortino_ratio(self, returns: list[Decimal]) -> Decimal:
        """Sortino ratio: (mean_return - risk_free) / downside_deviation * sqrt(252).

        Uses only negative returns for the denominator.
        """
        if len(returns) < 2:
            return ZERO

        mean_return = self._mean(returns)
        downside_dev = self._downside_deviation(returns)

        if downside_dev == ZERO:
            return ZERO

        excess_return = mean_return - self._daily_risk_free
        sortino = _quantize(excess_return / downside_dev * _SQRT_252)
        return sortino

    @staticmethod
    def _max_drawdown(equity_curve: list[Decimal]) -> tuple[Decimal, Decimal]:
        """Calculate maximum drawdown as percentage and absolute value.

        Returns:
            Tuple of (max_drawdown_pct, max_drawdown_value).
        """
        if not equity_curve:
            return ZERO, ZERO

        peak = equity_curve[0]
        max_dd_pct = ZERO
        max_dd_value = ZERO

        for equity in equity_curve:
            if equity > peak:
                peak = equity

            if peak > ZERO:
                drawdown_value = peak - equity
                drawdown_pct = (drawdown_value / peak) * Decimal("100")

                if drawdown_pct > max_dd_pct:
                    max_dd_pct = drawdown_pct
                    max_dd_value = drawdown_value

        return _quantize(max_dd_pct), _quantize(max_dd_value)

    @staticmethod
    def _compute_trade_metrics(trade_log: list[dict[str, Any]], result: BacktestResult) -> None:
        """Populate trade-level metrics on the result object."""
        if not trade_log:
            return

        winning = []
        losing = []

        for trade in trade_log:
            pnl = Decimal(str(trade.get("pnl", "0")))
            if pnl > ZERO:
                winning.append(pnl)
            elif pnl < ZERO:
                losing.append(pnl)

        result.winning_trades = len(winning)
        result.losing_trades = len(losing)

        # Win rate
        if result.total_trades > 0:
            result.win_rate = _quantize(
                Decimal(str(result.winning_trades))
                / Decimal(str(result.total_trades))
                * Decimal("100")
            )

        # Gross profit and loss
        result.gross_profit = sum(winning, ZERO)
        result.gross_loss = abs(sum(losing, ZERO))

        # Profit factor
        if result.gross_loss > ZERO:
            result.profit_factor = _quantize(result.gross_profit / result.gross_loss)

        # Average trade P&L
        total_pnl = sum((Decimal(str(t.get("pnl", "0"))) for t in trade_log), ZERO)
        result.avg_trade_pnl = _quantize(total_pnl / Decimal(str(result.total_trades)))

        # Average trade duration in bars (using timestamps)
        durations: list[int] = []
        for trade in trade_log:
            entry_ts = int(trade.get("entry_timestamp", 0))
            exit_ts = int(trade.get("exit_timestamp", 0))
            if entry_ts > 0 and exit_ts > 0:
                durations.append(exit_ts - entry_ts)

        if durations:
            avg_dur = Decimal(str(sum(durations))) / Decimal(str(len(durations)))
            result.avg_trade_duration_bars = _quantize(avg_dur, "0.01")

    @staticmethod
    def _mean(values: list[Decimal]) -> Decimal:
        """Calculate the arithmetic mean of a list of Decimals."""
        if not values:
            return ZERO
        total = sum(values, ZERO)
        return total / Decimal(str(len(values)))

    @staticmethod
    def _std(values: list[Decimal]) -> Decimal:
        """Calculate the sample standard deviation of a list of Decimals."""
        n = len(values)
        if n < 2:
            return ZERO

        mean = sum(values, ZERO) / Decimal(str(n))
        squared_diffs = [(v - mean) ** 2 for v in values]
        variance = sum(squared_diffs, ZERO) / Decimal(str(n - 1))

        # Decimal doesn't have sqrt, use float conversion
        std_float = math.sqrt(float(variance))
        return Decimal(str(std_float)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)

    @staticmethod
    def _downside_deviation(values: list[Decimal]) -> Decimal:
        """Calculate downside deviation (std of negative returns only)."""
        negative_returns = [v for v in values if v < ZERO]
        if len(negative_returns) < 2:
            return ZERO

        mean_neg = sum(negative_returns, ZERO) / Decimal(str(len(negative_returns)))
        squared_diffs = [(v - mean_neg) ** 2 for v in negative_returns]
        variance = sum(squared_diffs, ZERO) / Decimal(str(len(negative_returns) - 1))

        std_float = math.sqrt(float(variance))
        return Decimal(str(std_float)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
