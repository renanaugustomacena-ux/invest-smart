"""Shared test fixtures for the MONEYMAKER console."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure src/ package takes priority over the root-level moneymaker_console.py
_console_src = Path(__file__).resolve().parent.parent / "src"
if str(_console_src) not in sys.path:
    sys.path.insert(0, str(_console_src))
# Also remove current dir if it shadows the package
_console_root = str(Path(__file__).resolve().parent.parent)
if _console_root in sys.path:
    sys.path.remove(_console_root)
    sys.path.append(_console_root)

import pytest

from moneymaker_console.registry import CommandRegistry


@pytest.fixture()
def registry():
    """Return a fresh CommandRegistry with some test commands."""
    reg = CommandRegistry()
    reg.register("svc", "status", lambda: "all running", "Show service status")
    reg.register("svc", "restart", lambda name="all": f"restarted {name}", "Restart a service")
    reg.register("brain", "state", lambda: "brain active", "Show brain state")
    reg.register("exit", "", lambda: "bye", "Exit console", aliases=["q", "quit"])
    return reg


@pytest.fixture()
def mock_docker():
    """Return a mock DockerClient."""
    m = MagicMock()
    m.up.return_value = "[success] Services started"
    m.down.return_value = "[success] Services stopped"
    m.restart.return_value = "[success] Restarted"
    m.ps.return_value = "NAME  STATUS\nalgo  Up"
    m.logs.return_value = "log line 1\nlog line 2"
    m.scale.return_value = "[success] Scaled"
    m.exec_cmd.return_value = "[success] command output"
    m.config.return_value = "compose config output"
    m.pull.return_value = "[success] Pulled"
    return m


@pytest.fixture()
def mock_redis_client():
    """Return a mock RedisClient."""
    m = MagicMock()
    m.ping.return_value = True
    m.get.return_value = None
    m.get_json.return_value = None
    m.set.return_value = True
    m.set_json.return_value = True
    m.delete.return_value = True
    m.publish.return_value = True
    return m


@pytest.fixture()
def mock_db():
    """Return a mock PostgresClient."""
    m = MagicMock()
    m.ping.return_value = True
    m.query.return_value = []
    m.query_one.return_value = None
    m.execute.return_value = None
    return m


@pytest.fixture()
def mock_brain_client():
    """Return a mock BrainClient."""
    m = MagicMock()
    m.get_health.return_value = None
    return m


@pytest.fixture()
def mock_data_client():
    """Return a mock DataIngestionClient."""
    m = MagicMock()
    m.get_health.return_value = None
    m.get_metrics.return_value = None
    return m
