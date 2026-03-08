"""Tests for moneymaker_common.enums."""

from moneymaker_common.enums import Direction, MarketRegime, SourceTier, TrendDirection


class TestDirection:
    def test_values(self):
        assert Direction.BUY == "BUY"
        assert Direction.SELL == "SELL"
        assert Direction.HOLD == "HOLD"

    def test_is_string(self):
        assert isinstance(Direction.BUY, str)

    def test_string_comparison(self):
        assert Direction.BUY == "BUY"
        assert "BUY" == Direction.BUY

    def test_construct_from_string(self):
        d = Direction("BUY")
        assert d is Direction.BUY

    def test_invalid_raises(self):
        import pytest

        with pytest.raises(ValueError):
            Direction("INVALID")

    def test_member_count(self):
        assert len(Direction) == 3


class TestMarketRegime:
    def test_values(self):
        assert MarketRegime.TRENDING_UP == "trending_up"
        assert MarketRegime.TRENDING_DOWN == "trending_down"
        assert MarketRegime.RANGING == "ranging"
        assert MarketRegime.HIGH_VOLATILITY == "high_volatility"
        assert MarketRegime.REVERSAL == "reversal"

    def test_is_string(self):
        assert isinstance(MarketRegime.TRENDING_UP, str)

    def test_member_count(self):
        assert len(MarketRegime) == 5


class TestTrendDirection:
    def test_values(self):
        assert TrendDirection.BULLISH == "bullish"
        assert TrendDirection.BEARISH == "bearish"
        assert TrendDirection.NEUTRAL == "neutral"
        assert TrendDirection.UNKNOWN == "unknown"


class TestSourceTier:
    def test_values(self):
        assert SourceTier.ML_PRIMARY == "ml_primary"
        assert SourceTier.TECHNICAL == "technical"
        assert SourceTier.RULE_BASED == "rule_based"
