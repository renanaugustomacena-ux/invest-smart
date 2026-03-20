# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Data ingestion management commands."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry


def _data_start(*args: str) -> str:
    """Start the data ingestion pipeline."""
    try:
        from moneymaker_console.clients import ClientFactory

        return ClientFactory.get_docker().up("data-ingestion")
    except Exception as exc:
        return f"[error] Failed to start data ingestion: {exc}"


def _data_stop(*args: str) -> str:
    """Stop the data ingestion pipeline."""
    try:
        from moneymaker_console.clients import ClientFactory

        return ClientFactory.get_docker().down("data-ingestion")
    except Exception as exc:
        return f"[error] Failed to stop data ingestion: {exc}"


def _data_status(*args: str) -> str:
    """Display ingestion status."""
    lines = ["Data Ingestion Status", "=" * 40]

    # HTTP health
    try:
        from moneymaker_console.clients import ClientFactory

        data = ClientFactory.get_data()
        health = data.get_health()
        if health:
            lines.append("  Health:     OK")
            for k, v in health.items():
                lines.append(f"    {k}: {v}")
        else:
            lines.append("  Health:     NOT CONNECTED")
    except Exception:
        lines.append("  Health:     ERROR")

    # Tick throughput from DB
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        row = db.query_one(
            "SELECT count(*) AS cnt FROM market_ticks "
            "WHERE timestamp > NOW() - INTERVAL '5 minutes'"
        )
        if row:
            lines.append(f"  Ticks (5m): {row[0]}")
    except Exception:
        pass

    return "\n".join(lines)


def _data_symbols(*args: str) -> str:
    """List actively ingested symbols."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT DISTINCT symbol, "
            "array_agg(DISTINCT timeframe) AS timeframes, "
            "max(open_time) AS last_bar_at "
            "FROM ohlcv_bars "
            "WHERE open_time > NOW() - INTERVAL '1 hour' "
            "GROUP BY symbol ORDER BY symbol"
        )
        if not rows:
            return "No symbols with recent data in the last hour."
        lines = ["Active Symbols", "=" * 60]
        for row in rows:
            lines.append(f"  {row[0]:12s}  TFs: {row[1]}  Last: {row[2]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _data_add(*args: str) -> str:
    """Add a symbol to the ingestion list."""
    if not args:
        return "Usage: data add SYMBOL [--timeframes M1,M5,H1]"
    symbol = args[0].upper()
    return (
        f"[info] Symbol add requests must be configured in the data ingestion "
        f"service config. Symbol: {symbol}\n"
        f"Edit the data-ingestion config and restart the service."
    )


def _data_remove(*args: str) -> str:
    """Remove a symbol from ingestion."""
    if not args:
        return "Usage: data remove SYMBOL"
    return f"[info] Remove symbol '{args[0].upper()}' from data-ingestion config and restart."


def _data_backfill(*args: str) -> str:
    """Trigger historical data backfill."""
    if len(args) < 2:
        return "Usage: data backfill SYMBOL DAYS"
    symbol, days = args[0].upper(), args[1]
    return (
        f"[info] Backfill must be triggered via the data-ingestion API.\n"
        f"Symbol: {symbol}, Days: {days}"
    )


def _data_gaps(*args: str) -> str:
    """Analyze TimescaleDB for data gaps."""
    days = "7"
    if args:
        days = args[0]
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT time_bucket('1 hour', open_time) AS bucket, "
            "symbol, count(*) AS bar_count "
            "FROM ohlcv_bars "
            f"WHERE open_time > NOW() - INTERVAL '{int(days)} days' "
            "GROUP BY bucket, symbol "
            "HAVING count(*) < 4 "
            "ORDER BY bucket DESC LIMIT 50"
        )
        if not rows:
            return f"No data gaps found in the last {days} days."
        lines = [f"Data Gaps (last {days} days)", "=" * 60]
        for row in rows:
            lines.append(f"  {row[0]}  {row[1]:12s}  bars: {row[2]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _data_providers(*args: str) -> str:
    """List configured data providers."""
    try:
        from moneymaker_console.clients import ClientFactory

        data = ClientFactory.get_data()
        health = data.get_health()
        if health:
            providers = health.get("providers", {})
            if providers:
                lines = ["Data Providers", "=" * 40]
                for name, status in providers.items():
                    lines.append(f"  {name}: {status}")
                return "\n".join(lines)
        return "[info] Provider details not available from health endpoint."
    except Exception as exc:
        return f"[error] {exc}"


def _data_reconnect(*args: str) -> str:
    """Force reconnection to providers."""
    try:
        from moneymaker_console.clients import ClientFactory

        return ClientFactory.get_docker().restart("data-ingestion")
    except Exception as exc:
        return f"[error] {exc}"


def _data_buffer(*args: str) -> str:
    """Display aggregation buffer status."""
    try:
        from moneymaker_console.clients import ClientFactory

        data = ClientFactory.get_data()
        metrics = data.get_metrics()
        if metrics:
            lines = ["Buffer Metrics", "=" * 40]
            for line in metrics.splitlines():
                if "buffer" in line.lower() or "pending" in line.lower():
                    lines.append(f"  {line.strip()}")
            if len(lines) > 2:
                return "\n".join(lines)
        return "[info] Buffer metrics not available."
    except Exception as exc:
        return f"[error] {exc}"


def _data_latency(*args: str) -> str:
    """Display end-to-end latency metrics."""
    try:
        from moneymaker_console.clients import ClientFactory

        data = ClientFactory.get_data()
        metrics = data.get_metrics()
        if metrics:
            lines = ["Latency Metrics", "=" * 40]
            for line in metrics.splitlines():
                if "latency" in line.lower() or "duration" in line.lower():
                    if not line.startswith("#"):
                        lines.append(f"  {line.strip()}")
            if len(lines) > 2:
                return "\n".join(lines)
        return "[info] Latency metrics not available from Prometheus endpoint."
    except Exception as exc:
        return f"[error] {exc}"


def register(registry: CommandRegistry) -> None:
    registry.register("data", "start", _data_start, "Start the data ingestion pipeline")
    registry.register("data", "stop", _data_stop, "Stop the data ingestion pipeline")
    registry.register("data", "status", _data_status, "Display ingestion status")
    registry.register("data", "symbols", _data_symbols, "List actively ingested symbols")
    registry.register("data", "add", _data_add, "Add a symbol to the ingestion list")
    registry.register("data", "remove", _data_remove, "Remove a symbol from ingestion")
    registry.register("data", "backfill", _data_backfill, "Trigger historical backfill")
    registry.register("data", "gaps", _data_gaps, "Analyze data gaps in TimescaleDB")
    registry.register("data", "providers", _data_providers, "List data providers")
    registry.register("data", "reconnect", _data_reconnect, "Force reconnection to providers")
    registry.register("data", "buffer", _data_buffer, "Display aggregation buffer status")
    registry.register("data", "latency", _data_latency, "Display end-to-end latency metrics")
