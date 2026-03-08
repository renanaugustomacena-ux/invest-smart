"""MT5 Bridge commands — positions, execution, trailing stops, rate limiting."""

from __future__ import annotations

import os
from decimal import Decimal

from moneymaker_console.clients import ClientFactory
from moneymaker_console.registry import CommandRegistry


_MAGIC_DEFAULT = 123456


def _unavail() -> str:
    return "[warning] MT5 Bridge not available. Start with: svc up mt5-bridge"


def _mt5_connect(*args: str) -> str:
    """Initialize connection to MetaTrader 5."""
    docker = ClientFactory.get_docker()
    return docker.restart("mt5-bridge")


def _mt5_disconnect(*args: str) -> str:
    """Gracefully disconnect from MT5."""
    docker = ClientFactory.get_docker()
    from moneymaker_console.runner import run_tool, _PROJECT_ROOT, _DOCKER_COMPOSE
    return run_tool(
        ["docker", "compose", "-f", str(_DOCKER_COMPOSE), "stop", "mt5-bridge"],
        cwd=_PROJECT_ROOT,
    )


def _mt5_status(*args: str) -> str:
    """Display MT5 connection status."""
    mt5 = ClientFactory.get_mt5()
    health = mt5.check_health()
    if health:
        return (
            f"MT5 Bridge Status\n"
            f"{'=' * 40}\n"
            f"  Status:      {health.get('status', 'UNKNOWN')}\n"
            f"  Message:     {health.get('message', '')}\n"
            f"  Uptime:      {health.get('uptime_seconds', 0):.0f}s"
        )

    # DB fallback
    db = ClientFactory.get_postgres()
    if not db.ping():
        return _unavail()

    row = db.query_one(
        "SELECT count(*) FROM trade_executions "
        "WHERE closed_at IS NULL"
    )
    open_count = row[0] if row else 0
    return (
        f"MT5 Bridge Status (from DB — gRPC unreachable)\n"
        f"{'=' * 40}\n"
        f"  gRPC:        NOT CONNECTED\n"
        f"  Open Pos:    {open_count} (from DB)"
    )


def _mt5_positions(*args: str) -> str:
    """List all open positions."""
    symbol_filter = None
    for i, a in enumerate(args):
        if a == "--symbol" and i + 1 < len(args):
            symbol_filter = args[i + 1].upper()

    db = ClientFactory.get_postgres()
    if not db.ping():
        return _unavail()

    where = "WHERE te.closed_at IS NULL"
    params: tuple = ()
    if symbol_filter:
        where += " AND te.symbol = %s"
        params = (symbol_filter,)

    rows = db.query_dict(
        f"SELECT te.order_id, te.symbol, te.direction, te.quantity, "
        f"te.executed_price, te.stop_loss, te.take_profit, "
        f"te.commission, te.swap, te.opened_at "
        f"FROM trade_executions te "
        f"{where} ORDER BY te.opened_at DESC",
        params,
    )

    if not rows:
        return "[info] No open positions."

    lines = ["Open Positions", "=" * 60]
    for r in rows:
        lines.append(
            f"  #{r['order_id']}  {r['symbol']}  {r['direction']}  "
            f"{r['quantity']} lots  @{r['executed_price']}  "
            f"SL={r['stop_loss']}  TP={r['take_profit']}"
        )
    lines.append(f"\n  Total: {len(rows)} positions")
    return "\n".join(lines)


