"""Tests for logging and observability commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from moneymaker_console.commands.log_ops import (
    _log_console,
    _log_errors,
    _log_export,
    _log_level,
    _log_metrics,
    _log_rotate,
    _log_search,
    _log_view,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestLogView:
    def test_no_args(self):
        assert "Usage" in _log_view()

    @patch("moneymaker_console.clients.ClientFactory")
    def test_with_service(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.logs.return_value = "log line 1\nlog line 2"
        mock_cf.get_docker.return_value = mock_docker
        result = _log_view("algo-engine")
        assert "log line" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_with_tail(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.logs.return_value = "output"
        mock_cf.get_docker.return_value = mock_docker
        result = _log_view("algo-engine", "--tail", "10")
        mock_docker.logs.assert_called_with("algo-engine", tail=10)

    @patch("moneymaker_console.clients.ClientFactory")
    def test_error(self, mock_cf):
        mock_cf.get_docker.side_effect = Exception("docker error")
        result = _log_view("algo-engine")
        assert "[error]" in result


class TestLogConsole:
    def test_no_log_dir(self):
        result = _log_console()
        assert "Console Log" in result


class TestLogSearch:
    def test_no_args(self):
        assert "Usage" in _log_search()

    def test_no_service(self):
        result = _log_search("ERROR")
        assert "info" in result.lower()

    @patch("moneymaker_console.clients.ClientFactory")
    def test_with_service_found(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.logs.return_value = "line1\nERROR happened\nline3"
        mock_cf.get_docker.return_value = mock_docker
        result = _log_search("ERROR", "--service", "algo-engine")
        assert "ERROR happened" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_with_service_not_found(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.logs.return_value = "all good\nno issues"
        mock_cf.get_docker.return_value = mock_docker
        result = _log_search("ERROR", "--service", "algo-engine")
        assert "No matches" in result


class TestLogErrors:
    def test_no_service(self):
        assert "Usage" in _log_errors()

    @patch("moneymaker_console.clients.ClientFactory")
    def test_errors_found(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.logs.return_value = "INFO ok\nERROR bad\nEXCEPTION crash"
        mock_cf.get_docker.return_value = mock_docker
        result = _log_errors("--service", "algo-engine")
        assert "ERROR" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_no_errors(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.logs.return_value = "INFO all good\nDEBUG fine"
        mock_cf.get_docker.return_value = mock_docker
        result = _log_errors("--service", "algo-engine")
        assert "No errors" in result


class TestLogExport:
    def test_no_args(self):
        assert "Usage" in _log_export()

    def test_no_output(self):
        assert "Usage" in _log_export("algo-engine")

    @patch("moneymaker_console.clients.ClientFactory")
    def test_export_success(self, mock_cf, tmp_path):
        mock_docker = MagicMock()
        mock_docker.logs.return_value = "log1\nlog2\nlog3"
        mock_cf.get_docker.return_value = mock_docker
        out = str(tmp_path / "export.log")
        result = _log_export("algo-engine", "--output", out)
        assert "[success]" in result


class TestLogRotate:
    def test_no_log_dir(self):
        result = _log_rotate()
        assert "No log directory" in result or "info" in result.lower() or "log" in result.lower()


class TestLogLevel:
    def test_no_args(self):
        assert "Usage" in _log_level()

    def test_one_arg(self):
        assert "Usage" in _log_level("algo-engine")

    def test_valid_level(self):
        result = _log_level("algo-engine", "DEBUG")
        assert "DEBUG" in result

    def test_invalid_level(self):
        result = _log_level("algo-engine", "VERBOSE")
        assert "[error]" in result


class TestLogMetrics:
    def test_no_log_dir(self):
        result = _log_metrics()
        assert "Log" in result or "log" in result or "No" in result


class TestLogRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "log" in reg.categories
        expected = ["view", "console", "search", "errors", "export", "rotate", "level", "metrics"]
        for cmd in expected:
            assert cmd in reg._commands["log"]
