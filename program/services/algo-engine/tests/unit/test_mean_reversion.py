"""Tests for algo_engine.strategies.mean_reversion — MeanReversionStrategy."""

from decimal import Decimal

from moneymaker_common.enums import Direction

from algo_engine.strategies.mean_reversion import MeanReversionStrategy


class TestMeanReversionStrategy:
    def _make_features(self, **overrides) -> dict:
        base = {
            "bb_pct_b": Decimal("0.50"),
            "rsi": Decimal("50"),
            "stoch_k": Decimal("50"),
        }
        base.update(overrides)
        return base

    def test_name(self):
        s = MeanReversionStrategy()
        assert s.name == "mean_reversion_v1"

    def test_buy_oversold(self):
        """BB %B < 0.10 + RSI < 30 → BUY."""
        s = MeanReversionStrategy()
        features = self._make_features(
            bb_pct_b=Decimal("0.05"),
            rsi=Decimal("25"),
        )
        result = s.analyze(features)
        assert result.direction == Direction.BUY
        assert result.confidence >= Decimal("0.65")
        assert "BUY" in result.reasoning

    def test_buy_with_stochastic_confirmation(self):
        """Stochastic < 20 boosts BUY confidence."""
        s = MeanReversionStrategy()
        features_no_stoch = self._make_features(
            bb_pct_b=Decimal("0.05"),
            rsi=Decimal("25"),
            stoch_k=Decimal("50"),  # no confirmation
        )
        features_stoch = self._make_features(
            bb_pct_b=Decimal("0.05"),
            rsi=Decimal("25"),
            stoch_k=Decimal("15"),  # < 20, confirms
        )
        result_no = s.analyze(features_no_stoch)
        result_yes = s.analyze(features_stoch)
        assert result_yes.confidence > result_no.confidence

    def test_sell_overbought(self):
        """BB %B > 0.90 + RSI > 70 → SELL."""
        s = MeanReversionStrategy()
        features = self._make_features(
            bb_pct_b=Decimal("0.95"),
            rsi=Decimal("75"),
        )
        result = s.analyze(features)
        assert result.direction == Direction.SELL
        assert result.confidence >= Decimal("0.65")

    def test_sell_with_stochastic_confirmation(self):
        """Stochastic > 80 boosts SELL confidence."""
        s = MeanReversionStrategy()
        features_no = self._make_features(
            bb_pct_b=Decimal("0.95"),
            rsi=Decimal("75"),
            stoch_k=Decimal("50"),
        )
        features_yes = self._make_features(
            bb_pct_b=Decimal("0.95"),
            rsi=Decimal("75"),
            stoch_k=Decimal("85"),
        )
        result_no = s.analyze(features_no)
        result_yes = s.analyze(features_yes)
        assert result_yes.confidence > result_no.confidence

    def test_hold_when_ambiguous(self):
        """Mid-range indicators → HOLD."""
        s = MeanReversionStrategy()
        features = self._make_features()  # all at 0.50 / 50
        result = s.analyze(features)
        assert result.direction == Direction.HOLD

    def test_hold_when_bb_low_but_rsi_normal(self):
        """BB %B low but RSI not oversold → HOLD."""
        s = MeanReversionStrategy()
        features = self._make_features(
            bb_pct_b=Decimal("0.05"),
            rsi=Decimal("50"),
        )
        result = s.analyze(features)
        assert result.direction == Direction.HOLD

    def test_hold_when_rsi_low_but_bb_normal(self):
        """RSI oversold but BB %B not at extreme → HOLD."""
        s = MeanReversionStrategy()
        features = self._make_features(
            bb_pct_b=Decimal("0.50"),
            rsi=Decimal("25"),
        )
        result = s.analyze(features)
        assert result.direction == Direction.HOLD

    def test_confidence_capped(self):
        """Confidence should not exceed 0.85."""
        s = MeanReversionStrategy()
        features = self._make_features(
            bb_pct_b=Decimal("0.01"),
            rsi=Decimal("10"),
            stoch_k=Decimal("5"),  # strong confirmation
        )
        result = s.analyze(features)
        assert result.confidence <= Decimal("0.85")
