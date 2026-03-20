# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""System operations commands — health, resources, diagnostics."""

from __future__ import annotations

import concurrent.futures
import os
import subprocess

from moneymaker_console.clients import ClientFactory
from moneymaker_console.console_logging import mask_secrets
from moneymaker_console.registry import CommandRegistry
from moneymaker_console.runner import _PROJECT_ROOT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _service_unavailable(name: str) -> str:
    return f"[warning] Service '{name}' not available. Start with: svc up"


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


def _sys_status(*args: str) -> str:
    """Full system status dashboard."""
    lines = ["MONEYMAKER System Status", "=" * 40]

    # Database
    db = ClientFactory.get_postgres()
    lines.append(f"  PostgreSQL:  {'OK' if db.ping() else 'NOT CONNECTED'}")

    # Redis
    redis = ClientFactory.get_redis()
    lines.append(f"  Redis:       {'OK' if redis.ping() else 'NOT CONNECTED'}")

    # Algo Engine
    brain = ClientFactory.get_brain()
    lines.append(f"  Algo Engine:    {'OK' if brain.is_healthy() else 'NOT CONNECTED'}")

    # MT5 Bridge
    mt5 = ClientFactory.get_mt5()
    lines.append(f"  MT5 Bridge:  {'OK' if mt5.is_healthy() else 'NOT CONNECTED'}")

    # Data Ingestion
    data = ClientFactory.get_data()
    lines.append(f"  Data Ingest: {'OK' if data.is_healthy() else 'NOT CONNECTED'}")

    # Docker
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.Containers}} containers"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines.append(f"  Docker:      OK ({result.stdout.strip()})")
        else:
            lines.append("  Docker:      ERROR")
    except Exception:
        lines.append("  Docker:      NOT AVAILABLE")

    return "\n".join(lines)


def _sys_resources(*args: str) -> str:
    """Display CPU, RAM, GPU, and disk usage."""
    try:
        import psutil
    except ImportError:
        return "[warning] psutil not installed. Install with: pip install psutil"

    cpu = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    lines = [
        "System Resources",
        "=" * 40,
        f"  CPU:     {cpu:.1f}% ({cpu_count} cores)",
        f"  RAM:     {mem.used / (1024**3):.1f} / {mem.total / (1024**3):.1f} GB "
        f"({mem.percent:.1f}%)",
        f"  Disk:    {disk.used / (1024**3):.1f} / {disk.total / (1024**3):.1f} GB "
        f"({disk.percent:.1f}%)",
    ]

    # GPU (AMD ROCm)
    try:
        result = subprocess.run(
            ["rocm-smi", "--showtemp", "--showuse"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines()[:5]:
                lines.append(f"  GPU:     {line.strip()}")
        else:
            lines.append("  GPU:     ROCm query failed")
    except FileNotFoundError:
        lines.append("  GPU:     ROCm not available")
    except Exception:
        lines.append("  GPU:     Error querying GPU")

    return "\n".join(lines)


def _sys_health(*args: str) -> str:
    """Execute parallel health checks across all infrastructure."""
    checks = {
        "PostgreSQL": lambda: "OK" if ClientFactory.get_postgres().ping() else "ERROR",
        "Redis": lambda: "OK" if ClientFactory.get_redis().ping() else "ERROR",
        "Algo Engine (REST)": lambda: "OK" if ClientFactory.get_brain().is_healthy() else "ERROR",
        "MT5 Bridge (gRPC)": lambda: "OK" if ClientFactory.get_mt5().is_healthy() else "ERROR",
        "Data Ingestion (HTTP)": lambda: "OK" if ClientFactory.get_data().is_healthy() else "ERROR",
    }

    # Add Docker check
    def _check_docker():
        try:
            r = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
            )
            return "OK" if r.returncode == 0 else "ERROR"
        except Exception:
            return "NOT AVAILABLE"

    checks["Docker"] = _check_docker

    results: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fn): name for name, fn in checks.items()}
        for future in concurrent.futures.as_completed(futures, timeout=15):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = "ERROR"

    lines = ["Health Check", "=" * 40]
    for name in checks:
        status = results.get(name, "TIMEOUT")
        indicator = "[OK]" if status == "OK" else "[!!]"
        lines.append(f"  {indicator} {name:<25} {status}")

    return "\n".join(lines)


