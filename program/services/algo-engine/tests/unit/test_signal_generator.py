"""Tests for algo_engine.signals.generator — SignalGenerator."""

from decimal import Decimal

from moneymaker_common.decimal_utils import ZERO

from algo_engine.signals.generator import SignalGenerator
from algo_engine.strategies.base import SignalSuggestion


class TestSignalGenerator:
    def test_buy_signal_sl_tp(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion("BUY", Decimal("0.85"), "Test BUY")
        signal = gen.generate_signal(
            "XAUUSD", suggestion, Decimal("2000"), atr=Decimal("10")
        )

        assert signal["direction"] == "BUY"
        assert signal["symbol"] == "XAUUSD"
        # SL = 2000 - 1.5 * 10 = 1985
        assert signal["stop_loss"] == Decimal("1985")
        # TP = 2000 + 2.5 * 10 = 2025
        assert signal["take_profit"] == Decimal("2025")

    def test_sell_signal_sl_tp(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion("SELL", Decimal("0.75"), "Test SELL")
        signal = gen.generate_signal(
            "XAUUSD", suggestion, Decimal("2000"), atr=Decimal("10")
        )

        assert signal["direction"] == "SELL"
        # SL = 2000 + 1.5 * 10 = 2015
        assert signal["stop_loss"] == Decimal("2015")
        # TP = 2000 - 2.5 * 10 = 1975
        assert signal["take_profit"] == Decimal("1975")

    def test_hold_signal_no_sl_tp(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion("HOLD", Decimal("0.30"), "No signal")
        signal = gen.generate_signal(
            "XAUUSD", suggestion, Decimal("2000"), atr=Decimal("10")
        )

        assert signal["stop_loss"] == ZERO
        assert signal["take_profit"] == ZERO

    def test_zero_atr_no_sl_tp(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion("BUY", Decimal("0.80"), "No ATR")
        signal = gen.generate_signal("XAUUSD", suggestion, Decimal("2000"), atr=ZERO)

        assert signal["stop_loss"] == ZERO
        assert signal["take_profit"] == ZERO

    def test_risk_reward_ratio(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion("BUY", Decimal("0.85"), "RR test")
        signal = gen.generate_signal(
            "XAUUSD", suggestion, Decimal("2000"), atr=Decimal("10")
        )

        # Risk = 2000 - 1985 = 15, Reward = 2025 - 2000 = 25
        # RR = 25/15 = 1.6666...
        rr = signal["risk_reward_ratio"]
        expected = Decimal("25") / Decimal("15")
        assert abs(rr - expected) < Decimal("0.001")

    def test_signal_has_uuid(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion("BUY", Decimal("0.80"), "UUID test")
        signal = gen.generate_signal(
            "XAUUSD", suggestion, Decimal("2000"), atr=Decimal("10")
        )

        assert "signal_id" in signal
        assert len(signal["signal_id"]) == 36  # UUID4 format

    def test_signal_has_timestamp(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion("BUY", Decimal("0.80"), "TS test")
        signal = gen.generate_signal(
            "XAUUSD", suggestion, Decimal("2000"), atr=Decimal("10")
        )

        assert "timestamp_ms" in signal
        assert signal["timestamp_ms"] > 0

    def test_custom_atr_multipliers(self):
        gen = SignalGenerator(
            default_sl_atr_multiplier=Decimal("2.0"),
            default_tp_atr_multiplier=Decimal("3.0"),
        )
        suggestion = SignalSuggestion("BUY", Decimal("0.85"), "Custom mult")
        signal = gen.generate_signal(
            "XAUUSD", suggestion, Decimal("2000"), atr=Decimal("10")
        )

        # SL = 2000 - 2.0 * 10 = 1980
        assert signal["stop_loss"] == Decimal("1980")
        # TP = 2000 + 3.0 * 10 = 2030
        assert signal["take_profit"] == Decimal("2030")

    def test_metadata_passthrough(self):
        gen = SignalGenerator()
        suggestion = SignalSuggestion(
            "BUY",
            Decimal("0.80"),
            "Meta test",
            metadata={"strategy": "trend_v1"},
        )
        signal = gen.generate_signal(
            "XAUUSD", suggestion, Decimal("2000"), atr=Decimal("10")
        )
        assert signal["metadata"] == {"strategy": "trend_v1"}
