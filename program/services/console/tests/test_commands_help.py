"""Tests for the help command module."""

from __future__ import annotations

from moneymaker_console.commands.help import _cmd_help, register
from moneymaker_console.registry import CommandRegistry


class TestHelpCommand:
    def test_no_registry(self):
        import moneymaker_console.commands.help as help_mod

        old = help_mod._registry
        help_mod._registry = None
        try:
            result = _cmd_help()
            assert "[error]" in result
        finally:
            help_mod._registry = old

    def test_general_help(self, registry):
        register(registry)
        result = _cmd_help()
        assert "Command Reference" in result
        assert "svc" in result

    def test_category_help(self, registry):
        register(registry)
        result = _cmd_help("svc")
        assert "svc" in result.lower() or "status" in result.lower()

    def test_unknown_category(self, registry):
        register(registry)
        result = _cmd_help("nonexistent")
        assert "[error]" in result
        assert "nonexistent" in result

    def test_register_adds_help_command(self):
        reg = CommandRegistry()
        register(reg)
        assert "help" in reg.categories
