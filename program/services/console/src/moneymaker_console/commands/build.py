"""Build and container management commands."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry
from moneymaker_console.runner import _PROJECT_ROOT, run_tool, run_tool_live


def _build_all(*args: str) -> str:
    """Build all Docker images."""
    no_cache = "--no-cache" in args
    try:
        from moneymaker_console.clients import ClientFactory
        return ClientFactory.get_docker().build(no_cache=no_cache)
    except Exception as exc:
        return f"[error] {exc}"


def _build_brain(*args: str) -> str:
    """Build Algo Engine Docker image."""
    no_cache = "--no-cache" in args
    try:
        from moneymaker_console.clients import ClientFactory
        return ClientFactory.get_docker().build("algo-engine", no_cache=no_cache)
    except Exception as exc:
        return f"[error] {exc}"


def _build_ingestion(*args: str) -> str:
    """Build Data Ingestion Docker image."""
    no_cache = "--no-cache" in args
    try:
        from moneymaker_console.clients import ClientFactory
        return ClientFactory.get_docker().build("data-ingestion", no_cache=no_cache)
    except Exception as exc:
        return f"[error] {exc}"


def _build_bridge(*args: str) -> str:
    """Build MT5 Bridge Docker image."""
    no_cache = "--no-cache" in args
    try:
        from moneymaker_console.clients import ClientFactory
        return ClientFactory.get_docker().build("mt5-bridge", no_cache=no_cache)
    except Exception as exc:
        return f"[error] {exc}"


def _build_dashboard(*args: str) -> str:
    """Build Dashboard Docker image."""
    no_cache = "--no-cache" in args
    try:
        from moneymaker_console.clients import ClientFactory
        return ClientFactory.get_docker().build("dashboard", no_cache=no_cache)
    except Exception as exc:
        return f"[error] {exc}"


def _build_external(*args: str) -> str:
    """Build External Data service image."""
    no_cache = "--no-cache" in args
    try:
        from moneymaker_console.clients import ClientFactory
        return ClientFactory.get_docker().build("external-data", no_cache=no_cache)
    except Exception as exc:
        return f"[error] {exc}"


def _build_test_only(*args: str) -> str:
    """Run all test suites without building images."""
    from moneymaker_console.commands.test_cmds import _test_suite
    return _test_suite()


def _build_proto(*args: str) -> str:
    """Recompile Protocol Buffer definitions."""
    proto_dir = _PROJECT_ROOT / "shared" / "proto"
    if not proto_dir.exists():
        return f"[error] Proto directory not found: {proto_dir}"
    return run_tool_live(
        ["make", "proto"],
        cwd=str(_PROJECT_ROOT),
    )


def _build_status(*args: str) -> str:
    """Display build status of all Docker images."""
    return run_tool(
        ["docker", "images", "--filter", "reference=moneymaker-*",
         "--format", "table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}\\t{{.CreatedAt}}"],
    )


def _build_clean(*args: str) -> str:
    """Remove build artifacts."""
    lines = ["Cleaning build artifacts..."]
    # Clean __pycache__
    result = run_tool(
        ["find", str(_PROJECT_ROOT), "-type", "d", "-name", "__pycache__",
         "-exec", "rm", "-rf", "{}", "+"],
    )
    lines.append("  Removed __pycache__ directories")

    # Clean .pyc files
    run_tool(
        ["find", str(_PROJECT_ROOT), "-name", "*.pyc", "-delete"],
    )
    lines.append("  Removed .pyc files")

    if "--docker" in args:
        run_tool(["docker", "builder", "prune", "-f"])
        lines.append("  Pruned Docker build cache")

    lines.append("[success] Clean complete.")
    return "\n".join(lines)


def _build_push(*args: str) -> str:
    """Push Docker images to registry."""
    if not args:
        return "Usage: build push [SERVICE]  (pushes to configured registry)"
    service = args[0]
    return run_tool_live(
        ["docker", "compose", "-f",
         str(_PROJECT_ROOT / "infra" / "docker" / "docker-compose.yml"),
         "push", service],
        cwd=str(_PROJECT_ROOT),
    )


def _build_tag(*args: str) -> str:
    """Tag Docker images with a version."""
    if not args:
        return "Usage: build tag VERSION"
    version = args[0]
    git_hash = run_tool(["git", "rev-parse", "--short", "HEAD"]).strip()
    lines = [f"Tagging images with {version} (git: {git_hash})"]
    images = run_tool(
        ["docker", "images", "--filter", "reference=moneymaker-*",
         "--format", "{{.Repository}}:{{.Tag}}"]
    )
    for img in images.strip().splitlines():
        if img:
            repo = img.split(":")[0]
            run_tool(["docker", "tag", img, f"{repo}:{version}"])
            run_tool(["docker", "tag", img, f"{repo}:{git_hash}"])
            lines.append(f"  Tagged {repo}:{version} and {repo}:{git_hash}")
    return "\n".join(lines)


def register(registry: CommandRegistry) -> None:
    registry.register("build", "all", _build_all, "Build all Docker images", timeout_sec=600)
    registry.register("build", "brain", _build_brain, "Build Algo Engine image", timeout_sec=300)
    registry.register("build", "ingestion", _build_ingestion, "Build Data Ingestion image", timeout_sec=300)
    registry.register("build", "bridge", _build_bridge, "Build MT5 Bridge image", timeout_sec=300)
    registry.register("build", "dashboard", _build_dashboard, "Build Dashboard image", timeout_sec=300)
    registry.register("build", "external", _build_external, "Build External Data image", timeout_sec=300)
    registry.register("build", "test-only", _build_test_only, "Run tests without building", timeout_sec=300)
    registry.register("build", "proto", _build_proto, "Recompile protobuf definitions", timeout_sec=120)
    registry.register("build", "status", _build_status, "Display Docker image status")
    registry.register("build", "clean", _build_clean, "Remove build artifacts")
    registry.register("build", "push", _build_push, "Push images to registry", timeout_sec=300)
    registry.register("build", "tag", _build_tag, "Tag images with version")
