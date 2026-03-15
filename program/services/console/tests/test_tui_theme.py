"""Tests for TUI theme module."""

from __future__ import annotations

from moneymaker_console.tui.theme import HAS_RICH, MONEYMAKER_THEME, get_console


class TestTheme:
    def test_has_rich_is_bool(self):
        assert isinstance(HAS_RICH, bool)

    def test_theme_exists(self):
        if HAS_RICH:
            assert MONEYMAKER_THEME is not None
            # Check all expected style names
            for name in ("info", "warning", "error", "success",
                         "brain", "market", "risk", "system",
                         "kill", "signal"):
                assert name in MONEYMAKER_THEME.styles

    def test_get_console(self):
        console = get_console()
        if HAS_RICH:
            assert console is not None
        else:
            assert console is None

    def test_console_is_singleton(self):
        c1 = get_console()
        c2 = get_console()
        assert c1 is c2
