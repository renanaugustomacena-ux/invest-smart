# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Market intelligence commands."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry


def _market_regime(*args: str) -> str:
    """Display current market regime."""
    try:
        from moneymaker_console.clients import ClientFactory

        # Try Redis first
        try:
            redis = ClientFactory.get_redis()
            import json

            data = redis.get("moneymaker:regime")
            if data:
                regime = json.loads(data) if isinstance(data, str) else data
                lines = ["Market Regime", "=" * 40]
                if isinstance(regime, dict):
                    for k, v in regime.items():
                        lines.append(f"  {k}: {v}")
                else:
                    lines.append(f"  Regime: {regime}")
                return "\n".join(lines)
        except Exception:
            pass

        # Fallback to DB
        db = ClientFactory.get_postgres()
        row = db.query_one(
            "SELECT regime_type, confidence, updated_at "
            "FROM regime_classifications "
            "ORDER BY updated_at DESC LIMIT 1"
        )
        if row:
            return (
                f"Market Regime\n{'=' * 40}\n"
                f"  Regime:     {row[0]}\n"
                f"  Confidence: {row[1]}\n"
                f"  Updated:    {row[2]}"
            )
        return "[info] No regime data available."
    except Exception as exc:
        return f"[error] {exc}"


def _market_symbols(*args: str) -> str:
    """Display monitored symbols with regime and volatility."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT DISTINCT symbol, max(open_time) AS last_bar "
            "FROM ohlcv_bars "
            "WHERE open_time > NOW() - INTERVAL '1 hour' "
            "GROUP BY symbol ORDER BY symbol"
        )
        if not rows:
            return "No active symbols."
        lines = ["Monitored Symbols", "=" * 50]
        for r in rows:
            lines.append(f"  {r[0]:12s}  Last bar: {r[1]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _market_spread(*args: str) -> str:
    """Display bid-ask spread for a symbol."""
    if not args:
        return "Usage: market spread SYMBOL"
    symbol = args[0].upper()
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        row = db.query_one(
            "SELECT bid, ask, (ask - bid) AS spread, timestamp "
            "FROM market_ticks "
            f"WHERE symbol = '{symbol}' "
            "ORDER BY timestamp DESC LIMIT 1"
        )
        if row:
            return (
                f"Spread for {symbol}\n{'=' * 40}\n"
                f"  Bid:    {row[0]}\n"
                f"  Ask:    {row[1]}\n"
                f"  Spread: {row[2]}\n"
                f"  Time:   {row[3]}"
            )
        return f"No tick data for {symbol}."
    except Exception as exc:
        return f"[error] {exc}"


def _market_calendar(*args: str) -> str:
    """Display upcoming economic events."""
    days = int(args[0]) if args else 7
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT event_time, currency, impact, event_name "
            "FROM economic_calendar "
            f"WHERE event_time > NOW() AND event_time < NOW() + INTERVAL '{days} days' "
            "ORDER BY event_time LIMIT 20"
        )
        if not rows:
            return f"No economic events in the next {days} days."
        lines = [f"Economic Calendar (next {days} days)", "=" * 70]
        for r in rows:
            impact = r[2] or "N/A"
            marker = "!!!" if impact.upper() == "HIGH" else ""
            lines.append(f"  {r[0]}  {r[1]:4s}  [{impact:6s}] {r[3]} {marker}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _market_volatility(*args: str) -> str:
    """Display volatility metrics."""
    symbol_filter = f"WHERE symbol = '{args[0].upper()}'" if args else ""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT symbol, "
            "stddev(close) AS volatility, "
            "avg(high - low) AS avg_range, "
            "count(*) AS bars "
            f"FROM ohlcv_bars {symbol_filter} "
            "WHERE open_time > NOW() - INTERVAL '7 days' "
            "GROUP BY symbol ORDER BY volatility DESC NULLS LAST"
            if not symbol_filter
            else f"SELECT symbol, "
            f"stddev(close) AS volatility, "
            f"avg(high - low) AS avg_range, "
            f"count(*) AS bars "
            f"FROM ohlcv_bars {symbol_filter} "
            f"AND open_time > NOW() - INTERVAL '7 days' "
            f"GROUP BY symbol"
        )
        if not rows:
            return "No volatility data available."
        lines = ["Volatility Metrics (7d)", "=" * 60]
        for r in rows:
            vol = f"{r[1]:.5f}" if r[1] is not None else "N/A"
            rng = f"{r[2]:.5f}" if r[2] is not None else "N/A"
            lines.append(f"  {r[0]:12s}  vol={vol}  avg_range={rng}  bars={r[3]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _market_correlation(*args: str) -> str:
    """Display cross-symbol correlation matrix."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT DISTINCT symbol FROM ohlcv_bars "
            "WHERE open_time > NOW() - INTERVAL '7 days' "
            "ORDER BY symbol LIMIT 10"
        )
        if not rows or len(rows) < 2:
            return "Not enough symbols for correlation analysis."
        symbols = [r[0] for r in rows]
        return (
            f"Correlation Matrix\n{'=' * 40}\n"
            f"  Symbols: {', '.join(symbols)}\n"
            f"  [info] Full correlation requires pandas. "
            f"Use 'brain features' for per-symbol analysis."
        )
    except Exception as exc:
        return f"[error] {exc}"


