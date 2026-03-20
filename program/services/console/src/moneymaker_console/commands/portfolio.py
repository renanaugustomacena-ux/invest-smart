# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Portfolio management commands."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry


def _portfolio_overview(*args: str) -> str:
    """Display current portfolio overview."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        row = db.query_one(
            "SELECT count(*) AS positions, "
            "sum(volume) AS total_volume, "
            "sum(pnl) AS open_pnl "
            "FROM trade_executions "
            "WHERE closed_at IS NULL"
        )
        if not row or row[0] == 0:
            return "No open positions."
        return (
            f"Portfolio Overview\n{'=' * 40}\n"
            f"  Open Positions: {row[0]}\n"
            f"  Total Volume:   {row[1]:.2f} lots\n"
            f"  Open P&L:       ${row[2]:,.2f}"
            if row[2]
            else f"Portfolio Overview\n{'=' * 40}\n"
            f"  Open Positions: {row[0]}\n"
            f"  Total Volume:   {row[1] or 0:.2f} lots\n"
            f"  Open P&L:       N/A"
        )
    except Exception as exc:
        return f"[error] {exc}"


def _portfolio_allocation(*args: str) -> str:
    """Display capital allocation by symbol."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT symbol, direction, sum(volume) AS vol, count(*) AS cnt "
            "FROM trade_executions WHERE closed_at IS NULL "
            "GROUP BY symbol, direction ORDER BY vol DESC"
        )
        if not rows:
            return "No open positions for allocation analysis."
        lines = ["Portfolio Allocation", "=" * 50]
        for r in rows:
            lines.append(f"  {r[0]:12s} {r[1]:5s}  {r[2]:.2f} lots  ({r[3]} pos)")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _portfolio_heat_map(*args: str) -> str:
    """Display ASCII heat map of position P&L."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT symbol, pnl FROM trade_executions " "WHERE closed_at IS NULL ORDER BY symbol"
        )
        if not rows:
            return "No open positions."
        lines = ["Position Heat Map", "=" * 40]
        for r in rows:
            pnl = r[1] or 0
            color = "+" if pnl >= 0 else "-"
            bar_len = min(int(abs(pnl) / 5), 20)
            bar = color * bar_len
            lines.append(f"  {r[0]:12s}  ${pnl:>10,.2f}  {bar}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _portfolio_optimize(*args: str) -> str:
    """Suggest portfolio rebalancing."""
    return (
        "[info] Portfolio optimization (Markowitz MPT) requires numpy/scipy.\n"
        "Use 'perf by-symbol' for per-symbol performance analysis\n"
        "and 'risk correlation' for correlation insights."
    )


def _portfolio_var(*args: str) -> str:
    """Calculate Value at Risk."""
    confidence = 95
    for i, a in enumerate(args):
        if a == "--confidence" and i + 1 < len(args):
            confidence = int(args[i + 1])
    return (
        f"[info] VaR calculation at {confidence}% confidence requires\n"
        f"a return series with numpy. Use 'perf drawdown' for max drawdown."
    )


def _portfolio_cvar(*args: str) -> str:
    """Calculate Conditional VaR (Expected Shortfall)."""
    return "[info] CVaR requires numpy. Use 'perf drawdown' for drawdown analysis."


def _portfolio_stress_test(*args: str) -> str:
    """Run stress tests."""
    scenario = args[0] if args else "flash-crash"
    scenarios = {
        "flash-crash": "Simulates -5% move in 1 minute",
        "rate-hike": "Simulates sudden interest rate increase",
        "correlation-break": "Simulates historical correlations collapsing",
        "liquidity-dry": "Simulates spreads widening 10x",
    }
    desc = scenarios.get(scenario, f"Unknown scenario: {scenario}")
    return (
        f"Stress Test: {scenario}\n{'=' * 40}\n"
        f"  Scenario: {desc}\n"
        f"  [info] Full stress testing requires numpy/scipy.\n"
        f"  Check 'portfolio overview' for current exposure."
    )


def _portfolio_compare(*args: str) -> str:
    """Compare portfolio vs benchmarks."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        row = db.query_one(
            "SELECT sum(pnl) AS total, count(*) AS trades "
            "FROM trade_executions WHERE closed_at IS NOT NULL"
        )
        if row and row[0]:
            return (
                f"Portfolio vs Benchmark\n{'=' * 40}\n"
                f"  MONEYMAKER P&L:   ${row[0]:,.2f} ({row[1]} trades)\n"
                f"  Risk-free (5% ann): Requires equity curve\n"
                f"  S&P 500:       Requires external data"
            )
        return "No closed trade data for comparison."
    except Exception as exc:
        return f"[error] {exc}"


def register(registry: CommandRegistry) -> None:
    registry.register("portfolio", "overview", _portfolio_overview, "Portfolio overview")
    registry.register("portfolio", "allocation", _portfolio_allocation, "Capital allocation")
    registry.register("portfolio", "heat-map", _portfolio_heat_map, "Position P&L heat map")
    registry.register("portfolio", "optimize", _portfolio_optimize, "Suggest rebalancing")
    registry.register("portfolio", "var", _portfolio_var, "Value at Risk")
    registry.register("portfolio", "cvar", _portfolio_cvar, "Conditional VaR")
    registry.register("portfolio", "stress-test", _portfolio_stress_test, "Run stress tests")
    registry.register("portfolio", "compare", _portfolio_compare, "Compare vs benchmarks")
