# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Performance analytics commands."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry


def _perf_summary(*args: str) -> str:
    """Comprehensive performance summary."""
    days = int(args[0]) if args else 30
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        row = db.query_one(
            "SELECT count(*) AS total_trades, "
            "sum(pnl) AS total_pnl, "
            "avg(CASE WHEN pnl > 0 THEN pnl END) AS avg_win, "
            "avg(CASE WHEN pnl < 0 THEN pnl END) AS avg_loss, "
            "count(CASE WHEN pnl > 0 THEN 1 END)::float / "
            "  NULLIF(count(*), 0) AS win_rate, "
            "sum(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) / "
            "  NULLIF(abs(sum(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)), 0) AS profit_factor, "
            "max(pnl) AS largest_win, "
            "min(pnl) AS largest_loss "
            "FROM trade_executions "
            "WHERE closed_at IS NOT NULL "
            f"AND closed_at > NOW() - INTERVAL '{days} days'"
        )
        if not row or row[0] == 0:
            return f"No closed trades in the last {days} days."

        def fmt(v, prefix="$", decimals=2):
            if v is None:
                return "N/A"
            return f"{prefix}{v:,.{decimals}f}"

        lines = [
            f"Performance Summary (last {days} days)",
            "=" * 50,
            f"  Total Trades:  {row[0]}",
            f"  Total P&L:     {fmt(row[1])}",
            f"  Avg Win:       {fmt(row[2])}",
            f"  Avg Loss:      {fmt(row[3])}",
            f"  Win Rate:      {row[4]:.1%}" if row[4] else "  Win Rate:      N/A",
            f"  Profit Factor: {row[5]:.2f}" if row[5] else "  Profit Factor: N/A",
            f"  Largest Win:   {fmt(row[6])}",
            f"  Largest Loss:  {fmt(row[7])}",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _perf_daily(*args: str) -> str:
    """Display daily P&L."""
    days = int(args[0]) if args else 14
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT date_trunc('day', closed_at) AS trade_date, "
            "sum(pnl) AS daily_pnl, count(*) AS trades "
            "FROM trade_executions "
            "WHERE closed_at IS NOT NULL "
            f"AND closed_at > NOW() - INTERVAL '{days} days' "
            "GROUP BY trade_date ORDER BY trade_date"
        )
        if not rows:
            return f"No daily data in the last {days} days."
        lines = [f"Daily P&L (last {days} days)", "=" * 50]
        for r in rows:
            pnl = r[1] or 0
            bar = (
                "+" * min(int(abs(pnl) / 10), 20) if pnl >= 0 else "-" * min(int(abs(pnl) / 10), 20)
            )
            sign = "+" if pnl >= 0 else ""
            lines.append(f"  {str(r[0])[:10]}  {sign}${pnl:,.2f}  ({r[2]} trades)  {bar}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _perf_weekly(*args: str) -> str:
    """Display weekly P&L."""
    weeks = int(args[0]) if args else 8
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT date_trunc('week', closed_at) AS week, "
            "sum(pnl) AS weekly_pnl, count(*) AS trades "
            "FROM trade_executions "
            "WHERE closed_at IS NOT NULL "
            f"AND closed_at > NOW() - INTERVAL '{weeks} weeks' "
            "GROUP BY week ORDER BY week"
        )
        if not rows:
            return f"No weekly data in the last {weeks} weeks."
        lines = [f"Weekly P&L (last {weeks} weeks)", "=" * 50]
        cum = 0
        for r in rows:
            pnl = r[1] or 0
            cum += pnl
            sign = "+" if pnl >= 0 else ""
            lines.append(f"  {str(r[0])[:10]}  {sign}${pnl:,.2f}  cum=${cum:,.2f}  ({r[2]} trades)")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _perf_monthly(*args: str) -> str:
    """Display monthly P&L."""
    months = int(args[0]) if args else 6
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT date_trunc('month', closed_at) AS month, "
            "sum(pnl) AS monthly_pnl, count(*) AS trades "
            "FROM trade_executions "
            "WHERE closed_at IS NOT NULL "
            f"AND closed_at > NOW() - INTERVAL '{months} months' "
            "GROUP BY month ORDER BY month"
        )
        if not rows:
            return f"No monthly data in the last {months} months."
        lines = ["Monthly P&L", "=" * 50]
        for r in rows:
            pnl = r[1] or 0
            sign = "+" if pnl >= 0 else ""
            lines.append(f"  {str(r[0])[:7]}  {sign}${pnl:,.2f}  ({r[2]} trades)")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _perf_by_symbol(*args: str) -> str:
    """P&L breakdown by symbol."""
    days = int(args[0]) if args else 30
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT symbol, sum(pnl) AS total, count(*) AS trades, "
            "count(CASE WHEN pnl > 0 THEN 1 END)::float / NULLIF(count(*), 0) AS wr "
            "FROM trade_executions "
            "WHERE closed_at IS NOT NULL "
            f"AND closed_at > NOW() - INTERVAL '{days} days' "
            "GROUP BY symbol ORDER BY total DESC"
        )
        if not rows:
            return "No data."
        lines = [f"P&L by Symbol (last {days} days)", "=" * 60]
        for r in rows:
            wr = f"{r[3]:.0%}" if r[3] is not None else "N/A"
            lines.append(f"  {r[0]:12s}  P&L=${r[1]:,.2f}  trades={r[2]:4d}  WR={wr}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _perf_by_strategy(*args: str) -> str:
    """P&L breakdown by strategy."""
    days = int(args[0]) if args else 30
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT ts.strategy_source, sum(te.pnl) AS total, count(*) AS trades "
            "FROM trade_executions te "
            "JOIN trading_signals ts ON te.signal_id = ts.id "
            "WHERE te.closed_at IS NOT NULL "
            f"AND te.closed_at > NOW() - INTERVAL '{days} days' "
            "GROUP BY ts.strategy_source ORDER BY total DESC"
        )
        if not rows:
            return "No data."
        lines = [f"P&L by Strategy (last {days} days)", "=" * 60]
        for r in rows:
            lines.append(f"  {r[0] or 'unknown':20s}  P&L=${r[1]:,.2f}  trades={r[2]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _perf_by_session(*args: str) -> str:
    """P&L breakdown by trading session."""
    days = int(args[0]) if args else 30
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT "
            "CASE "
            "  WHEN EXTRACT(HOUR FROM opened_at AT TIME ZONE 'UTC') BETWEEN 0 AND 6 THEN 'ASIAN' "
            "  WHEN EXTRACT(HOUR FROM opened_at AT TIME ZONE 'UTC') BETWEEN 7 AND 11 THEN 'LONDON' "
            "  WHEN EXTRACT(HOUR FROM opened_at AT TIME ZONE 'UTC') BETWEEN 12 AND 14 THEN 'OVERLAP' "
            "  WHEN EXTRACT(HOUR FROM opened_at AT TIME ZONE 'UTC') BETWEEN 15 AND 20 THEN 'NEW_YORK' "
            "  ELSE 'OFF_HOURS' "
            "END AS session, "
            "sum(pnl) AS total, count(*) AS trades "
            "FROM trade_executions "
            "WHERE closed_at IS NOT NULL "
            f"AND closed_at > NOW() - INTERVAL '{days} days' "
            "GROUP BY session ORDER BY total DESC"
        )
        if not rows:
            return "No data."
        lines = [f"P&L by Session (last {days} days)", "=" * 50]
        for r in rows:
            lines.append(f"  {r[0]:15s}  P&L=${r[1]:,.2f}  trades={r[2]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _perf_by_regime(*args: str) -> str:
    """P&L breakdown by market regime."""
    days = int(args[0]) if args else 30
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT ts.regime_at_entry, sum(te.pnl) AS total, count(*) AS trades "
            "FROM trade_executions te "
            "JOIN trading_signals ts ON te.signal_id = ts.id "
            "WHERE te.closed_at IS NOT NULL "
            f"AND te.closed_at > NOW() - INTERVAL '{days} days' "
            "GROUP BY ts.regime_at_entry ORDER BY total DESC"
        )
        if not rows:
            return "No data."
        lines = [f"P&L by Regime (last {days} days)", "=" * 50]
        for r in rows:
            lines.append(f"  {r[0] or 'N/A':15s}  P&L=${r[1]:,.2f}  trades={r[2]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _perf_drawdown(*args: str) -> str:
    """Display drawdown curve."""
    days = int(args[0]) if args else 30
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT closed_at, pnl FROM trade_executions "
            "WHERE closed_at IS NOT NULL "
            f"AND closed_at > NOW() - INTERVAL '{days} days' "
            "ORDER BY closed_at"
        )
        if not rows:
            return "No data."
        cum = 0
        peak = 0
        max_dd = 0
        for r in rows:
            cum += r[1] or 0
            if cum > peak:
                peak = cum
            dd = cum - peak
            if dd < max_dd:
                max_dd = dd
        return (
            f"Drawdown Analysis (last {days} days)\n"
            f"{'=' * 40}\n"
            f"  Current equity (cum P&L): ${cum:,.2f}\n"
            f"  Peak equity:              ${peak:,.2f}\n"
            f"  Current drawdown:         ${cum - peak:,.2f}\n"
            f"  Maximum drawdown:         ${max_dd:,.2f}"
        )
    except Exception as exc:
        return f"[error] {exc}"


