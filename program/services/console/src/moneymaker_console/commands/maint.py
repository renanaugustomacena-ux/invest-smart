# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Maintenance and database operations commands."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry
from moneymaker_console.runner import _PROJECT_ROOT, run_tool, run_tool_live


def _maint_vacuum(*args: str) -> str:
    """Run VACUUM ANALYZE on all tables."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        db.execute("VACUUM ANALYZE")
        return "[success] VACUUM ANALYZE completed on all tables."
    except Exception as exc:
        return f"[error] VACUUM failed: {exc}"


def _maint_reindex(*args: str) -> str:
    """Rebuild all database indexes."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        db_name = __import__("os").environ.get("MONEYMAKER_DB_NAME", "moneymaker_brain")
        db.execute(f"REINDEX DATABASE {db_name}")
        return f"[success] REINDEX DATABASE {db_name} completed."
    except Exception as exc:
        return f"[error] REINDEX failed: {exc}"


def _maint_clear_cache(*args: str) -> str:
    """Remove caches from the project tree."""
    lines = ["Clearing caches..."]
    run_tool(
        [
            "find",
            str(_PROJECT_ROOT),
            "-type",
            "d",
            "-name",
            "__pycache__",
            "-exec",
            "rm",
            "-rf",
            "{}",
            "+",
        ],
    )
    lines.append("  Removed __pycache__ directories")

    run_tool(
        [
            "find",
            str(_PROJECT_ROOT),
            "-type",
            "d",
            "-name",
            ".pytest_cache",
            "-exec",
            "rm",
            "-rf",
            "{}",
            "+",
        ],
    )
    lines.append("  Removed .pytest_cache directories")

    if "--redis" in args:
        try:
            from moneymaker_console.clients import ClientFactory

            redis = ClientFactory.get_redis()
            redis._conn.flushdb()
            lines.append("  Flushed Redis cache")
        except Exception:
            lines.append("  [warning] Redis flush failed")

    lines.append("[success] Cache cleared.")
    return "\n".join(lines)


def _maint_retention(*args: str) -> str:
    """Display data retention policies."""
    return (
        "Data Retention Policies\n"
        "=" * 40 + "\n"
        "  trade_executions:     730 days\n"
        "  trading_signals:      730 days\n"
        "  strategy_performance: 365 days\n"
        "  market_ticks:         configurable (TICK_RETENTION_DAYS)\n"
        "  ohlcv_bars:           configurable (BAR_RETENTION_DAYS)\n"
        "  drift_log:            90 days\n"
        "  performance_snapshot: 90 days"
    )


def _maint_backup(*args: str) -> str:
    """Create a full database backup."""
    import os
    from datetime import datetime

    db_host = os.environ.get("MONEYMAKER_DB_HOST", "localhost")
    db_port = os.environ.get("MONEYMAKER_DB_PORT", "5432")
    db_name = os.environ.get("MONEYMAKER_DB_NAME", "moneymaker_brain")
    db_user = os.environ.get("MONEYMAKER_DB_USER", "moneymaker_admin")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    compress = "--compress" in args
    ext = ".sql.gz" if compress else ".sql"
    out_file = _PROJECT_ROOT.parent / "logs" / f"moneymaker_backup_{ts}{ext}"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pg_dump",
        "-h",
        db_host,
        "-p",
        db_port,
        "-U",
        db_user,
        "-d",
        db_name,
        "-F",
        "p",
    ]
    if compress:
        import subprocess

        try:
            pg = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            gz = subprocess.Popen(
                ["gzip"],
                stdin=pg.stdout,
                stdout=open(str(out_file), "wb"),
                stderr=subprocess.PIPE,
            )
            pg.stdout.close()  # allow SIGPIPE
            gz.communicate()
            pg.wait()
            if pg.returncode != 0:
                return f"[error] pg_dump failed (exit {pg.returncode})"
            return f"[success] Compressed backup saved to {out_file}"
        except FileNotFoundError as exc:
            return f"[error] Command not found: {exc}"
    else:
        cmd.extend(["-f", str(out_file)])
        result = run_tool(cmd)
        return f"[success] Backup saved to {out_file}\n{result}"


