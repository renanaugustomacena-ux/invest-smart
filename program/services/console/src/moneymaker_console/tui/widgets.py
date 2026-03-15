"""Custom Rich renderables: sparklines, progress indicators."""

from __future__ import annotations

from typing import Sequence

# ---------------------------------------------------------------------------
# ASCII Sparkline
# ---------------------------------------------------------------------------

_SPARK_CHARS = " ▁▂▃▄▅▆▇█"


def sparkline(values: Sequence[float], width: int = 20) -> str:
    """Render a sequence of floats as a compact ASCII sparkline.

    Returns a string of *width* block characters representing the values.
    """
    if not values:
        return " " * width

    # Sample / pad to *width*
    sampled: list[float] = []
    n = len(values)
    for i in range(width):
        idx = int(i * n / width)
        sampled.append(values[min(idx, n - 1)])

    lo = min(sampled)
    hi = max(sampled)
    span = hi - lo if hi != lo else 1.0

    chars: list[str] = []
    for v in sampled:
        idx = int((v - lo) / span * (len(_SPARK_CHARS) - 1))
        chars.append(_SPARK_CHARS[idx])
    return "".join(chars)


# ---------------------------------------------------------------------------
# Mini progress bar
# ---------------------------------------------------------------------------


def progress_bar(value: float, total: float, width: int = 20) -> str:
    """Render a simple ASCII progress bar.

    ``value`` / ``total`` determines fill percentage.
    """
    if total <= 0:
        return "[" + " " * width + "]"
    pct = max(0.0, min(1.0, value / total))
    filled = int(pct * width)
    return "[" + "█" * filled + "░" * (width - filled) + f"] {pct:.0%}"


# ---------------------------------------------------------------------------
# Status indicator
# ---------------------------------------------------------------------------


def status_dot(ok: bool) -> str:
    """Return a green or red dot for boolean status."""
    return "● " if ok else "○ "


# ---------------------------------------------------------------------------
# Value coloring helpers (for Rich markup)
# ---------------------------------------------------------------------------


def color_pnl(value: float) -> str:
    """Color a P&L value green (positive) or red (negative)."""
    if value > 0:
        return f"[success]+${value:,.2f}[/success]"
    if value < 0:
        return f"[error]-${abs(value):,.2f}[/error]"
    return "$0.00"


def color_pct(value: float, invert: bool = False) -> str:
    """Color a percentage green/red. *invert* reverses the logic."""
    positive_is_good = not invert
    if (value > 0 and positive_is_good) or (value < 0 and not positive_is_good):
        return f"[success]{value:+.2f}%[/success]"
    if (value < 0 and positive_is_good) or (value > 0 and not positive_is_good):
        return f"[error]{value:+.2f}%[/error]"
    return f"{value:.2f}%"
