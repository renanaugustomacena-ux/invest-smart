"""Tests for algo_engine.features.regime — RegimeClassifier."""

from decimal import Decimal

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import MarketRegime

from algo_engine.features.regime import RegimeClassification, RegimeClassifier


class TestRegimeClassifier:
    """Tests for the rule-based regime classifier."""

    def _make_features(self, **overrides) -> dict:
        """Build a base feature dict with sensible defaults, apply overrides."""
        base = {
            "adx": Decimal("15"),
            "atr": Decimal("5"),
            "rsi": Decimal("50"),
            "ema_fast": Decimal("100"),
            "ema_slow": Decimal("100"),
            "bb_width": Decimal("0.05"),
        }
        base.update(overrides)
        return base

    def test_trending_up(self):
        """ADX > 25 + EMA fast > slow → TRENDING_UP."""
        classifier = RegimeClassifier(hysteresis_bars=1)
        features = self._make_features(
            adx=Decimal("35"),
            ema_fast=Decimal("110"),
            ema_slow=Decimal("100"),
        )
        result = classifier.classify(features)
        assert result.regime == MarketRegime.TRENDING_UP
        assert result.confidence > ZERO
        assert result.adx == Decimal("35")

    def test_trending_down(self):
        """ADX > 25 + EMA fast < slow → TRENDING_DOWN."""
        classifier = RegimeClassifier(hysteresis_bars=1)
        features = self._make_features(
            adx=Decimal("30"),
            ema_fast=Decimal("90"),
            ema_slow=Decimal("100"),
        )
        result = classifier.classify(features)
        assert result.regime == MarketRegime.TRENDING_DOWN

    def test_ranging_low_adx(self):
        """ADX < 20 → RANGING with higher confidence."""
        classifier = RegimeClassifier()
        features = self._make_features(adx=Decimal("15"))
        result = classifier.classify(features)
        assert result.regime == MarketRegime.RANGING
        assert result.confidence == Decimal("0.70")

    def test_ranging_moderate_adx(self):
        """ADX between 20-25, no EMA crossover → RANGING."""
        classifier = RegimeClassifier()
        features = self._make_features(adx=Decimal("22"))
        result = classifier.classify(features)
        assert result.regime == MarketRegime.RANGING
        assert result.confidence == Decimal("0.60")

    def test_high_volatility(self):
        """ATR > 2x average ATR → HIGH_VOLATILITY (overrides trending)."""
        classifier = RegimeClassifier(atr_window=5, hysteresis_bars=1)

        # Seed with normal ATR values
        for _ in range(5):
            classifier.classify(self._make_features(atr=Decimal("5")))

        # Now spike ATR to > 2x average
        features = self._make_features(
            atr=Decimal("15"),  # 3x the average of 5
            adx=Decimal("35"),  # Would be trending, but volatility overrides
            ema_fast=Decimal("110"),
            ema_slow=Decimal("100"),
        )
        result = classifier.classify(features)
        assert result.regime == MarketRegime.HIGH_VOLATILITY
        assert result.atr_ratio > Decimal("2")

    def test_reversal_adx_declining_rsi_extreme(self):
        """ADX declining from >40 + RSI extreme → REVERSAL."""
        classifier = RegimeClassifier(hysteresis_bars=1)

        # First call: establish high previous ADX
        classifier.classify(
            self._make_features(
                adx=Decimal("45"),
                ema_fast=Decimal("110"),
                ema_slow=Decimal("100"),
            )
        )

        # Second call: ADX declining + RSI overbought
        features = self._make_features(
            adx=Decimal("35"),
            rsi=Decimal("75"),
        )
        result = classifier.classify(features)
        assert result.regime == MarketRegime.REVERSAL

    def test_reversal_with_oversold_rsi(self):
        """ADX declining from >40 + RSI oversold → REVERSAL."""
        classifier = RegimeClassifier(hysteresis_bars=1)

        # Establish high previous ADX
        classifier.classify(
            self._make_features(
                adx=Decimal("42"),
                ema_fast=Decimal("110"),
                ema_slow=Decimal("100"),
            )
        )

        # ADX declining + RSI oversold
        features = self._make_features(
            adx=Decimal("30"),
            rsi=Decimal("25"),
        )
        result = classifier.classify(features)
        assert result.regime == MarketRegime.REVERSAL

    def test_no_reversal_when_rsi_normal(self):
        """ADX declining but RSI normal → no REVERSAL, falls to trend/range."""
        classifier = RegimeClassifier(hysteresis_bars=1)

        # Establish high previous ADX
        classifier.classify(
            self._make_features(
                adx=Decimal("45"),
                ema_fast=Decimal("110"),
                ema_slow=Decimal("100"),
            )
        )

        # ADX declining but RSI is normal
        features = self._make_features(
            adx=Decimal("35"),
            rsi=Decimal("50"),
            ema_fast=Decimal("110"),
            ema_slow=Decimal("100"),
        )
        result = classifier.classify(features)
        # Should be TRENDING_UP since ADX > 25 and ema_fast > ema_slow
        assert result.regime == MarketRegime.TRENDING_UP

    def test_classification_returns_dataclass(self):
        """Result is a proper RegimeClassification dataclass."""
        classifier = RegimeClassifier()
        result = classifier.classify(self._make_features())
        assert isinstance(result, RegimeClassification)
        assert isinstance(result.regime, MarketRegime)
        assert isinstance(result.confidence, Decimal)
        assert isinstance(result.reasoning, str)
        assert isinstance(result.adx, Decimal)
        assert isinstance(result.atr_ratio, Decimal)

    def test_empty_features_defaults_to_ranging(self):
        """Empty feature dict → RANGING (all defaults are zero/low)."""
        classifier = RegimeClassifier()
        result = classifier.classify({})
        assert result.regime == MarketRegime.RANGING

    def test_volatility_overrides_trending(self):
        """HIGH_VOLATILITY has highest priority, overrides even trending signals."""
        classifier = RegimeClassifier(atr_window=3, hysteresis_bars=1)

        # Build ATR history
        for _ in range(3):
            classifier.classify(self._make_features(atr=Decimal("5")))

        # Trending conditions + volatile ATR → volatility wins
        features = self._make_features(
            adx=Decimal("40"),
            ema_fast=Decimal("120"),
            ema_slow=Decimal("100"),
            atr=Decimal("20"),  # 4x average
        )
        result = classifier.classify(features)
        assert result.regime == MarketRegime.HIGH_VOLATILITY


