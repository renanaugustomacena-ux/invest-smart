"""Utility tool commands."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from moneymaker_console.registry import CommandRegistry
from moneymaker_console.runner import _PROJECT_ROOT, run_tool

_registry_ref: CommandRegistry | None = None


def _tool_list(*args: str) -> str:
    """List all registered commands."""
    if _registry_ref is None:
        return "[error] Registry not initialized."
    lines = [
        f"MONEYMAKER Command Reference — {_registry_ref.command_count} commands, "
        f"{len(_registry_ref.categories)} categories",
        "=" * 70,
    ]
    lines.append(_registry_ref.get_help())
    return "\n".join(lines)


def _tool_logs(*args: str) -> str:
    """Show recent console log entries."""
    from datetime import date

    log_dir = _PROJECT_ROOT / "services" / "console" / "logs"
    today = date.today()
    log_file = log_dir / f"console_{today.strftime('%Y%m%d')}.json"
    if not log_file.exists():
        return "No console log for today."
    content = log_file.read_text().strip().splitlines()
    lines = ["Recent Console Log Entries", "=" * 50]
    for entry in content[-20:]:
        lines.append(f"  {entry[:120]}")
    return "\n".join(lines)


def _tool_env_check(*args: str) -> str:
    """Check Python environment for required dependencies."""
    deps = {
        "rich": "TUI rendering",
        "psycopg2": "PostgreSQL",
        "redis": "Redis",
        "httpx": "HTTP client",
        "grpc": "gRPC",
        "psutil": "System monitoring",
        "dotenv": "Env file loading",
    }
    import_names = {
        "psycopg2": "psycopg2",
        "grpc": "grpc",
        "dotenv": "dotenv",
    }
    lines = ["Environment Check", "=" * 50]
    for pkg, desc in deps.items():
        mod = import_names.get(pkg, pkg)
        try:
            __import__(mod)
            lines.append(f"  [OK]      {pkg:15s} — {desc}")
        except ImportError:
            lines.append(f"  [MISSING] {pkg:15s} — {desc}")
    lines.append(f"\n  Python: {sys.version.split()[0]}")
    return "\n".join(lines)


def _tool_shell(*args: str) -> str:
    """Open an interactive Python shell."""
    return (
        "[info] Shell access:\n"
        "  Python: python3 -c 'import IPython; IPython.start_ipython()'\n"
        "  Docker: svc exec SERVICE bash\n"
        "  SQL:    tool sql 'SELECT 1'"
    )


_BLOCKED_DDL = {"DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE"}


def _tool_sql(*args: str) -> str:
    """Execute a SQL query."""
    if not args:
        return "Usage: tool sql 'SELECT ...'"

    unsafe = "--unsafe" in args
    # Strip flags from the query text so they don't become part of the SQL
    query = " ".join(a for a in args if a != "--unsafe")
    upper = query.strip().upper()

    if not upper.startswith("SELECT") and not unsafe:
        return "[error] Only SELECT queries allowed. Use --unsafe for DML."

    # Block DDL statements even with --unsafe (destructive schema changes)
    first_word = upper.split()[0] if upper.split() else ""
    if first_word in _BLOCKED_DDL:
        return f"[error] {first_word} statements are blocked. Use psql directly for schema changes."

    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(query)
        if not rows:
            return "Query returned no rows."
        lines = [f"Query Results ({len(rows)} rows)", "=" * 60]
        for r in rows[:50]:
            lines.append(f"  {r}")
        if len(rows) > 50:
            lines.append(f"  ... and {len(rows) - 50} more rows")
        return "\n".join(lines)
    except Exception as exc:
        return f"[error] {exc}"


def _tool_redis_cli(*args: str) -> str:
    """Execute a Redis command."""
    if not args:
        return "Usage: tool redis-cli COMMAND [ARGS...]"
    cmd = args[0].upper()
    try:
        from moneymaker_console.clients import ClientFactory

        redis = ClientFactory.get_redis()
        if cmd == "GET" and len(args) > 1:
            result = redis.get(args[1])
            return f"  {args[1]} = {result}"
        elif cmd == "PING":
            return "  PONG" if redis.ping() else "  Connection failed"
        elif cmd == "INFO":
            info = redis.info()
            lines = ["Redis Info", "=" * 40]
            for k, v in (info or {}).items():
                lines.append(f"  {k}: {v}")
            return "\n".join(lines)
        else:
            return f"[info] Command '{cmd}' — use redis-cli directly for full access."
    except Exception as exc:
        return f"[error] {exc}"


def _tool_benchmark(*args: str) -> str:
    """Benchmark console-to-service latency."""
    import time

    lines = ["Latency Benchmark", "=" * 40]

    # Postgres
    try:
        from moneymaker_console.clients import ClientFactory

        start = time.monotonic()
        ClientFactory.get_postgres().ping()
        elapsed = (time.monotonic() - start) * 1000
        lines.append(f"  PostgreSQL:  {elapsed:.1f} ms")
    except Exception:
        lines.append("  PostgreSQL:  FAILED")

    # Redis
    try:
        from moneymaker_console.clients import ClientFactory

        start = time.monotonic()
        ClientFactory.get_redis().ping()
        elapsed = (time.monotonic() - start) * 1000
        lines.append(f"  Redis:       {elapsed:.1f} ms")
    except Exception:
        lines.append("  Redis:       FAILED")

    # Brain REST
    try:
        from moneymaker_console.clients import ClientFactory

        start = time.monotonic()
        ClientFactory.get_brain().is_healthy()
        elapsed = (time.monotonic() - start) * 1000
        lines.append(f"  Brain REST:  {elapsed:.1f} ms")
    except Exception:
        lines.append("  Brain REST:  FAILED")

    # MT5 gRPC
    try:
        from moneymaker_console.clients import ClientFactory

        start = time.monotonic()
        ClientFactory.get_mt5().is_healthy()
        elapsed = (time.monotonic() - start) * 1000
        lines.append(f"  MT5 gRPC:    {elapsed:.1f} ms")
    except Exception:
        lines.append("  MT5 gRPC:    FAILED")

    return "\n".join(lines)


def _tool_version(*args: str) -> str:
    """Display version information."""
    from moneymaker_console import __version__

    lines = [
        "MONEYMAKER Version Info",
        "=" * 40,
        f"  Console:    v{__version__}",
        f"  Python:     {sys.version.split()[0]}",
    ]

    # Docker
    docker_ver = run_tool(["docker", "--version"]).strip()
    lines.append(f"  Docker:     {docker_ver[:40]}")

    # Go
    go_ver = run_tool(["go", "version"]).strip()
    lines.append(f"  Go:         {go_ver[:40]}")

    # Postgres
    try:
        from moneymaker_console.clients import ClientFactory

        row = ClientFactory.get_postgres().query_one("SELECT version()")
        if row:
            lines.append(f"  PostgreSQL: {str(row[0])[:50]}")
    except Exception:
        lines.append("  PostgreSQL: N/A")

    # Redis
    try:
        from moneymaker_console.clients import ClientFactory

        info = ClientFactory.get_redis().info()
        if info:
            lines.append(f"  Redis:      {info.get('redis_version', 'N/A')}")
    except Exception:
        lines.append("  Redis:      N/A")

    return "\n".join(lines)


def _tool_whoami(*args: str) -> str:
    """Display operator identity."""
    import getpass

    return (
        f"Operator Identity\n{'=' * 40}\n"
        f"  User:        {getpass.getuser()}\n"
        f"  MT5 Account: {os.environ.get('MT5_ACCOUNT', 'N/A')}\n"
        f"  Environment: {os.environ.get('MONEYMAKER_ENV', 'development')}\n"
        f"  UTC Time:    {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
    )


def _tool_motd(*args: str) -> str:
    """Message of the Day."""
    lines = [
        "=" * 50,
        "  MONEYMAKER TRADING ECOSYSTEM — MOTD",
        "=" * 50,
        f"  Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]
    # Quick status checks
    try:
        from moneymaker_console.clients import ClientFactory

        db_ok = ClientFactory.get_postgres().ping()
        lines.append(f"  Database:   {'OK' if db_ok else 'DOWN'}")
    except Exception:
        lines.append("  Database:   DOWN")

    try:
        from moneymaker_console.clients import ClientFactory

        redis_ok = ClientFactory.get_redis().ping()
        lines.append(f"  Redis:      {'OK' if redis_ok else 'DOWN'}")
    except Exception:
        lines.append("  Redis:      DOWN")

    lines.extend(
        [
            "",
            "  Type 'help' for command reference.",
            "  Type 'sys health' for full health check.",
            "=" * 50,
        ]
    )
    return "\n".join(lines)


def register(registry: CommandRegistry) -> None:
    global _registry_ref
    _registry_ref = registry
    registry.register("tool", "list", _tool_list, "List all commands")
    registry.register("tool", "logs", _tool_logs, "View console log")
    registry.register("tool", "env-check", _tool_env_check, "Check dependencies")
    registry.register("tool", "shell", _tool_shell, "Open interactive shell")
    registry.register("tool", "sql", _tool_sql, "Execute SQL query", dangerous=True)
    registry.register("tool", "redis-cli", _tool_redis_cli, "Execute Redis command")
    registry.register("tool", "benchmark", _tool_benchmark, "Latency benchmark")
    registry.register("tool", "version", _tool_version, "Version information")
    registry.register("tool", "whoami", _tool_whoami, "Operator identity")
    registry.register("tool", "motd", _tool_motd, "Message of the Day")
