"""Tests for algo_engine.backtesting.data_loader — CSV/Parquet loading."""

import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from algo_engine.backtesting.data_loader import (
    _row_to_bar,
    _to_decimal,
    iter_bars_from_csv,
    load_bars_from_csv,
)


# ---------------------------------------------------------------------------
# _to_decimal
# ---------------------------------------------------------------------------


class TestToDecimal:
    def test_string_input(self):
        result = _to_decimal("1.23456789")
        assert isinstance(result, Decimal)
        assert result == Decimal("1.23456789")

    def test_float_input(self):
        result = _to_decimal(1.5)
        assert isinstance(result, Decimal)

    def test_int_input(self):
        result = _to_decimal(100)
        assert isinstance(result, Decimal)
        assert result == Decimal("100.00000000")

    def test_decimal_passthrough(self):
        d = Decimal("42.12345678")
        result = _to_decimal(d)
        assert result is d  # Same object — no re-quantize

    def test_precision_is_8_decimal_places(self):
        result = _to_decimal("1.123456789012")
        # Should be quantized to 8 decimal places
        assert str(result).count(".") == 1
        decimal_part = str(result).split(".")[1]
        assert len(decimal_part) == 8

    def test_zero(self):
        result = _to_decimal("0")
        assert result == Decimal("0E-8") or result == Decimal("0.00000000")


# ---------------------------------------------------------------------------
# _row_to_bar
# ---------------------------------------------------------------------------


class TestRowToBar:
    def test_basic_conversion(self):
        row = {
            "timestamp": "1700000000000",
            "open": "1900.50",
            "high": "1905.00",
            "low": "1898.00",
            "close": "1903.25",
            "volume": "5000",
        }
        columns = {
            "timestamp": "timestamp",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        }
        bar = _row_to_bar(row, columns)
        assert bar.timestamp == 1700000000000
        assert bar.open == _to_decimal("1900.50")
        assert bar.high == _to_decimal("1905.00")
        assert bar.low == _to_decimal("1898.00")
        assert bar.close == _to_decimal("1903.25")
        assert bar.volume == _to_decimal("5000")

    def test_custom_column_mapping(self):
        row = {"ts": "1700000000000", "o": "100", "h": "110", "l": "90", "c": "105", "v": "999"}
        columns = {
            "timestamp": "ts",
            "open": "o",
            "high": "h",
            "low": "l",
            "close": "c",
            "volume": "v",
        }
        bar = _row_to_bar(row, columns)
        assert bar.timestamp == 1700000000000
        assert bar.close == _to_decimal("105")

    def test_missing_column_raises(self):
        row = {"timestamp": "1700000000000", "open": "100"}
        columns = {
            "timestamp": "timestamp",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        }
        with pytest.raises(KeyError):
            _row_to_bar(row, columns)


# ---------------------------------------------------------------------------
# load_bars_from_csv
# ---------------------------------------------------------------------------


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    """Helper to write a CSV test file."""
    content = header + "\n" + "\n".join(rows) + "\n"
    path.write_text(content, encoding="utf-8")


