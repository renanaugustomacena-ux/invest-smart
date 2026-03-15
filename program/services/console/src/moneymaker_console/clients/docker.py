"""Docker Compose wrapper for service lifecycle management."""

from __future__ import annotations

from moneymaker_console.runner import (
    _DOCKER_COMPOSE,
    _PROJECT_ROOT,
    run_tool,
    run_tool_live,
)


class DockerClient:
    """Wraps docker compose commands targeting the MONEYMAKER stack."""

    def __init__(self) -> None:
        self._compose_file = str(_DOCKER_COMPOSE)
        self._cwd = _PROJECT_ROOT

    def _compose_cmd(self, *args: str) -> list[str]:
        """Build a docker compose command list."""
        return [
            "docker",
            "compose",
            "-f",
            self._compose_file,
            *args,
        ]

    def up(self, *services: str, detach: bool = True) -> str:
        """Start services."""
        cmd = self._compose_cmd("up")
        if detach:
            cmd.append("-d")
        cmd.extend(services)
        return run_tool_live(cmd, cwd=self._cwd)

    def down(self, *services: str) -> str:
        """Stop services."""
        cmd = self._compose_cmd("down")
        cmd.extend(services)
        return run_tool(cmd, cwd=self._cwd)

    def restart(self, service: str) -> str:
        """Restart a specific service."""
        return run_tool(self._compose_cmd("restart", service), cwd=self._cwd)

    def ps(self) -> str:
        """List running containers."""
        return run_tool(self._compose_cmd("ps", "--format", "table"), cwd=self._cwd)

    def logs(self, service: str, tail: int = 50, follow: bool = False) -> str:
        """Show logs for a service."""
        cmd = self._compose_cmd("logs", "--tail", str(tail))
        if follow:
            cmd.append("-f")
        cmd.append(service)
        if follow:
            return run_tool_live(cmd, cwd=self._cwd)
        return run_tool(cmd, cwd=self._cwd)

    def build(self, *services: str, no_cache: bool = False) -> str:
        """Build service images."""
        cmd = self._compose_cmd("build")
        if no_cache:
            cmd.append("--no-cache")
        cmd.extend(services)
        return run_tool_live(cmd, cwd=self._cwd)

    def exec_cmd(self, service: str, command: str) -> str:
        """Execute a command inside a running container."""
        cmd = self._compose_cmd("exec", service, *command.split())
        return run_tool(cmd, cwd=self._cwd)

    def scale(self, service: str, replicas: int) -> str:
        """Scale a service to N replicas."""
        return run_tool(
            self._compose_cmd("up", "-d", "--scale", f"{service}={replicas}", service),
            cwd=self._cwd,
        )

    def pull(self, *services: str) -> str:
        """Pull latest images."""
        cmd = self._compose_cmd("pull")
        cmd.extend(services)
        return run_tool(cmd, cwd=self._cwd)

    def config(self) -> str:
        """Show effective compose config."""
        return run_tool(self._compose_cmd("config"), cwd=self._cwd)
