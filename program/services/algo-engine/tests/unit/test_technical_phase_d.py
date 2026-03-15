"""Tests for Phase D indicators — 9 new indicators + 2 helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.features.technical import (
    _calculate_rsi_series,
    _decimal_ln,
    calculate_cmf,
    calculate_dema,
    calculate_force_index,
    calculate_historical_volatility,
    calculate_keltner_channels,
    calculate_parabolic_sar,
    calculate_parkinson_volatility,
    calculate_stochastic_rsi,
    calculate_ultimate_oscillator,
    calculate_vwap,
)

ZERO = Decimal("0")


# ---- Helper fixtures ----


@pytest.fixture
def uptrend_closes() -> list[Decimal]:
    """50 bars with clear uptrend + oscillation."""
    return [Decimal(str(100 + i * 0.5 + (i % 3 - 1) * 0.3)) for i in range(50)]


@pytest.fixture
def uptrend_highs(uptrend_closes: list[Decimal]) -> list[Decimal]:
    return [c + Decimal("1.5") for c in uptrend_closes]


@pytest.fixture
def uptrend_lows(uptrend_closes: list[Decimal]) -> list[Decimal]:
    return [c - Decimal("1.5") for c in uptrend_closes]


@pytest.fixture
def constant_volumes() -> list[Decimal]:
    return [Decimal("1000") for _ in range(50)]


@pytest.fixture
def downtrend_closes() -> list[Decimal]:
    return [Decimal(str(150 - i * 0.5)) for i in range(50)]


@pytest.fixture
def downtrend_highs(downtrend_closes: list[Decimal]) -> list[Decimal]:
    return [c + Decimal("1.5") for c in downtrend_closes]


@pytest.fixture
def downtrend_lows(downtrend_closes: list[Decimal]) -> list[Decimal]:
    return [c - Decimal("1.5") for c in downtrend_closes]


# ---- _decimal_ln ----


class TestDecimalLn:
    def test_ln_one_is_zero(self):
        result = _decimal_ln(Decimal("1"))
        assert abs(result) < Decimal("0.0001")

    def test_ln_e_is_near_one(self):
        e = Decimal("2.718281828459045")
        result = _decimal_ln(e)
        assert abs(result - Decimal("1")) < Decimal("0.0001")

    def test_ln_two(self):
        result = _decimal_ln(Decimal("2"))
        assert abs(result - Decimal("0.6931")) < Decimal("0.001")

    def test_ln_zero_returns_zero(self):
        assert _decimal_ln(ZERO) == ZERO

    def test_ln_negative_returns_zero(self):
        assert _decimal_ln(Decimal("-5")) == ZERO

    def test_ln_large_value(self):
        result = _decimal_ln(Decimal("1000"))
        # ln(1000) ~ 6.9078
        assert abs(result - Decimal("6.9078")) < Decimal("0.01")

    def test_ln_small_positive(self):
        result = _decimal_ln(Decimal("0.1"))
        # ln(0.1) ~ -2.3026
        assert abs(result - Decimal("-2.3026")) < Decimal("0.01")


# ---- _calculate_rsi_series ----


class TestRSISeries:
    def test_insufficient_data(self):
        assert _calculate_rsi_series([Decimal("100")] * 10, 14) == []

    def test_returns_list(self, uptrend_closes):
        series = _calculate_rsi_series(uptrend_closes, 14)
        assert isinstance(series, list)
        assert len(series) > 0

    def test_values_in_range(self, uptrend_closes):
        series = _calculate_rsi_series(uptrend_closes, 14)
        for val in series:
            assert ZERO <= val <= Decimal("100")

    def test_uptrend_high_rsi(self):
        closes = [Decimal(str(100 + i)) for i in range(30)]
        series = _calculate_rsi_series(closes, 14)
        assert series[-1] > Decimal("80")


# ---- DEMA ----


class TestDEMA:
    def test_insufficient_data(self):
        vals = [Decimal("100")] * 10
        assert calculate_dema(vals, 20) == ZERO

    def test_constant_price_equals_price(self):
        vals = [Decimal("100")] * 50
        dema = calculate_dema(vals, 20)
        assert abs(dema - Decimal("100")) < Decimal("0.01")

    def test_returns_decimal(self, uptrend_closes):
        result = calculate_dema(uptrend_closes, 20)
        assert isinstance(result, Decimal)
        assert result > ZERO

    def test_more_reactive_than_ema(self, uptrend_closes):
        from algo_engine.features.technical import calculate_ema

        dema = calculate_dema(uptrend_closes, 20)
        ema = calculate_ema(uptrend_closes, 20)
        # In uptrend, DEMA should be closer to (or above) current price than EMA
        current = uptrend_closes[-1]
        assert abs(dema - current) <= abs(ema - current) + Decimal("1")


# ---- Keltner Channels ----


class TestKeltnerChannels:
    def test_insufficient_data(self):
        short = [Decimal("100")] * 5
        assert calculate_keltner_channels(short, short, short) == (ZERO, ZERO, ZERO)

    def test_upper_gt_middle_gt_lower(self, uptrend_highs, uptrend_lows, uptrend_closes):
        u, m, l = calculate_keltner_channels(uptrend_highs, uptrend_lows, uptrend_closes)
        assert u > m > l

    def test_returns_decimals(self, uptrend_highs, uptrend_lows, uptrend_closes):
        u, m, l = calculate_keltner_channels(uptrend_highs, uptrend_lows, uptrend_closes)
        assert all(isinstance(v, Decimal) for v in (u, m, l))

    def test_constant_price_bands_collapse(self):
        vals = [Decimal("100")] * 50
        u, m, l = calculate_keltner_channels(vals, vals, vals)
        # ATR = 0 when H=L=C, so bands should be zero
        assert u == ZERO and m == ZERO and l == ZERO


# ---- Parabolic SAR ----


class TestParabolicSAR:
    def test_insufficient_data(self):
        assert calculate_parabolic_sar([Decimal("100")], [Decimal("99")]) == (ZERO, "unknown")

    def test_uptrend_bullish(self, uptrend_highs, uptrend_lows):
        sar, trend = calculate_parabolic_sar(uptrend_highs, uptrend_lows)
        assert trend == "bullish"
        assert sar > ZERO

    def test_downtrend_bearish(self, downtrend_highs, downtrend_lows):
        sar, trend = calculate_parabolic_sar(downtrend_highs, downtrend_lows)
        assert trend == "bearish"
        assert sar > ZERO

    def test_returns_decimal_and_str(self, uptrend_highs, uptrend_lows):
        sar, trend = calculate_parabolic_sar(uptrend_highs, uptrend_lows)
        assert isinstance(sar, Decimal)
        assert isinstance(trend, str)
        assert trend in ("bullish", "bearish", "unknown")


# ---- VWAP ----


class TestVWAP:
    def test_empty_data(self):
        assert calculate_vwap([], [], [], []) == ZERO

    def test_zero_volume(self):
        h = [Decimal("102")]
        l = [Decimal("98")]
        c = [Decimal("100")]
        v = [ZERO]
        assert calculate_vwap(h, l, c, v) == ZERO

    def test_constant_price_equals_price(self):
        n = 20
        h = [Decimal("100")] * n
        l = [Decimal("100")] * n
        c = [Decimal("100")] * n
        v = [Decimal("1000")] * n
        assert calculate_vwap(h, l, c, v) == Decimal("100")

    def test_within_price_range(
        self, uptrend_highs, uptrend_lows, uptrend_closes, constant_volumes
    ):
        vwap = calculate_vwap(uptrend_highs, uptrend_lows, uptrend_closes, constant_volumes)
        assert min(uptrend_lows) <= vwap <= max(uptrend_highs)


# ---- CMF ----


class TestCMF:
    def test_insufficient_data(self):
        short = [Decimal("100")] * 5
        assert calculate_cmf(short, short, short, short, period=20) == ZERO

    def test_close_at_high_positive(self):
        """When close = high, MF multiplier is +1 → CMF positive."""
        n = 25
        h = [Decimal("110")] * n
        l = [Decimal("100")] * n
        c = [Decimal("110")] * n  # close at high
        v = [Decimal("1000")] * n
        cmf = calculate_cmf(h, l, c, v, period=20)
        assert cmf > ZERO

    def test_close_at_low_negative(self):
        """When close = low, MF multiplier is -1 → CMF negative."""
        n = 25
        h = [Decimal("110")] * n
        l = [Decimal("100")] * n
        c = [Decimal("100")] * n  # close at low
        v = [Decimal("1000")] * n
        cmf = calculate_cmf(h, l, c, v, period=20)
        assert cmf < ZERO

    def test_approx_bounded(self, uptrend_highs, uptrend_lows, uptrend_closes, constant_volumes):
        cmf = calculate_cmf(uptrend_highs, uptrend_lows, uptrend_closes, constant_volumes, 20)
        assert Decimal("-1.1") <= cmf <= Decimal("1.1")


# ---- Stochastic RSI ----


class TestStochasticRSI:
    def test_insufficient_data(self):
        assert calculate_stochastic_rsi([Decimal("100")] * 10) == (ZERO, ZERO)

    def test_returns_tuple(self, uptrend_closes):
        k, d = calculate_stochastic_rsi(uptrend_closes)
        assert isinstance(k, Decimal)
        assert isinstance(d, Decimal)

    def test_range_0_100(self, uptrend_closes):
        k, d = calculate_stochastic_rsi(uptrend_closes)
        assert ZERO <= k <= Decimal("100")
        if d > ZERO:
            assert d <= Decimal("100")

    def test_strong_uptrend_high(self):
        closes = [Decimal(str(100 + i)) for i in range(50)]
        k, d = calculate_stochastic_rsi(closes, 14, 14, 3, 3)
        assert k > Decimal("80")


# ---- Ultimate Oscillator ----


class TestUltimateOscillator:
    def test_insufficient_data(self):
        short = [Decimal("100")] * 10
        assert calculate_ultimate_oscillator(short, short, short) == ZERO

    def test_returns_decimal(self, uptrend_highs, uptrend_lows, uptrend_closes):
        uo = calculate_ultimate_oscillator(uptrend_highs, uptrend_lows, uptrend_closes)
        assert isinstance(uo, Decimal)

    def test_range_0_100(self, uptrend_highs, uptrend_lows, uptrend_closes):
        uo = calculate_ultimate_oscillator(uptrend_highs, uptrend_lows, uptrend_closes)
        assert ZERO <= uo <= Decimal("100")

    def test_uptrend_above_50(self):
        """Strong uptrend should have UO > 50."""
        closes = [Decimal(str(100 + i)) for i in range(50)]
        highs = [c + Decimal("0.5") for c in closes]
        lows = [c - Decimal("0.5") for c in closes]
        uo = calculate_ultimate_oscillator(highs, lows, closes, 7, 14, 28)
        assert uo > Decimal("50")


# ---- Historical Volatility ----


class TestHistoricalVolatility:
    def test_insufficient_data(self):
        assert calculate_historical_volatility([Decimal("100")] * 10, 20) == ZERO

    def test_constant_price_zero_vol(self):
        closes = [Decimal("100")] * 30
        vol = calculate_historical_volatility(closes, 20)
        assert vol == ZERO

    def test_positive_for_volatile_data(self, uptrend_closes):
        vol = calculate_historical_volatility(uptrend_closes, 20)
        assert vol > ZERO

    def test_returns_decimal(self, uptrend_closes):
        vol = calculate_historical_volatility(uptrend_closes, 20)
        assert isinstance(vol, Decimal)


# ---- Parkinson Volatility ----


class TestParkinsonVolatility:
    def test_insufficient_data(self):
        short = [Decimal("100")] * 5
        assert calculate_parkinson_volatility(short, short, 20) == ZERO

    def test_equal_high_low_zero(self):
        """When H == L (flat bars), Parkinson vol should be zero."""
        vals = [Decimal("100")] * 30
        vol = calculate_parkinson_volatility(vals, vals, 20)
        assert vol == ZERO

    def test_positive_for_range(self, uptrend_highs, uptrend_lows):
        vol = calculate_parkinson_volatility(uptrend_highs, uptrend_lows, 20)
        assert vol > ZERO

    def test_returns_decimal(self, uptrend_highs, uptrend_lows):
        vol = calculate_parkinson_volatility(uptrend_highs, uptrend_lows, 20)
        assert isinstance(vol, Decimal)


# ---- Force Index ----


class TestForceIndex:
    def test_insufficient_data(self):
        short = [Decimal("100")] * 5
        assert calculate_force_index(short, short, 13) == ZERO

    def test_uptrend_positive(self, uptrend_closes, constant_volumes):
        fi = calculate_force_index(uptrend_closes, constant_volumes, 13)
        assert fi > ZERO

    def test_downtrend_negative(self, downtrend_closes, constant_volumes):
        fi = calculate_force_index(downtrend_closes, constant_volumes, 13)
        assert fi < ZERO

    def test_returns_decimal(self, uptrend_closes, constant_volumes):
        fi = calculate_force_index(uptrend_closes, constant_volumes, 13)
        assert isinstance(fi, Decimal)


# ---- Pipeline integration ----


class TestPipelineNewKeys:
    """Verify pipeline produces all new Phase D feature keys."""

    def test_new_keys_present(self, sample_ohlcv_bars):
        from algo_engine.features.pipeline import FeaturePipeline

        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)

        new_keys = [
            "dema",
            "keltner_upper",
            "keltner_middle",
            "keltner_lower",
            "parabolic_sar",
            "parabolic_sar_trend",
            "vwap",
            "cmf",
            "stoch_rsi_k",
            "stoch_rsi_d",
            "ultimate_osc",
            "hist_vol",
            "parkinson_vol",
            "force_index",
        ]
        for key in new_keys:
            assert key in features, f"Missing feature key: {key}"

    def test_numeric_keys_are_decimal(self, sample_ohlcv_bars):
        from algo_engine.features.pipeline import FeaturePipeline

        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", sample_ohlcv_bars)

        decimal_keys = [
            "dema",
            "keltner_upper",
            "keltner_middle",
            "keltner_lower",
            "parabolic_sar",
            "vwap",
            "cmf",
            "stoch_rsi_k",
            "stoch_rsi_d",
            "ultimate_osc",
            "hist_vol",
            "parkinson_vol",
            "force_index",
        ]
        for key in decimal_keys:
            assert isinstance(
                features[key], Decimal
            ), f"{key} should be Decimal, got {type(features[key])}"
