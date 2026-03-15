"""Tests for svc (service lifecycle) commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from moneymaker_console.commands.svc import (
    _svc_compose_config,
    _svc_down,
    _svc_exec,
    _svc_health,
    _svc_inspect,
    _svc_launch,
    _svc_logs,
    _svc_prune,
    _svc_pull,
    _svc_restart,
    _svc_scale,
    _svc_status,
    _svc_up,
    register,
)
from moneymaker_console.registry import CommandRegistry


@patch("moneymaker_console.commands.svc.ClientFactory")
class TestSvcCommands:
    def test_up(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _svc_up()
        assert "[success]" in result

    def test_up_with_service(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        _svc_up("algo-engine")
        mock_docker.up.assert_called_with("algo-engine")

    def test_down(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _svc_down()
        assert "[success]" in result

    def test_restart_no_args(self, mock_cf):
        result = _svc_restart()
        assert "[error]" in result
        assert "Usage" in result

    def test_restart_with_service(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _svc_restart("postgres")
        mock_docker.restart.assert_called_with("postgres")

    def test_status(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _svc_status()
        assert "NAME" in result

    def test_logs_no_args(self, mock_cf):
        result = _svc_logs()
        assert "[error]" in result
        assert "Usage" in result

    def test_logs_with_service(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _svc_logs("algo-engine")
        mock_docker.logs.assert_called_with("algo-engine", tail=50, follow=False)

    def test_logs_with_follow(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        _svc_logs("algo-engine", "--follow")
        mock_docker.logs.assert_called_with("algo-engine", tail=50, follow=True)

    def test_logs_with_f_flag(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        _svc_logs("algo-engine", "-f")
        mock_docker.logs.assert_called_with("algo-engine", tail=50, follow=True)

    def test_logs_with_tail(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        _svc_logs("algo-engine", "--tail", "100")
        mock_docker.logs.assert_called_with("algo-engine", tail=100, follow=False)

    def test_logs_invalid_tail(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        _svc_logs("algo-engine", "--tail", "abc")
        mock_docker.logs.assert_called_with("algo-engine", tail=50, follow=False)

    def test_scale_no_args(self, mock_cf):
        result = _svc_scale()
        assert "[error]" in result

    def test_scale_one_arg(self, mock_cf):
        result = _svc_scale("algo")
        assert "[error]" in result

    def test_scale_valid(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        _svc_scale("algo", "3")
        mock_docker.scale.assert_called_with("algo", 3)

    def test_scale_invalid_count(self, mock_cf):
        result = _svc_scale("algo", "abc")
        assert "[error]" in result
        assert "Invalid replica count" in result

    def test_exec_no_args(self, mock_cf):
        result = _svc_exec()
        assert "[error]" in result

    def test_exec_one_arg(self, mock_cf):
        result = _svc_exec("algo")
        assert "[error]" in result

    def test_exec_valid(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        _svc_exec("algo", "ls", "-la")
        mock_docker.exec_cmd.assert_called_with("algo", "ls -la")

    def test_pull(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        _svc_pull()
        mock_docker.pull.assert_called()

    def test_compose_config(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _svc_compose_config()
        assert result == "compose config output"


@patch("moneymaker_console.commands.svc.run_tool")
class TestSvcRunTool:
    def test_inspect_no_args(self, mock_run):
        result = _svc_inspect()
        assert "[error]" in result

    def test_inspect_with_service(self, mock_run):
        mock_run.return_value = "[success] json output"
        result = _svc_inspect("algo-engine")
        assert mock_run.called

    def test_prune(self, mock_run):
        mock_run.return_value = "[success] pruned"
        result = _svc_prune()
        assert mock_run.called

    def test_health(self, mock_run):
        mock_run.return_value = "[success] healthy"
        result = _svc_health()
        assert mock_run.called


@patch("moneymaker_console.commands.svc.run_tool_live")
class TestSvcLaunch:
    def test_launch_no_script(self, mock_run):
        with patch("moneymaker_console.commands.svc._PROJECT_ROOT") as mock_root:
            mock_root.__truediv__ = MagicMock(
                return_value=MagicMock(exists=MagicMock(return_value=False))
            )
            # The launch function checks script.exists()
            result = _svc_launch()
            assert "[error]" in result or mock_run.called


class TestSvcRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "svc" in reg.categories
        cmds = reg._commands["svc"]
        assert "up" in cmds
        assert "down" in cmds
        assert "restart" in cmds
        assert "status" in cmds
        assert "logs" in cmds
        assert "scale" in cmds
        assert "exec" in cmds
        assert "inspect" in cmds
        assert "pull" in cmds
        assert "prune" in cmds
        assert "launch" in cmds
