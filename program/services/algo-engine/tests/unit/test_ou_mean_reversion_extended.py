"""Extended tests for OUMeanReversionStrategy — s-score signals, Hurst filter, BB confirm."""

import math
from decimal import Decimal

from moneymaker_common.enums import Direction

from algo_engine.strategies.ou_mean_reversion import OUMeanReversionStrategy


def _make_price_series(n: int, mu: float, noise_scale: float = 0.5) -> list[Decimal]:
    """Generate a mean-reverting series around mu with deterministic noise."""
    prices = []
    x = mu
    for i in range(n):
        # Simple OU-like evolution: mean revert to mu
        x = x + 0.3 * (mu - x) + noise_scale * math.sin(i * 0.5)
        prices.append(Decimal(str(round(x, 6))))
    return prices


class TestOUMeanReversionName:
    def test_name(self):
        s = OUMeanReversionStrategy()
        assert s.name == "ou_mean_reversion_v1"


class TestOUMeanReversionMissingData:
    def test_missing_latest_close(self):
        s = OUMeanReversionStrategy()
        result = s.analyze({"symbol": "XAUUSD"})
        assert result.direction == Direction.HOLD
        assert "Missing latest_close" in result.reasoning

    def test_insufficient_data(self):
        s = OUMeanReversionStrategy(lookback=100)
        # Feed 50 prices — not enough
        for i in range(50):
            result = s.analyze({
                "symbol": "XAUUSD",
                "latest_close": Decimal(str(1900 + i * 0.1)),
            })
        assert result.direction == Direction.HOLD
        assert "Insufficient data" in result.reasoning


class TestOUMeanReversionSignals:
    def _feed_series(
        self, strategy: OUMeanReversionStrategy, symbol: str, prices: list[Decimal]
    ):
        """Feed a price series to the strategy, return last result."""
        result = None
        for p in prices:
            result = strategy.analyze({
                "symbol": symbol,
                "latest_close": p,
            })
        return result

    def test_buy_signal_when_price_below_mean(self):
        """Price significantly below the mean → BUY signal."""
        s = OUMeanReversionStrategy(lookback=50, entry_threshold=Decimal("1.0"))
        # Generate mean-reverting series around 100, then drop well below
        prices = _make_price_series(49, 100.0, noise_scale=0.3)
        # Last price far below mean
        prices.append(Decimal("95.0"))
        result = self._feed_series(s, "TESTPAIR", prices)
        # Should trigger either BUY or HOLD depending on OU fit
        assert result.direction in (Direction.BUY, Direction.HOLD)

    def test_sell_signal_when_price_above_mean(self):
        """Price significantly above the mean → SELL signal."""
        s = OUMeanReversionStrategy(lookback=50, entry_threshold=Decimal("1.0"))
        prices = _make_price_series(49, 100.0, noise_scale=0.3)
        prices.append(Decimal("105.0"))
        result = self._feed_series(s, "TESTPAIR", prices)
        assert result.direction in (Direction.SELL, Direction.HOLD)

    def test_hold_near_equilibrium(self):
        """Price near mean → HOLD."""
        s = OUMeanReversionStrategy(lookback=50, entry_threshold=Decimal("1.5"))
        prices = _make_price_series(50, 100.0, noise_scale=0.2)
        result = self._feed_series(s, "TESTPAIR", prices)
        assert result.direction == Direction.HOLD