def _mt5_history(*args: str) -> str:
    """Display trade history."""
    days = 7
    symbol_filter = None
    for i, a in enumerate(args):
        if a == "--days" and i + 1 < len(args):
            try:
                days = int(args[i + 1])
            except ValueError:
                pass
        if a == "--symbol" and i + 1 < len(args):
            symbol_filter = args[i + 1].upper()

    db = ClientFactory.get_postgres()
    if not db.ping():
        return _unavail()

    where = f"WHERE te.closed_at IS NOT NULL AND te.closed_at > NOW() - INTERVAL '{days} days'"
    params: tuple = ()
    if symbol_filter:
        where += " AND te.symbol = %s"
        params = (symbol_filter,)

    rows = db.query_dict(
        f"SELECT te.order_id, te.symbol, te.direction, te.quantity, "
        f"te.executed_price, te.pnl, te.commission, te.swap, "
        f"te.opened_at, te.closed_at "
        f"FROM trade_executions te "
        f"{where} ORDER BY te.closed_at DESC LIMIT 50",
        params,
    )

    if not rows:
        return f"[info] No closed trades in last {days} days."

    lines = [f"Trade History (last {days} days)", "=" * 60]
    total_pnl = Decimal("0")
    for r in rows:
        pnl = Decimal(str(r.get("pnl", 0)))
        total_pnl += pnl
        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        lines.append(
            f"  #{r['order_id']}  {r['symbol']}  {r['direction']}  "
            f"{r['quantity']} lots  P&L: {pnl_str}"
        )
    lines.append(f"\n  Total P&L: ${total_pnl:.2f}  ({len(rows)} trades)")
    return "\n".join(lines)


def _mt5_close(*args: str) -> str:
    """Close a specific position by ticket."""
    if not args:
        return "[error] Usage: mt5 close <TICKET>"
    return f"[info] Close ticket #{args[0]} — requires gRPC connection to MT5 Bridge."


def _mt5_close_all(*args: str) -> str:
    """Close ALL open positions."""
    return "[info] Close all positions — requires gRPC connection to MT5 Bridge."


def _mt5_modify(*args: str) -> str:
    """Modify SL/TP of a position."""
    if not args:
        return "[error] Usage: mt5 modify <TICKET> --sl <SL> --tp <TP>"
    return f"[info] Modify ticket #{args[0]} — requires gRPC connection."


def _mt5_account(*args: str) -> str:
    """Display full account information."""
    lines = [
        "MT5 Account",
        "=" * 40,
        f"  Account:   {os.environ.get('MT5_ACCOUNT', 'NOT SET')}",
        f"  Server:    {os.environ.get('MT5_SERVER', 'NOT SET')}",
        f"  Magic:     {os.environ.get('MT5_MAGIC_NUMBER', str(_MAGIC_DEFAULT))}",
    ]
    # Get equity from DB
    db = ClientFactory.get_postgres()
    equity = os.environ.get("BRAIN_DEFAULT_EQUITY", "1000")
    leverage = os.environ.get("BRAIN_DEFAULT_LEVERAGE", "100")
    lines.extend([
        f"  Equity:    ${equity}",
        f"  Leverage:  1:{leverage}",
    ])
    return "\n".join(lines)


def _mt5_sync(*args: str) -> str:
    """Force sync between MT5 and MONEYMAKER database."""
    redis = ClientFactory.get_redis()
    if redis.publish("moneymaker:mt5:commands", "sync"):
        return "[success] Sync command sent to MT5 Bridge."
    return "[warning] Could not send sync command — Redis not available."


def _mt5_orders(*args: str) -> str:
    """List pending orders."""
    db = ClientFactory.get_postgres()
    rows = db.query_dict(
        "SELECT order_id, symbol, direction, quantity, requested_price, "
        "status, created_at FROM trade_executions "
        "WHERE status = 'PENDING' ORDER BY created_at DESC LIMIT 20"
    )
    if not rows:
        return "[info] No pending orders."

    lines = ["Pending Orders", "=" * 40]
    for r in rows:
        lines.append(
            f"  #{r['order_id']}  {r['symbol']}  {r['direction']}  "
            f"{r['quantity']} lots  @{r['requested_price']}"
        )
    return "\n".join(lines)


