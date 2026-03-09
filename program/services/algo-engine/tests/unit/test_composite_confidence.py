"""Tests for CompositeConfidence — multi-factor calibrated scoring."""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.signals.composite_confidence import CompositeConfidence


def _bullish_features():
    return {
        "ema_fast": Decimal("2355"),
        "ema_slow": Decimal("2340"),
        "rsi": Decimal("65"),
        "macd_histogram": Decimal("2.0"),
        "stoch_k": Decimal("70"),
        "plus_di": Decimal("30"),
        "minus_di": Decimal("15"),
        "bb_pct_b": Decimal("0.80"),
        "feature_composite_score": Decimal("0.5"),
    }


def _bearish_features():
    return {
        "ema_fast": Decimal("2330"),
        "ema_slow": Decimal("2345"),
        "rsi": Decimal("30"),
        "macd_histogram": Decimal("-3.0"),
        "stoch_k": Decimal("20"),
        "plus_di": Decimal("10"),
        "minus_di": Decimal("35"),
        "bb_pct_b": Decimal("0.15"),
        "feature_composite_score": Decimal("-0.6"),
    }


def _neutral_features():
    return {
        "ema_fast": Decimal("2340"),
        "ema_slow": Decimal("2340"),
        "rsi": Decimal("50"),
        "macd_histogram": Decimal("0"),
        "stoch_k": Decimal("50"),
        "plus_di": Decimal("20"),
        "minus_di": Decimal("20"),
        "bb_pct_b": Decimal("0.50"),
    }


class TestIndicatorAgreement:
    def test_all_agree_buy(self):
        cc = CompositeConfidence()
        result = cc._indicator_agreement(_bullish_features(), "BUY")
        assert result == Decimal("1"), f"All indicators bullish, expected 1.0, got {result}"

    def test_all_agree_sell(self):
        cc = CompositeConfidence()
        result = cc._indicator_agreement(_bearish_features(), "SELL")
        assert result == Decimal("1"), f"All indicators bearish, expected 1.0, got {result}"

    def test_none_agree(self):
        cc = CompositeConfidence()
        # Bullish features but SELL direction
        result = cc._indicator_agreement(_bullish_features(), "SELL")
        assert result == Decimal("0"), f"No agreement, expected 0, got {result}"

    def test_neutral_partial(self):
        cc = CompositeConfidence()
        result = cc._indicator_agreement(_neutral_features(), "BUY")
        # Some will agree, some won't (RSI=50 → not > 50 for BUY)
        assert Decimal("0") <= result <= Decimal("1")


class TestHistoricalEdge:
    def test_positive_belief_edge(self):
        cc = CompositeConfidence()
        result = cc._historical_edge(Decimal("0.6"), win_rate=None)
        assert result == Decimal("0.8")  # (0.6 + 1) / 2

    def test_negative_belief_edge(self):
        cc = CompositeConfidence()
        result = cc._historical_edge(Decimal("-0.4"), win_rate=None)
        assert result == Decimal("0.3")  # (-0.4 + 1) / 2

    def test_explicit_win_rate_overrides(self):
        cc = CompositeConfidence()
        result = cc._historical_edge(Decimal("-0.9"), win_rate=Decimal("0.70"))
        assert result == Decimal("0.70")


class TestCompositeComputation:
    def test_strong_bullish_high_confidence(self):
        cc = CompositeConfidence()
        confidence = cc.compute(
            features=_bullish_features(),
            direction="BUY",
            belief_edge=Decimal("0.5"),
        )
        assert confidence > Decimal("0.6"), f"Strong bull should be > 0.6, got {confidence}"
        assert confidence <= Decimal("1")

    def test_strong_bearish_high_confidence(self):
        cc = CompositeConfidence()
        confidence = cc.compute(
            features=_bearish_features(),
            direction="SELL",
            belief_edge=Decimal("0.5"),
        )
        assert confidence > Decimal("0.6"), f"Strong bear should be > 0.6, got {confidence}"

    def test_conflicting_low_confidence(self):
        cc = CompositeConfidence()
        # Bullish features but SELL direction = disagreement
        confidence = cc.compute(
            features=_bullish_features(),
            direction="SELL",
            belief_edge=Decimal("-0.5"),
        )
        assert confidence < Decimal("0.4"), f"Conflicting signal should be < 0.4, got {confidence}"

    def test_output_bounded_0_1(self):
        cc = CompositeConfidence()
        for direction in ("BUY", "SELL"):
            for edge in (Decimal("-1"), Decimal("0"), Decimal("1")):
                conf = cc.compute(
                    features=_bullish_features(),
                    direction=direction,
                    belief_edge=edge,
                )
                assert Decimal("0") <= conf <= Decimal("1"), f"Out of bounds: {conf}"

    def test_with_explicit_win_rate(self):
        cc = CompositeConfidence()
        conf = cc.compute(
            features=_bullish_features(),
            direction="BUY",
            win_rate=Decimal("0.65"),
        )
        assert conf > Decimal("0.5")
