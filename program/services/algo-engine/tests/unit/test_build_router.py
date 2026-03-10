"""Tests for algo_engine.strategies.build_algo_router factory."""

from decimal import Decimal

from moneymaker_common.enums import Direction, MarketRegime

from algo_engine.strategies import build_algo_router


class TestBuildDefaultRouter:
    def test_all_regimes_registered(self):
        """All 5 regimes should be registered."""
        router = build_algo_router()
        regimes = router.get_registered_regimes()
        for regime in MarketRegime:
            assert regime.value in regimes

    def test_trending_up_uses_trend_strategy(self):
        router = build_algo_router()
        features = {
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("35"),
        }
        result = router.route(MarketRegime.TRENDING_UP, features)
        assert result.direction == Direction.BUY

    def test_ranging_uses_mean_reversion_strategy(self):
        router = build_algo_router()
        features = {
            "bb_pct_b": Decimal("0.05"),
            "rsi": Decimal("25"),
            "stoch_k": Decimal("15"),
        }
        result = router.route(MarketRegime.RANGING, features)
        assert result.direction == Direction.BUY

    def test_high_volatility_uses_defensive_strategy(self):
        router = build_algo_router()
        result = router.route(MarketRegime.HIGH_VOLATILITY, {"adx": Decimal("50")})
        assert result.direction == Direction.HOLD

    def test_reversal_uses_defensive_strategy(self):
        router = build_algo_router()
        result = router.route(MarketRegime.REVERSAL, {"rsi": Decimal("80")})
        assert result.direction == Direction.HOLD

    def test_unknown_regime_uses_default_defensive(self):
        router = build_algo_router()
        result = router.route("completely_unknown", {})
        assert result.direction == Direction.HOLD
