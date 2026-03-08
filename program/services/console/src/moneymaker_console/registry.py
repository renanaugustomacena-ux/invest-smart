"""Command registry with dispatch, aliases, and middleware support."""

from __future__ import annotations

import signal
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

# Default command timeout in seconds.  Long-running operations (build, test,
# backup) use per-command overrides; everything else gets this safety net.
_DEFAULT_TIMEOUT_SEC = 60

from moneymaker_console.console_logging import log_event


# ---------------------------------------------------------------------------
# Command dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Command:
    """A single registered console command."""

    handler: Callable[..., str]
    help_text: str
    category: str
    aliases: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    dangerous: bool = False
    hidden: bool = False
    timeout_sec: int = _DEFAULT_TIMEOUT_SEC


# ---------------------------------------------------------------------------
# CommandRegistry
# ---------------------------------------------------------------------------

class CommandRegistry:
    """Central dispatch table mapping (category, subcmd) to Command objects.

    Supports middleware, aliases, and auto-discovery of command modules.
    """

    def __init__(self) -> None:
        self._commands: dict[str, dict[str, Command]] = {}
        self._aliases: dict[str, tuple[str, str]] = {}
        self._middleware: list[Callable] = []
        self._confirm_fn: Callable[[str], bool] | None = None

    # -- Confirmation -------------------------------------------------------

    def set_confirmation_handler(self, fn: Callable[[str], bool]) -> None:
        """Set the callback used to confirm dangerous commands.

        *fn* receives a human-readable label (e.g. ``"kill activate [!]"``)
        and must return ``True`` to proceed or ``False`` to abort.
        """
        self._confirm_fn = fn

    # -- Registration -------------------------------------------------------

    def register(
        self,
        category: str,
        name: str,
        handler: Callable[..., str],
        help_text: str,
        *,
        aliases: list[str] | None = None,
        requires_confirmation: bool = False,
        dangerous: bool = False,
        hidden: bool = False,
        timeout_sec: int = _DEFAULT_TIMEOUT_SEC,
    ) -> None:
        """Register a command under *category* / *name*."""
        if category not in self._commands:
            self._commands[category] = {}
        cmd = Command(
            handler=handler,
            help_text=help_text,
            category=category,
            aliases=aliases or [],
            requires_confirmation=requires_confirmation,
            dangerous=dangerous,
            hidden=hidden,
            timeout_sec=timeout_sec,
        )
        self._commands[category][name] = cmd

        # Register aliases
        for alias in cmd.aliases:
            self._aliases[alias] = (category, name)

    # -- Middleware ----------------------------------------------------------

    def add_middleware(self, fn: Callable) -> None:
        """Add a middleware function that wraps every command execution.

        Signature: ``fn(category, subcmd, args, result) -> result``
        """
        self._middleware.append(fn)

    # -- Dispatch -----------------------------------------------------------

    def dispatch(self, category: str, subcmd: str, args: list[str]) -> str:
        """Execute a command by category and sub-command."""
        if category not in self._commands:
            return f"[error] Unknown category '{category}'. Type 'help'."
        cmds = self._commands[category]
        if subcmd not in cmds:
            available = ", ".join(sorted(k for k in cmds if k))
            return (
                f"[error] Unknown sub-command '{subcmd}' in '{category}'. "
                f"Available: {available}"
            )

        cmd = cmds[subcmd]

        # -- Confirmation gate for dangerous / requires_confirmation --------
        if cmd.requires_confirmation:
            label = f"{category} {subcmd}"
            if cmd.dangerous:
                label += " [!] DANGEROUS"
            if self._confirm_fn is not None:
                if not self._confirm_fn(label):
                    log_event(
                        "dispatch_cancelled",
                        category=category,
                        subcmd=subcmd,
                    )
                    return f"[cancelled] {category} {subcmd} — aborted by operator."
            else:
                # No confirmation handler — refuse to execute
                return (
                    f"[error] {category} {subcmd} requires confirmation "
                    "but no confirmation handler is configured."
                )

        start = time.monotonic()
        try:
            # Enforce per-command timeout (Unix only; on Windows signal.SIGALRM
            # is unavailable, so commands run without a hard timeout).
            _prev_handler = None
            if hasattr(signal, "SIGALRM") and cmd.timeout_sec > 0:

                def _timeout_handler(signum: int, frame: Any) -> None:
                    raise TimeoutError(
                        f"{category} {subcmd} timed out after {cmd.timeout_sec}s"
                    )

                _prev_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(cmd.timeout_sec)

            try:
                result = cmd.handler(*args)
            finally:
                if _prev_handler is not None:
                    signal.alarm(0)  # Cancel pending alarm
                    signal.signal(signal.SIGALRM, _prev_handler)
        except TimeoutError as te:
            log_event(
                "dispatch_timeout",
                category=category,
                subcmd=subcmd,
                timeout_sec=cmd.timeout_sec,
            )
            result = f"[timeout] {te}"
        except Exception as exc:
            log_event(
                "dispatch_error",
                category=category,
                subcmd=subcmd,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            result = f"[error] {category} {subcmd}: {exc}"

        elapsed_ms = (time.monotonic() - start) * 1000
        log_event(
            "dispatch_ok",
            category=category,
            subcmd=subcmd,
            duration_ms=round(elapsed_ms, 1),
        )

        # Run middleware
        for mw in self._middleware:
            try:
                result = mw(category, subcmd, args, result)
            except Exception as mw_exc:
                log_event(
                    "middleware_error",
                    middleware=getattr(mw, "__name__", repr(mw)),
                    error=str(mw_exc),
                )

        return result

    def dispatch_interactive(self, cmd_line: str) -> str:
        """Dispatch from an interactive command line (TUI or CLI fallback).

        Supports:
        - 'category subcmd args...'
        - Single-word commands registered under empty sub-command ''
        - Alias resolution
        """
        parts = cmd_line.strip().split()
        if not parts:
            return ""

        token = parts[0].lower()

        # Check alias first (e.g., 'q' -> ('exit', ''))
        if token in self._aliases:
            cat, sub = self._aliases[token]
            return self.dispatch(cat, sub, parts[1:])

        category = token

        # Single-word commands (registered with subcmd='')
        if category in self._commands and "" in self._commands[category]:
            return self.dispatch(category, "", parts[1:])

        subcmd = parts[1].lower() if len(parts) > 1 else ""
        args = parts[2:]

        # Check if subcmd is an alias
        full_alias = f"{category} {subcmd}".strip()
        if full_alias in self._aliases:
            cat, sub = self._aliases[full_alias]
            return self.dispatch(cat, sub, args)

        if not subcmd and category in self._commands:
            if "" in self._commands[category]:
                return self.dispatch(category, "", [])
            available = ", ".join(sorted(k for k in self._commands[category] if k))
            return f"Sub-commands for '{category}': {available}"

        return self.dispatch(category, subcmd, args)

    # -- Help ---------------------------------------------------------------

    def get_help(self, category: str | None = None) -> str:
        """Generate a human-readable command reference."""
        lines: list[str] = []
        cats = [category] if category else sorted(self._commands.keys())
        for cat in cats:
            if cat not in self._commands:
                continue
            cmds = self._commands[cat]
            subcmds = " | ".join(
                name for name in sorted(cmds.keys())
                if name and not cmds[name].hidden
            )
            if subcmds:
                lines.append(f"  {cat:<12} {subcmds}")
        return "\n".join(lines)

    def get_detailed_help(self, category: str | None = None) -> str:
        """Generate detailed help with descriptions for each command."""
        lines: list[str] = []
        cats = [category] if category else sorted(self._commands.keys())
        for cat in cats:
            if cat not in self._commands:
                continue
            lines.append(f"\n  [{cat.upper()}]")
            for name in sorted(self._commands[cat].keys()):
                if not name:
                    continue
                cmd = self._commands[cat][name]
                if cmd.hidden:
                    continue
                danger = " [!]" if cmd.dangerous else ""
                lines.append(f"    {cat} {name:<20} {cmd.help_text}{danger}")
        return "\n".join(lines)

    # -- Auto-completion ----------------------------------------------------

    def get_completions(self, partial: str) -> list[str]:
        """Return possible completions for a partial command string."""
        parts = partial.strip().split()

        if not parts or (len(parts) == 1 and not partial.endswith(" ")):
            # Completing category name
            prefix = parts[0].lower() if parts else ""
            return [c for c in sorted(self._commands) if c.startswith(prefix)]

        category = parts[0].lower()
        if category not in self._commands:
            return []

        if len(parts) == 1 and partial.endswith(" "):
            # Category typed, show all sub-commands
            return [
                f"{category} {name}"
                for name in sorted(self._commands[category])
                if name
            ]

        # Completing sub-command
        sub_prefix = parts[1].lower() if len(parts) > 1 else ""
        return [
            f"{category} {name}"
            for name in sorted(self._commands[category])
            if name and name.startswith(sub_prefix)
        ]

    # -- Properties ---------------------------------------------------------

    @property
    def categories(self) -> list[str]:
        return sorted(self._commands.keys())

    @property
    def command_count(self) -> int:
        return sum(
            len([n for n in cmds if n])
            for cmds in self._commands.values()
        )