def _mt5_autotrading(*args: str) -> str:
    """Enable, disable, or check autotrading."""
    redis = ClientFactory.get_redis()
    if args and args[0].lower() in ("on", "off"):
        val = args[0].lower() == "on"
        redis.set("moneymaker:autotrading_enabled", str(val).lower())
        return f"[success] Autotrading {'ENABLED' if val else 'DISABLED'}."

    val = redis.get("moneymaker:autotrading_enabled")
    enabled = val is None or val.lower() == "true"
    return f"Autotrading: {'ENABLED' if enabled else 'DISABLED'}"


def _mt5_trailing(*args: str) -> str:
    """View or toggle trailing stop system."""
    enabled = os.environ.get("TRAILING_STOP_ENABLED", "true").lower() == "true"
    pips = os.environ.get("TRAILING_STOP_PIPS", "50.0")
    activation = os.environ.get("TRAILING_ACTIVATION_PIPS", "30")

    if args and args[0].lower() in ("on", "off"):
        return f"[info] Set TRAILING_STOP_ENABLED via: config set TRAILING_STOP_ENABLED {args[0].lower() == 'on'}"

    return (
        f"Trailing Stop Configuration\n"
        f"{'=' * 40}\n"
        f"  Enabled:     {enabled}\n"
        f"  Distance:    {pips} pips\n"
        f"  Activation:  {activation} pips profit"
    )


def _mt5_trailing_config(*args: str) -> str:
    """Configure trailing stop parameters."""
    lines = ["Current Trailing Stop Config:"]
    lines.append(f"  TRAILING_STOP_PIPS = {os.environ.get('TRAILING_STOP_PIPS', '50.0')}")
    lines.append(f"  TRAILING_ACTIVATION_PIPS = {os.environ.get('TRAILING_ACTIVATION_PIPS', '30')}")
    lines.append("\nModify via: config set TRAILING_STOP_PIPS <value>")
    return "\n".join(lines)


def _mt5_rate_limit(*args: str) -> str:
    """View or configure rate limiting for trade execution."""
    redis = ClientFactory.get_redis()
    max_per_min = os.environ.get("SIGNAL_MAX_PER_MINUTE", "10")
    burst = os.environ.get("SIGNAL_BURST", "5")

    if args and args[0].lower() == "set":
        return "[info] Configure via: config set SIGNAL_MAX_PER_MINUTE <N>"

    info = redis.get_json("moneymaker:rate_limit:state")
    current = info.get("current", 0) if info else 0

    return (
        f"Rate Limiting\n"
        f"{'=' * 40}\n"
        f"  Max/min:     {max_per_min}\n"
        f"  Burst:       {burst}\n"
        f"  Current:     {current} trades this minute"
    )


def register(registry: CommandRegistry) -> None:
    registry.register("mt5", "connect", _mt5_connect, "Connect to MT5 terminal")
    registry.register("mt5", "disconnect", _mt5_disconnect, "Disconnect from MT5")
    registry.register("mt5", "status", _mt5_status, "MT5 connection status")
    registry.register("mt5", "positions", _mt5_positions,
                       "Open positions [--symbol S]")
    registry.register("mt5", "history", _mt5_history,
                       "Trade history [--days N] [--symbol S]")
    registry.register("mt5", "close", _mt5_close, "Close position by ticket",
                       requires_confirmation=True)
    registry.register("mt5", "close-all", _mt5_close_all,
                       "Close ALL positions",
                       requires_confirmation=True, dangerous=True)
    registry.register("mt5", "modify", _mt5_modify, "Modify SL/TP",
                       requires_confirmation=True)
    registry.register("mt5", "account", _mt5_account, "Account information")
    registry.register("mt5", "sync", _mt5_sync, "Force database sync")
    registry.register("mt5", "orders", _mt5_orders, "Pending orders")
    registry.register("mt5", "autotrading", _mt5_autotrading,
                       "Autotrading [on|off|status]")
    registry.register("mt5", "trailing", _mt5_trailing,
                       "Trailing stop [on|off|status]")
    registry.register("mt5", "trailing-config", _mt5_trailing_config,
                       "Trailing stop parameters")
    registry.register("mt5", "rate-limit", _mt5_rate_limit,
                       "Rate limiting [view|set]")
