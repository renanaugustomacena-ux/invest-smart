"""Tests for SignalGenerator and SignalRateLimiter."""

from __future__ import annotations

import time
from decimal import Decimal
from unittest.mock import patch

import pytest

from algo_engine.signals.generator import SignalGenerator
from algo_engine.signals.rate_limiter import SignalRateLimiter
from algo_engine.strategies.base import SignalSuggestion


# ===========================================================================
# SignalGenerator tests
# ===========================================================================

class TestSignalGeneratorBuySignal:
    def test_buy_signal_structure(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion(
            direction="BUY",
            confidence=Decimal("0.80"),
            reasoning="Trend confirmed",
        )
        signal = gen.generate_signal(
            "XAUUSD", suggestion,
            current_price=Decimal("2000.00"),
            atr=Decimal("10.00"),
        )
        assert signal is not None
        assert signal["symbol"] == "XAUUSD"
        assert signal["direction"] == "BUY"
        assert signal["confidence"] == Decimal("0.80")
        assert signal["entry_price"] == Decimal("2000.00")
        assert signal["signal_id"]  # UUID present
        assert signal["timestamp_ms"] > 0

    def test_buy_sl_below_entry(self):
        gen = SignalGenerator(
            default_sl_atr_multiplier=Decimal("1.5"),
            default_tp_atr_multiplier=Decimal("2.5"),
        )
        suggestion = SignalSuggestion(direction="BUY", confidence=Decimal("0.70"), reasoning="test")
        signal = gen.generate_signal(
            "EURUSD", suggestion,
            current_price=Decimal("1.10000"),
            atr=Decimal("0.00100"),
        )
        assert signal["stop_loss"] == Decimal("1.10000") - Decimal("0.00150")
        assert signal["take_profit"] == Decimal("1.10000") + Decimal("0.00250")

    def test_buy_risk_reward_calculated(self):
        gen = SignalGenerator(
            default_sl_atr_multiplier=Decimal("1.5"),
            default_tp_atr_multiplier=Decimal("3.0"),
        )
        suggestion = SignalSuggestion(direction="BUY", confidence=Decimal("0.70"), reasoning="test")
        signal = gen.generate_signal(
            "EURUSD", suggestion,
            current_price=Decimal("1.10000"),
            atr=Decimal("0.00100"),
        )
        # RR = tp_distance / sl_distance = 3.0 / 1.5 = 2.0
        assert signal["risk_reward_ratio"] == Decimal("2")


class TestSignalGeneratorSellSignal:
    def test_sell_sl_above_entry(self):
        gen = SignalGenerator(
            default_sl_atr_multiplier=Decimal("1.5"),
            default_tp_atr_multiplier=Decimal("2.5"),
        )
        suggestion = SignalSuggestion(direction="SELL", confidence=Decimal("0.70"), reasoning="test")
        signal = gen.generate_signal(
            "EURUSD", suggestion,
            current_price=Decimal("1.10000"),
            atr=Decimal("0.00100"),
        )
        assert signal["stop_loss"] == Decimal("1.10000") + Decimal("0.00150")
        assert signal["take_profit"] == Decimal("1.10000") - Decimal("0.00250")


class TestSignalGeneratorEdgeCases:
    def test_zero_atr_returns_none(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion(direction="BUY", confidence=Decimal("0.80"), reasoning="test")
        signal = gen.generate_signal(
            "EURUSD", suggestion,
            current_price=Decimal("1.10000"),
            atr=Decimal("0"),
        )
        assert signal is None

    def test_negative_atr_returns_none(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion(direction="BUY", confidence=Decimal("0.80"), reasoning="test")
        signal = gen.generate_signal(
            "EURUSD", suggestion,
            current_price=Decimal("1.10000"),
            atr=Decimal("-1.0"),
        )
        assert signal is None

    def test_hold_signal_passes_with_zero_atr(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion(direction="HOLD", confidence=Decimal("0.30"), reasoning="test")
        signal = gen.generate_signal(
            "EURUSD", suggestion,
            current_price=Decimal("1.10000"),
            atr=Decimal("0"),
        )
        assert signal is not None
        assert signal["direction"] == "HOLD"
        assert signal["stop_loss"] == Decimal("0")
        assert signal["take_profit"] == Decimal("0")

    def test_order_type_from_metadata(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion(
            direction="BUY",
            confidence=Decimal("0.75"),
            reasoning="test",
            metadata={"order_type": "LIMIT"},
        )
        signal = gen.generate_signal(
            "EURUSD", suggestion,
            current_price=Decimal("1.10000"),
            atr=Decimal("0.00100"),
        )
        assert signal["order_type"] == "LIMIT"

    def test_default_order_type_market(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion(direction="BUY", confidence=Decimal("0.75"), reasoning="test")
        signal = gen.generate_signal(
            "EURUSD", suggestion,
            current_price=Decimal("1.10000"),
            atr=Decimal("0.00100"),
        )
        assert signal["order_type"] == "MARKET"

    def test_unique_signal_ids(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion(direction="BUY", confidence=Decimal("0.70"), reasoning="test")
        ids = set()
        for _ in range(10):
            signal = gen.generate_signal(
                "EURUSD", suggestion,
                current_price=Decimal("1.10000"),
                atr=Decimal("0.001"),
            )
            ids.add(signal["signal_id"])
        assert len(ids) == 10


# ===========================================================================
# SignalRateLimiter tests
# ===========================================================================

class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = SignalRateLimiter(max_per_hour=5)
        for _ in range(5):
            assert rl.allow()
            rl.record()

    def test_blocks_at_limit(self):
        rl = SignalRateLimiter(max_per_hour=3)
        for _ in range(3):
            rl.record()
        assert not rl.allow()

    def test_current_count(self):
        rl = SignalRateLimiter(max_per_hour=10)
        assert rl.current_count == 0
        rl.record()
        rl.record()
        assert rl.current_count == 2

    def test_remaining(self):
        rl = SignalRateLimiter(max_per_hour=5)
        assert rl.remaining == 5
        rl.record()
        assert rl.remaining == 4

    def test_remaining_never_negative(self):
        rl = SignalRateLimiter(max_per_hour=1)
        rl.record()
        rl.record()
        assert rl.remaining == 0

    def test_old_timestamps_expire(self):
        rl = SignalRateLimiter(max_per_hour=2)
        base = time.monotonic()
        with patch("algo_engine.signals.rate_limiter.time") as mock_time:
            mock_time.monotonic.return_value = base
            rl.record()
            rl.record()

            # 1 hour + 1 second later
            mock_time.monotonic.return_value = base + 3601
            assert rl.allow()
            assert rl.current_count == 0
