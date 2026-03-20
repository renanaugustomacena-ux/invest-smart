# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""BacktestEngine — feeds historical bars through the production AlgoEngine.

Zero code changes between backtest and live: BacktestEngine wraps the exact
same AlgoEngine.process_bar() used in production. The only difference is the
data source (historical bars instead of a live ZMQ feed).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from moneymaker_common.logging import get_logger

from algo_engine.backtesting.metrics import BacktestMetrics, BacktestResult
from algo_engine.backtesting.simulator import TradeSimulator
from algo_engine.engine import AlgoEngine
from algo_engine.features.pipeline import OHLCVBar

logger = get_logger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""

    symbol: str
    timeframe: str
    initial_equity: Decimal = Decimal("10000")
    spread_pips: Decimal = Decimal("1.5")
    slippage_pips: Decimal = Decimal("0.5")
    commission_per_lot: Decimal = Decimal("7")
    pip_value: Decimal = Decimal("0.0001")
    risk_free_rate: Decimal = Decimal("0.02")


class BacktestEngine:
    """Feeds historical OHLCV bars into a production AlgoEngine instance.

    Collects all emitted signals and passes them to a TradeSimulator for
    fill simulation, equity tracking, and SL/TP management. After the run
    completes, computes comprehensive performance metrics via BacktestMetrics.

    Usage:
        engine = BacktestEngine(algo_engine=algo, config=config)
        result = await engine.run(bars)
        print(result.metrics)
    """

    def __init__(
        self,
        *,
        algo_engine: AlgoEngine,
        config: BacktestConfig,
    ) -> None:
        self._algo_engine = algo_engine
        self._config = config
        self._simulator = TradeSimulator(
            initial_equity=config.initial_equity,
            spread_pips=config.spread_pips,
            slippage_pips=config.slippage_pips,
            commission_per_lot=config.commission_per_lot,
            pip_value=config.pip_value,
        )
        self._signals: list[dict[str, Any]] = []
        self._bars_processed: int = 0

    @property
    def simulator(self) -> TradeSimulator:
        """Access the underlying TradeSimulator for inspection."""
        return self._simulator

    async def run(self, bars: list[OHLCVBar]) -> BacktestResult:
        """Execute the backtest over the provided historical bars.

        Each bar is fed to AlgoEngine.process_bar() exactly as it would be
        in production. Emitted signals are forwarded to the TradeSimulator
        for fill simulation. After all bars are processed, remaining open
        positions are closed at the final bar's close price.

        Args:
            bars: Chronologically sorted list of OHLCVBar instances.

        Returns:
            BacktestResult with full equity curve, trade log, and metrics.
        """
        if not bars:
            logger.warning("Empty bar list provided to backtest")
            return self._build_result(bars)

        start_time = time.monotonic()
        total_bars = len(bars)
        log_interval = max(1, total_bars // 20)

        logger.info(
            "Backtest starting",
            symbol=self._config.symbol,
            timeframe=self._config.timeframe,
            total_bars=total_bars,
            initial_equity=str(self._config.initial_equity),
        )

        for i, bar in enumerate(bars):
            self._bars_processed += 1

            # Process bar through the production pipeline
            signal = await self._algo_engine.process_bar(
                self._config.symbol, self._config.timeframe, bar
            )

            if signal is not None:
                self._signals.append(signal)
                self._simulator.open_position(signal, bar)

            # Check SL/TP hits and update equity for open positions
            self._simulator.process_bar(bar)

            # Progress logging
            if (i + 1) % log_interval == 0:
                pct = ((i + 1) / total_bars) * 100
                logger.info(
                    "Backtest progress",
                    percent=f"{pct:.0f}%",
                    bars_processed=i + 1,
                    signals=len(self._signals),
                    open_positions=self._simulator.open_position_count,
                )

        # Close any remaining open positions at the last bar's close
        if bars:
            self._simulator.close_all_positions(bars[-1])

        elapsed = time.monotonic() - start_time
        logger.info(
            "Backtest complete",
            elapsed_seconds=f"{elapsed:.2f}",
            bars_processed=self._bars_processed,
            total_signals=len(self._signals),
            total_trades=len(self._simulator.trade_log),
        )

        return self._build_result(bars)

    def _build_result(self, bars: list[OHLCVBar]) -> BacktestResult:
        """Compute metrics and assemble the final BacktestResult."""
        metrics_calculator = BacktestMetrics(
            risk_free_rate=self._config.risk_free_rate,
        )
        return metrics_calculator.compute(
            equity_curve=self._simulator.equity_curve,
            trade_log=self._simulator.trade_log,
            bars_processed=self._bars_processed,
            initial_equity=self._config.initial_equity,
        )

    async def run_streaming(self, bar_iterator) -> BacktestResult:
        """Run backtest from a streaming bar iterator (memory-efficient).

        Accepts any iterable of OHLCVBar, including generators from
        data_loader.iter_bars_from_csv(). Collects bars into a list
        for the final result but processes them one at a time.

        Args:
            bar_iterator: Iterable of OHLCVBar instances.

        Returns:
            BacktestResult with full equity curve, trade log, and metrics.
        """
        bars_collected: list[OHLCVBar] = []
        for bar in bar_iterator:
            bars_collected.append(bar)

            signal = await self._algo_engine.process_bar(
                self._config.symbol, self._config.timeframe, bar
            )
            self._bars_processed += 1

            if signal is not None:
                self._signals.append(signal)
                self._simulator.open_position(signal, bar)

            self._simulator.process_bar(bar)

        if bars_collected:
            self._simulator.close_all_positions(bars_collected[-1])

        return self._build_result(bars_collected)
