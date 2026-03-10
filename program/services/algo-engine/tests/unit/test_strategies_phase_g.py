"""Tests for 5 untested strategies: MultiFactorStrategy, AdaptiveTrendStrategy,
OUMeanReversionStrategy, VolScaledMomentumStrategy, BreakoutStrategy."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from moneymaker_common.enums import Direction, TrendDirection

D = Decimal


# ===========================================================================
# BreakoutStrategy
# ===========================================================================
from algo_engine.strategies.breakout import BreakoutStrategy


class TestBreakout:
    def test_upper_breakout_buy(self):
        s = BreakoutStrategy()
        features = {
            "latest_close": D("1.12000"),
            "donchian_upper": D("1.11500"),
            "donchian_lower": D("1.09000"),
            "adx": D("25"),
            "atr": D("0.00200"),
            "atr_sma": D("0.00150"),
            "volume_ratio": D("2.0"),
        }
        sig = s.analyze(features)
        assert sig.direction == Direction.BUY
        # All 3 confirmations: 0.50 + 0.30 = 0.80
        assert sig.confidence == D("0.80")

    def test_lower_breakout_sell(self):
        s = BreakoutStrategy()
        features = {
            "latest_close": D("1.08900"),
            "donchian_upper": D("1.11500"),
            "donchian_lower": D("1.09000"),
            "adx": D("10"),
            "atr": D("0.00100"),
            "volume_ratio": D("1.0"),
        }
        sig = s.analyze(features)
        assert sig.direction == Direction.SELL
        # 0 confirmations: base 0.50
        assert sig.confidence == D("0.50")

    def test_no_breakout_hold(self):
        s = BreakoutStrategy()
        features = {
            "latest_close": D("1.10000"),
            "donchian_upper": D("1.11000"),
            "donchian_lower": D("1.09000"),
        }
        sig = s.analyze(features)
        assert sig.direction == Direction.HOLD

    def test_no_donchian_hold(self):
        s = BreakoutStrategy()
        features = {"latest_close": D("1.10000")}
        sig = s.analyze(features)
        assert sig.direction == Direction.HOLD

    def test_confidence_capped_at_85(self):
        s = BreakoutStrategy()
        features = {
            "latest_close": D("1.12000"),
            "donchian_upper": D("1.11500"),
            "donchian_lower": D("1.09000"),
            "adx": D("30"),
            "atr": D("0.00300"),
            "atr_sma": D("0.00100"),
            "volume_ratio": D("3.0"),
        }
        sig = s.analyze(features)
        assert sig.confidence <= D("0.85")


# ===========================================================================
# VolScaledMomentumStrategy
# ===========================================================================
from algo_engine.strategies.vol_momentum import VolScaledMomentumStrategy


class TestVolMomentum:
    def test_buy_with_positive_roc(self):
        s = VolScaledMomentumStrategy()
        features = {
            "latest_close": D("1.10000"),
            "roc": D("2.5"),
            "atr": D("0.00150"),
            "atr_pct": D("0.14"),
            "adx": D("25"),
        }
        sig = s.analyze(features)
        assert sig.direction == Direction.BUY
        assert sig.confidence >= D("0.50")

    def test_sell_with_negative_roc(self):
        s = VolScaledMomentumStrategy()
        features = {
            "latest_close": D("1.10000"),
            "roc": D("-3.0"),
            "atr": D("0.00150"),
            "atr_pct": D("0.14"),
            "adx": D("30"),
        }
        sig = s.analyze(features)
        assert sig.direction == Direction.SELL

    def test_hold_zero_roc(self):
        s = VolScaledMomentumStrategy()
        features = {
            "latest_close": D("1.10000"),
            "roc": D("0"),
            "atr_pct": D("0.14"),
            "adx": D("30"),
        }
        sig = s.analyze(features)
        assert sig.direction == Direction.HOLD

    def test_hold_low_adx(self):
        s = VolScaledMomentumStrategy()
        features = {
            "latest_close": D("1.10000"),
            "roc": D("2.0"),
            "atr_pct": D("0.14"),
            "adx": D("10"),
        }
        sig = s.analyze(features)
        assert sig.direction == Direction.HOLD

    def test_hurst_boost(self):
        s = VolScaledMomentumStrategy()
        base_features = {
            "latest_close": D("1.10000"),
            "roc": D("1.0"),
            "atr_pct": D("0.14"),
            "adx": D("25"),
        }
        sig_no_hurst = s.analyze(base_features)

        features_hurst = {**base_features, "hurst": D("0.60")}
        sig_hurst = s.analyze(features_hurst)
        assert sig_hurst.confidence >= sig_no_hurst.confidence


# ===========================================================================
# MultiFactorStrategy
# ===========================================================================
from algo_engine.strategies.multi_factor import MultiFactorStrategy


class TestMultiFactor:
    def _bullish_features(self) -> dict[str, Any]:
        return {
            "roc": D("3.0"),
            "rsi": D("60"),
            "macd_histogram": D("0.0010"),
            "atr": D("0.0020"),
            "bb_pct_b": D("0.10"),
            "stoch_k": D("15"),
            "williams_r": D("-85"),
            "ema_trend": TrendDirection.BULLISH,
            "adx": D("30"),
            "plus_di": D("25"),
            "minus_di": D("15"),
            "latest_close": D("1950"),
            "sma_200": D("1900"),
            "volume_ratio": D("2.0"),
        }

    def test_strong_bullish_buy(self):
        s = MultiFactorStrategy()
        sig = s.analyze(self._bullish_features())
        assert sig.direction == Direction.BUY
        assert sig.confidence > D("0.40")

    def test_strong_bearish_sell(self):
        s = MultiFactorStrategy()
        features = {
            "roc": D("-3.0"),
            "rsi": D("40"),
            "macd_histogram": D("-0.0010"),
            "atr": D("0.0020"),
            "bb_pct_b": D("0.90"),
            "stoch_k": D("85"),
            "williams_r": D("-10"),
            "ema_trend": TrendDirection.BEARISH,
            "adx": D("30"),
            "plus_di": D("10"),
            "minus_di": D("25"),
            "latest_close": D("1850"),
            "sma_200": D("1900"),
            "volume_ratio": D("2.0"),
        }
        sig = s.analyze(features)
        assert sig.direction == Direction.SELL

    def test_neutral_hold(self):
        s = MultiFactorStrategy()
        features = {
            "roc": D("0.1"),
            "rsi": D("50"),
            "macd_histogram": D("0"),
            "atr": D("0.001"),
            "bb_pct_b": D("0.50"),
            "stoch_k": D("50"),
            "williams_r": D("-50"),
            "ema_trend": TrendDirection.NEUTRAL,
            "adx": D("10"),
            "plus_di": D("15"),
            "minus_di": D("15"),
            "latest_close": D("1900"),
            "sma_200": D("1900"),
            "volume_ratio": D("1.0"),
        }
        sig = s.analyze(features)
        assert sig.direction == Direction.HOLD

    def test_empty_features_hold(self):
        s = MultiFactorStrategy()
        sig = s.analyze({})
        assert sig.direction == Direction.HOLD

    def test_confidence_capped(self):
        s = MultiFactorStrategy()
        sig = s.analyze(self._bullish_features())
        assert sig.confidence <= D("0.85")


# ===========================================================================
# AdaptiveTrendStrategy
# ===========================================================================
from algo_engine.strategies.adaptive_trend import AdaptiveTrendStrategy


class TestAdaptiveTrend:
    def test_returns_signal_suggestion(self):
        s = AdaptiveTrendStrategy()
        sig = s.analyze({})
        assert hasattr(sig, "direction")
        assert hasattr(sig, "confidence")
        assert hasattr(sig, "reasoning")

    def test_name(self):
        s = AdaptiveTrendStrategy()
        assert s.name == "adaptive_trend_v1"

    def test_empty_features_hold(self):
        s = AdaptiveTrendStrategy()
        sig = s.analyze({})
        assert sig.direction == Direction.HOLD

    def test_missing_closes_hold(self):
        s = AdaptiveTrendStrategy()
        features = {
            "adx": D("30"),
            "dominant_cycle": 20,
        }
        sig = s.analyze(features)
        assert sig.direction == Direction.HOLD


# ===========================================================================
# OUMeanReversionStrategy
# ===========================================================================
from algo_engine.strategies.ou_mean_reversion import OUMeanReversionStrategy


class TestOUMeanReversion:
    def test_name(self):
        s = OUMeanReversionStrategy()
        assert s.name == "ou_mean_reversion_v1"

    def test_missing_close_hold(self):
        s = OUMeanReversionStrategy()
        sig = s.analyze({"symbol": "EURUSD"})
        assert sig.direction == Direction.HOLD

    def test_insufficient_history_hold(self):
        s = OUMeanReversionStrategy(lookback=100)
        # Feed only 5 prices — need 100
        for i in range(5):
            sig = s.analyze({
                "symbol": "EURUSD",
                "latest_close": D("1.10000") + D(str(i)) * D("0.0001"),
            })
        assert sig.direction == Direction.HOLD

    def test_builds_price_history(self):
        s = OUMeanReversionStrategy(lookback=10)
        for i in range(15):
            s.analyze({
                "symbol": "EURUSD",
                "latest_close": D("1.10000") + D(str(i)) * D("0.0001"),
            })
        assert len(s._price_history.get("EURUSD", [])) <= 10

    def test_separate_symbol_histories(self):
        s = OUMeanReversionStrategy(lookback=10)
        for i in range(5):
            s.analyze({"symbol": "EURUSD", "latest_close": D("1.10000")})
            s.analyze({"symbol": "GBPUSD", "latest_close": D("1.30000")})
        assert "EURUSD" in s._price_history
        assert "GBPUSD" in s._price_history
