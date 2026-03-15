"""Tests for utility tool commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from moneymaker_console.commands.tool import (
    _tool_benchmark,
    _tool_env_check,
    _tool_list,
    _tool_logs,
    _tool_motd,
    _tool_redis_cli,
    _tool_shell,
    _tool_sql,
    _tool_version,
    _tool_whoami,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestToolList:
    def test_no_registry(self):
        import moneymaker_console.commands.tool as t
        old = t._registry_ref
        t._registry_ref = None
        result = _tool_list()
        t._registry_ref = old
        assert "[error]" in result

    def test_with_registry(self):
        reg = CommandRegistry()
        register(reg)
        result = _tool_list()
        assert "Command Reference" in result


class TestToolLogs:
    def test_no_log_file(self):
        result = _tool_logs()
        assert "No console log" in result or "Recent" in result


class TestToolEnvCheck:
    def test_env_check(self):
        result = _tool_env_check()
        assert "Environment" in result
        assert "Python" in result


class TestToolShell:
    def test_shell_info(self):
        result = _tool_shell()
        assert "Shell" in result or "shell" in result or "info" in result


class TestToolSql:
    def test_no_args(self):
        assert "Usage" in _tool_sql()

    def test_non_select_blocked(self):
        result = _tool_sql("UPDATE foo SET x=1")
        assert "[error]" in result

    def test_ddl_blocked(self):
        result = _tool_sql("DROP TABLE foo", "--unsafe")
        assert "[error]" in result
        assert "DROP" in result

    def test_truncate_blocked(self):
        result = _tool_sql("TRUNCATE table foo", "--unsafe")
        assert "[error]" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_select_success(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [(1, "foo"), (2, "bar")]
        mock_cf.get_postgres.return_value = mock_db
        result = _tool_sql("SELECT * FROM test")
        assert "2 rows" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_select_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _tool_sql("SELECT * FROM test")
        assert "no rows" in result.lower()

    @patch("moneymaker_console.clients.ClientFactory")
    def test_select_error(self, mock_cf):
        mock_cf.get_postgres.side_effect = Exception("db error")
        result = _tool_sql("SELECT 1")
        assert "[error]" in result


class TestToolRedisCli:
    def test_no_args(self):
        assert "Usage" in _tool_redis_cli()

    @patch("moneymaker_console.clients.ClientFactory")
    def test_get(self, mock_cf):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "myvalue"
        mock_cf.get_redis.return_value = mock_redis
        result = _tool_redis_cli("GET", "mykey")
        assert "myvalue" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_ping(self, mock_cf):
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_cf.get_redis.return_value = mock_redis
        result = _tool_redis_cli("PING")
        assert "PONG" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_info(self, mock_cf):
        mock_redis = MagicMock()
        mock_redis.info.return_value = {"redis_version": "7.2"}
        mock_cf.get_redis.return_value = mock_redis
        result = _tool_redis_cli("INFO")
        assert "7.2" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_unknown_cmd(self, mock_cf):
        mock_redis = MagicMock()
        mock_cf.get_redis.return_value = mock_redis
        result = _tool_redis_cli("FLUSHALL")
        assert "info" in result.lower()


class TestToolBenchmark:
    @patch("moneymaker_console.clients.ClientFactory")
    def test_benchmark(self, mock_cf):
        mock_db = MagicMock()
        mock_db.ping.return_value = True
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_brain = MagicMock()
        mock_brain.is_healthy.return_value = True
        mock_mt5 = MagicMock()
        mock_mt5.is_healthy.return_value = True

        mock_cf.get_postgres.return_value = mock_db
        mock_cf.get_redis.return_value = mock_redis
        mock_cf.get_brain.return_value = mock_brain
        mock_cf.get_mt5.return_value = mock_mt5

        result = _tool_benchmark()
        assert "Benchmark" in result
        assert "ms" in result


class TestToolVersion:
    @patch("moneymaker_console.commands.tool.run_tool")
    def test_version(self, mock_run):
        mock_run.return_value = "Docker version 24.0"
        result = _tool_version()
        assert "Version" in result


class TestToolWhoami:
    def test_whoami(self):
        result = _tool_whoami()
        assert "Operator" in result


class TestToolMotd:
    @patch("moneymaker_console.clients.ClientFactory")
    def test_motd(self, mock_cf):
        mock_db = MagicMock()
        mock_db.ping.return_value = True
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_cf.get_postgres.return_value = mock_db
        mock_cf.get_redis.return_value = mock_redis
        result = _tool_motd()
        assert "MONEYMAKER" in result


class TestToolRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "tool" in reg.categories
        expected = ["list", "logs", "env-check", "shell", "sql",
                    "redis-cli", "benchmark", "version", "whoami", "motd"]
        for cmd in expected:
            assert cmd in reg._commands["tool"]
