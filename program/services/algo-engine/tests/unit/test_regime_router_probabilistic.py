"""Tests for RegimeRouter.route_probabilistic — Bayesian weighted routing."""

from decimal import Decimal

from moneymaker_common.enums import Direction

from algo_engine.strategies.regime_router import RegimeRouter


class TestRouteProbabilistic:
    def test_single_regime_full_posterior(self, stub_buy_strategy):
        """One regime with 100% posterior → its signal."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        result = router.route_probabilistic(
            {"trending_up": Decimal("1.0")},
            {"symbol": "XAUUSD"},
        )
        assert result.direction == Direction.BUY
        assert result.confidence > Decimal("0")

    def test_below_min_posterior_ignored(self, stub_buy_strategy):
        """Regime below 10% threshold is skipped → HOLD."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        result = router.route_probabilistic(
            {"trending_up": Decimal("0.05")},
            {},
        )
        assert result.direction == Direction.HOLD

    def test_two_same_direction_regimes(self, stub_buy_strategy):
        """Two BUY regimes → consensus BUY."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        # Second BUY strategy
        from tests.conftest import StubStrategy

        buy2 = StubStrategy(name="momentum", direction="BUY", confidence=Decimal("0.70"))
        router.register_strategy("ranging", buy2)

        result = router.route_probabilistic(
            {"trending_up": Decimal("0.60"), "ranging": Decimal("0.40")},
            {},
        )
        assert result.direction == Direction.BUY

    def test_conflicting_regimes_low_score_hold(self, stub_buy_strategy, stub_sell_strategy):
        """Evenly split BUY/SELL → HOLD (directional score near zero)."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        router.register_strategy("trending_down", stub_sell_strategy)

        result = router.route_probabilistic(
            {"trending_up": Decimal("0.50"), "trending_down": Decimal("0.50")},
            {},
        )
        # With similar confidence, directional score should be near zero → HOLD
        # stub_buy confidence=0.80, stub_sell confidence=0.75
        # score ≈ (0.5*0.80 - 0.5*0.75) / 1.0 = 0.025 < 0.10
        assert result.direction == Direction.HOLD

    def test_dominant_sell_regime(self, stub_buy_strategy, stub_sell_strategy):
        """SELL dominant by posterior → SELL signal."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        router.register_strategy("trending_down", stub_sell_strategy)

        result = router.route_probabilistic(
            {"trending_up": Decimal("0.15"), "trending_down": Decimal("0.85")},
            {},
        )
        assert result.direction == Direction.SELL

    def test_dominant_buy_regime(self, stub_buy_strategy, stub_sell_strategy):
        """BUY dominant by posterior → BUY signal."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        router.register_strategy("trending_down", stub_sell_strategy)

        result = router.route_probabilistic(
            {"trending_up": Decimal("0.85"), "trending_down": Decimal("0.15")},
            {},
        )
        assert result.direction == Direction.BUY

    def test_confidence_capped_at_085(self, stub_buy_strategy):
        """Confidence should be capped at 0.85."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        result = router.route_probabilistic(
            {"trending_up": Decimal("1.0")},
            {},
        )
        assert result.confidence <= Decimal("0.85")

    def test_no_registered_strategy_for_regime(self):
        """Posteriors reference regime with no strategy → fallback."""
        router = RegimeRouter()
        result = router.route_probabilistic(
            {"unknown_regime": Decimal("0.90")},
            {},
        )
        assert result.direction == Direction.HOLD
        assert result.confidence == Decimal("0")

    def test_fallback_to_default_strategy(self, stub_hold_strategy):
        """No matching regime but default set → use default."""
        router = RegimeRouter()
        router.set_default_strategy(stub_hold_strategy)
        result = router.route_probabilistic(
            {"nonexistent": Decimal("0.90")},
            {},
        )
        assert result.direction == Direction.HOLD

    def test_metadata_contains_strategy_info(self, stub_buy_strategy):
        """Result metadata should contain probabilistic routing info."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        result = router.route_probabilistic(
            {"trending_up": Decimal("0.80")},
            {},
        )
        assert result.metadata is not None
        assert result.metadata["strategy"] == "probabilistic_router"
        assert "directional_score" in result.metadata
        assert "regime_posteriors" in result.metadata

    def test_reasoning_includes_regime_info(self, stub_buy_strategy, stub_sell_strategy):
        """Reasoning should mention participating strategies."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        router.register_strategy("trending_down", stub_sell_strategy)
        result = router.route_probabilistic(
            {"trending_up": Decimal("0.70"), "trending_down": Decimal("0.30")},
            {},
        )
        assert "Probabilistic consensus" in result.reasoning

    def test_hold_confidence_is_030(self, stub_buy_strategy, stub_sell_strategy):
        """When direction is HOLD (conflicting), confidence should be 0.30."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        router.register_strategy("trending_down", stub_sell_strategy)
        result = router.route_probabilistic(
            {"trending_up": Decimal("0.50"), "trending_down": Decimal("0.50")},
            {},
        )
        if result.direction == Direction.HOLD:
            assert result.confidence == Decimal("0.30")

    def test_empty_posteriors(self):
        """Empty posterior dict → HOLD."""
        router = RegimeRouter()
        result = router.route_probabilistic({}, {})
        assert result.direction == Direction.HOLD

    def test_three_regimes_mixed(self, stub_buy_strategy, stub_sell_strategy, stub_hold_strategy):
        """Three regimes with mixed signals — buy dominant."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        router.register_strategy("trending_down", stub_sell_strategy)
        router.register_strategy("ranging", stub_hold_strategy)

        result = router.route_probabilistic(
            {
                "trending_up": Decimal("0.60"),
                "trending_down": Decimal("0.20"),
                "ranging": Decimal("0.20"),
            },
            {},
        )
        # BUY dominant: 0.60 * 0.80 = 0.48 buy, 0.20 * 0.75 = 0.15 sell
        # directional = (0.48 - 0.15) / 1.0 = 0.33 > 0.10 → BUY
        assert result.direction == Direction.BUY


# ---------------------------------------------------------------------------
# RegimeRouter.route — metadata injection
# ---------------------------------------------------------------------------


class TestRouteMetadataInjection:
    def test_strategy_name_injected(self, stub_buy_strategy):
        """route() should inject strategy name into metadata."""
        router = RegimeRouter()
        router.register_strategy("trending_up", stub_buy_strategy)
        result = router.route("trending_up", {"symbol": "EURUSD"})
        assert result.metadata is not None
        assert result.metadata["strategy"] == "stub_buy"

    def test_no_strategy_hold_has_reasoning(self):
        """HOLD due to no strategy should explain why."""
        router = RegimeRouter()
        result = router.route("nonexistent", {})
        assert "Nessuna strategia" in result.reasoning or "nonexistent" in result.reasoning
