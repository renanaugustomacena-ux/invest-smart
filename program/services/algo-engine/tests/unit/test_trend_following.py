"""Tests for algo_engine.strategies.trend_following — TrendFollowingStrategy."""

from decimal import Decimal

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import Direction

from algo_engine.strategies.trend_following import TrendFollowingStrategy


class TestTrendFollowingStrategy:
    def _make_features(self, **overrides) -> dict:
        """Build a feature dict with sensible neutral defaults."""
        base = {
            "ema_fast": Decimal("100"),
            "ema_slow": Decimal("100"),
            "sma_200": Decimal("95"),
            "latest_close": Decimal("100"),
            "macd_histogram": ZERO,
            "adx": Decimal("15"),
        }
        base.update(overrides)
        return base

    def test_name(self):
        s = TrendFollowingStrategy()
        assert s.name == "trend_following_v1"

    def test_buy_all_confirmations(self):
        """All 4 buy indicators confirm → BUY."""
        s = TrendFollowingStrategy()
        features = self._make_features(
            ema_fast=Decimal("110"),  # fast > slow
            ema_slow=Decimal("100"),
            sma_200=Decimal("90"),  # price > SMA(200)
            latest_close=Decimal("110"),
            macd_histogram=Decimal("5"),  # positive
            adx=Decimal("35"),  # > 25
        )
        result = s.analyze(features)
        assert result.direction == Direction.BUY
        assert result.confidence > Decimal("0.50")
        assert result.metadata["confirmations"] == 4

    def test_sell_all_confirmations(self):
        """All 4 sell indicators confirm → SELL."""
        s = TrendFollowingStrategy()
        features = self._make_features(
            ema_fast=Decimal("90"),  # fast < slow
            ema_slow=Decimal("100"),
            sma_200=Decimal("110"),  # price < SMA(200)
            latest_close=Decimal("95"),
            macd_histogram=Decimal("-5"),  # negative
            adx=Decimal("35"),  # > 25
        )
        result = s.analyze(features)
        assert result.direction == Direction.SELL
        assert result.confidence > Decimal("0.50")
        assert result.metadata["confirmations"] == 4

    def test_hold_insufficient_confirmations(self):
        """Only 2 confirmations → HOLD."""
        s = TrendFollowingStrategy()
        features = self._make_features(
            ema_fast=Decimal("110"),  # 1 buy confirmation
            ema_slow=Decimal("100"),
            sma_200=Decimal("90"),  # 2nd buy confirmation
            latest_close=Decimal("100"),
            macd_histogram=ZERO,  # no confirmation
            adx=Decimal("15"),  # < 25, no confirmation
        )
        result = s.analyze(features)
        assert result.direction == Direction.HOLD
        assert "insufficienti" in result.reasoning.lower()

    def test_hold_when_all_neutral(self):
        """No directional signal → HOLD."""
        s = TrendFollowingStrategy()
        features = self._make_features()  # All neutral defaults
        result = s.analyze(features)
        assert result.direction == Direction.HOLD

    def test_confidence_increases_with_adx(self):
        """Higher ADX → higher confidence."""
        s = TrendFollowingStrategy()
        features_low = self._make_features(
            ema_fast=Decimal("110"),
            ema_slow=Decimal("100"),
            sma_200=Decimal("90"),
            latest_close=Decimal("110"),
            macd_histogram=Decimal("5"),
            adx=Decimal("30"),
        )
        features_high = self._make_features(
            ema_fast=Decimal("110"),
            ema_slow=Decimal("100"),
            sma_200=Decimal("90"),
            latest_close=Decimal("110"),
            macd_histogram=Decimal("5"),
            adx=Decimal("60"),
        )
        result_low = s.analyze(features_low)
        result_high = s.analyze(features_high)
        assert result_high.confidence > result_low.confidence

    def test_confidence_capped_at_090(self):
        """Confidence should not exceed 0.90 even with very high ADX."""
        s = TrendFollowingStrategy()
        features = self._make_features(
            ema_fast=Decimal("110"),
            ema_slow=Decimal("100"),
            sma_200=Decimal("90"),
            latest_close=Decimal("110"),
            macd_histogram=Decimal("5"),
            adx=Decimal("80"),
        )
        result = s.analyze(features)
        assert result.confidence <= Decimal("0.90")

    def test_buy_with_exactly_3_confirmations(self):
        """3 confirmations (minimum) → BUY signal generated."""
        s = TrendFollowingStrategy()
        features = self._make_features(
            ema_fast=Decimal("110"),  # 1st confirmation
            ema_slow=Decimal("100"),
            sma_200=Decimal("90"),  # 2nd
            latest_close=Decimal("110"),
            macd_histogram=Decimal("5"),  # 3rd
            adx=Decimal("15"),  # < 25, not a confirmation
        )
        result = s.analyze(features)
        assert result.direction == Direction.BUY
        assert result.metadata["confirmations"] == 3

    def test_missing_features_default_to_hold(self):
        """Missing all features → HOLD (no confirmations possible)."""
        s = TrendFollowingStrategy()
        result = s.analyze({})
        assert result.direction == Direction.HOLD
