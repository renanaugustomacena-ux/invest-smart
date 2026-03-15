"""Tests for new technical indicators: ADX, Stochastic, OBV, Donchian, Williams %R, ROC, CCI."""

from decimal import Decimal

from moneymaker_common.decimal_utils import ZERO

from algo_engine.features.technical import (
    calculate_adx,
    calculate_cci,
    calculate_donchian_channels,
    calculate_obv,
    calculate_roc,
    calculate_stochastic,
    calculate_williams_r,
)

# ---------------------------------------------------------------------------
# ADX
# ---------------------------------------------------------------------------


class TestADX:
    def test_insufficient_data(self):
        # Needs 2*period+1 bars
        highs = [Decimal("10")] * 10
        lows = [Decimal("5")] * 10
        closes = [Decimal("8")] * 10
        assert calculate_adx(highs, lows, closes, 14) == (ZERO, ZERO, ZERO)

    def test_strong_uptrend(self, sample_highs, sample_lows, sample_closes):
        adx, plus_di, minus_di = calculate_adx(sample_highs, sample_lows, sample_closes, 14)
        # In an uptrend, ADX should be positive and +DI > -DI
        assert adx > ZERO
        assert plus_di > minus_di

    def test_constant_price_low_adx(self):
        n = 40
        highs = [Decimal("100")] * n
        lows = [Decimal("100")] * n
        closes = [Decimal("100")] * n
        adx, _, _ = calculate_adx(highs, lows, closes, 14)
        assert adx == ZERO  # No movement

    def test_period_zero(self):
        assert calculate_adx([Decimal("10")], [Decimal("5")], [Decimal("8")], 0) == (
            ZERO,
            ZERO,
            ZERO,
        )


# ---------------------------------------------------------------------------
# Stochastic Oscillator
# ---------------------------------------------------------------------------


class TestStochastic:
    def test_insufficient_data(self):
        assert calculate_stochastic(
            [Decimal("10")] * 3, [Decimal("5")] * 3, [Decimal("8")] * 3, 14, 3
        ) == (ZERO, ZERO)

    def test_at_highest_high(self):
        # Close equals highest high → %K = 100
        highs = [Decimal(str(10 + i)) for i in range(20)]
        lows = [Decimal(str(5 + i)) for i in range(20)]
        closes = list(highs)  # Close at the high
        k, d = calculate_stochastic(highs, lows, closes, 14, 3)
        assert k == Decimal("100")

    def test_at_lowest_low(self):
        # Close equals lowest low in lookback → %K = 0
        # Use constant range so last close at the low IS the lowest low
        highs = [Decimal("20")] * 20
        lows = [Decimal("10")] * 20
        closes = [Decimal("10")] * 20  # Close at low throughout
        k, d = calculate_stochastic(highs, lows, closes, 14, 3)
        assert k == ZERO

    def test_range(self, sample_highs, sample_lows, sample_closes):
        k, d = calculate_stochastic(sample_highs, sample_lows, sample_closes, 14, 3)
        assert ZERO <= k <= Decimal("100")
        assert ZERO <= d <= Decimal("100")

    def test_constant_price_midpoint(self):
        n = 20
        highs = [Decimal("100")] * n
        lows = [Decimal("100")] * n
        closes = [Decimal("100")] * n
        k, d = calculate_stochastic(highs, lows, closes, 14, 3)
        assert k == Decimal("50")  # No range → midpoint


# ---------------------------------------------------------------------------
# OBV
# ---------------------------------------------------------------------------


class TestOBV:
    def test_insufficient_data(self):
        assert calculate_obv([Decimal("10")], [Decimal("100")]) == ZERO

    def test_all_up_closes(self):
        closes = [Decimal(str(i)) for i in range(1, 6)]  # 1,2,3,4,5
        volumes = [Decimal("100")] * 5
        obv = calculate_obv(closes, volumes)
        # 4 up days × 100 = 400
        assert obv == Decimal("400")

    def test_all_down_closes(self):
        closes = [Decimal(str(i)) for i in range(5, 0, -1)]  # 5,4,3,2,1
        volumes = [Decimal("100")] * 5
        obv = calculate_obv(closes, volumes)
        # 4 down days × 100 = -400
        assert obv == Decimal("-400")

    def test_mixed(self):
        closes = [Decimal("10"), Decimal("12"), Decimal("11"), Decimal("13")]
        volumes = [Decimal("100"), Decimal("200"), Decimal("150"), Decimal("300")]
        # Day 2: up, +200  | OBV = 200
        # Day 3: down, -150 | OBV = 50
        # Day 4: up, +300  | OBV = 350
        assert calculate_obv(closes, volumes) == Decimal("350")

    def test_unchanged_price(self):
        closes = [Decimal("10"), Decimal("10"), Decimal("10")]
        volumes = [Decimal("100"), Decimal("200"), Decimal("300")]
        assert calculate_obv(closes, volumes) == ZERO


