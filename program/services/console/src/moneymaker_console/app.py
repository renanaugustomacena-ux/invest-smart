# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Application class — wires registry, renderer, poller, and clients."""

from __future__ import annotations

import os
import platform
import signal
import sys
import time
from pathlib import Path

from moneymaker_console import __version__
from moneymaker_console.commands import discover_and_register
from moneymaker_console.console_logging import init_log_dir, log_event
from moneymaker_console.registry import CommandRegistry
from moneymaker_console.tui.theme import HAS_RICH, get_console

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_CONSOLE_DIR = Path(__file__).resolve().parent.parent.parent  # services/console/
_LOG_DIR = _CONSOLE_DIR / "logs"

# Windows encoding fix
if platform.system() == "Windows":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def _load_dotenv() -> None:
    """Load program/.env if python-dotenv is available."""
    try:
        from dotenv import load_dotenv

        env_file = _CONSOLE_DIR.parent.parent / ".env"  # program/.env
        if env_file.exists():
            load_dotenv(env_file)
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Boot sequence
# ---------------------------------------------------------------------------


def _boot() -> CommandRegistry:
    """Execute the console boot sequence and return a ready registry."""
    # 1. Logging
    init_log_dir(_LOG_DIR)
    log_event("boot_start", version=__version__)

    # 2. Environment
    _load_dotenv()

    # 3. Command registration
    registry = CommandRegistry()
    discover_and_register(registry)

    log_event(
        "boot_complete",
        categories=len(registry.categories),
        commands=registry.command_count,
    )
    return registry


# ---------------------------------------------------------------------------
# TUI Mode
# ---------------------------------------------------------------------------


def _run_tui(registry: CommandRegistry) -> None:
    """Launch the full Rich Live TUI dashboard."""
    from moneymaker_console.poller.status_poller import StatusPoller
    from moneymaker_console.tui.input import InputHandler
    from moneymaker_console.tui.renderer import TUIRenderer

    from moneymaker_console.poller.market_poller import MarketPoller

    con = get_console()
    renderer = TUIRenderer(get_help_fn=registry.get_help)
    poller = StatusPoller()
    poller.start()

    market_poller = MarketPoller()
    market_poller.start()

    cmd_buffer = ""
    cmd_history: list[str] = []
    history_idx = -1
    should_exit = False
    tab_candidates: list[str] = []
    tab_index = -1

    def _sigint(*_):
        nonlocal should_exit
        should_exit = True

    signal.signal(signal.SIGINT, _sigint)

    from rich.live import Live

    with InputHandler() as inp:
        try:
            with Live(
                renderer.build_layout(),
                console=con,
                screen=True,
                auto_refresh=False,
            ) as live:
                while not should_exit:
                    # Update status
                    renderer.update_status(poller.get())
                    renderer.update_market_prices(market_poller.get_prices())
                    renderer.set_cmd_buffer(cmd_buffer)

                    if renderer.is_dirty:
                        live.update(renderer.build_layout())
                        live.refresh()
                        renderer.mark_clean()

                    ch = inp.get_char()
                    if ch is not None:
                        if ch in ("\r", "\n"):
                            if cmd_buffer.strip():
                                result = registry.dispatch_interactive(
                                    cmd_buffer,
                                )
                                if result == "__EXIT__":
                                    should_exit = True
                                    break
                                renderer.set_last_result(result)
                                log_event(
                                    "command",
                                    cmd=cmd_buffer,
                                    result=result[:200],
                                )
                                cmd_history.append(cmd_buffer)
                                history_idx = -1
                            cmd_buffer = ""
                        elif ch in ("\x08", "\x7f"):
                            cmd_buffer = cmd_buffer[:-1]
                        elif ch == "\x03":
                            should_exit = True
                        elif ch == "\x1b":
                            # Escape sequence (arrow keys)
                            ch2 = inp.get_char()
                            if ch2 == "[":
                                ch3 = inp.get_char()
                                if ch3 == "A" and cmd_history:
                                    # Up arrow
                                    if history_idx == -1:
                                        history_idx = len(cmd_history) - 1
                                    elif history_idx > 0:
                                        history_idx -= 1
                                    cmd_buffer = cmd_history[history_idx]
                                elif ch3 == "B" and cmd_history:
                                    # Down arrow
                                    if history_idx < len(cmd_history) - 1:
                                        history_idx += 1
                                        cmd_buffer = cmd_history[history_idx]
                                    else:
                                        history_idx = -1
                                        cmd_buffer = ""
                        elif ch == "\t":
                            # Tab auto-completion
                            completions = registry.get_completions(cmd_buffer)
                            if len(completions) == 1:
                                cmd_buffer = completions[0] + " "
                                tab_candidates = []
                                tab_index = -1
                            elif completions:
                                if tab_candidates == completions:
                                    tab_index = (tab_index + 1) % len(completions)
                                    cmd_buffer = completions[tab_index]
                                else:
                                    tab_candidates = completions
                                    tab_index = 0
                                    cmd_buffer = completions[0]
                        elif ch.isprintable():
                            cmd_buffer += ch
                            tab_candidates = []
                            tab_index = -1

                    time.sleep(1.0 / 8)  # 8 Hz refresh

        finally:
            market_poller.stop()
            poller.stop()

    print("\nMONEYMAKER Console terminated.")


# ---------------------------------------------------------------------------
# CLI Interactive Fallback
# ---------------------------------------------------------------------------


def _run_cli_interactive(registry: CommandRegistry) -> None:
    """Simple readline-based interactive mode (no Rich)."""
    print(f"MONEYMAKER Trading Console v{__version__} (CLI fallback)")
    print("Type 'help' for commands. 'exit' to quit.\n")

    while True:
        try:
            cmd = input("MONEYMAKER> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExit.")
            break

        if not cmd:
            continue

        result = registry.dispatch_interactive(cmd)
        if result == "__EXIT__":
            print("Exit.")
            break
        print(result)
        log_event("command", cmd=cmd, result=result[:200])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """MONEYMAKER Console entry point — mode selection."""
    registry = _boot()

    if len(sys.argv) > 1:
        from moneymaker_console.cli.dispatch import run_cli

        sys.exit(run_cli(registry, sys.argv[1:]))
    else:
        if HAS_RICH:
            _run_tui(registry)
        else:
            _run_cli_interactive(registry)
