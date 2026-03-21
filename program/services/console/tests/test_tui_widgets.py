"""Tests for TUI widgets — sparklines, progress bars, status dots, colors.

No unittest.mock — pure function tests with deterministic inputs.
"""

from __future__ import annotations

from moneymaker_console.tui.widgets import (
    color_pnl,
    color_pct,
    progress_bar,
    sparkline,
    status_dot,
)


# ---------------------------------------------------------------------------
# sparkline
# ---------------------------------------------------------------------------


class TestSparkline:
    def test_empty_values(self):
        result = sparkline([], width=10)
        assert result == " " * 10

    def test_single_value(self):
        result = sparkline([5.0], width=5)
        assert len(result) == 5

    def test_all_same_values(self):
        """When all values are equal, span=1.0, all map to index 0."""
        result = sparkline([3.0, 3.0, 3.0, 3.0], width=4)
        assert len(result) == 4
        # All same → all " " (idx=0 in _SPARK_CHARS)
        assert result == " " * 4

    def test_ascending_values(self):
        result = sparkline([0, 1, 2, 3, 4, 5, 6, 7, 8], width=9)
        assert len(result) == 9
        # First char should be lowest (space), last should be highest (█)
        assert result[0] == " "
        assert result[-1] == "█"

    def test_descending_values(self):
        result = sparkline([8, 7, 6, 5, 4, 3, 2, 1, 0], width=9)
        assert len(result) == 9
        assert result[0] == "█"
        assert result[-1] == " "

    def test_width_shorter_than_values(self):
        result = sparkline([1.0, 2.0, 3.0, 4.0, 5.0], width=3)
        assert len(result) == 3

    def test_width_longer_than_values(self):
        result = sparkline([1.0, 5.0], width=10)
        assert len(result) == 10

    def test_negative_values(self):
        result = sparkline([-5.0, -3.0, -1.0, 0.0, 2.0], width=5)
        assert len(result) == 5
        assert result[0] == " "   # lowest
        assert result[-1] == "█"  # highest

    def test_two_values(self):
        result = sparkline([0.0, 100.0], width=2)
        assert len(result) == 2
        assert result[0] == " "
        assert result[1] == "█"


# ---------------------------------------------------------------------------
# progress_bar
# ---------------------------------------------------------------------------


class TestProgressBar:
    def test_zero_progress(self):
        result = progress_bar(0, 100, width=10)
        assert "░" * 10 in result
        assert "0%" in result

    def test_full_progress(self):
        result = progress_bar(100, 100, width=10)
        assert "█" * 10 in result
        assert "100%" in result

    def test_half_progress(self):
        result = progress_bar(50, 100, width=10)
        assert "█" * 5 in result
        assert "50%" in result

    def test_total_zero(self):
        result = progress_bar(50, 0, width=10)
        assert "[" in result
        assert "]" in result

    def test_total_negative(self):
        result = progress_bar(50, -10, width=10)
        assert " " * 10 in result  # empty bar

    def test_value_exceeds_total(self):
        result = progress_bar(200, 100, width=10)
        # Clamped to 100%
        assert "█" * 10 in result
        assert "100%" in result

    def test_negative_value(self):
        result = progress_bar(-10, 100, width=10)
        # Clamped to 0%
        assert "░" * 10 in result
        assert "0%" in result

    def test_default_width(self):
        result = progress_bar(50, 100)
        # Default width is 20
        assert len(result.split("]")[0]) - 1 == 20  # chars between [ and ]


# ---------------------------------------------------------------------------
# status_dot
# ---------------------------------------------------------------------------


class TestStatusDot:
    def test_ok_true(self):
        assert status_dot(True) == "● "

    def test_ok_false(self):
        assert status_dot(False) == "○ "


# ---------------------------------------------------------------------------
# color_pnl
# ---------------------------------------------------------------------------


class TestColorPnl:
    def test_positive(self):
        result = color_pnl(150.50)
        assert "[success]" in result
        assert "+$150.50" in result

    def test_negative(self):
        result = color_pnl(-42.99)
        assert "[error]" in result
        assert "$42.99" in result

    def test_zero(self):
        assert color_pnl(0.0) == "$0.00"

    def test_large_positive(self):
        result = color_pnl(1234567.89)
        assert "[success]" in result
        assert "+$1,234,567.89" in result

    def test_small_negative(self):
        result = color_pnl(-0.01)
        assert "[error]" in result


# ---------------------------------------------------------------------------
# color_pct
# ---------------------------------------------------------------------------


class TestColorPct:
    def test_positive_normal(self):
        result = color_pct(5.25)
        assert "[success]" in result
        assert "+5.25%" in result

    def test_negative_normal(self):
        result = color_pct(-3.10)
        assert "[error]" in result
        assert "-3.10%" in result

    def test_zero(self):
        result = color_pct(0.0)
        assert "0.00%" in result
        assert "[success]" not in result
        assert "[error]" not in result

    def test_positive_inverted(self):
        """With invert=True, positive is bad (red)."""
        result = color_pct(5.0, invert=True)
        assert "[error]" in result

    def test_negative_inverted(self):
        """With invert=True, negative is good (green)."""
        result = color_pct(-3.0, invert=True)
        assert "[success]" in result

    def test_zero_inverted(self):
        result = color_pct(0.0, invert=True)
        assert "0.00%" in result