def _maint_restore(*args: str) -> str:
    """Restore database from a backup file."""
    if not args:
        return "Usage: maint restore FILE"
    return f"[warning] Restore from '{args[0]}' is destructive. Use psql manually for safety."


def _maint_prune_old(*args: str) -> str:
    """Delete old data from drift logs and snapshots."""
    if not args:
        return "Usage: maint prune-old DAYS [--dry-run]"
    days = int(args[0])
    dry_run = "--dry-run" in args

    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()

        tables = ["drift_log", "performance_snapshot"]
        lines = [f"Pruning data older than {days} days", "=" * 40]
        for table in tables:
            try:
                count_row = db.query_one(
                    f"SELECT count(*) FROM {table} "
                    f"WHERE created_at < NOW() - INTERVAL '{days} days'"
                )
                count = count_row[0] if count_row else 0
                if dry_run:
                    lines.append(f"  [dry-run] {table}: would delete {count} rows")
                else:
                    db.execute(
                        f"DELETE FROM {table} " f"WHERE created_at < NOW() - INTERVAL '{days} days'"
                    )
                    lines.append(f"  {table}: deleted {count} rows")
            except Exception as exc:
                lines.append(f"  {table}: skipped ({exc})")

        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _maint_migrate(*args: str) -> str:
    """Run pending database migrations."""
    dry_run = "--dry-run" in args
    if dry_run:
        return "[info] Migration dry-run: check init-db/*.sql for pending schema changes."
    return run_tool_live(
        ["python3", "-m", "algo_engine.storage.db_migrate"],
        cwd=str(_PROJECT_ROOT / "services" / "algo-engine"),
    )


