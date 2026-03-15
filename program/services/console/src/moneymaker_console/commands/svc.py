"""Service lifecycle management — Docker Compose operations."""

from __future__ import annotations

from moneymaker_console.clients import ClientFactory
from moneymaker_console.registry import CommandRegistry
from moneymaker_console.runner import run_tool, run_tool_live, _PROJECT_ROOT, _DOCKER_COMPOSE


def _svc_up(*args: str) -> str:
    """Start all or specific services."""
    docker = ClientFactory.get_docker()
    return docker.up(*args)


def _svc_down(*args: str) -> str:
    """Stop all or specific services."""
    docker = ClientFactory.get_docker()
    return docker.down(*args)


def _svc_restart(*args: str) -> str:
    """Restart a specific service."""
    if not args:
        return "[error] Usage: svc restart <service>"
    docker = ClientFactory.get_docker()
    return docker.restart(args[0])


def _svc_status(*args: str) -> str:
    """Display Docker Compose service status."""
    docker = ClientFactory.get_docker()
    return docker.ps()


def _svc_logs(*args: str) -> str:
    """Show logs for a service."""
    if not args:
        return "[error] Usage: svc logs <service> [--follow] [--tail N]"
    service = args[0]
    follow = "--follow" in args or "-f" in args
    tail = 50
    for i, a in enumerate(args):
        if a == "--tail" and i + 1 < len(args):
            try:
                tail = int(args[i + 1])
            except ValueError:
                pass
    docker = ClientFactory.get_docker()
    return docker.logs(service, tail=tail, follow=follow)


def _svc_scale(*args: str) -> str:
    """Scale a service to N replicas."""
    if len(args) < 2:
        return "[error] Usage: svc scale <service> <replicas>"
    service = args[0]
    try:
        replicas = int(args[1])
    except ValueError:
        return f"[error] Invalid replica count: {args[1]}"
    docker = ClientFactory.get_docker()
    return docker.scale(service, replicas)


def _svc_exec(*args: str) -> str:
    """Execute a command inside a running container."""
    if len(args) < 2:
        return "[error] Usage: svc exec <service> <command...>"
    service = args[0]
    command = " ".join(args[1:])
    docker = ClientFactory.get_docker()
    return docker.exec_cmd(service, command)


def _svc_inspect(*args: str) -> str:
    """Display detailed container inspection data."""
    if not args:
        return "[error] Usage: svc inspect <service>"
    cmd = [
        "docker",
        "compose",
        "-f",
        str(_DOCKER_COMPOSE),
        "ps",
        "--format",
        "json",
        args[0],
    ]
    return run_tool(cmd, cwd=_PROJECT_ROOT)


def _svc_pull(*args: str) -> str:
    """Pull latest Docker images."""
    docker = ClientFactory.get_docker()
    return docker.pull(*args)


def _svc_prune(*args: str) -> str:
    """Remove stopped containers, unused images, and dangling volumes."""
    return run_tool(
        ["docker", "system", "prune", "-f"],
        cwd=_PROJECT_ROOT,
    )


def _svc_compose_config(*args: str) -> str:
    """Show effective Docker Compose config."""
    docker = ClientFactory.get_docker()
    return docker.config()


def _svc_health(*args: str) -> str:
    """Run Docker health checks for services."""
    cmd = [
        "docker",
        "compose",
        "-f",
        str(_DOCKER_COMPOSE),
        "ps",
        "--format",
        "table",
    ]
    return run_tool(cmd, cwd=_PROJECT_ROOT)


def _svc_launch(*args: str) -> str:
    """Launch the full MONEYMAKER stack with validation."""
    script = _PROJECT_ROOT / "scripts" / "launch.sh"
    if not script.exists():
        return "[error] Launch script not found at scripts/launch.sh"
    cmd = ["bash", str(script)]
    if "--no-build" in args:
        cmd.append("--no-build")
    return run_tool_live(cmd, cwd=_PROJECT_ROOT)


def register(registry: CommandRegistry) -> None:
    registry.register("svc", "up", _svc_up, "Start services (docker compose up)", timeout_sec=120)
    registry.register(
        "svc", "down", _svc_down, "Stop services (docker compose down)", timeout_sec=120
    )
    registry.register("svc", "restart", _svc_restart, "Restart a service", timeout_sec=120)
    registry.register("svc", "status", _svc_status, "Container status")
    registry.register("svc", "logs", _svc_logs, "Service logs [--follow] [--tail N]")
    registry.register("svc", "scale", _svc_scale, "Scale service replicas", timeout_sec=120)
    registry.register("svc", "exec", _svc_exec, "Execute command in container", timeout_sec=120)
    registry.register("svc", "inspect", _svc_inspect, "Container inspection details")
    registry.register("svc", "pull", _svc_pull, "Pull latest images", timeout_sec=300)
    registry.register(
        "svc", "prune", _svc_prune, "Prune unused Docker resources", requires_confirmation=True
    )
    registry.register("svc", "compose-config", _svc_compose_config, "Show effective compose config")
    registry.register("svc", "health", _svc_health, "Docker health check status")
    registry.register(
        "svc",
        "launch",
        _svc_launch,
        "Launch full stack with validation [--no-build]",
        timeout_sec=300,
    )
