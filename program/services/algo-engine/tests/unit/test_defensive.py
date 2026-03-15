"""Tests for algo_engine.strategies.defensive — DefensiveStrategy."""

from decimal import Decimal

from moneymaker_common.enums import Direction

from algo_engine.strategies.defensive import DefensiveStrategy


class TestDefensiveStrategy:
    def test_name(self):
        s = DefensiveStrategy()
        assert s.name == "defensive_v1"

    def test_always_hold(self):
        """Defensive strategy always returns HOLD."""
        s = DefensiveStrategy()
        features = {
            "adx": Decimal("50"),
            "atr": Decimal("20"),
            "rsi": Decimal("80"),
        }
        result = s.analyze(features)
        assert result.direction == Direction.HOLD

    def test_hold_with_empty_features(self):
        """Even with empty features → HOLD."""
        s = DefensiveStrategy()
        result = s.analyze({})
        assert result.direction == Direction.HOLD

    def test_high_confidence_hold(self):
        """Defensive HOLD should have high confidence."""
        s = DefensiveStrategy()
        result = s.analyze({"adx": Decimal("10")})
        assert result.confidence >= Decimal("0.70")

    def test_metadata_includes_fail_safe(self):
        """Metadata should indicate fail-safe reason."""
        s = DefensiveStrategy()
        result = s.analyze({})
        assert result.metadata is not None
        assert result.metadata["reason"] == "fail_safe"

    def test_reasoning_mentions_defensive(self):
        """Reasoning should identify as defensive."""
        s = DefensiveStrategy()
        result = s.analyze({"adx": Decimal("30"), "atr": Decimal("15"), "rsi": Decimal("45")})
        assert "Difensiva" in result.reasoning
