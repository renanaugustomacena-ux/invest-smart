"""Tests for MTFConfirmation — cross-timeframe agreement ratio."""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.features.mtf_confirmation import MTFConfirmation, MTFConfirmationResult


def _fully_aligned_bullish():
    """All timeframes bullish with strong momentum and trending ADX."""
    return {
        "ema_fast": Decimal("2355"),
        "ema_slow": Decimal("2340"),
        "rsi": Decimal("65"),
        "adx": Decimal("30"),
        "atr": Decimal("5.0"),
        "atr_sma": Decimal("3.0"),
        "m15_trend": "bullish",
        "m15_rsi": Decimal("62"),
        "m15_adx": Decimal("28"),
        "h1_trend": "bullish",
        "h1_rsi": Decimal("58"),
        "h1_adx": Decimal("32"),
    }


def _fully_aligned_bearish():
    """All timeframes bearish."""
    return {
        "ema_fast": Decimal("2330"),
        "ema_slow": Decimal("2345"),
        "rsi": Decimal("35"),
        "adx": Decimal("30"),
        "atr": Decimal("5.0"),
        "atr_sma": Decimal("3.0"),
        "m15_trend": "bearish",
        "m15_rsi": Decimal("38"),
        "m15_adx": Decimal("28"),
        "h1_trend": "bearish",
        "h1_rsi": Decimal("40"),
        "h1_adx": Decimal("35"),
    }


def _conflicting_features():
    """Primary bullish, HTFs bearish — disagreement."""
    return {
        "ema_fast": Decimal("2355"),
        "ema_slow": Decimal("2340"),
        "rsi": Decimal("65"),
        "adx": Decimal("30"),
        "atr": Decimal("5.0"),
        "atr_sma": Decimal("3.0"),
        "m15_trend": "bearish",
        "m15_rsi": Decimal("42"),
        "m15_adx": Decimal("28"),
        "h1_trend": "bearish",
        "h1_rsi": Decimal("38"),
        "h1_adx": Decimal("32"),
    }


def _minimal_features():
    """Only primary timeframe data, no HTF enrichment."""
    return {
        "ema_fast": Decimal("2355"),
        "ema_slow": Decimal("2340"),
        "rsi": Decimal("65"),
        "adx": Decimal("30"),
    }


class TestTrendAlignment:
    def test_all_bullish_buy(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_fully_aligned_bullish(), "BUY")
        assert result.trend_agreement == Decimal("1"), (
            f"All bullish for BUY should be 1.0, got {result.trend_agreement}"
        )

    def test_all_bearish_sell(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_fully_aligned_bearish(), "SELL")
        assert result.trend_agreement == Decimal("1")

    def test_conflicting_buy(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_conflicting_features(), "BUY")
        # Primary is bullish (agrees), M15+H1 bearish (disagree)
        # 1 vote out of 3
        expected = Decimal("1") / Decimal("3")
        assert abs(result.trend_agreement - expected) < Decimal("0.01")

    def test_opposite_direction_zero(self):
        mtf = MTFConfirmation()
        # All bullish features but SELL direction
        result = mtf.compute(_fully_aligned_bullish(), "SELL")
        assert result.trend_agreement == Decimal("0")


class TestMomentumAlignment:
    def test_all_above_50_buy(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_fully_aligned_bullish(), "BUY")
        assert result.momentum_agreement == Decimal("1")

    def test_all_below_50_sell(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_fully_aligned_bearish(), "SELL")
        assert result.momentum_agreement == Decimal("1")

    def test_conflicting_momentum(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_conflicting_features(), "BUY")
        # Primary RSI=65 (>50, agrees), M15 RSI=42 (<50, disagrees), H1 RSI=38 (<50, disagrees)
        expected = Decimal("1") / Decimal("3")
        assert abs(result.momentum_agreement - expected) < Decimal("0.01")


class TestStrengthAlignment:
    def test_all_trending(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_fully_aligned_bullish(), "BUY")
        # All ADX > 25
        assert result.strength_agreement == Decimal("1")

    def test_weak_trend(self):
        features = _fully_aligned_bullish()
        features["adx"] = Decimal("15")
        features["m15_adx"] = Decimal("18")
        features["h1_adx"] = Decimal("20")
        mtf = MTFConfirmation()
        result = mtf.compute(features, "BUY")
        assert result.strength_agreement == Decimal("0")


class TestVolatilityContext:
    def test_expanding_atr(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_fully_aligned_bullish(), "BUY")
        # atr=5.0 > atr_sma=3.0 → expanding
        assert result.volatility_context == Decimal("1")

    def test_contracting_atr(self):
        features = _fully_aligned_bullish()
        features["atr"] = Decimal("2.0")
        features["atr_sma"] = Decimal("4.0")
        mtf = MTFConfirmation()
        result = mtf.compute(features, "BUY")
        assert result.volatility_context == Decimal("0")

    def test_missing_atr_data(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_minimal_features(), "BUY")
        # No ATR data → neutral 0.5
        assert result.volatility_context == Decimal("0.5")


class TestCompositeRatio:
    def test_perfect_alignment_near_one(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_fully_aligned_bullish(), "BUY")
        assert result.confirmation_ratio == Decimal("1.0000")

    def test_perfect_bearish_alignment(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_fully_aligned_bearish(), "SELL")
        assert result.confirmation_ratio == Decimal("1.0000")

    def test_conflicting_low_ratio(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_conflicting_features(), "BUY")
        # Only primary agrees on trend+momentum, all agree on strength, vol expanding
        assert result.confirmation_ratio < Decimal("0.6")

    def test_minimal_data_still_works(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_minimal_features(), "BUY")
        # Only primary data available — still computes without error
        assert Decimal("0") <= result.confirmation_ratio <= Decimal("1")

    def test_bounded_zero_to_one(self):
        mtf = MTFConfirmation()
        for direction in ("BUY", "SELL"):
            for features_fn in (_fully_aligned_bullish, _fully_aligned_bearish,
                                _conflicting_features, _minimal_features):
                result = mtf.compute(features_fn(), direction)
                assert Decimal("0") <= result.confirmation_ratio <= Decimal("1"), (
                    f"Ratio out of bounds: {result.confirmation_ratio}"
                )

    def test_result_is_frozen_dataclass(self):
        mtf = MTFConfirmation()
        result = mtf.compute(_fully_aligned_bullish(), "BUY")
        assert isinstance(result, MTFConfirmationResult)
        with pytest.raises(AttributeError):
            result.confirmation_ratio = Decimal("0.5")  # type: ignore[misc]
