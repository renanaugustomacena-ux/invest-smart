# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Algo-engine strategy router factory.

Builds the same router as algo_engine.strategies.build_default_router()
but replaces REVERSAL -> DefensiveStrategy with REVERSAL -> BreakoutStrategy.
"""

from __future__ import annotations

from moneymaker_common.enums import MarketRegime

from algo_engine.strategies.defensive import DefensiveStrategy
from algo_engine.strategies.mean_reversion import MeanReversionStrategy
from algo_engine.strategies.regime_router import RegimeRouter
from algo_engine.strategies.trend_following import TrendFollowingStrategy

from algo_engine.strategies.breakout import BreakoutStrategy


def build_algo_router() -> RegimeRouter:
    """Build strategy router with breakout strategy for reversals."""
    router = RegimeRouter()
    trend = TrendFollowingStrategy()
    mean_rev = MeanReversionStrategy()
    defensive = DefensiveStrategy()
    breakout = BreakoutStrategy()

    router.register_strategy(MarketRegime.TRENDING_UP, trend)
    router.register_strategy(MarketRegime.TRENDING_DOWN, trend)
    router.register_strategy(MarketRegime.RANGING, mean_rev)
    router.register_strategy(MarketRegime.HIGH_VOLATILITY, defensive)
    router.register_strategy(MarketRegime.REVERSAL, breakout)
    router.set_default_strategy(defensive)
    return router
