"""Exit command — terminates the console session."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry


def _cmd_exit(*args: str) -> str:
    """Exit the console."""
    return "__EXIT__"


def register(registry: CommandRegistry) -> None:
    registry.register("exit", "", _cmd_exit, "Exit the console")
    # Alias: 'q' and 'quit'
    registry._aliases["q"] = ("exit", "")
    registry._aliases["quit"] = ("exit", "")