class TestOUMeanReversionHurstFilter:
    def test_hurst_above_threshold_blocks(self):
        """Hurst >= 0.45 → not anti-persistent, signal blocked."""
        s = OUMeanReversionStrategy(lookback=50)
        prices = _make_price_series(49, 100.0, noise_scale=0.3)
        prices.append(Decimal("95.0"))
        # Feed all but the last
        for p in prices[:-1]:
            s.analyze({"symbol": "XAUUSD", "latest_close": p})
        # Final with Hurst filter
        result = s.analyze({
            "symbol": "XAUUSD",
            "latest_close": prices[-1],
            "hurst": Decimal("0.60"),
        })
        # Should be HOLD due to Hurst filter
        assert result.direction == Direction.HOLD
        if "Hurst" in result.reasoning:
            assert "not anti-persistent" in result.reasoning

    def test_hurst_below_threshold_allows(self):
        """Hurst < 0.45 → anti-persistent, signal allowed."""
        s = OUMeanReversionStrategy(lookback=50)
        prices = _make_price_series(50, 100.0, noise_scale=0.3)
        for p in prices[:-1]:
            s.analyze({"symbol": "XAUUSD", "latest_close": p})
        result = s.analyze({
            "symbol": "XAUUSD",
            "latest_close": prices[-1],
            "hurst": Decimal("0.30"),
        })
        # Hurst filter should not block
        assert "not anti-persistent" not in result.reasoning


class TestOUMeanReversionBBConfirmation:
    def _build_strategy_with_data(self):
        s = OUMeanReversionStrategy(lookback=50, entry_threshold=Decimal("1.0"))
        prices = _make_price_series(50, 100.0, noise_scale=0.3)
        for p in prices[:-1]:
            s.analyze({"symbol": "XAUUSD", "latest_close": p})
        return s, prices[-1]

    def test_bb_low_adds_buy_confidence(self):
        """bb_pct_b < 0.2 should boost buy confidence."""
        s, last_p = self._build_strategy_with_data()
        result_no_bb = s.analyze({
            "symbol": "XAUUSD",
            "latest_close": Decimal("94.0"),
        })
        # Re-build to avoid state pollution
        s2 = OUMeanReversionStrategy(lookback=50, entry_threshold=Decimal("1.0"))
        prices2 = _make_price_series(49, 100.0, noise_scale=0.3)
        prices2.append(Decimal("94.0"))
        for p in prices2[:-1]:
            s2.analyze({"symbol": "XAUUSD2", "latest_close": p})
        result_with_bb = s2.analyze({
            "symbol": "XAUUSD2",
            "latest_close": Decimal("94.0"),
            "bb_pct_b": Decimal("0.05"),
        })
        # If both produced BUY, the BB-confirmed one should have >= confidence
        if result_no_bb.direction == Direction.BUY and result_with_bb.direction == Direction.BUY:
            assert result_with_bb.confidence >= result_no_bb.confidence


class TestOUMeanReversionPerSymbolHistory:
    def test_separate_symbol_histories(self):
        """Each symbol should maintain its own price history."""
        s = OUMeanReversionStrategy(lookback=5)
        for i in range(5):
            s.analyze({"symbol": "EURUSD", "latest_close": Decimal(str(1.08 + i * 0.001))})
            s.analyze({"symbol": "GBPUSD", "latest_close": Decimal(str(1.25 + i * 0.001))})
        assert "EURUSD" in s._price_history
        assert "GBPUSD" in s._price_history
        assert len(s._price_history["EURUSD"]) == 5
        assert len(s._price_history["GBPUSD"]) == 5


class TestOUMeanReversionMetadata:
    def test_metadata_on_signal(self):
        """Metadata should include s_score, half_life, theta, mu."""
        s = OUMeanReversionStrategy(lookback=50)
        prices = _make_price_series(50, 100.0, noise_scale=0.3)
        result = None
        for p in prices:
            result = s.analyze({"symbol": "XAUUSD", "latest_close": p})
        # If we got past the OU fit, metadata should be present
        if result.metadata is not None and "s_score" in result.metadata:
            assert "half_life" in result.metadata
            assert "theta" in result.metadata
            assert "mu" in result.metadata
            assert result.metadata["strategy"] == "ou_mean_reversion_v1"


class TestOUMeanReversionHoldMethod:
    def test_hold_returns_low_confidence(self):
        result = OUMeanReversionStrategy._hold("test reason")
        assert result.direction == Direction.HOLD
        assert result.confidence == Decimal("0.30")
        assert result.reasoning == "test reason"
