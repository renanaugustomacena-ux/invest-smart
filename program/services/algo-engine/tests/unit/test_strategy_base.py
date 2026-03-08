"""Tests for algo_engine.strategies.base — SignalSuggestion and TradingStrategy ABC."""

from decimal import Decimal

import pytest

from algo_engine.strategies.base import SignalSuggestion, TradingStrategy


class TestSignalSuggestion:
    def test_valid_buy(self):
        s = SignalSuggestion("BUY", Decimal("0.80"), "Test buy")
        assert s.direction == "BUY"
        assert s.confidence == Decimal("0.80")
        assert s.reasoning == "Test buy"
        assert s.metadata is None

    def test_valid_sell(self):
        s = SignalSuggestion("SELL", Decimal("0.75"), "Test sell")
        assert s.direction == "SELL"

    def test_valid_hold(self):
        s = SignalSuggestion("HOLD", Decimal("0.10"), "No signal")
        assert s.direction == "HOLD"

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError, match="Direzione non valida"):
            SignalSuggestion("INVALID", Decimal("0.50"), "Bad")

    def test_confidence_above_1_raises(self):
        with pytest.raises(ValueError, match="confidenza"):
            SignalSuggestion("BUY", Decimal("1.5"), "Too confident")

    def test_confidence_below_0_raises(self):
        with pytest.raises(ValueError, match="confidenza"):
            SignalSuggestion("BUY", Decimal("-0.1"), "Negative")

    def test_confidence_boundary_zero(self):
        s = SignalSuggestion("HOLD", Decimal("0"), "Zero confidence")
        assert s.confidence == Decimal("0")

    def test_confidence_boundary_one(self):
        s = SignalSuggestion("BUY", Decimal("1"), "Max confidence")
        assert s.confidence == Decimal("1")

    def test_metadata(self):
        s = SignalSuggestion(
            "BUY",
            Decimal("0.80"),
            "Meta",
            metadata={"strategy": "trend_v1", "version": 2},
        )
        assert s.metadata == {"strategy": "trend_v1", "version": 2}


class TestTradingStrategyABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            TradingStrategy()

    def test_subclass_must_implement_name(self):
        class IncompleteStrategy(TradingStrategy):
            def analyze(self, features):
                return SignalSuggestion("HOLD", Decimal("0"), "")

        with pytest.raises(TypeError):
            IncompleteStrategy()

    def test_subclass_must_implement_analyze(self):
        class IncompleteStrategy(TradingStrategy):
            @property
            def name(self):
                return "test"

        with pytest.raises(TypeError):
            IncompleteStrategy()
