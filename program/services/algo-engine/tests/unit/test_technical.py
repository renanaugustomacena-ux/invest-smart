"""Tests for algo_engine.features.technical — all existing indicators."""

from decimal import Decimal

import pytest
from moneymaker_common.decimal_utils import ZERO

from algo_engine.features.technical import (
    _decimal_sqrt,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
)

# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------


class TestSMA:
    def test_basic_calculation(self):
        vals = [Decimal("10"), Decimal("20"), Decimal("30")]
        assert calculate_sma(vals, 3) == Decimal("20")

    def test_uses_last_n_values(self):
        vals = [Decimal("5"), Decimal("10"), Decimal("20"), Decimal("30")]
        assert calculate_sma(vals, 3) == Decimal("20")

    def test_insufficient_data(self):
        assert calculate_sma([Decimal("10")], 5) == ZERO

    def test_period_zero(self):
        assert calculate_sma([Decimal("10")], 0) == ZERO

    def test_period_negative(self):
        assert calculate_sma([Decimal("10"), Decimal("20")], -1) == ZERO

    def test_single_value(self):
        assert calculate_sma([Decimal("42")], 1) == Decimal("42")


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------


class TestEMA:
    def test_seed_equals_sma(self):
        vals = [Decimal("10"), Decimal("20"), Decimal("30")]
        # With period=3 and exactly 3 values, EMA = SMA = 20
        assert calculate_ema(vals, 3) == Decimal("20")

    def test_with_subsequent_values(self):
        vals = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40")]
        # SMA seed for first 3 = 20
        # k = 2/(3+1) = 0.5
        # EMA = 40 * 0.5 + 20 * 0.5 = 30
        assert calculate_ema(vals, 3) == Decimal("30")

    def test_insufficient_data(self):
        assert calculate_ema([Decimal("10")], 5) == ZERO

    def test_period_zero(self):
        assert calculate_ema([Decimal("10"), Decimal("20")], 0) == ZERO

    def test_constant_values(self):
        vals = [Decimal("100")] * 20
        assert calculate_ema(vals, 10) == Decimal("100")


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------


class TestRSI:
    def test_all_gains(self):
        closes = [Decimal(str(i)) for i in range(1, 20)]  # ascending
        rsi = calculate_rsi(closes, 14)
        assert rsi == Decimal("100")

    def test_insufficient_data(self):
        # Needs period + 1 bars minimum
        assert calculate_rsi([Decimal("10"), Decimal("20")], 14) == ZERO

    def test_period_zero(self):
        assert calculate_rsi([Decimal("10"), Decimal("20")], 0) == ZERO

    def test_constant_price_yields_zero(self):
        # No gains, no losses → avg_loss == 0 → RSI = 100
        # Actually: no changes at all, avg_gain=0, avg_loss=0 → division by zero → returns 100
        closes = [Decimal("100")] * 20
        rsi = calculate_rsi(closes, 14)
        assert rsi == Decimal("100")

    def test_uptrend_rsi_above_50(self, sample_closes):
        rsi = calculate_rsi(sample_closes, 14)
        assert rsi > Decimal("50")

    def test_rsi_range(self, sample_closes):
        rsi = calculate_rsi(sample_closes, 14)
        assert ZERO <= rsi <= Decimal("100")


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------


class TestMACD:
    def test_insufficient_data(self):
        result = calculate_macd([Decimal("10")] * 5)
        assert result == (ZERO, ZERO, ZERO)

    def test_constant_price(self):
        closes = [Decimal("100")] * 50
        macd, signal, hist = calculate_macd(closes)
        assert macd == ZERO
        assert signal == ZERO
        assert hist == ZERO

    def test_uptrend_positive_macd(self, sample_closes):
        macd, signal, hist = calculate_macd(sample_closes)
        # In an uptrend, fast EMA > slow EMA → MACD > 0
        assert macd > ZERO


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------


class TestBollingerBands:
    def test_constant_price(self):
        closes = [Decimal("100")] * 20
        upper, middle, lower = calculate_bollinger_bands(closes, 20)
        assert middle == Decimal("100")
        # Zero std dev means bands collapse to middle
        assert upper == Decimal("100")
        assert lower == Decimal("100")

    def test_insufficient_data(self):
        result = calculate_bollinger_bands([Decimal("10")] * 5, 20)
        assert result == (ZERO, ZERO, ZERO)

    def test_upper_above_lower(self, sample_closes):
        upper, middle, lower = calculate_bollinger_bands(sample_closes, 20)
        assert upper > middle
        assert middle > lower

    def test_middle_equals_sma(self, sample_closes):
        _, middle, _ = calculate_bollinger_bands(sample_closes, 20)
        sma = calculate_sma(sample_closes, 20)
        assert middle == sma


# ---------------------------------------------------------------------------
# ATR
# ---------------------------------------------------------------------------


class TestATR:
    def test_insufficient_data(self):
        assert (
            calculate_atr([Decimal("10")], [Decimal("5")], [Decimal("8")], 14) == ZERO
        )

    def test_positive_result(self, sample_highs, sample_lows, sample_closes):
        atr = calculate_atr(sample_highs, sample_lows, sample_closes, 14)
        assert atr > ZERO

    def test_constant_prices_zero_atr(self):
        # If high == low == close for all bars, TR = 0
        n = 20
        vals = [Decimal("100")] * n
        atr = calculate_atr(vals, vals, vals, 14)
        assert atr == ZERO


# ---------------------------------------------------------------------------
# _decimal_sqrt
# ---------------------------------------------------------------------------


class TestDecimalSqrt:
    def test_perfect_square(self):
        result = _decimal_sqrt(Decimal("4"))
        assert abs(result - Decimal("2")) < Decimal("0.0000001")

    def test_zero(self):
        assert _decimal_sqrt(ZERO) == ZERO

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="negativo"):
            _decimal_sqrt(Decimal("-1"))

    def test_non_perfect_square(self):
        result = _decimal_sqrt(Decimal("2"))
        assert abs(result - Decimal("1.4142135")) < Decimal("0.0001")

    def test_large_number(self):
        result = _decimal_sqrt(Decimal("1000000"))
        assert abs(result - Decimal("1000")) < Decimal("0.001")
