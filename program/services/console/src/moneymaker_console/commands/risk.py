"""Risk management commands — limits, exposure, circuit breaker, validation."""

from __future__ import annotations

import os
from decimal import Decimal

from moneymaker_console.clients import ClientFactory
from moneymaker_console.registry import CommandRegistry


def _risk_status(*args: str) -> str:
    """Display the complete risk dashboard."""
    db = ClientFactory.get_postgres()
    redis = ClientFactory.get_redis()

    lines = ["Risk Dashboard", "=" * 40]

    # Open positions
    row = db.query_one("SELECT count(*) FROM trade_executions WHERE closed_at IS NULL")
    max_pos = os.environ.get("MAX_POSITION_COUNT", "5")
    open_count = row[0] if row else 0
    lines.append(f"  Open Pos:    {open_count} / {max_pos} max")

    # Daily P&L
    row = db.query_one(
        "SELECT COALESCE(sum(pnl), 0) FROM trade_executions "
        "WHERE closed_at >= CURRENT_DATE"
    )
    daily_pnl = Decimal(str(row[0])) if row else Decimal("0")
    lines.append(f"  Day P&L:     ${daily_pnl:.2f}")

    # Max drawdown
    max_dd = os.environ.get("MAX_DRAWDOWN_PCT", "10.0")
    daily_loss_limit = os.environ.get("MAX_DAILY_LOSS_PCT", "2.0")
    lines.append(f"  Max DD:      {max_dd}% limit")
    lines.append(f"  Daily Loss:  {daily_loss_limit}% limit")

    # Spiral protection
    spiral = redis.get_json("moneymaker:spiral_protection")
    if spiral and spiral.get("active"):
        lines.append(f"  Spiral:      ACTIVE ({spiral.get('consecutive_losses', 0)} consec losses)")
    else:
        lines.append("  Spiral:      INACTIVE")

    # Circuit breaker
    cb = redis.get("moneymaker:circuit_breaker")
    lines.append(f"  Circuit:     [{cb or 'ARMED'}]")

    # Kill switch
    kill = redis.get_json("moneymaker:kill_switch")
    if kill and kill.get("active"):
        lines.append("  Kill Switch: ACTIVE")
    else:
        lines.append("  Kill Switch: INACTIVE")

    return "\n".join(lines)


def _risk_limits(*args: str) -> str:
    """Show all configured risk limits."""
    lines = [
        "Risk Limits",
        "=" * 40,
        f"  Max Drawdown:     {os.environ.get('MAX_DRAWDOWN_PCT', '10.0')}%",
        f"  Max Daily Loss:   {os.environ.get('MAX_DAILY_LOSS_PCT', '2.0')}%",
        f"  Max Positions:    {os.environ.get('MAX_POSITION_COUNT', '5')}",
        f"  Max Lot Size:     {os.environ.get('MAX_LOT_SIZE', '1.0')}",
        f"  Confidence Min:   {os.environ.get('BRAIN_CONFIDENCE_THRESHOLD', '0.65')}",
        f"  Risk per Trade:   {os.environ.get('BRAIN_RISK_PER_TRADE_PCT', '1.0')}%",
        f"  Max Exposure/CCY: {os.environ.get('BRAIN_MAX_EXPOSURE_PER_CURRENCY', '3')}",
        f"  Spiral Threshold: {os.environ.get('BRAIN_SPIRAL_LOSS_THRESHOLD', '3')} losses",
        f"  Spiral Cooldown:  {os.environ.get('BRAIN_SPIRAL_COOLDOWN_MINUTES', '60')} min",
    ]
    return "\n".join(lines)


def _risk_set_max_dd(*args: str) -> str:
    """Set the maximum drawdown percentage."""
    if not args:
        return "[error] Usage: risk set-max-dd <PERCENT>"
    try:
        val = float(args[0])
        if val <= 0 or val > 50:
            return "[error] Drawdown must be between 0 and 50%."
    except ValueError:
        return f"[error] Invalid percentage: {args[0]}"
    return f"[info] Set MAX_DRAWDOWN_PCT={val}% via: config set MAX_DRAWDOWN_PCT {val}"


def _risk_set_max_pos(*args: str) -> str:
    """Set the maximum number of concurrent positions."""
    if not args:
        return "[error] Usage: risk set-max-pos <N>"
    try:
        val = int(args[0])
        if val <= 0 or val > 20:
            return "[error] Position count must be between 1 and 20."
    except ValueError:
        return f"[error] Invalid number: {args[0]}"
    return f"[info] Set MAX_POSITION_COUNT={val} via: config set MAX_POSITION_COUNT {val}"


def _risk_set_max_lot(*args: str) -> str:
    """Set the maximum lot size per trade."""
    if not args:
        return "[error] Usage: risk set-max-lot <SIZE>"
    try:
        val = float(args[0])
        if val <= 0 or val > 10:
            return "[error] Lot size must be between 0 and 10."
    except ValueError:
        return f"[error] Invalid lot size: {args[0]}"
    return f"[info] Set MAX_LOT_SIZE={val} via: config set MAX_LOT_SIZE {val}"


def _risk_set_daily_loss(*args: str) -> str:
    """Set the maximum daily loss percentage."""
    if not args:
        return "[error] Usage: risk set-daily-loss <PERCENT>"
    try:
        val = float(args[0])
        if val <= 0 or val > 20:
            return "[error] Daily loss must be between 0 and 20%."
    except ValueError:
        return f"[error] Invalid percentage: {args[0]}"
    return f"[info] Set MAX_DAILY_LOSS_PCT={val}% via: config set MAX_DAILY_LOSS_PCT {val}"


