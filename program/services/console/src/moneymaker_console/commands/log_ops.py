"""Logging and observability commands."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry
from moneymaker_console.runner import _PROJECT_ROOT, run_tool


def _log_view(*args: str) -> str:
    """View recent logs for a service."""
    if not args:
        return "Usage: log view SERVICE [--tail N]"
    service = args[0]
    tail = 50
    for i, a in enumerate(args):
        if a == "--tail" and i + 1 < len(args):
            tail = int(args[i + 1])
    try:
        from moneymaker_console.clients import ClientFactory
        return ClientFactory.get_docker().logs(service, tail=tail)
    except Exception as exc:
        return f"[error] {exc}"


def _log_console(*args: str) -> str:
    """View the console's own JSON log."""
    from datetime import date
    days = int(args[0]) if args else 1
    today = date.today()
    log_dir = _PROJECT_ROOT / "services" / "console" / "logs"

    lines = [f"Console Log (last {days} day(s))", "=" * 50]
    for d in range(days):
        from datetime import timedelta
        target = today - timedelta(days=d)
        log_file = log_dir / f"console_{target.strftime('%Y%m%d')}.json"
        if log_file.exists():
            content = log_file.read_text().strip().splitlines()
            for entry in content[-20:]:
                lines.append(f"  {entry[:120]}")
        else:
            lines.append(f"  [No log for {target}]")
    return "\n".join(lines)


def _log_search(*args: str) -> str:
    """Search logs for a pattern."""
    if not args:
        return "Usage: log search QUERY [--service SERVICE]"
    query = args[0]
    service = None
    for i, a in enumerate(args):
        if a == "--service" and i + 1 < len(args):
            service = args[i + 1]

    if service:
        try:
            from moneymaker_console.clients import ClientFactory
            logs = ClientFactory.get_docker().logs(service, tail=200)
            matches = [l for l in logs.splitlines() if query.lower() in l.lower()]
            if matches:
                return "\n".join(matches[:30])
            return f"No matches for '{query}' in {service} logs."
        except Exception as exc:
            return f"[error] {exc}"

    return f"[info] Use 'log search {query} --service SERVICE' to search a specific service."


def _log_errors(*args: str) -> str:
    """Display ERROR-level log entries."""
    service = None
    for i, a in enumerate(args):
        if a == "--service" and i + 1 < len(args):
            service = args[i + 1]

    if not service:
        return "Usage: log errors --service SERVICE"

    try:
        from moneymaker_console.clients import ClientFactory
        logs = ClientFactory.get_docker().logs(service, tail=500)
        errors = [l for l in logs.splitlines()
                  if "ERROR" in l.upper() or "EXCEPTION" in l.upper() or "TRACEBACK" in l.upper()]
        if errors:
            lines = [f"Errors in {service} (last 500 lines)", "=" * 60]
            lines.extend(errors[:30])
            return "\n".join(lines)
        return f"No errors found in {service} logs."
    except Exception as exc:
        return f"[error] {exc}"


def _log_export(*args: str) -> str:
    """Export logs to a file."""
    if not args:
        return "Usage: log export SERVICE --output FILE"
    service = args[0]
    output = None
    for i, a in enumerate(args):
        if a == "--output" and i + 1 < len(args):
            output = args[i + 1]
    if not output:
        return "Usage: log export SERVICE --output FILE"
    try:
        from moneymaker_console.clients import ClientFactory
        logs = ClientFactory.get_docker().logs(service, tail=5000)
        from pathlib import Path
        Path(output).write_text(logs)
        return f"[success] Exported {len(logs.splitlines())} lines to {output}"
    except Exception as exc:
        return f"[error] {exc}"


def _log_rotate(*args: str) -> str:
    """Trigger log rotation."""
    import glob
    from pathlib import Path
    log_dir = _PROJECT_ROOT / "services" / "console" / "logs"
    if not log_dir.exists():
        return "No log directory found."
    log_files = sorted(log_dir.glob("console_*.json"))
    if len(log_files) <= 30:
        return f"[info] {len(log_files)} log files, no rotation needed (threshold: 30)."
    old_files = log_files[:-30]
    for f in old_files:
        f.unlink()
    return f"[success] Rotated {len(old_files)} old log files."


def _log_level(*args: str) -> str:
    """Change log level for a service."""
    if len(args) < 2:
        return "Usage: log level SERVICE LEVEL  (DEBUG/INFO/WARNING/ERROR)"
    service, level = args[0], args[1].upper()
    if level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        return f"[error] Invalid level: {level}. Use DEBUG/INFO/WARNING/ERROR."
    return f"[info] Log level change to {level} for {service} requires service REST API or restart."


def _log_metrics(*args: str) -> str:
    """Display log volume metrics."""
    log_dir = _PROJECT_ROOT / "services" / "console" / "logs"
    if not log_dir.exists():
        return "No log directory."
    total_size = sum(f.stat().st_size for f in log_dir.iterdir() if f.is_file())
    file_count = sum(1 for f in log_dir.iterdir() if f.is_file())
    return (
        f"Log Metrics\n{'=' * 40}\n"
        f"  Console log files: {file_count}\n"
        f"  Total size:        {total_size / 1024:.1f} KB\n"
        f"  Log directory:     {log_dir}"
    )


def register(registry: CommandRegistry) -> None:
    registry.register("log", "view", _log_view, "View service logs")
    registry.register("log", "console", _log_console, "View console log")
    registry.register("log", "search", _log_search, "Search logs")
    registry.register("log", "errors", _log_errors, "Show error entries")
    registry.register("log", "export", _log_export, "Export logs to file")
    registry.register("log", "rotate", _log_rotate, "Rotate old log files")
    registry.register("log", "level", _log_level, "Change log level")
    registry.register("log", "metrics", _log_metrics, "Log volume metrics")
