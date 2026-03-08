"""Backtesting framework for the algo-engine trading system.

Zero code changes between backtest and live: BacktestEngine wraps the same
AlgoEngine used in production, feeding historical bars through the identical
9-step deterministic pipeline.
"""

from algo_engine.backtesting.engine import BacktestEngine
from algo_engine.backtesting.metrics import BacktestMetrics, BacktestResult
from algo_engine.backtesting.simulator import TradeSimulator

__all__ = [
    "BacktestEngine",
    "BacktestMetrics",
    "BacktestResult",
    "TradeSimulator",
]
