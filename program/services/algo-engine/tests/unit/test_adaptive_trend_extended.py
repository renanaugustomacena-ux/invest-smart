"""Extended tests for AdaptiveTrendStrategy — all branches + edge cases."""

from decimal import Decimal

from moneymaker_common.enums import Direction

from algo_engine.strategies.adaptive_trend import AdaptiveTrendStrategy, _clamp


class TestClamp:
    def test_within_bounds(self):
        assert _clamp(10, 5, 15) == 10

    def test_below_min(self):
        assert _clamp(2, 5, 15) == 5

    def test_above_max(self):
        assert _clamp(20, 5, 15) == 15

    def test_at_boundaries(self):
        assert _clamp(5, 5, 15) == 5
        assert _clamp(15, 5, 15) == 15


class TestAdaptiveTrendName:
    def test_name(self):
        s = AdaptiveTrendStrategy()
        assert s.name == "adaptive_trend_v1"


class TestAdaptiveTrendBuySignal:
    def test_strong_buy_signal(self):
        s = AdaptiveTrendStrategy()
        features = {
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("35"),
            "rsi": Decimal("55"),
        }
        result = s.analyze(features)
        assert result.direction == Direction.BUY
        assert result.confidence > Decimal("0.50")

    def test_buy_with_dominant_cycle(self):
        """Cycle detection should add bonus confidence."""
        s = AdaptiveTrendStrategy()
        features_no_cycle = {
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("30"),
            "rsi": Decimal("55"),
        }
        features_with_cycle = {**features_no_cycle, "dominant_cycle": 16}
        result_no = s.analyze(features_no_cycle)
        result_with = s.analyze(features_with_cycle)
        # Cycle bonus should increase confidence
        assert result_with.confidence >= result_no.confidence


class TestAdaptiveTrendSellSignal:
    def test_strong_sell_signal(self):
        s = AdaptiveTrendStrategy()
        features = {
            "ema_fast": Decimal("90"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("110"),
            "latest_close": Decimal("95"),
            "macd_histogram": Decimal("-5"),
            "adx": Decimal("35"),
            "rsi": Decimal("40"),
        }
        result = s.analyze(features)
        assert result.direction == Direction.SELL
        assert result.confidence > Decimal("0.50")


class TestAdaptiveTrendHold:
    def test_insufficient_confirmations(self):
        """Below min_confirmations → HOLD."""
        s = AdaptiveTrendStrategy(min_confirmations=3)
        features = {
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            # Only 1 buy confirmation (EMA crossover), missing the rest
        }
        result = s.analyze(features)
        assert result.direction == Direction.HOLD
        assert "Insufficient" in result.reasoning

    def test_conflicting_signals(self):
        """Equal buy and sell confirmations → HOLD."""
        s = AdaptiveTrendStrategy(min_confirmations=2)
        features = {
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),  # BUY
            "sma_200": Decimal("115"),
            "latest_close": Decimal("110"),  # SELL (below SMA200)
            "macd_histogram": Decimal("5"),  # BUY
            "rsi": Decimal("40"),  # SELL
        }
        result = s.analyze(features)
        # 2 BUY vs 2 SELL → conflicting
        assert result.direction == Direction.HOLD
        assert "Conflicting" in result.reasoning


class TestAdaptiveTrendHurstFilter:
    def test_mean_reverting_hurst_blocks(self):
        """Hurst < 0.45 → mean-reverting, suppress trend signal."""
        s = AdaptiveTrendStrategy()
        features = {
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("35"),
            "rsi": Decimal("55"),
            "hurst": Decimal("0.35"),
        }
        result = s.analyze(features)
        assert result.direction == Direction.HOLD
        assert "mean-reverting" in result.reasoning

    def test_insufficient_persistence_hurst_blocks(self):
        """Hurst between 0.45 and 0.55 → insufficient persistence."""
        s = AdaptiveTrendStrategy()
        features = {
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("35"),
            "rsi": Decimal("55"),
            "hurst": Decimal("0.48"),
        }
        result = s.analyze(features)
        assert result.direction == Direction.HOLD
        assert "insufficient trend persistence" in result.reasoning

    def test_trending_hurst_allows_signal(self):
        """Hurst >= 0.55 → trending, signal passes."""
        s = AdaptiveTrendStrategy()
        features = {
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("35"),
            "rsi": Decimal("55"),
            "hurst": Decimal("0.65"),
        }
        result = s.analyze(features)
        assert result.direction == Direction.BUY


class TestAdaptiveTrendAdxBehavior:
    def test_adx_below_threshold_no_extra_confirmation(self):
        """ADX < 25 should not add a confirmation."""
        s = AdaptiveTrendStrategy(min_confirmations=3)
        features = {
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("20"),  # Below 25
            "rsi": Decimal("45"),  # SELL side
        }
        result = s.analyze(features)
        # 3 BUY (EMA, SMA, MACD) but RSI sell → ADX not added since < 25
        assert result.direction == Direction.BUY

    def test_adx_reinforces_dominant_side(self):
        """ADX > 25 should reinforce the dominant direction's confirmations."""
        s = AdaptiveTrendStrategy(min_confirmations=3)
        features = {
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("30"),
            "rsi": Decimal("55"),
        }
        result = s.analyze(features)
        # 4 BUY (EMA + SMA + MACD + RSI) + ADX reinforces → 5 BUY
        assert result.direction == Direction.BUY


class TestAdaptiveTrendMetadata:
    def test_metadata_contains_cycle_info(self):
        s = AdaptiveTrendStrategy()
        features = {
            "dominant_cycle": 24,
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("30"),
            "rsi": Decimal("55"),
        }
        result = s.analyze(features)
        assert result.metadata is not None
        assert result.metadata["cycle"] == 24
        assert "adaptive_rsi" in result.metadata
        assert "adaptive_ema_fast" in result.metadata


class TestAdaptiveTrendCycleAdaptation:
    def test_short_cycle_adjusts_periods(self):
        s = AdaptiveTrendStrategy()
        features = {
            "dominant_cycle": 8,
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("30"),
            "rsi": Decimal("55"),
        }
        result = s.analyze(features)
        assert result.metadata is not None
        # With cycle=8: rsi=max(7,min(4,28))=7, ema_fast=max(5,min(2,25))=5
        assert result.metadata["adaptive_rsi"] == 7
        assert result.metadata["adaptive_ema_fast"] == 5

    def test_long_cycle_adjusts_periods(self):
        s = AdaptiveTrendStrategy()
        features = {
            "dominant_cycle": 100,
            "ema_fast": Decimal("110"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("90"),
            "latest_close": Decimal("110"),
            "macd_histogram": Decimal("5"),
            "adx": Decimal("30"),
            "rsi": Decimal("55"),
        }
        result = s.analyze(features)
        assert result.metadata is not None
        # Clamped to max values
        assert result.metadata["adaptive_rsi"] == 28
        assert result.metadata["adaptive_ema_fast"] == 25
