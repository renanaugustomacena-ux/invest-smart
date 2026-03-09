"""Tests for FeatureScorer — unified market dimension scoring."""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.features.feature_scorer import FeatureAssessment, FeatureScorer, _clamp


class TestClamp:
    def test_within_range(self):
        assert _clamp(Decimal("0.5")) == Decimal("0.5")

    def test_above_max(self):
        assert _clamp(Decimal("3.0")) == Decimal("1")

    def test_below_min(self):
        assert _clamp(Decimal("-5.0")) == Decimal("-1")


class TestFeatureAssessment:
    def test_composite_weighted(self):
        a = FeatureAssessment(
            trend=Decimal("1"),
            momentum=Decimal("1"),
            volatility=Decimal("1"),
            volume=Decimal("1"),
        )
        assert a.composite == Decimal("1.0000")

    def test_composite_zero(self):
        a = FeatureAssessment(
            trend=Decimal("0"),
            momentum=Decimal("0"),
            volatility=Decimal("0"),
            volume=Decimal("0"),
        )
        assert a.composite == Decimal("0.0000")

    def test_composite_mixed(self):
        a = FeatureAssessment(
            trend=Decimal("1"),
            momentum=Decimal("-1"),
            volatility=Decimal("0"),
            volume=Decimal("0"),
        )
        # 1*0.35 + (-1)*0.30 + 0*0.20 + 0*0.15 = 0.05
        assert a.composite == Decimal("0.0500")


class TestScoreTrend:
    def test_bullish_ema_alignment(self):
        scorer = FeatureScorer()
        features = {
            "ema_fast": Decimal("2350.00"),
            "ema_slow": Decimal("2340.00"),
            "adx": Decimal("30"),
            "sma_long": Decimal("2300.00"),
            "latest_close": Decimal("2355.00"),
        }
        assessment = scorer.score(features)
        assert assessment.trend > Decimal("0"), f"Bullish setup should score positive, got {assessment.trend}"

    def test_bearish_ema_alignment(self):
        scorer = FeatureScorer()
        features = {
            "ema_fast": Decimal("2330.00"),
            "ema_slow": Decimal("2350.00"),
            "adx": Decimal("30"),
            "sma_long": Decimal("2400.00"),
            "latest_close": Decimal("2325.00"),
        }
        assessment = scorer.score(features)
        assert assessment.trend < Decimal("0"), f"Bearish setup should score negative, got {assessment.trend}"

    def test_neutral_when_emas_equal(self):
        scorer = FeatureScorer()
        features = {
            "ema_fast": Decimal("2340.00"),
            "ema_slow": Decimal("2340.00"),
            "adx": Decimal("15"),
            "latest_close": Decimal("2340.00"),
        }
        assessment = scorer.score(features)
        assert abs(assessment.trend) < Decimal("0.3"), f"Equal EMAs should be near-neutral, got {assessment.trend}"

    def test_zero_ema_slow_returns_zero(self):
        scorer = FeatureScorer()
        features = {"ema_fast": Decimal("100"), "ema_slow": Decimal("0"), "latest_close": Decimal("100")}
        assessment = scorer.score(features)
        assert assessment.trend == Decimal("0")


class TestScoreMomentum:
    def test_overbought_rsi(self):
        scorer = FeatureScorer()
        features = {
            "rsi": Decimal("80"),
            "macd_histogram": Decimal("2.5"),
            "stoch_k": Decimal("85"),
            "latest_close": Decimal("2340"),
            "ema_fast": Decimal("2340"), "ema_slow": Decimal("2340"),
        }
        assessment = scorer.score(features)
        assert assessment.momentum > Decimal("0.3"), f"Overbought should score positive, got {assessment.momentum}"

    def test_oversold_rsi(self):
        scorer = FeatureScorer()
        features = {
            "rsi": Decimal("20"),
            "macd_histogram": Decimal("-3.0"),
            "stoch_k": Decimal("15"),
            "latest_close": Decimal("2340"),
            "ema_fast": Decimal("2340"), "ema_slow": Decimal("2340"),
        }
        assessment = scorer.score(features)
        assert assessment.momentum < Decimal("-0.3"), f"Oversold should score negative, got {assessment.momentum}"

    def test_neutral_rsi(self):
        scorer = FeatureScorer()
        features = {
            "rsi": Decimal("50"),
            "macd_histogram": Decimal("0"),
            "stoch_k": Decimal("50"),
            "latest_close": Decimal("2340"),
            "ema_fast": Decimal("2340"), "ema_slow": Decimal("2340"),
        }
        assessment = scorer.score(features)
        assert abs(assessment.momentum) < Decimal("0.1"), f"Neutral momentum should be near-zero, got {assessment.momentum}"