def _sys_db(*args: str) -> str:
    """Display TimescaleDB status."""
    db = ClientFactory.get_postgres()
    if not db.ping():
        return _service_unavailable("PostgreSQL")

    lines = ["TimescaleDB Status", "=" * 40]

    # Version
    row = db.query_one("SELECT version()")
    if row:
        ver = str(row[0]).split(",")[0]
        lines.append(f"  Version:     {ver}")

    # Database size
    row = db.query_one("SELECT pg_size_pretty(pg_database_size(current_database()))")
    if row:
        lines.append(f"  DB Size:     {row[0]}")

    # Active connections
    rows = db.query(
        "SELECT state, count(*) FROM pg_stat_activity "
        "WHERE datname = current_database() GROUP BY state"
    )
    for state, count in rows:
        lines.append(f"  Connections: {state or 'null'} = {count}")

    # Table sizes (top 10)
    rows = db.query(
        "SELECT relname, pg_size_pretty(pg_total_relation_size(c.oid)) "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind = 'r' "
        "ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 10"
    )
    if rows:
        lines.append("\n  Top Tables:")
        for name, size in rows:
            lines.append(f"    {name:<30} {size}")

    return "\n".join(lines)


def _sys_redis(*args: str) -> str:
    """Display Redis status."""
    redis = ClientFactory.get_redis()
    if not redis.ping():
        return _service_unavailable("Redis")

    info = redis.info("server")
    mem_info = redis.info("memory")
    client_info = redis.info("clients")
    keyspace = redis.info("keyspace")

    lines = [
        "Redis Status",
        "=" * 40,
        f"  Version:     {info.get('redis_version', 'N/A')}",
        f"  Uptime:      {info.get('uptime_in_days', 'N/A')} days",
        f"  Memory:      {mem_info.get('used_memory_human', 'N/A')}",
        f"  Peak Memory: {mem_info.get('used_memory_peak_human', 'N/A')}",
        f"  Clients:     {client_info.get('connected_clients', 'N/A')}",
    ]

    # Keyspace
    for db_name, db_info in keyspace.items():
        if isinstance(db_info, dict):
            keys = db_info.get("keys", 0)
            lines.append(f"  {db_name}:       {keys} keys")

    # Kill switch state
    kill_data = redis.get_json("moneymaker:kill_switch")
    if kill_data and kill_data.get("active"):
        lines.append("\n  [!!] Kill switch is ACTIVE")
    else:
        lines.append("\n  Kill switch: INACTIVE")

    return "\n".join(lines)


def _sys_docker(*args: str) -> str:
    """Display Docker Compose service status."""
    docker = ClientFactory.get_docker()
    return docker.ps()


def _sys_network(*args: str) -> str:
    """Display network diagnostics — service reachability."""
    lines = ["Network Diagnostics", "=" * 40]

    endpoints = [
        ("Algo Engine Metrics", "localhost", int(os.environ.get("BRAIN_METRICS_PORT", "9092"))),
        (
            "Data Ingestion Health",
            "localhost",
            int(os.environ.get("DATA_INGESTION_HEALTH_PORT", "8081")),
        ),
        (
            "MT5 Bridge gRPC",
            "localhost",
            int(os.environ.get("MONEYMAKER_MT5_BRIDGE_GRPC_PORT", "50055")),
        ),
        ("PostgreSQL", "localhost", int(os.environ.get("MONEYMAKER_DB_PORT", "5432"))),
        ("Redis", "localhost", int(os.environ.get("MONEYMAKER_REDIS_PORT", "6379"))),
        ("Prometheus", "localhost", 9091),
        ("Grafana", "localhost", 3000),
        ("Dashboard", "localhost", int(os.environ.get("DASHBOARD_PORT", "8888"))),
    ]

    import socket

    for name, host, port in endpoints:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            status = "OPEN" if result == 0 else "CLOSED"
        except Exception:
            status = "ERROR"
        indicator = "[OK]" if status == "OPEN" else "[!!]"
        lines.append(f"  {indicator} {name:<25} :{port} {status}")

    return "\n".join(lines)


def _sys_env(*args: str) -> str:
    """Display MONEYMAKER environment variables (secrets masked)."""
    show_secrets = "--show-secrets" in args

    prefix_filter = (
        "MONEYMAKER_",
        "BRAIN_",
        "MT5_",
        "MAX_",
        "POLYGON_",
        "REDIS_",
        "GRAFANA_",
        "DI_DB_",
        "ADMIN_DB_",
        "TRAILING_",
        "SIGNAL_",
        "FRED_",
    )
    secret_words = ("KEY", "SECRET", "PASSWORD", "TOKEN", "DSN", "CREDENTIAL")

    lines = ["MONEYMAKER Environment Variables", "=" * 40]
    for key in sorted(os.environ.keys()):
        if not any(key.startswith(p) for p in prefix_filter):
            continue
        value = os.environ[key]
        if not show_secrets and any(w in key.upper() for w in secret_words):
            value = mask_secrets(value)
        lines.append(f"  {key:<40} = {value}")

    if not show_secrets:
        lines.append("\n  (Secrets masked. Use --show-secrets to reveal.)")

    return "\n".join(lines)


