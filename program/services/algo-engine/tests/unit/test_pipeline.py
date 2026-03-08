"""Tests for algo_engine.features.pipeline — FeaturePipeline."""

from decimal import Decimal

from moneymaker_common.decimal_utils import ZERO

from algo_engine.features.pipeline import FeaturePipeline


class TestFeaturePipeline:
    def test_empty_bars_returns_empty_dict(self):
        pipeline = FeaturePipeline()
        assert pipeline.compute_features("XAUUSD", []) == {}

    def test_returns_expected_keys(self, sample_ohlcv_bars):
        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)
        expected_keys = {
            "symbol",
            "bar_count",
            "latest_close",
            "latest_high",
            "latest_low",
            "latest_timestamp",
            "rsi",
            "ema_fast",
            "ema_slow",
            "sma",
            "macd_line",
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_width",
            "bb_pct_b",
            "atr",
            "atr_pct",
            "ema_trend",
        }
        assert expected_keys.issubset(set(features.keys()))

    def test_symbol_propagated(self, sample_ohlcv_bars):
        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)
        assert features["symbol"] == "XAUUSD"

    def test_bar_count(self, sample_ohlcv_bars):
        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)
        assert features["bar_count"] == 50

    def test_numeric_features_are_decimal(self, sample_ohlcv_bars):
        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)
        decimal_keys = [
            "latest_close",
            "rsi",
            "ema_fast",
            "ema_slow",
            "sma",
            "macd_line",
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_width",
            "bb_pct_b",
            "atr",
            "atr_pct",
        ]
        for key in decimal_keys:
            assert isinstance(
                features[key], Decimal
            ), f"{key} should be Decimal, got {type(features[key])}"

    def test_uptrend_ema_trend_bullish(self, sample_ohlcv_bars):
        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)
        assert features["ema_trend"] == "bullish"

    def test_custom_periods(self, sample_ohlcv_bars):
        pipeline = FeaturePipeline(rsi_period=7, ema_fast_period=5, ema_slow_period=10)
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)
        assert features["rsi"] > ZERO

    def test_latest_close_is_last_bar(self, sample_ohlcv_bars):
        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)
        assert features["latest_close"] == sample_ohlcv_bars[-1].close

    def test_bollinger_band_relationships(self, sample_ohlcv_bars):
        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)
        assert features["bb_upper"] > features["bb_middle"]
        assert features["bb_middle"] > features["bb_lower"]
        assert features["bb_width"] > ZERO

    def test_atr_positive(self, sample_ohlcv_bars):
        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)
        assert features["atr"] > ZERO
        assert features["atr_pct"] > ZERO
