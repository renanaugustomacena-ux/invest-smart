"""Tests for CommandRegistry dispatch, aliases, help, and completions."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure console src is on path
_console_src = Path(__file__).resolve().parent.parent / "src"
if str(_console_src) not in sys.path:
    sys.path.insert(0, str(_console_src))

from moneymaker_console.registry import CommandRegistry  # noqa: E402


@pytest.fixture()
def registry():
    reg = CommandRegistry()
    reg.register("svc", "status", lambda: "all running", "Show service status")
    reg.register("svc", "restart", lambda name="all": f"restarted {name}", "Restart a service")
    reg.register("brain", "state", lambda: "brain active", "Show brain state")
    reg.register("exit", "", lambda: "bye", "Exit console", aliases=["q", "quit"])
    reg.register("hidden", "secret", lambda: "hidden", "Hidden cmd", hidden=True)
    return reg


class TestRegistration:
    def test_categories(self, registry):
        assert "svc" in registry.categories
        assert "brain" in registry.categories
        assert "exit" in registry.categories

    def test_command_count(self, registry):
        # 'svc': 2, 'brain': 1, 'exit': 0 (empty subcmd not counted), 'hidden': 1
        assert registry.command_count == 4


class TestDispatch:
    def test_dispatch_valid(self, registry):
        result = registry.dispatch("svc", "status", [])
        assert result == "all running"

    def test_dispatch_with_args(self, registry):
        result = registry.dispatch("svc", "restart", ["postgres"])
        assert "restarted postgres" in result

    def test_dispatch_unknown_category(self, registry):
        result = registry.dispatch("nonexistent", "foo", [])
        assert "[error]" in result

    def test_dispatch_unknown_subcmd(self, registry):
        result = registry.dispatch("svc", "nonexistent", [])
        assert "[error]" in result
        assert "Available:" in result

    def test_dispatch_handler_exception(self, registry):
        registry.register(
            "fail", "boom", lambda: (_ for _ in ()).throw(ValueError("test")), "Will fail"
        )

        # Use a simpler approach
        def raise_error():
            raise ValueError("test error")

        registry.register("fail2", "boom", raise_error, "Will fail")
        result = registry.dispatch("fail2", "boom", [])
        assert "[error]" in result
        assert "test error" in result


class TestDispatchInteractive:
    def test_empty_input(self, registry):
        assert registry.dispatch_interactive("") == ""

    def test_alias_resolution(self, registry):
        assert registry.dispatch_interactive("q") == "bye"
        assert registry.dispatch_interactive("quit") == "bye"

    def test_two_part_command(self, registry):
        result = registry.dispatch_interactive("svc status")
        assert result == "all running"

    def test_single_word_command(self, registry):
        result = registry.dispatch_interactive("exit")
        assert result == "bye"

    def test_category_only_shows_subcmds(self, registry):
        result = registry.dispatch_interactive("svc")
        # exit has empty subcmd so it should use the handler
        # svc has no empty subcmd, so it lists available
        assert "restart" in result or "status" in result


class TestHelp:
    def test_get_help_all(self, registry):
        text = registry.get_help()
        assert "svc" in text
        assert "brain" in text

    def test_get_help_category(self, registry):
        text = registry.get_help("svc")
        assert "status" in text
        assert "restart" in text

    def test_hidden_excluded_from_help(self, registry):
        text = registry.get_help("hidden")
        assert "secret" not in text

    def test_detailed_help(self, registry):
        text = registry.get_detailed_help("brain")
        assert "brain state" in text.lower() or "brain" in text.lower()


class TestCompletions:
    def test_complete_empty(self, registry):
        completions = registry.get_completions("")
        assert "svc" in completions
        assert "brain" in completions

    def test_complete_partial_category(self, registry):
        completions = registry.get_completions("sv")
        assert "svc" in completions
        assert "brain" not in completions

    def test_complete_category_with_space(self, registry):
        completions = registry.get_completions("svc ")
        assert any("status" in c for c in completions)
        assert any("restart" in c for c in completions)

    def test_complete_subcmd(self, registry):
        completions = registry.get_completions("svc st")
        assert any("status" in c for c in completions)
        assert not any("restart" in c for c in completions)


class TestMiddleware:
    def test_middleware_runs(self, registry):
        log = []
        registry.add_middleware(lambda cat, sub, args, result: (log.append(cat), result)[1])
        registry.dispatch("svc", "status", [])
        assert "svc" in log

    def test_middleware_can_transform_result(self, registry):
        registry.add_middleware(lambda cat, sub, args, result: result.upper())
        result = registry.dispatch("svc", "status", [])
        assert result == "ALL RUNNING"