def _sys_ports(*args: str) -> str:
    """Display port allocation table."""
    ports = [
        ("PostgreSQL", int(os.environ.get("MONEYMAKER_DB_PORT", "5432"))),
        ("Redis", int(os.environ.get("MONEYMAKER_REDIS_PORT", "6379"))),
        ("Data Ingestion Health", int(os.environ.get("DATA_INGESTION_HEALTH_PORT", "8081"))),
        ("Data Ingestion ZMQ", 5555),
        ("Data Ingestion Metrics", int(os.environ.get("MONEYMAKER_METRICS_PORT", "9090"))),
        ("Algo Engine Metrics", int(os.environ.get("BRAIN_METRICS_PORT", "9092"))),
        ("Algo Engine gRPC", int(os.environ.get("MONEYMAKER_BRAIN_GRPC_PORT", "50054"))),
        ("MT5 Bridge gRPC", int(os.environ.get("MONEYMAKER_MT5_BRIDGE_GRPC_PORT", "50055"))),
        ("MT5 Bridge Metrics", 9094),
        ("Dashboard", int(os.environ.get("DASHBOARD_PORT", "8888"))),
        ("Prometheus", 9091),
        ("Grafana", 3000),
    ]

    lines = ["Port Allocation", "=" * 40]
    for name, port in ports:
        lines.append(f"  {name:<30} :{port}")

    return "\n".join(lines)


def _sys_uptime(*args: str) -> str:
    """Display service uptime from Docker inspect."""
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(_PROJECT_ROOT / "infra" / "docker" / "docker-compose.yml"),
                "ps",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return "[warning] Docker not available."

        import json

        lines = ["Service Uptime", "=" * 40]
        for line in result.stdout.strip().splitlines():
            try:
                svc = json.loads(line)
                name = svc.get("Name", svc.get("Service", "?"))
                state = svc.get("State", "?")
                status = svc.get("Status", "?")
                lines.append(f"  {name:<30} {state:<12} {status}")
            except json.JSONDecodeError:
                continue
        return "\n".join(lines) if len(lines) > 2 else "[info] No running containers."
    except Exception as exc:
        return f"[error] {exc}"


def _sys_gpu(*args: str) -> str:
    """Display AMD GPU status via rocm-smi."""
    try:
        result = subprocess.run(
            ["rocm-smi"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return f"GPU Status (AMD ROCm)\n{'=' * 40}\n{result.stdout.strip()}"
        return "[warning] rocm-smi returned an error."
    except FileNotFoundError:
        return "[info] ROCm not available on this system."
    except Exception as exc:
        return f"[error] GPU query failed: {exc}"


def _sys_disk(*args: str) -> str:
    """Display detailed disk usage by service directory."""
    try:
        import psutil

        disk = psutil.disk_usage("/")
        lines = [
            "Disk Usage",
            "=" * 40,
            f"  Total:  {disk.total / (1024**3):.1f} GB",
            f"  Used:   {disk.used / (1024**3):.1f} GB ({disk.percent:.1f}%)",
            f"  Free:   {disk.free / (1024**3):.1f} GB",
        ]
    except ImportError:
        lines = ["Disk Usage", "=" * 40, "  psutil not installed"]

    # Service directory sizes
    dirs = [
        ("algo-engine", _PROJECT_ROOT / "services" / "algo-engine"),
        ("data-ingestion", _PROJECT_ROOT / "services" / "data-ingestion"),
        ("mt5-bridge", _PROJECT_ROOT / "services" / "mt5-bridge"),
        ("console", _PROJECT_ROOT / "services" / "console"),
    ]

    lines.append("\n  Service Directories:")
    for name, path in dirs:
        if path.exists():
            try:
                result = subprocess.run(
                    ["du", "-sh", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                size = result.stdout.split()[0] if result.returncode == 0 else "?"
            except Exception:
                size = "?"
            lines.append(f"    {name:<25} {size}")

    return "\n".join(lines)


def register(registry: CommandRegistry) -> None:
    registry.register("sys", "status", _sys_status, "Full system status dashboard")
    registry.register("sys", "resources", _sys_resources, "CPU/RAM/GPU/Disk usage")
    registry.register("sys", "health", _sys_health, "Parallel health check (all services)")
    registry.register("sys", "db", _sys_db, "TimescaleDB status and table sizes")
    registry.register("sys", "redis", _sys_redis, "Redis status and memory")
    registry.register("sys", "docker", _sys_docker, "Docker Compose container status")
    registry.register("sys", "network", _sys_network, "Network diagnostics — port reachability")
    registry.register("sys", "env", _sys_env, "Environment variables (secrets masked)")
    registry.register("sys", "ports", _sys_ports, "Port allocation table")
    registry.register("sys", "uptime", _sys_uptime, "Service uptime from Docker")
    registry.register("sys", "gpu", _sys_gpu, "AMD GPU status (ROCm)")
    registry.register("sys", "disk", _sys_disk, "Detailed disk usage")
