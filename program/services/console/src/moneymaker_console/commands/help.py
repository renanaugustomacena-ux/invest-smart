# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Help command — displays command reference."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry

_registry: CommandRegistry | None = None


def _cmd_help(*args: str) -> str:
    """Show command reference."""
    if _registry is None:
        return "[error] Registry not initialized."
    if args:
        category = args[0].lower()
        detailed = _registry.get_detailed_help(category)
        if detailed.strip():
            return detailed
        return f"[error] Unknown category '{category}'."
    return (
        f"MONEYMAKER Trading Console — Command Reference\n"
        f"Commands: {_registry.command_count} across "
        f"{len(_registry.categories)} categories\n\n"
        f"{_registry.get_help()}\n\n"
        f"Type 'help <category>' for details. 'exit' to quit."
    )


def register(registry: CommandRegistry) -> None:
    global _registry
    _registry = registry
    registry.register("help", "", _cmd_help, "Show command reference")
