# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

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
