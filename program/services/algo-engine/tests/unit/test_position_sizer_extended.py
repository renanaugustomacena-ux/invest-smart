"""Extended tests for position_sizer.py — infer functions, drawdown scaling, edge cases."""

from decimal import Decimal

import pytest

from algo_engine.signals.position_sizer import (
    PIP_SIZES,
    PIP_VALUES,
    PositionSizer,
    infer_pip_size,
    infer_pip_value,
)


# ---------------------------------------------------------------------------
# infer_pip_size
# ---------------------------------------------------------------------------


class TestInferPipSize:
    def test_all_registered_symbols(self):
        """Every symbol in PIP_SIZES should return its value."""
        for symbol, expected in PIP_SIZES.items():
            assert infer_pip_size(symbol) == expected

    def test_digits_override_low(self):
        """digits <= 3 → 0.01 (JPY-like)."""
        assert infer_pip_size("ANYTHING", digits=3) == Decimal("0.01")
        assert infer_pip_size("ANYTHING", digits=2) == Decimal("0.01")

    def test_digits_override_high(self):
        """digits > 3 → 0.0001."""
        assert infer_pip_size("ANYTHING", digits=5) == Decimal("0.0001")
        assert infer_pip_size("ANYTHING", digits=4) == Decimal("0.0001")

    def test_jpy_heuristic(self):
        assert infer_pip_size("CADJPY") == Decimal("0.01")
        assert infer_pip_size("CHFJPY") == Decimal("0.01")

    def test_xau_heuristic(self):
        assert infer_pip_size("XAUEUR") == Decimal("0.01")

    def test_xag_heuristic(self):
        assert infer_pip_size("XAGEUR") == Decimal("0.001")

    def test_index_heuristic(self):
        assert infer_pip_size("US30.cash") == Decimal("1.0")
        assert infer_pip_size("NAS100") == Decimal("1.0")

    def test_crypto_heuristic(self):
        assert infer_pip_size("BTCUSD") == Decimal("1.0")
        assert infer_pip_size("ETHUSD") == Decimal("1.0")

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="non trovato"):
            infer_pip_size("UNKNOWNSYMBOL123")


# ---------------------------------------------------------------------------
# infer_pip_value
# ---------------------------------------------------------------------------


class TestInferPipValue:
    def test_all_registered_symbols(self):
        for symbol, expected in PIP_VALUES.items():
            assert infer_pip_value(symbol) == expected

    def test_jpy_heuristic(self):
        assert infer_pip_value("CADJPY") == Decimal("6.7")

    def test_xau_heuristic(self):
        assert infer_pip_value("XAUEUR") == Decimal("1")

    def test_xag_heuristic(self):
        assert infer_pip_value("XAGEUR") == Decimal("50")

    def test_index_heuristic(self):
        assert infer_pip_value("US30.cash") == Decimal("1")
        assert infer_pip_value("DAX40") == Decimal("1")

    def test_crypto_heuristic(self):
        assert infer_pip_value("BTCUSD") == Decimal("1")

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="non trovato"):
            infer_pip_value("UNKNOWNSYMBOL123")


# ---------------------------------------------------------------------------
# PositionSizer._drawdown_scaling
# ---------------------------------------------------------------------------


class TestDrawdownScaling:
    def test_no_drawdown(self):
        assert PositionSizer._drawdown_scaling(Decimal("0")) == Decimal("1.0")

    def test_low_drawdown(self):
        assert PositionSizer._drawdown_scaling(Decimal("1.5")) == Decimal("1.0")

    def test_boundary_2pct(self):
        assert PositionSizer._drawdown_scaling(Decimal("2.0")) == Decimal("0.5")

    def test_mid_drawdown(self):
        assert PositionSizer._drawdown_scaling(Decimal("3.5")) == Decimal("0.5")

    def test_boundary_4pct(self):
        assert PositionSizer._drawdown_scaling(Decimal("4.0")) == Decimal("0.25")

    def test_high_drawdown(self):
        assert PositionSizer._drawdown_scaling(Decimal("4.5")) == Decimal("0.25")

    def test_kill_zone(self):
        assert PositionSizer._drawdown_scaling(Decimal("5.0")) == Decimal("0")

    def test_extreme_drawdown(self):
        assert PositionSizer._drawdown_scaling(Decimal("10.0")) == Decimal("0")


# ---------------------------------------------------------------------------
# PositionSizer.calculate — extended edge cases
# ---------------------------------------------------------------------------


class TestPositionSizerCalculate:
    def test_unknown_symbol_returns_min_lots(self):
        sizer = PositionSizer()
        lots = sizer.calculate(
            symbol="UNKNOWNSYMBOL",
            entry_price=Decimal("100"),
            stop_loss=Decimal("99"),
        )
        assert lots == Decimal("0.01")

    def test_same_entry_and_sl_returns_min(self):
        sizer = PositionSizer()
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0850"),
        )
        assert lots == Decimal("0.01")

    def test_custom_risk_pct(self):
        sizer = PositionSizer(risk_per_trade_pct=Decimal("2.0"))
        lots_2pct = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            equity=Decimal("10000"),
        )
        sizer1 = PositionSizer(risk_per_trade_pct=Decimal("1.0"))
        lots_1pct = sizer1.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            equity=Decimal("10000"),
        )
        assert lots_2pct >= lots_1pct

    def test_custom_min_max_lots(self):
        sizer = PositionSizer(min_lots=Decimal("0.05"), max_lots=Decimal("0.50"))
        # Very small account → should clamp to min
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            equity=Decimal("100"),
        )
        assert lots >= Decimal("0.05")

    def test_usdjpy_calculation(self):
        sizer = PositionSizer()
        lots = sizer.calculate(
            symbol="USDJPY",
            entry_price=Decimal("150.00"),
            stop_loss=Decimal("149.50"),
            equity=Decimal("10000"),
        )
        assert Decimal("0.01") <= lots <= Decimal("0.10")

    def test_high_drawdown_returns_min(self):
        sizer = PositionSizer()
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            equity=Decimal("10000"),
            drawdown_pct=Decimal("6.0"),
        )
        assert lots == Decimal("0.01")

    def test_moderate_drawdown_reduces_size(self):
        sizer = PositionSizer()
        lots_normal = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            equity=Decimal("10000"),
            drawdown_pct=Decimal("0"),
        )
        lots_stressed = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            equity=Decimal("10000"),
            drawdown_pct=Decimal("3.0"),
        )
        assert lots_stressed <= lots_normal

    def test_sell_direction_uses_abs_distance(self):
        """Stop loss above entry (sell) should work the same way."""
        sizer = PositionSizer()
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0820"),
            stop_loss=Decimal("1.0850"),
            equity=Decimal("10000"),
        )
        assert Decimal("0.01") <= lots <= Decimal("0.10")

    def test_result_quantized_to_2_decimal_places(self):
        sizer = PositionSizer()
        lots = sizer.calculate(
            symbol="EURUSD",
            entry_price=Decimal("1.0850"),
            stop_loss=Decimal("1.0820"),
            equity=Decimal("10000"),
        )
        # Should be quantized to 0.01
        assert lots == lots.quantize(Decimal("0.01"))
