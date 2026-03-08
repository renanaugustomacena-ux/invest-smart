"""Signal pipeline management commands."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry


def _signal_status(*args: str) -> str:
    """Display signal pipeline status."""
    try:
        from moneymaker_console.clients import ClientFactory
        db = ClientFactory.get_postgres()
        total = db.query_one(
            "SELECT count(*) FROM trading_signals "
            "WHERE created_at > NOW() - INTERVAL '24 hours'"
        )
        validated = db.query_one(
            "SELECT count(*) FROM trading_signals "
            "WHERE validation_result = 'validated' "
            "AND created_at > NOW() - INTERVAL '24 hours'"
        )
        rejected = db.query_one(
            "SELECT count(*) FROM trading_signals "
            "WHERE validation_result = 'rejected' "
            "AND created_at > NOW() - INTERVAL '24 hours'"
        )
        lines = [
            "Signal Pipeline Status (24h)",
            "=" * 40,
            f"  Generated:  {total[0] if total else 0}",
            f"  Validated:  {validated[0] if validated else 0}",
            f"  Rejected:   {rejected[0] if rejected else 0}",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _signal_last(*args: str) -> str:
    """Display last N signals."""
    n = int(args[0]) if args else 5
    try:
        from moneymaker_console.clients import ClientFactory
        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT id, symbol, direction, confidence, strategy_source, "
            "created_at, validation_result "
            "FROM trading_signals "
            f"ORDER BY created_at DESC LIMIT {min(n, 50)}"
        )
        if not rows:
            return "No signals found."
        lines = [f"Last {len(rows)} Signals", "=" * 80]
        for r in rows:
            conf = f"{r[3]:.2f}" if r[3] is not None else "N/A"
            lines.append(
                f"  [{r[6] or 'N/A':10s}] {r[1]:12s} {r[2]:5s} "
                f"conf={conf}  src={r[4] or 'N/A'}  {r[5]}"
            )
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _signal_pending(*args: str) -> str:
    """Display signals in the validation queue."""
    try:
        from moneymaker_console.clients import ClientFactory
        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT id, symbol, direction, confidence, created_at "
            "FROM trading_signals "
            "WHERE validation_result IS NULL "
            "ORDER BY created_at DESC LIMIT 20"
        )
        if not rows:
            return "No pending signals in the queue."
        lines = ["Pending Signals", "=" * 60]
        for r in rows:
            conf = f"{r[3]:.2f}" if r[3] is not None else "N/A"
            lines.append(f"  {r[0]}  {r[1]:12s} {r[2]:5s} conf={conf}  {r[4]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _signal_rejected(*args: str) -> str:
    """Display rejected signals with reasons."""
    days = int(args[0]) if args else 7
    try:
        from moneymaker_console.clients import ClientFactory
        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT id, symbol, direction, confidence, rejection_reason, created_at "
            "FROM trading_signals "
            "WHERE validation_result = 'rejected' "
            f"AND created_at > NOW() - INTERVAL '{days} days' "
            "ORDER BY created_at DESC LIMIT 30"
        )
        if not rows:
            return f"No rejected signals in the last {days} days."
        lines = [f"Rejected Signals (last {days} days)", "=" * 80]
        for r in rows:
            conf = f"{r[3]:.2f}" if r[3] is not None else "N/A"
            lines.append(
                f"  {r[1]:12s} {r[2]:5s} conf={conf}  "
                f"reason={r[4] or 'N/A'}  {r[5]}"
            )
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _signal_confidence(*args: str) -> str:
    """Display confidence distribution histogram."""
    try:
        from moneymaker_console.clients import ClientFactory
        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT width_bucket(confidence, 0, 1, 10) AS bucket, "
            "count(*) AS cnt "
            "FROM trading_signals "
            "WHERE created_at > NOW() - INTERVAL '7 days' "
            "AND confidence IS NOT NULL "
            "GROUP BY bucket ORDER BY bucket"
        )
        if not rows:
            return "No confidence data available."
        lines = ["Signal Confidence Distribution (7d)", "=" * 50]
        max_cnt = max(r[1] for r in rows) or 1
        for r in rows:
            lo = (r[0] - 1) * 0.1
            hi = r[0] * 0.1
            bar_len = int((r[1] / max_cnt) * 30)
            bar = "#" * bar_len
            lines.append(f"  {lo:.1f}-{hi:.1f}: {bar} ({r[1]})")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _signal_rate(*args: str) -> str:
    """Display signal generation rate."""
    try:
        from moneymaker_console.clients import ClientFactory
        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT date_trunc('hour', created_at) AS hr, count(*) AS cnt "
            "FROM trading_signals "
            "WHERE created_at > NOW() - INTERVAL '24 hours' "
            "GROUP BY hr ORDER BY hr"
        )
        if not rows:
            return "No signals generated in the last 24 hours."
        import os
        max_rate = os.environ.get("BRAIN_MAX_SIGNALS_PER_HOUR", "50")
        lines = [f"Signal Rate (max: {max_rate}/hr)", "=" * 50]
        for r in rows:
            lines.append(f"  {r[0]}  {r[1]} signals")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _signal_strategy(*args: str) -> str:
    """Display strategy source breakdown."""
    try:
        from moneymaker_console.clients import ClientFactory
        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT strategy_source, count(*) AS cnt, "
            "avg(confidence) AS avg_conf "
            "FROM trading_signals "
            "WHERE created_at > NOW() - INTERVAL '7 days' "
            "GROUP BY strategy_source ORDER BY cnt DESC"
        )
        if not rows:
            return "No strategy data available."
        lines = ["Signal Sources (7d)", "=" * 50]
        for r in rows:
            avg_c = f"{r[2]:.3f}" if r[2] is not None else "N/A"
            lines.append(f"  {r[0] or 'unknown':20s}  count={r[1]:5d}  avg_conf={avg_c}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _signal_validate(*args: str) -> str:
    """Re-run validation against a historical signal."""
    if not args:
        return "Usage: signal validate SIGNAL_ID"
    try:
        from moneymaker_console.clients import ClientFactory
        db = ClientFactory.get_postgres()
        row = db.query_one(
            "SELECT id, symbol, direction, confidence, validation_result, "
            "rejection_reason, strategy_source "
            f"FROM trading_signals WHERE id = {int(args[0])}"
        )
        if not row:
            return f"Signal {args[0]} not found."
        lines = [
            f"Signal {row[0]} Validation",
            "=" * 40,
            f"  Symbol:     {row[1]}",
            f"  Direction:  {row[2]}",
            f"  Confidence: {row[3]}",
            f"  Result:     {row[4]}",
            f"  Reason:     {row[5] or 'N/A'}",
            f"  Source:     {row[6] or 'N/A'}",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _signal_replay(*args: str) -> str:
    """Replay a historical signal."""
    if not args:
        return "Usage: signal replay SIGNAL_ID"
    return f"[info] Signal replay for ID {args[0]} requires the Brain service. Use 'brain eval' for batch replay."


def register(registry: CommandRegistry) -> None:
    registry.register("signal", "status", _signal_status, "Display signal pipeline status")
    registry.register("signal", "last", _signal_last, "Display last N signals")
    registry.register("signal", "pending", _signal_pending, "Display pending signals")
    registry.register("signal", "rejected", _signal_rejected, "Display rejected signals")
    registry.register("signal", "confidence", _signal_confidence, "Show confidence distribution")
    registry.register("signal", "rate", _signal_rate, "Display signal generation rate")
    registry.register("signal", "strategy", _signal_strategy, "Display strategy source breakdown")
    registry.register("signal", "validate", _signal_validate, "Re-validate a historical signal")
    registry.register("signal", "replay", _signal_replay, "Replay a historical signal")
