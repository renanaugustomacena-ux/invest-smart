# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""TUI renderer with 8-panel Rich Layout and dirty-flag rendering."""

from __future__ import annotations

import datetime
from typing import Any

from moneymaker_console import __version__

try:
    from rich.layout import Layout
    from rich.panel import Panel
except ImportError as _exc:
    raise ImportError(
        "The 'rich' package is required for the TUI renderer. " "Install it with: pip install rich"
    ) from _exc


class TUIRenderer:
    """Renders the 8-panel MONEYMAKER dashboard using Rich Layout.

    Layout structure::

        ┌─────────────────────────────────────────┐
        │               HEADER (3 rows)           │
        ├──────────────────┬──────────────────────┤
        │   MARKET DATA    │      ALGO ENGINE        │
        ├──────────────────┤──────────────────────┤
        │ RISK & POSITIONS │      SYSTEM          │
        ├──────────────────┴──────────────────────┤
        │           COMMAND INTERFACE              │
        └─────────────────────────────────────────┘
    """

    def __init__(self, get_help_fn=None) -> None:
        self._last_result = ""
        self._cmd_buffer = ""
        self._status_cache: dict[str, Any] = {}
        self._market_prices: dict[str, dict[str, Any]] = {}
        self._dirty = True
        self._get_help = get_help_fn

    # -- State setters (called from main loop) ------------------------------

    def update_status(self, cache: dict[str, Any]) -> None:
        if cache != self._status_cache:
            self._status_cache = cache
            self._dirty = True

    def update_market_prices(self, prices: dict[str, dict[str, Any]]) -> None:
        if prices != self._market_prices:
            self._market_prices = prices
            self._dirty = True

    def set_last_result(self, result: str) -> None:
        self._last_result = result
        self._dirty = True

    def set_cmd_buffer(self, buf: str) -> None:
        if buf != self._cmd_buffer:
            self._cmd_buffer = buf
            self._dirty = True

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False

    # -- Layout building ----------------------------------------------------

    def build_layout(self) -> Layout:
        """Build the complete Rich Layout with all panels."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=14),
        )
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )
        layout["left"].split_column(
            Layout(name="market"),
            Layout(name="risk"),
        )
        layout["right"].split_column(
            Layout(name="brain"),
            Layout(name="system"),
        )

        # Header
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c = self._status_cache
        mt5 = c.get("mt5", "UNKNOWN")
        data = c.get("data", "UNKNOWN")
        brain = c.get("brain_state", "UNKNOWN")
        header_text = (
            f"MONEYMAKER TRADING CONSOLE v{__version__}  |  {now}\n"
            f"[MT5: {mt5}]  [Data: {data}]  [Brain: {brain}]"
        )
        layout["header"].update(Panel(header_text, style="bold cyan"))

        # Panels
        layout["market"].update(
            Panel(
                self._market_panel(),
                title="MARKET DATA",
                style="market",
            )
        )
        layout["brain"].update(
            Panel(
                self._brain_panel(),
                title="ALGO ENGINE",
                style="brain",
            )
        )
        layout["risk"].update(
            Panel(
                self._risk_panel(),
                title="RISK & POSITIONS",
                style="risk",
            )
        )
        layout["system"].update(
            Panel(
                self._system_panel(),
                title="SYSTEM",
                style="system",
            )
        )

        # Footer — command interface
        layout["footer"].update(
            Panel(
                self._footer_panel(),
                title="Command",
            )
        )

        return layout

    # -- Panel content ------------------------------------------------------

    def _market_panel(self) -> str:
        c = self._status_cache
        lines = [
            f"  Symbols:   {c.get('symbols', 'N/A')}",
            f"  Regime:    {c.get('regime', 'N/A')}",
            f"  Session:   {c.get('session', 'N/A')}",
        ]
        # Live prices from market poller
        if self._market_prices:
            lines.append("  ─── Live Prices ───")
            for symbol, data in sorted(self._market_prices.items())[:6]:
                last = data.get("last")
                spread = data.get("spread")
                price_str = f"{last:.5f}" if last else "N/A"
                spread_str = f"  sp={spread}" if spread else ""
                lines.append(f"  {symbol:12s} {price_str}{spread_str}")
        else:
            lines.append(f"  Last Tick: {c.get('last_tick', 'N/A')}")
            lines.append(f"  Spread:    {c.get('spread', 'N/A')}")
        return "\n".join(lines)

    def _brain_panel(self) -> str:
        c = self._status_cache
        return (
            f"  State:     {c.get('brain_state', 'N/A')}\n"
            f"  Mode:      {c.get('brain_mode', 'N/A')}\n"
            f"  Epoch:     {c.get('epoch', 'N/A')}\n"
            f"  Loss:      {c.get('loss', 'N/A')}\n"
            f"  LR:        {c.get('lr', 'N/A')}\n"
            f"  Drift:     {c.get('drift', 'N/A')}\n"
            f"  Maturity:  {c.get('maturity', 'N/A')}"
        )

    def _risk_panel(self) -> str:
        c = self._status_cache
        return (
            f"  Open Pos:  {c.get('positions', 'N/A')}\n"
            f"  Exposure:  {c.get('exposure', 'N/A')}\n"
            f"  Day P&L:   {c.get('pnl', 'N/A')}\n"
            f"  Max DD:    {c.get('max_dd', 'N/A')}\n"
            f"  Spiral:    {c.get('spiral', 'INACTIVE')}\n"
            f"  Circuit:   {c.get('circuit', '[ARMED]')}\n"
            f"  Calendar:  {c.get('calendar', 'N/A')}"
        )

    def _system_panel(self) -> str:
        c = self._status_cache
        return (
            f"  CPU:    {c.get('cpu', 'N/A')}\n"
            f"  RAM:    {c.get('ram', 'N/A')}\n"
            f"  GPU:    {c.get('gpu', 'N/A')}\n"
            f"  DB:     {c.get('db', 'N/A')}\n"
            f"  Redis:  {c.get('redis', 'N/A')}\n"
            f"  Disk:   {c.get('disk', 'N/A')}"
        )

    def _footer_panel(self) -> str:
        last_line = ""
        if self._last_result:
            lines = self._last_result.splitlines()
            last_line = lines[-1] if lines else ""
            if len(last_line) > 70:
                last_line = last_line[:67] + "..."

        cmd_ref = self._get_help() if self._get_help else ""
        return f"> Last: {last_line}\n" f"MONEYMAKER> {self._cmd_buffer}_\n\n" f"{cmd_ref}"
