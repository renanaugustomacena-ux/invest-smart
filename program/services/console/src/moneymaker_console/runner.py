# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Subprocess runners for executing external tools.

Provides ``run_tool`` (capture output) and ``run_tool_live`` (stream output).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Path constants (resolved at import time from the console package location)
# ---------------------------------------------------------------------------

_PACKAGE_DIR = Path(__file__).resolve().parent  # src/moneymaker_console/
_CONSOLE_DIR = _PACKAGE_DIR.parent.parent  # services/console/
_SERVICES_DIR = _CONSOLE_DIR.parent  # services/
_PROJECT_ROOT = _SERVICES_DIR.parent  # program/
_ALGO_ENGINE_DIR = _SERVICES_DIR / "algo-engine"
_ALGO_ENGINE_TESTS = _ALGO_ENGINE_DIR / "tests"
_DATA_INGESTION_DIR = _SERVICES_DIR / "data-ingestion"
_MT5_BRIDGE_DIR = _SERVICES_DIR / "mt5-bridge"
_SHARED_DIR = _PROJECT_ROOT / "shared"
_INFRA_DIR = _PROJECT_ROOT / "infra"
_DOCKER_COMPOSE = _INFRA_DIR / "docker" / "docker-compose.yml"
_LOG_DIR = _CONSOLE_DIR / "logs"

OUTPUT_TRIM_LINES = 80
SUBPROCESS_TIMEOUT_S = 300
BUILD_TIMEOUT_S = 600


def _build_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build environment dict with PYTHONPATH set."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_PROJECT_ROOT)
    if extra:
        env.update(extra)
    return env


def run_tool(
    cmd: list[str],
    cwd: Path | None = None,
    timeout: int = SUBPROCESS_TIMEOUT_S,
    env_extra: dict[str, str] | None = None,
) -> str:
    """Execute a command and capture output (trimmed to N lines)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd or _PROJECT_ROOT),
            env=_build_env(env_extra),
        )
        output = result.stdout + result.stderr
        lines = output.strip().splitlines()
        if len(lines) > OUTPUT_TRIM_LINES:
            lines = lines[:OUTPUT_TRIM_LINES] + [
                f"... ({len(lines) - OUTPUT_TRIM_LINES} lines omitted)"
            ]
        status = "[success]" if result.returncode == 0 else "[error]"
        return f"{status} {chr(10).join(lines)}"
    except subprocess.TimeoutExpired:
        return f"[error] Timeout ({timeout}s)"
    except FileNotFoundError:
        return f"[error] Command not found: {cmd[0]}"
    except Exception as exc:
        return f"[error] {exc}"


def run_tool_live(
    cmd: list[str],
    cwd: Path | None = None,
    timeout: int = BUILD_TIMEOUT_S,
    env_extra: dict[str, str] | None = None,
) -> str:
    """Execute a command with streaming line-by-line output."""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(cwd or _PROJECT_ROOT),
            env=_build_env(env_extra),
        )
        lines: list[str] = []
        for line in proc.stdout:  # type: ignore[union-attr]
            stripped = line.rstrip()
            print(stripped)
            lines.append(stripped)
        proc.wait(timeout=timeout)
        status = "[success]" if proc.returncode == 0 else "[error]"
        return f"{status} Completed (exit code: {proc.returncode})"
    except subprocess.TimeoutExpired:
        proc.kill()  # type: ignore[possibly-undefined]
        return f"[error] Timeout ({timeout}s)"
    except FileNotFoundError:
        return f"[error] Command not found: {cmd[0]}"
    except Exception as exc:
        return f"[error] {exc}"
