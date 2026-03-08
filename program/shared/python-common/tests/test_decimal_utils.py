"""Tests for moneymaker_common.decimal_utils."""

from decimal import Decimal


from moneymaker_common.decimal_utils import (
    ZERO,
    calculate_lot_size,
    calculate_pips,
    decimal_to_str,
    pct_change,
    position_value,
    to_decimal,
)


# ---------------------------------------------------------------------------
# to_decimal
# ---------------------------------------------------------------------------


class TestToDecimal:
    def test_from_string(self):
        assert to_decimal("1900.50") == Decimal("1900.50")

    def test_from_int(self):
        assert to_decimal(100) == Decimal("100")

    def test_from_float_avoids_precision_loss(self):
        result = to_decimal(0.1) + to_decimal(0.2)
        assert result == Decimal("0.3")

    def test_passthrough_returns_same_object(self):
        d = Decimal("50.123")
        assert to_decimal(d) is d

    def test_negative_value(self):
        assert to_decimal("-42.5") == Decimal("-42.5")

    def test_zero(self):
        assert to_decimal(0) == ZERO


# ---------------------------------------------------------------------------
# decimal_to_str
# ---------------------------------------------------------------------------


class TestDecimalToStr:
    def test_default_8_places(self):
        result = decimal_to_str(Decimal("1.123456789"))
        assert result == "1.12345679"  # banker's rounding

    def test_custom_places(self):
        assert decimal_to_str(Decimal("1.5"), places=2) == "1.50"

    def test_zero_padded(self):
        assert decimal_to_str(Decimal("5"), places=4) == "5.0000"

    def test_large_number(self):
        result = decimal_to_str(Decimal("99999.123"), places=2)
        assert result == "99999.12"


# ---------------------------------------------------------------------------
# calculate_pips
# ---------------------------------------------------------------------------


class TestCalculatePips:
    def test_normal(self):
        result = calculate_pips(Decimal("0.0050"), Decimal("0.0001"))
        assert result == Decimal("50")

    def test_zero_pip_size_returns_zero(self):
        assert calculate_pips(Decimal("10.0"), ZERO) == ZERO

    def test_negative_diff(self):
        result = calculate_pips(Decimal("-0.0030"), Decimal("0.0001"))
        assert result == Decimal("-30")


# ---------------------------------------------------------------------------
# position_value
# ---------------------------------------------------------------------------


class TestPositionValue:
    def test_normal(self):
        result = position_value(Decimal("1.0"), Decimal("2000"), Decimal("100"))
        assert result == Decimal("200000")

    def test_fractional_lots(self):
        result = position_value(Decimal("0.01"), Decimal("2000"), Decimal("100"))
        assert result == Decimal("2000")


# ---------------------------------------------------------------------------
# calculate_lot_size
# ---------------------------------------------------------------------------


class TestCalculateLotSize:
    def test_normal(self):
        result = calculate_lot_size(Decimal("100"), Decimal("50"), Decimal("10"))
        assert result == Decimal("0.2")

    def test_zero_stop_loss_returns_zero(self):
        assert calculate_lot_size(Decimal("100"), ZERO, Decimal("10")) == ZERO

    def test_zero_pip_value_returns_zero(self):
        assert calculate_lot_size(Decimal("100"), Decimal("50"), ZERO) == ZERO


# ---------------------------------------------------------------------------
# pct_change
# ---------------------------------------------------------------------------


class TestPctChange:
    def test_positive_change(self):
        assert pct_change(Decimal("100"), Decimal("110")) == Decimal("10")

    def test_negative_change(self):
        assert pct_change(Decimal("100"), Decimal("90")) == Decimal("-10")

    def test_no_change(self):
        assert pct_change(Decimal("100"), Decimal("100")) == ZERO

    def test_from_zero_returns_zero(self):
        assert pct_change(ZERO, Decimal("50")) == ZERO