def _risk_exposure(*args: str) -> str:
    """Display current exposure breakdown."""
    db = ClientFactory.get_postgres()
    rows = db.query_dict(
        "SELECT symbol, direction, sum(quantity) as total_lots, count(*) as positions "
        "FROM trade_executions WHERE closed_at IS NULL "
        "GROUP BY symbol, direction ORDER BY symbol"
    )
    if not rows:
        return "[info] No open exposure."

    lines = ["Exposure Breakdown", "=" * 40]
    for r in rows:
        lines.append(
            f"  {r['symbol']:<10} {r['direction']:<5} "
            f"{r['total_lots']:.2f} lots  ({r['positions']} pos)"
        )
    return "\n".join(lines)


def _risk_correlation(*args: str) -> str:
    """Display cross-symbol correlation matrix."""
    db = ClientFactory.get_postgres()
    rows = db.query(
        "SELECT DISTINCT symbol FROM trade_executions "
        "WHERE closed_at IS NOT NULL AND closed_at > NOW() - INTERVAL '20 days'"
    )
    if not rows:
        return "[info] Not enough data for correlation analysis."

    symbols = [r[0] for r in rows]
    lines = [f"Correlation Matrix ({len(symbols)} symbols)", "=" * 40]
    lines.append("  (Requires sufficient trade history for computation)")
    lines.append(f"  Active symbols: {', '.join(symbols)}")
    return "\n".join(lines)


def _risk_kill_switch(*args: str) -> str:
    """Activate the global kill switch (alias for kill activate)."""
    from moneymaker_console.commands.kill import _kill_activate
    return _kill_activate(*args)


def _risk_circuit_breaker(*args: str) -> str:
    """Control the automatic circuit breaker."""
    redis = ClientFactory.get_redis()
    if args:
        action = args[0].lower()
        if action == "arm":
            redis.set("moneymaker:circuit_breaker", "ARMED")
            return "[success] Circuit breaker ARMED."
        elif action == "disarm":
            redis.set("moneymaker:circuit_breaker", "DISARMED")
            return "[warning] Circuit breaker DISARMED."

    state = redis.get("moneymaker:circuit_breaker") or "ARMED"
    return f"Circuit Breaker: [{state}]"


def _risk_validation(*args: str) -> str:
    """Display the 11-point signal validation checklist."""
    lines = [
        "Signal Validation Checklist (11 points)",
        "=" * 40,
        "  1.  HOLD direction rejection",
        "  2.  Max open positions check",
        "  3.  Max drawdown check",
        "  4.  Daily loss limit check",
        "  5.  Min confidence threshold",
        "  6.  Stop-loss presence & positioning",
        "  7.  Risk/reward ratio",
        "  8.  Margin sufficiency",
        "  9.  Correlation exposure",
        "  10. Economic calendar blackout",
        "  11. Session awareness",
        "",
        "  Run 'signal rejected' to see which checks are blocking signals.",
    ]
    return "\n".join(lines)


def _risk_history(*args: str) -> str:
    """Display risk event history."""
    days = 7
    for i, a in enumerate(args):
        if a == "--days" and i + 1 < len(args):
            try:
                days = int(args[i + 1])
            except ValueError:
                pass

    db = ClientFactory.get_postgres()
    rows = db.query(
        "SELECT symbol, direction, confidence, rejection_reason, created_at "
        "FROM trading_signals "
        "WHERE validation_result = 'rejected' "
        f"AND created_at > NOW() - INTERVAL '{days} days' "
        "ORDER BY created_at DESC LIMIT 20"
    )
    if not rows:
        return f"[info] No rejected signals in last {days} days."

    lines = [f"Risk Events (rejected signals, last {days} days)", "=" * 60]
    for sym, direction, conf, reason, ts in rows:
        lines.append(f"  {ts}  {sym} {direction} conf={conf:.2f}  {reason}")
    return "\n".join(lines)


def _risk_spiral(*args: str) -> str:
    """Display spiral protection status."""
    from moneymaker_console.commands.brain import _brain_spiral
    return _brain_spiral(*args)


def register(registry: CommandRegistry) -> None:
    registry.register("risk", "status", _risk_status, "Risk dashboard")
    registry.register("risk", "limits", _risk_limits, "Current risk limits")
    registry.register("risk", "set-max-dd", _risk_set_max_dd,
                       "Set max drawdown %")
    registry.register("risk", "set-max-pos", _risk_set_max_pos,
                       "Set max concurrent positions")
    registry.register("risk", "set-max-lot", _risk_set_max_lot,
                       "Set max lot size per trade")
    registry.register("risk", "set-daily-loss", _risk_set_daily_loss,
                       "Set max daily loss %")
    registry.register("risk", "exposure", _risk_exposure,
                       "Exposure by symbol/direction")
    registry.register("risk", "correlation", _risk_correlation,
                       "Cross-symbol correlation matrix")
    registry.register("risk", "kill-switch", _risk_kill_switch,
                       "Activate global kill switch",
                       requires_confirmation=True, dangerous=True)
    registry.register("risk", "circuit-breaker", _risk_circuit_breaker,
                       "Circuit breaker [arm|disarm|status]")
    registry.register("risk", "validation", _risk_validation,
                       "11-point validation checklist")
    registry.register("risk", "history", _risk_history,
                       "Rejected signals history [--days N]")
    registry.register("risk", "spiral", _risk_spiral,
                       "Spiral protection status")