# ---------------------------------------------------------------------------
# Donchian Channels
# ---------------------------------------------------------------------------


class TestDonchianChannels:
    def test_insufficient_data(self):
        assert calculate_donchian_channels([Decimal("10")] * 5, [Decimal("5")] * 5, 20) == (
            ZERO,
            ZERO,
            ZERO,
        )

    def test_basic_calculation(self):
        highs = [Decimal(str(10 + i)) for i in range(20)]  # 10-29
        lows = [Decimal(str(5 + i)) for i in range(20)]  # 5-24
        upper, middle, lower = calculate_donchian_channels(highs, lows, 20)
        assert upper == Decimal("29")  # max high
        assert lower == Decimal("5")  # min low
        assert middle == Decimal("17")  # (29 + 5) / 2

    def test_constant_price(self):
        n = 20
        highs = [Decimal("100")] * n
        lows = [Decimal("90")] * n
        upper, middle, lower = calculate_donchian_channels(highs, lows, 20)
        assert upper == Decimal("100")
        assert lower == Decimal("90")
        assert middle == Decimal("95")

    def test_upper_above_lower(self, sample_highs, sample_lows):
        upper, middle, lower = calculate_donchian_channels(sample_highs, sample_lows, 20)
        assert upper >= middle >= lower


# ---------------------------------------------------------------------------
# Williams %R
# ---------------------------------------------------------------------------


class TestWilliamsR:
    def test_insufficient_data(self):
        assert calculate_williams_r([Decimal("10")], [Decimal("5")], [Decimal("8")], 14) == ZERO

    def test_at_highest_high(self):
        highs = [Decimal(str(10 + i)) for i in range(14)]
        lows = [Decimal(str(5 + i)) for i in range(14)]
        closes = list(highs)  # Close at highest
        wr = calculate_williams_r(highs, lows, closes, 14)
        assert wr == ZERO  # At top → %R = 0

    def test_at_lowest_low(self):
        # Use constant range so last close at the low IS the lowest low
        highs = [Decimal("20")] * 14
        lows = [Decimal("10")] * 14
        closes = [Decimal("10")] * 14  # Close at low throughout
        wr = calculate_williams_r(highs, lows, closes, 14)
        assert wr == Decimal("-100")  # At bottom → %R = -100

    def test_range(self, sample_highs, sample_lows, sample_closes):
        wr = calculate_williams_r(sample_highs, sample_lows, sample_closes, 14)
        assert Decimal("-100") <= wr <= ZERO


# ---------------------------------------------------------------------------
# Rate of Change (ROC)
# ---------------------------------------------------------------------------


class TestROC:
    def test_insufficient_data(self):
        assert calculate_roc([Decimal("10")] * 5, 10) == ZERO

    def test_positive_change(self):
        closes = [Decimal("100")] * 10 + [Decimal("110")]
        roc = calculate_roc(closes, 10)
        assert roc == Decimal("10")  # 10% increase

    def test_negative_change(self):
        closes = [Decimal("100")] * 10 + [Decimal("90")]
        roc = calculate_roc(closes, 10)
        assert roc == Decimal("-10")  # 10% decrease

    def test_no_change(self):
        closes = [Decimal("100")] * 15
        assert calculate_roc(closes, 10) == ZERO

    def test_uptrend_positive(self, sample_closes):
        roc = calculate_roc(sample_closes, 10)
        assert roc > ZERO  # Uptrend


# ---------------------------------------------------------------------------
# CCI
# ---------------------------------------------------------------------------


class TestCCI:
    def test_insufficient_data(self):
        assert (
            calculate_cci([Decimal("10")] * 5, [Decimal("5")] * 5, [Decimal("8")] * 5, 20) == ZERO
        )

    def test_constant_price(self):
        n = 20
        highs = [Decimal("100")] * n
        lows = [Decimal("100")] * n
        closes = [Decimal("100")] * n
        cci = calculate_cci(highs, lows, closes, 20)
        assert cci == ZERO  # No deviation

    def test_returns_decimal(self, sample_highs, sample_lows, sample_closes):
        cci = calculate_cci(sample_highs, sample_lows, sample_closes, 20)
        assert isinstance(cci, Decimal)

    def test_uptrend_positive(self, sample_highs, sample_lows, sample_closes):
        cci = calculate_cci(sample_highs, sample_lows, sample_closes, 20)
        # In an uptrend, typical price should be above its SMA → CCI > 0
        assert cci > ZERO