def _market_session(*args: str) -> str:
    """Display current trading session."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    hour = now.hour

    if 0 <= hour < 7:
        session = "ASIAN"
    elif 7 <= hour < 12:
        session = "LONDON"
    elif 12 <= hour < 15:
        session = "OVERLAP_LONDON_NY"
    elif 15 <= hour < 21:
        session = "NEW_YORK"
    else:
        session = "OFF_HOURS"

    return (
        f"Trading Session\n{'=' * 40}\n"
        f"  Current:  {session}\n"
        f"  UTC Time: {now.strftime('%H:%M:%S')}\n"
        f"  Note:     Session times are approximate"
    )


def _market_news(*args: str) -> str:
    """Display recent news events."""
    impact_filter = ""
    if args:
        impact_filter = f"AND impact = '{args[0].upper()}'"
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT event_time, currency, impact, event_name "
            f"FROM economic_calendar "
            f"WHERE event_time > NOW() - INTERVAL '24 hours' "
            f"{impact_filter} "
            "ORDER BY event_time DESC LIMIT 20"
        )
        if not rows:
            return "No recent news events."
        lines = ["Recent News Events", "=" * 70]
        for r in rows:
            lines.append(f"  {r[0]}  {r[1]:4s}  [{r[2] or 'N/A':6s}] {r[3]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _market_indicators(*args: str) -> str:
    """Display technical indicators for a symbol."""
    if not args:
        return "Usage: market indicators SYMBOL"
    symbol = args[0].upper()
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        row = db.query_one(
            "SELECT feature_vector, created_at "
            "FROM feature_vectors "
            f"WHERE symbol = '{symbol}' "
            "ORDER BY created_at DESC LIMIT 1"
        )
        if row and row[0]:
            lines = [f"Technical Indicators — {symbol}", "=" * 50]
            if isinstance(row[0], dict):
                for k, v in row[0].items():
                    val = f"{v:.5f}" if isinstance(v, float) else str(v)
                    lines.append(f"  {k:30s}: {val}")
            else:
                lines.append(f"  Vector: {str(row[0])[:200]}")
            lines.append(f"  Updated: {row[1]}")
            return "\n".join(lines)
        return f"No feature data for {symbol}."
    except Exception as exc:
        return f"[error] {exc}"


def _market_macro(*args: str) -> str:
    """Display macroeconomic indicators."""
    try:
        from moneymaker_console.clients import ClientFactory

        redis = ClientFactory.get_redis()
        vix = redis.get("moneymaker:macro:vix")
        dxy = redis.get("moneymaker:macro:dxy")
        lines = ["Macro Indicators", "=" * 40]
        lines.append(f"  VIX:  {vix or 'N/A'}")
        lines.append(f"  DXY:  {dxy or 'N/A'}")
        lines.append("  [info] Full macro data via 'market macro-status'")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _market_macro_status(*args: str) -> str:
    """Display external data service health."""
    try:
        import httpx

        port = __import__("os").environ.get("EXTERNAL_DATA_PORT", "9095")
        resp = httpx.get(f"http://localhost:{port}/health", timeout=5)
        if resp.status_code == 200:
            return f"External Data Service\n{'=' * 40}\n  Status: OK\n  {resp.json()}"
        return f"External Data Service: HTTP {resp.status_code}"
    except Exception:
        return "[info] External data service not available."


def _market_dashboard(*args: str) -> str:
    """Show dashboard URL."""
    import os

    port = os.environ.get("DASHBOARD_PORT", "8000")
    return (
        f"MONEYMAKER Dashboard\n{'=' * 40}\n"
        f"  URL: http://localhost:{port}\n"
        f"  Open in your browser to view the full dashboard."
    )


def register(registry: CommandRegistry) -> None:
    registry.register("market", "regime", _market_regime, "Display current market regime")
    registry.register("market", "symbols", _market_symbols, "Display monitored symbols")
    registry.register("market", "spread", _market_spread, "Display bid-ask spread")
    registry.register("market", "calendar", _market_calendar, "Display economic calendar")
    registry.register("market", "volatility", _market_volatility, "Display volatility metrics")
    registry.register("market", "correlation", _market_correlation, "Display correlation matrix")
    registry.register("market", "session", _market_session, "Display current trading session")
    registry.register("market", "news", _market_news, "Display recent news events")
    registry.register("market", "indicators", _market_indicators, "Display technical indicators")
    registry.register("market", "macro", _market_macro, "Display macroeconomic indicators")
    registry.register(
        "market", "macro-status", _market_macro_status, "External data service status"
    )
    registry.register("market", "dashboard", _market_dashboard, "Show dashboard URL")
