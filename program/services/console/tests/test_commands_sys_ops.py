"""Tests for system operations commands."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from moneymaker_console.commands.sys_ops import (
    _sys_db,
    _sys_docker,
    _sys_env,
    _sys_health,
    _sys_network,
    _sys_ports,
    _sys_redis,
    _sys_resources,
    _sys_status,
    register,
)
from moneymaker_console.registry import CommandRegistry


@patch("moneymaker_console.commands.sys_ops.subprocess")
@patch("moneymaker_console.commands.sys_ops.ClientFactory")
class TestSysStatus:
    def test_all_services_up(self, mock_cf, mock_sub):
        mock_pg = MagicMock()
        mock_pg.ping.return_value = True
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_brain = MagicMock()
        mock_brain.is_healthy.return_value = True
        mock_mt5 = MagicMock()
        mock_mt5.is_healthy.return_value = True
        mock_data = MagicMock()
        mock_data.is_healthy.return_value = True

        mock_cf.get_postgres.return_value = mock_pg
        mock_cf.get_redis.return_value = mock_redis
        mock_cf.get_brain.return_value = mock_brain
        mock_cf.get_mt5.return_value = mock_mt5
        mock_cf.get_data.return_value = mock_data

        mock_sub.run.return_value = MagicMock(returncode=0, stdout="5 containers")

        result = _sys_status()
        assert "System Status" in result
        assert "OK" in result

    def test_services_down(self, mock_cf, mock_sub):
        mock_pg = MagicMock()
        mock_pg.ping.return_value = False
        mock_redis = MagicMock()
        mock_redis.ping.return_value = False
        mock_brain = MagicMock()
        mock_brain.is_healthy.return_value = False
        mock_mt5 = MagicMock()
        mock_mt5.is_healthy.return_value = False
        mock_data = MagicMock()
        mock_data.is_healthy.return_value = False

        mock_cf.get_postgres.return_value = mock_pg
        mock_cf.get_redis.return_value = mock_redis
        mock_cf.get_brain.return_value = mock_brain
        mock_cf.get_mt5.return_value = mock_mt5
        mock_cf.get_data.return_value = mock_data

        mock_sub.run.return_value = MagicMock(returncode=1, stdout="")

        result = _sys_status()
        assert "System Status" in result
        assert "NOT CONNECTED" in result


@patch("moneymaker_console.commands.sys_ops.ClientFactory")
class TestSysDb:
    def test_db_connected(self, mock_cf):
        mock_db = MagicMock()
        mock_db.ping.return_value = True
        mock_db.query_one.side_effect = [
            ("PostgreSQL 16.1 on x86_64",),  # version
            ("50 MB",),  # size
        ]
        mock_db.query.return_value = [
            ("active", 5),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _sys_db()
        assert "TimescaleDB" in result or "PostgreSQL" in result

    def test_db_not_connected(self, mock_cf):
        mock_db = MagicMock()
        mock_db.ping.return_value = False
        mock_cf.get_postgres.return_value = mock_db
        result = _sys_db()
        assert "[warning]" in result


@patch("moneymaker_console.commands.sys_ops.ClientFactory")
class TestSysRedis:
    def test_redis_connected(self, mock_cf):
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {
            "redis_version": "7.2",
            "uptime_in_days": 10,
            "used_memory_human": "10M",
            "used_memory_peak_human": "15M",
            "connected_clients": 5,
        }
        mock_redis.get_json.return_value = None
        mock_cf.get_redis.return_value = mock_redis
        result = _sys_redis()
        assert "Redis" in result

    def test_redis_not_connected(self, mock_cf):
        mock_redis = MagicMock()
        mock_redis.ping.return_value = False
        mock_cf.get_redis.return_value = mock_redis
        result = _sys_redis()
        assert "[warning]" in result


@patch("moneymaker_console.commands.sys_ops.ClientFactory")
class TestSysDocker:
    def test_docker_status(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.ps.return_value = "RUNNING"
        mock_cf.get_docker.return_value = mock_docker
        result = _sys_docker()
        assert result is not None


class TestSysResources:
    @patch("moneymaker_console.commands.sys_ops.subprocess")
    def test_resources(self, mock_sub):
        mock_sub.run.return_value = MagicMock(returncode=0, stdout="cpu info\n")
        result = _sys_resources()
        assert "Resource" in result or "CPU" in result or "System" in result or "psutil" in result


class TestSysPorts:
    def test_shows_port_table(self):
        result = _sys_ports()
        assert "Port" in result


class TestSysEnv:
    def test_shows_env_header(self):
        result = _sys_env()
        assert "MONEYMAKER" in result

    def test_masks_secrets(self):
        with patch.dict(os.environ, {"MONEYMAKER_API_KEY": "supersecret"}):
            result = _sys_env()
            assert "supersecret" not in result

    def test_show_secrets_flag(self):
        with patch.dict(os.environ, {"MONEYMAKER_API_KEY": "supersecret"}):
            result = _sys_env("--show-secrets")
            assert "supersecret" in result


class TestSysNetwork:
    def test_network_check(self):
        result = _sys_network()
        assert "Network" in result


@patch("moneymaker_console.commands.sys_ops.subprocess")
@patch("moneymaker_console.commands.sys_ops.ClientFactory")
class TestSysHealth:
    def test_health_check(self, mock_cf, mock_sub):
        mock_pg = MagicMock()
        mock_pg.ping.return_value = True
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_brain = MagicMock()
        mock_brain.is_healthy.return_value = True
        mock_mt5 = MagicMock()
        mock_mt5.is_healthy.return_value = True
        mock_data = MagicMock()
        mock_data.is_healthy.return_value = True

        mock_cf.get_postgres.return_value = mock_pg
        mock_cf.get_redis.return_value = mock_redis
        mock_cf.get_brain.return_value = mock_brain
        mock_cf.get_mt5.return_value = mock_mt5
        mock_cf.get_data.return_value = mock_data

        mock_sub.run.return_value = MagicMock(returncode=0)

        result = _sys_health()
        assert "Health" in result


class TestSysRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "sys" in reg.categories
        expected = [
            "status",
            "resources",
            "health",
            "db",
            "redis",
            "docker",
            "network",
            "env",
            "ports",
        ]
        for cmd in expected:
            assert cmd in reg._commands["sys"]
