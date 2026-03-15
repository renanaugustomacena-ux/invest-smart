"""Auto-discovery of command modules.

Each .py file in this package must export a ``register(registry)`` function
that registers its commands with the CommandRegistry.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from moneymaker_console.registry import CommandRegistry


def discover_and_register(registry: CommandRegistry) -> None:
    """Import all command modules in this package and call register()."""
    package_dir = Path(__file__).parent

    for finder, name, _ispkg in pkgutil.iter_modules([str(package_dir)]):
        try:
            module = importlib.import_module(f"moneymaker_console.commands.{name}")
            if hasattr(module, "register"):
                module.register(registry)
        except Exception as exc:
            # Never crash on a bad command module — log and skip
            from moneymaker_console.console_logging import log_event

            log_event("command_discovery_error", module=name, error=str(exc))
