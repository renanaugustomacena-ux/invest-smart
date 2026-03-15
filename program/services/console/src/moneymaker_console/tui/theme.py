"""Rich theme definitions for the MONEYMAKER console."""

from __future__ import annotations

try:
    from rich.console import Console
    from rich.theme import Theme

    MONEYMAKER_THEME = Theme(
        {
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "bold green",
            "brain": "bold magenta",
            "market": "bold blue",
            "risk": "bold yellow",
            "system": "dim white",
            "kill": "bold red",
            "signal": "bold cyan",
        }
    )

    _console = Console(theme=MONEYMAKER_THEME)
    HAS_RICH = True
except ImportError:
    MONEYMAKER_THEME = None  # type: ignore[assignment]
    _console = None  # type: ignore[assignment]
    HAS_RICH = False


def get_console() -> Console:
    """Return the themed Rich Console singleton."""
    return _console
