"""Tests for algo_engine.strategies.regime_router — RegimeRouter."""

from decimal import Decimal

from algo_engine.strategies.regime_router import RegimeRouter


class TestRegimeRouter:
    def test_route_to_registered_strategy(self, stub_buy_strategy):
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        result = router.route("trending_up", {"symbol": "XAUUSD"})
        assert result.direction == "BUY"
        assert result.confidence == Decimal("0.80")

    def test_route_uses_default_for_unknown_regime(self, stub_hold_strategy):
        router = RegimeRouter()
        router.set_default_strategy(stub_hold_strategy)
        result = router.route("unknown_regime", {})
        assert result.direction == "HOLD"

    def test_no_strategy_no_default_returns_hold(self):
        router = RegimeRouter()
        result = router.route("trending_up", {})
        assert result.direction == "HOLD"
        assert result.confidence == Decimal("0")

    def test_registered_regimes(self, stub_buy_strategy, stub_sell_strategy):
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        router.register_strategy("trending_down", stub_sell_strategy)
        regimes = router.get_registered_regimes()
        assert "trending_up" in regimes
        assert "trending_down" in regimes
        assert len(regimes) == 2

    def test_multiple_regimes_route_correctly(
        self, stub_buy_strategy, stub_sell_strategy, stub_hold_strategy
    ):
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        router.register_strategy("trending_down", stub_sell_strategy)
        router.register_strategy("ranging", stub_hold_strategy)

        assert router.route("trending_up", {}).direction == "BUY"
        assert router.route("trending_down", {}).direction == "SELL"
        assert router.route("ranging", {}).direction == "HOLD"
