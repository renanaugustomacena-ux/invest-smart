"""Tests for the exit command module."""

from __future__ import annotations

from moneymaker_console.commands.exit_cmd import _cmd_exit, register
from moneymaker_console.registry import CommandRegistry


class TestExitCommand:
    def test_returns_exit_sentinel(self):
        assert _cmd_exit() == "__EXIT__"

    def test_ignores_args(self):
        assert _cmd_exit("foo", "bar") == "__EXIT__"

    def test_register_adds_category(self):
        reg = CommandRegistry()
        register(reg)
        assert "exit" in reg.categories

    def test_aliases_registered(self):
        reg = CommandRegistry()
        register(reg)
        assert "q" in reg._aliases
        assert "quit" in reg._aliases
        assert reg._aliases["q"] == ("exit", "")
        assert reg._aliases["quit"] == ("exit", "")
