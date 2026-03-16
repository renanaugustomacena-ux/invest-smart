"""Shared test fixtures for the MONEYMAKER console."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ package takes priority over the root-level moneymaker_console.py
_console_src = Path(__file__).resolve().parent.parent / "src"
if str(_console_src) not in sys.path:
    sys.path.insert(0, str(_console_src))
# Also remove current dir if it shadows the package
_console_root = str(Path(__file__).resolve().parent.parent)
if _console_root in sys.path:
    sys.path.remove(_console_root)
    sys.path.append(_console_root)

import pytest  # noqa: E402

from moneymaker_console.registry import CommandRegistry  # noqa: E402


@pytest.fixture()
def registry():
    """Return a fresh CommandRegistry with some test commands."""
    reg = CommandRegistry()
    reg.register("svc", "status", lambda: "all running", "Show service status")
    reg.register("svc", "restart", lambda name="all": f"restarted {name}", "Restart a service")
    reg.register("brain", "state", lambda: "brain active", "Show brain state")
    reg.register("exit", "", lambda: "bye", "Exit console", aliases=["q", "quit"])
    return reg