class TestScoreVolatility:
    def test_expanding_volatility(self):
        scorer = FeatureScorer()
        features = {
            "atr": Decimal("5.0"),
            "atr_sma": Decimal("3.0"),
            "bb_width": Decimal("0.025"),
            "ema_fast": Decimal("100"), "ema_slow": Decimal("100"),
            "latest_close": Decimal("100"),
        }
        assessment = scorer.score(features)
        assert assessment.volatility > Decimal("0"), f"Expanding ATR should score positive, got {assessment.volatility}"

    def test_contracting_volatility(self):
        scorer = FeatureScorer()
        features = {
            "atr": Decimal("2.0"),
            "atr_sma": Decimal("4.0"),
            "bb_width": Decimal("0.003"),
            "ema_fast": Decimal("100"), "ema_slow": Decimal("100"),
            "latest_close": Decimal("100"),
        }
        assessment = scorer.score(features)
        assert assessment.volatility < Decimal("0"), f"Contracting ATR should score negative, got {assessment.volatility}"


class TestScoreVolume:
    def test_high_volume(self):
        scorer = FeatureScorer()
        features = {
            "volume_ratio": Decimal("1.8"),
            "ema_fast": Decimal("100"), "ema_slow": Decimal("100"),
            "latest_close": Decimal("100"),
        }
        assessment = scorer.score(features)
        assert assessment.volume > Decimal("0"), f"High volume should score positive, got {assessment.volume}"

    def test_low_volume(self):
        scorer = FeatureScorer()
        features = {
            "volume_ratio": Decimal("0.4"),
            "ema_fast": Decimal("100"), "ema_slow": Decimal("100"),
            "latest_close": Decimal("100"),
        }
        assessment = scorer.score(features)
        assert assessment.volume < Decimal("0"), f"Low volume should score negative, got {assessment.volume}"

    def test_no_volume_data(self):
        scorer = FeatureScorer()
        features = {
            "ema_fast": Decimal("100"), "ema_slow": Decimal("100"),
            "latest_close": Decimal("100"),
        }
        assessment = scorer.score(features)
        assert assessment.volume == Decimal("0")


class TestBoundedness:
    """All scores must always be in [-1, +1]."""

    def test_extreme_bullish_bounded(self):
        scorer = FeatureScorer()
        features = {
            "ema_fast": Decimal("3000"), "ema_slow": Decimal("2000"),
            "adx": Decimal("90"), "sma_long": Decimal("1500"),
            "latest_close": Decimal("3100"),
            "rsi": Decimal("99"), "macd_histogram": Decimal("100"),
            "stoch_k": Decimal("99"),
            "atr": Decimal("50"), "atr_sma": Decimal("5"),
            "bb_width": Decimal("0.5"),
            "volume_ratio": Decimal("10"),
        }
        a = scorer.score(features)
        for name, val in [("trend", a.trend), ("momentum", a.momentum),
                          ("volatility", a.volatility), ("volume", a.volume)]:
            assert Decimal("-1") <= val <= Decimal("1"), f"{name} out of bounds: {val}"

    def test_extreme_bearish_bounded(self):
        scorer = FeatureScorer()
        features = {
            "ema_fast": Decimal("1000"), "ema_slow": Decimal("3000"),
            "adx": Decimal("90"), "sma_long": Decimal("4000"),
            "latest_close": Decimal("900"),
            "rsi": Decimal("1"), "macd_histogram": Decimal("-100"),
            "stoch_k": Decimal("1"),
            "atr": Decimal("0.1"), "atr_sma": Decimal("10"),
            "bb_width": Decimal("0.0001"),
            "volume_ratio": Decimal("0.01"),
        }
        a = scorer.score(features)
        for name, val in [("trend", a.trend), ("momentum", a.momentum),
                          ("volatility", a.volatility), ("volume", a.volume)]:
            assert Decimal("-1") <= val <= Decimal("1"), f"{name} out of bounds: {val}"
