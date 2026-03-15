"""Test suite orchestration commands."""

from __future__ import annotations

from moneymaker_console.registry import CommandRegistry
from moneymaker_console.runner import (
    _ALGO_ENGINE_DIR,
    _PROJECT_ROOT,
    _SERVICES_DIR,
    run_tool_live,
)


def _test_all(*args: str) -> str:
    """Run the complete Algo Engine pytest suite."""
    return run_tool_live(
        ["python3", "-m", "pytest", "-v", "--tb=short"],
        cwd=str(_ALGO_ENGINE_DIR),
        env_extra={"PYTHONPATH": str(_ALGO_ENGINE_DIR / "src")},
    )


def _test_brain_verify(*args: str) -> str:
    """Run Brain Verification tests."""
    return run_tool_live(
        ["python3", "-m", "pytest", "tests/brain_verification/", "-v", "--tb=short"],
        cwd=str(_ALGO_ENGINE_DIR),
        env_extra={"PYTHONPATH": str(_ALGO_ENGINE_DIR / "src")},
    )


def _test_cascade(*args: str) -> str:
    """Run cascade / e2e tests."""
    return run_tool_live(
        ["python3", "-m", "pytest", "tests/e2e/", "-v", "--tb=short"],
        cwd=str(_ALGO_ENGINE_DIR),
        env_extra={"PYTHONPATH": str(_ALGO_ENGINE_DIR / "src")},
    )


def _test_go(*args: str) -> str:
    """Run Go test suite for Data Ingestion."""
    return run_tool_live(
        ["go", "test", "./...", "-v"],
        cwd=str(_SERVICES_DIR / "data-ingestion"),
    )


def _test_mt5(*args: str) -> str:
    """Run MT5 Bridge tests."""
    bridge_dir = _SERVICES_DIR / "mt5-bridge"
    return run_tool_live(
        ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=str(bridge_dir),
        env_extra={"PYTHONPATH": str(bridge_dir / "src")},
    )


def _test_common(*args: str) -> str:
    """Run shared Python library tests."""
    common_dir = _PROJECT_ROOT / "shared" / "python-common"
    return run_tool_live(
        ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=str(common_dir),
        env_extra={"PYTHONPATH": str(common_dir / "src")},
    )


def _test_suite(*args: str) -> str:
    """Run ALL test suites sequentially."""
    results = []
    suites = [
        ("Algo Engine", _test_all),
        ("Go (Data Ingestion)", _test_go),
        ("MT5 Bridge", _test_mt5),
        ("Shared Common", _test_common),
    ]
    for name, fn in suites:
        results.append(f"\n{'=' * 60}\n  Running: {name}\n{'=' * 60}")
        try:
            out = fn()
            passed = "PASSED" if "passed" in out.lower() or "ok" in out.lower() else "CHECK OUTPUT"
            results.append(out)
            results.append(f"  >> {name}: {passed}")
        except Exception as exc:
            results.append(f"  >> {name}: FAILED ({exc})")
    return "\n".join(results)


def _test_lint(*args: str) -> str:
    """Run linting tools."""
    results = []
    # Python
    results.append(
        run_tool_live(
            ["python3", "-m", "ruff", "check", "."],
            cwd=str(_ALGO_ENGINE_DIR),
        )
    )
    return "\n".join(results) if results else "Lint complete."


def _test_typecheck(*args: str) -> str:
    """Run mypy type checking."""
    return run_tool_live(
        ["python3", "-m", "mypy", "src/algo_engine/", "--ignore-missing-imports"],
        cwd=str(_ALGO_ENGINE_DIR),
    )


def _test_ci(*args: str) -> str:
    """Run the full CI pipeline."""
    steps = [
        ("Lint", _test_lint),
        ("Typecheck", _test_typecheck),
        ("Test", _test_all),
    ]
    results = []
    for name, fn in steps:
        results.append(f"\n--- CI Step: {name} ---")
        try:
            results.append(fn())
        except Exception as exc:
            results.append(f"  FAILED: {exc}")
            results.append(f"\n[error] CI failed at step: {name}")
            return "\n".join(results)
    results.append("\n[success] CI pipeline completed.")
    return "\n".join(results)


def _test_coverage(*args: str) -> str:
    """Run tests with coverage reporting."""
    return run_tool_live(
        [
            "python3",
            "-m",
            "pytest",
            "--cov=algo_engine",
            "--cov-report=term-missing",
            "-v",
            "--tb=short",
        ],
        cwd=str(_ALGO_ENGINE_DIR),
        env_extra={"PYTHONPATH": str(_ALGO_ENGINE_DIR / "src")},
    )


def _test_specific(*args: str) -> str:
    """Run a specific test file or directory."""
    if not args:
        return "Usage: test specific PATH"
    path = args[0]
    return run_tool_live(
        ["python3", "-m", "pytest", path, "-v", "--tb=short"],
        cwd=str(_ALGO_ENGINE_DIR),
        env_extra={"PYTHONPATH": str(_ALGO_ENGINE_DIR / "src")},
    )


def register(registry: CommandRegistry) -> None:
    registry.register(
        "test", "all", _test_all, "Run complete Algo Engine test suite", timeout_sec=300
    )
    registry.register(
        "test", "brain-verify", _test_brain_verify, "Run Brain Verification tests", timeout_sec=120
    )
    registry.register("test", "cascade", _test_cascade, "Run cascade / e2e tests", timeout_sec=300)
    registry.register("test", "go", _test_go, "Run Go Data Ingestion tests", timeout_sec=120)
    registry.register("test", "mt5", _test_mt5, "Run MT5 Bridge tests", timeout_sec=120)
    registry.register(
        "test", "common", _test_common, "Run shared Python library tests", timeout_sec=120
    )
    registry.register("test", "suite", _test_suite, "Run ALL test suites", timeout_sec=600)
    registry.register("test", "lint", _test_lint, "Run linting tools", timeout_sec=120)
    registry.register(
        "test", "typecheck", _test_typecheck, "Run mypy type checking", timeout_sec=120
    )
    registry.register("test", "ci", _test_ci, "Run full CI pipeline", timeout_sec=600)
    registry.register(
        "test", "coverage", _test_coverage, "Run tests with coverage", timeout_sec=300
    )
    registry.register(
        "test", "specific", _test_specific, "Run a specific test file", timeout_sec=120
    )
