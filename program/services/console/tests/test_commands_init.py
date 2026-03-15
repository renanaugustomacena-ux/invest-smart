"""Tests for commands/__init__.py discover_and_register."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from moneymaker_console.commands import discover_and_register
from moneymaker_console.registry import CommandRegistry


class TestDiscoverAndRegister:
    def test_discovers_modules(self):
        registry = CommandRegistry()
        discover_and_register(registry)
        # At minimum, help and exit should be registered
        assert "help" in registry.categories
        assert "exit" in registry.categories

    def test_registers_multiple_categories(self):
        registry = CommandRegistry()
        discover_and_register(registry)
        assert len(registry.categories) > 2

    def test_broken_module_skipped(self):
        registry = CommandRegistry()
        # Even if one module fails, others should still register
        with patch("moneymaker_console.commands.pkgutil.iter_modules") as mock_iter:
            mock_iter.return_value = [
                (None, "broken_module", False),
            ]
            with patch("moneymaker_console.commands.importlib.import_module") as mock_import:
                mock_import.side_effect = ImportError("broken")
                discover_and_register(registry)
                # Should not raise

    def test_module_without_register(self):
        registry = CommandRegistry()
        with patch("moneymaker_console.commands.pkgutil.iter_modules") as mock_iter:
            mock_iter.return_value = [
                (None, "no_register", False),
            ]
            with patch("moneymaker_console.commands.importlib.import_module") as mock_import:
                mock_module = MagicMock(spec=[])  # No register attribute
                mock_import.return_value = mock_module
                discover_and_register(registry)
                # Should not raise, should skip silently