class TestLoadBarsFromCSV:
    def test_basic_load(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        _write_csv(
            csv_file,
            "timestamp,open,high,low,close,volume",
            [
                "1700000000000,1900.50,1905.00,1898.00,1903.25,5000",
                "1700000060000,1903.25,1908.00,1901.00,1906.50,4500",
                "1700000120000,1906.50,1910.00,1904.00,1909.00,6000",
            ],
        )
        bars = load_bars_from_csv(csv_file)
        assert len(bars) == 3
        assert bars[0].timestamp < bars[1].timestamp < bars[2].timestamp
        assert bars[0].close == _to_decimal("1903.25")

    def test_sorts_by_timestamp(self, tmp_path):
        csv_file = tmp_path / "unsorted.csv"
        _write_csv(
            csv_file,
            "timestamp,open,high,low,close,volume",
            [
                "1700000120000,100,110,90,105,100",
                "1700000000000,100,110,90,102,100",
                "1700000060000,100,110,90,103,100",
            ],
        )
        bars = load_bars_from_csv(csv_file)
        assert bars[0].timestamp == 1700000000000
        assert bars[1].timestamp == 1700000060000
        assert bars[2].timestamp == 1700000120000

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            load_bars_from_csv("/nonexistent/path/data.csv")

    def test_empty_csv_no_header(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="no header row"):
            load_bars_from_csv(csv_file)

    def test_missing_columns(self, tmp_path):
        csv_file = tmp_path / "bad_cols.csv"
        _write_csv(csv_file, "timestamp,open,close", ["1700000000000,100,105"])
        with pytest.raises(ValueError, match="Missing columns"):
            load_bars_from_csv(csv_file)

    def test_custom_column_mapping(self, tmp_path):
        csv_file = tmp_path / "custom.csv"
        _write_csv(
            csv_file,
            "ts,o,h,l,c,v",
            ["1700000000000,100,110,90,105,500"],
        )
        bars = load_bars_from_csv(
            csv_file,
            columns={
                "timestamp": "ts",
                "open": "o",
                "high": "h",
                "low": "l",
                "close": "c",
                "volume": "v",
            },
        )
        assert len(bars) == 1
        assert bars[0].close == _to_decimal("105")

    def test_invalid_row_skipped(self, tmp_path):
        csv_file = tmp_path / "mixed.csv"
        _write_csv(
            csv_file,
            "timestamp,open,high,low,close,volume",
            [
                "1700000000000,1900,1905,1898,1903,5000",
                "not_a_number,bad,data,here,nope,never",
                "1700000060000,1903,1908,1901,1906,4500",
            ],
        )
        bars = load_bars_from_csv(csv_file)
        assert len(bars) == 2  # Bad row skipped

    def test_accepts_string_path(self, tmp_path):
        csv_file = tmp_path / "str_path.csv"
        _write_csv(
            csv_file,
            "timestamp,open,high,low,close,volume",
            ["1700000000000,100,110,90,105,500"],
        )
        bars = load_bars_from_csv(str(csv_file))
        assert len(bars) == 1

    def test_single_row(self, tmp_path):
        csv_file = tmp_path / "single.csv"
        _write_csv(
            csv_file,
            "timestamp,open,high,low,close,volume",
            ["1700000000000,1900.12345678,1905,1898,1903,5000"],
        )
        bars = load_bars_from_csv(csv_file)
        assert len(bars) == 1
        assert bars[0].open == _to_decimal("1900.12345678")


# ---------------------------------------------------------------------------
# iter_bars_from_csv
# ---------------------------------------------------------------------------


class TestIterBarsFromCSV:
    def test_basic_iteration(self, tmp_path):
        csv_file = tmp_path / "iter.csv"
        _write_csv(
            csv_file,
            "timestamp,open,high,low,close,volume",
            [
                "1700000000000,100,110,90,105,500",
                "1700000060000,105,115,95,110,600",
            ],
        )
        bars = list(iter_bars_from_csv(csv_file))
        assert len(bars) == 2
        assert bars[0].timestamp == 1700000000000

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            list(iter_bars_from_csv("/nonexistent.csv"))

    def test_invalid_rows_skipped(self, tmp_path):
        csv_file = tmp_path / "iter_mixed.csv"
        _write_csv(
            csv_file,
            "timestamp,open,high,low,close,volume",
            [
                "1700000000000,100,110,90,105,500",
                "bad,bad,bad,bad,bad,bad",
                "1700000060000,105,115,95,110,600",
            ],
        )
        bars = list(iter_bars_from_csv(csv_file))
        assert len(bars) == 2

    def test_yields_in_file_order(self, tmp_path):
        """iter_bars does NOT sort — yields in file order."""
        csv_file = tmp_path / "order.csv"
        _write_csv(
            csv_file,
            "timestamp,open,high,low,close,volume",
            [
                "1700000120000,100,110,90,105,500",
                "1700000000000,100,110,90,102,500",
            ],
        )
        bars = list(iter_bars_from_csv(csv_file))
        assert bars[0].timestamp == 1700000120000  # File order, not sorted
        assert bars[1].timestamp == 1700000000000

    def test_custom_columns(self, tmp_path):
        csv_file = tmp_path / "iter_custom.csv"
        _write_csv(csv_file, "ts,o,h,l,c,v", ["1700000000000,100,110,90,105,500"])
        bars = list(
            iter_bars_from_csv(
                csv_file,
                columns={
                    "timestamp": "ts",
                    "open": "o",
                    "high": "h",
                    "low": "l",
                    "close": "c",
                    "volume": "v",
                },
            )
        )
        assert len(bars) == 1