class TestRegimeHysteresis:
    """Tests for hysteresis (consecutive-bar confirmation) logic."""

    def _make_features(self, **overrides) -> dict:
        base = {
            "adx": Decimal("15"),
            "atr": Decimal("5"),
            "rsi": Decimal("50"),
            "ema_fast": Decimal("100"),
            "ema_slow": Decimal("100"),
            "bb_width": Decimal("0.05"),
        }
        base.update(overrides)
        return base

    def test_regime_change_requires_consecutive_bars(self):
        """With default hysteresis_bars=3, regime must be confirmed 3 times."""
        classifier = RegimeClassifier(hysteresis_bars=3)
        trending_features = self._make_features(
            adx=Decimal("35"),
            ema_fast=Decimal("110"),
            ema_slow=Decimal("100"),
        )

        # First two bars: raw says TRENDING_UP, but hysteresis keeps RANGING
        r1 = classifier.classify(trending_features)
        assert r1.regime == MarketRegime.RANGING

        r2 = classifier.classify(trending_features)
        assert r2.regime == MarketRegime.RANGING

        # Third bar: confirmed → switch to TRENDING_UP
        r3 = classifier.classify(trending_features)
        assert r3.regime == MarketRegime.TRENDING_UP

    def test_interrupted_candidate_resets_count(self):
        """If a different regime appears mid-count, the counter resets."""
        classifier = RegimeClassifier(hysteresis_bars=3)
        trending_up = self._make_features(
            adx=Decimal("35"),
            ema_fast=Decimal("110"),
            ema_slow=Decimal("100"),
        )
        ranging = self._make_features(adx=Decimal("15"))

        # Two bars of trending
        classifier.classify(trending_up)
        classifier.classify(trending_up)

        # Interrupted by ranging (matches current regime → resets candidate)
        classifier.classify(ranging)

        # Trending again — counter restarts from 1
        r = classifier.classify(trending_up)
        assert r.regime == MarketRegime.RANGING  # only 1 bar, not yet confirmed

    def test_hysteresis_bars_one_means_immediate(self):
        """hysteresis_bars=1 gives immediate regime switching (no delay)."""
        classifier = RegimeClassifier(hysteresis_bars=1)
        features = self._make_features(
            adx=Decimal("35"),
            ema_fast=Decimal("110"),
            ema_slow=Decimal("100"),
        )
        result = classifier.classify(features)
        assert result.regime == MarketRegime.TRENDING_UP