def _maint_table_sizes(*args: str) -> str:
    """Display table sizes in the database."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT schemaname || '.' || tablename AS tbl, "
            "pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total, "
            "pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) AS data, "
            "pg_size_pretty(pg_indexes_size(schemaname || '.' || tablename)) AS idx "
            "FROM pg_tables "
            "WHERE schemaname NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC"
        )
        if not rows:
            return "No tables found."
        lines = ["Table Sizes", "=" * 70]
        lines.append(f"  {'Table':40s} {'Total':12s} {'Data':12s} {'Index':12s}")
        lines.append(f"  {'-'*40} {'-'*12} {'-'*12} {'-'*12}")
        for r in rows:
            lines.append(f"  {r[0]:40s} {r[1]:12s} {r[2]:12s} {r[3]:12s}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _maint_chunk_stats(*args: str) -> str:
    """Display TimescaleDB chunk statistics."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT hypertable_name, "
            "count(*) AS num_chunks, "
            "min(range_start) AS oldest, "
            "max(range_end) AS newest "
            "FROM timescaledb_information.chunks "
            "GROUP BY hypertable_name "
            "ORDER BY hypertable_name"
        )
        if not rows:
            return "No TimescaleDB hypertables found."
        lines = ["Hypertable Chunk Stats", "=" * 70]
        for r in rows:
            lines.append(f"  {r[0]:30s}  chunks={r[1]:5d}  range: {r[2]} — {r[3]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _maint_compress(*args: str) -> str:
    """Enable TimescaleDB compression on old chunks."""
    days = 30
    for i, a in enumerate(args):
        if a == "--older-than" and i + 1 < len(args):
            days = int(args[i + 1])
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query("SELECT hypertable_name FROM timescaledb_information.hypertables")
        if not rows:
            return "No hypertables found."
        lines = [f"Compressing chunks older than {days} days", "=" * 40]
        for r in rows:
            try:
                db.execute(
                    "SELECT compress_chunk(c.chunk_name) "
                    "FROM timescaledb_information.chunks c "
                    "WHERE c.hypertable_name = %s "
                    "AND c.range_end < NOW() - INTERVAL '%s days' "
                    "AND NOT c.is_compressed",
                    (r[0], days),
                )
                lines.append(f"  {r[0]}: compression initiated")
            except Exception as exc:
                lines.append(f"  {r[0]}: skipped ({exc})")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _maint_dead_code(*args: str) -> str:
    """Run dead code detection."""
    return run_tool_live(
        ["python3", "-m", "vulture", "src/algo_engine/", "--min-confidence", "80"],
        cwd=str(_PROJECT_ROOT / "services" / "algo-engine"),
    )


def _maint_sanitize(*args: str) -> str:
    """Run project sanitization."""
    lines = ["Project Sanitization", "=" * 40]
    # Remove .pyc
    run_tool(["find", str(_PROJECT_ROOT), "-name", "*.pyc", "-delete"])
    lines.append("  Removed .pyc files")
    # Check .env permissions
    env_file = _PROJECT_ROOT / ".env"
    if env_file.exists():
        mode = oct(env_file.stat().st_mode & 0o777)
        if mode != "0o600":
            lines.append(f"  [warning] .env permissions: {mode} (should be 0o600)")
        else:
            lines.append("  .env permissions: OK (600)")
    lines.append("[success] Sanitization complete.")
    return "\n".join(lines)


def _maint_integrity(*args: str) -> str:
    """Verify database integrity."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        lines = ["Database Integrity Check", "=" * 40]

        # Foreign key check
        fk_row = db.query_one(
            "SELECT count(*) FROM information_schema.table_constraints "
            "WHERE constraint_type = 'FOREIGN KEY'"
        )
        lines.append(f"  Foreign keys: {fk_row[0] if fk_row else 0}")

        # Orphaned signals (no execution)
        orphan = db.query_one(
            "SELECT count(*) FROM trading_signals ts "
            "LEFT JOIN trade_executions te ON ts.id = te.signal_id "
            "WHERE ts.validation_result = 'validated' "
            "AND te.id IS NULL "
            "AND ts.created_at < NOW() - INTERVAL '1 hour'"
        )
        orphan_count = orphan[0] if orphan else 0
        lines.append(f"  Orphaned signals: {orphan_count}")

        lines.append("[success] Integrity check complete.")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def register(registry: CommandRegistry) -> None:
    registry.register("maint", "vacuum", _maint_vacuum, "Run VACUUM ANALYZE", timeout_sec=300)
    registry.register(
        "maint", "reindex", _maint_reindex, "Rebuild database indexes", timeout_sec=300
    )
    registry.register(
        "maint",
        "clear-cache",
        _maint_clear_cache,
        "Remove caches",
        requires_confirmation=True,
        dangerous=True,
    )
    registry.register("maint", "retention", _maint_retention, "Display retention policies")
    registry.register("maint", "backup", _maint_backup, "Create database backup", timeout_sec=600)
    registry.register(
        "maint", "restore", _maint_restore, "Restore from backup", dangerous=True, timeout_sec=600
    )
    registry.register(
        "maint",
        "prune-old",
        _maint_prune_old,
        "Delete old data",
        requires_confirmation=True,
        timeout_sec=120,
    )
    registry.register(
        "maint", "migrate", _maint_migrate, "Run database migrations", timeout_sec=120
    )
    registry.register("maint", "table-sizes", _maint_table_sizes, "Display table sizes")
    registry.register("maint", "chunk-stats", _maint_chunk_stats, "Display chunk statistics")
    registry.register("maint", "compress", _maint_compress, "Compress old chunks", timeout_sec=300)
    registry.register(
        "maint", "dead-code", _maint_dead_code, "Run dead code detection", timeout_sec=120
    )
    registry.register(
        "maint", "sanitize", _maint_sanitize, "Run project sanitization", timeout_sec=120
    )
    registry.register(
        "maint", "integrity", _maint_integrity, "Verify database integrity", timeout_sec=120
    )