def _perf_equity(*args: str) -> str:
    """Display equity curve."""
    days = int(args[0]) if args else 30
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT date_trunc('day', closed_at) AS day, sum(pnl) AS daily_pnl "
            "FROM trade_executions "
            "WHERE closed_at IS NOT NULL "
            f"AND closed_at > NOW() - INTERVAL '{days} days' "
            "GROUP BY day ORDER BY day"
        )
        if not rows:
            return "No data."
        from moneymaker_console.tui.widgets import sparkline

        values = []
        cum = 0
        for r in rows:
            cum += r[1] or 0
            values.append(cum)
        chart = sparkline(values)
        return (
            f"Equity Curve (last {days} days)\n"
            f"{'=' * 40}\n"
            f"  {chart}\n"
            f"  Start: $0  End: ${cum:,.2f}"
        )
    except Exception as exc:
        return f"[error] {exc}"


def _perf_trades(*args: str) -> str:
    """List individual trades."""
    days = int(args[0]) if args else 7
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT symbol, direction, volume, entry_price, exit_price, "
            "pnl, commission, opened_at, closed_at "
            "FROM trade_executions "
            "WHERE closed_at IS NOT NULL "
            f"AND closed_at > NOW() - INTERVAL '{days} days' "
            "ORDER BY closed_at DESC LIMIT 30"
        )
        if not rows:
            return f"No trades in the last {days} days."
        lines = [f"Trade Log (last {days} days)", "=" * 90]
        for r in rows:
            pnl = r[5] or 0
            sign = "+" if pnl >= 0 else ""
            lines.append(
                f"  {r[0]:12s} {r[1]:5s} {r[2]:.2f}lot  "
                f"entry={r[3]}  exit={r[4]}  "
                f"P&L={sign}${pnl:,.2f}  {str(r[8])[:16]}"
            )
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _perf_expectancy(*args: str) -> str:
    """Calculate system expectancy."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        row = db.query_one(
            "SELECT "
            "avg(CASE WHEN pnl > 0 THEN pnl END) AS avg_win, "
            "avg(CASE WHEN pnl < 0 THEN pnl END) AS avg_loss, "
            "count(CASE WHEN pnl > 0 THEN 1 END)::float / NULLIF(count(*), 0) AS wr "
            "FROM trade_executions WHERE closed_at IS NOT NULL"
        )
        if not row or row[2] is None:
            return "Not enough data for expectancy calculation."
        wr = row[2]
        avg_w = row[0] or 0
        avg_l = abs(row[1] or 0)
        expectancy = (wr * avg_w) - ((1 - wr) * avg_l)
        return (
            f"System Expectancy\n{'=' * 40}\n"
            f"  Win Rate:      {wr:.1%}\n"
            f"  Avg Win:       ${avg_w:,.2f}\n"
            f"  Avg Loss:      ${avg_l:,.2f}\n"
            f"  Expectancy:    ${expectancy:,.2f} per trade\n"
            f"  {'POSITIVE' if expectancy > 0 else 'NEGATIVE'} edge"
        )
    except Exception as exc:
        return f"[error] {exc}"


def _perf_risk_adjusted(*args: str) -> str:
    """Display risk-adjusted return metrics."""
    return (
        "[info] Risk-adjusted metrics (Sharpe, Sortino, Calmar) require "
        "a full return series calculation.\n"
        "Use 'perf summary' for core metrics or query the database directly."
    )


def _perf_correlation_pnl(*args: str) -> str:
    """Analyze P&L correlation between symbols."""
    return (
        "[info] P&L correlation analysis requires pandas.\n"
        "Use 'perf by-symbol' for per-symbol breakdown."
    )


def register(registry: CommandRegistry) -> None:
    registry.register("perf", "summary", _perf_summary, "Performance summary")
    registry.register("perf", "daily", _perf_daily, "Daily P&L")
    registry.register("perf", "weekly", _perf_weekly, "Weekly P&L")
    registry.register("perf", "monthly", _perf_monthly, "Monthly P&L")
    registry.register("perf", "by-symbol", _perf_by_symbol, "P&L by symbol")
    registry.register("perf", "by-strategy", _perf_by_strategy, "P&L by strategy")
    registry.register("perf", "by-session", _perf_by_session, "P&L by trading session")
    registry.register("perf", "by-regime", _perf_by_regime, "P&L by market regime")
    registry.register("perf", "drawdown", _perf_drawdown, "Drawdown analysis")
    registry.register("perf", "equity", _perf_equity, "Equity curve")
    registry.register("perf", "trades", _perf_trades, "List individual trades")
    registry.register("perf", "expectancy", _perf_expectancy, "System expectancy")
    registry.register("perf", "risk-adjusted", _perf_risk_adjusted, "Risk-adjusted metrics")
    registry.register("perf", "correlation-pnl", _perf_correlation_pnl, "P&L correlation")
