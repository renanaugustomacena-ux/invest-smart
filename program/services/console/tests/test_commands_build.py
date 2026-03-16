"""Tests for build and container management commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from moneymaker_console.commands.build import (
    _build_all,
    _build_brain,
    _build_bridge,
    _build_clean,
    _build_dashboard,
    _build_external,
    _build_ingestion,
    _build_proto,
    _build_push,
    _build_status,
    _build_tag,
    register,
)
from moneymaker_console.registry import CommandRegistry


@patch("moneymaker_console.clients.ClientFactory")
class TestBuildServices:
    def test_build_all(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.build.return_value = "[success] built"
        mock_cf.get_docker.return_value = mock_docker
        _build_all()
        mock_docker.build.assert_called_with(no_cache=False)

    def test_build_all_no_cache(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.build.return_value = "[success] built"
        mock_cf.get_docker.return_value = mock_docker
        _build_all("--no-cache")
        mock_docker.build.assert_called_with(no_cache=True)

    def test_build_brain(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.build.return_value = "built"
        mock_cf.get_docker.return_value = mock_docker
        _build_brain()
        mock_docker.build.assert_called_with("algo-engine", no_cache=False)

    def test_build_ingestion(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.build.return_value = "built"
        mock_cf.get_docker.return_value = mock_docker
        _build_ingestion()
        mock_docker.build.assert_called_with("data-ingestion", no_cache=False)

    def test_build_bridge(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.build.return_value = "built"
        mock_cf.get_docker.return_value = mock_docker
        _build_bridge()
        mock_docker.build.assert_called_with("mt5-bridge", no_cache=False)

    def test_build_dashboard(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.build.return_value = "built"
        mock_cf.get_docker.return_value = mock_docker
        _build_dashboard()
        mock_docker.build.assert_called_with("dashboard", no_cache=False)

    def test_build_external(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.build.return_value = "built"
        mock_cf.get_docker.return_value = mock_docker
        _build_external()
        mock_docker.build.assert_called_with("external-data", no_cache=False)

    def test_build_error(self, mock_cf):
        mock_cf.get_docker.side_effect = Exception("docker err")
        result = _build_all()
        assert "[error]" in result


class TestBuildProto:
    @patch("moneymaker_console.commands.build.run_tool_live")
    def test_proto_exists(self, mock_run):
        mock_run.return_value = "compiled"
        result = _build_proto()
        assert mock_run.called or "error" in result.lower()


class TestBuildStatus:
    @patch("moneymaker_console.commands.build.run_tool")
    def test_status(self, mock_run):
        mock_run.return_value = "moneymaker-brain latest 500MB"
        result = _build_status()
        assert "moneymaker" in result


class TestBuildClean:
    @patch("moneymaker_console.commands.build.run_tool")
    def test_clean_basic(self, mock_run):
        mock_run.return_value = ""
        result = _build_clean()
        assert "[success]" in result

    @patch("moneymaker_console.commands.build.run_tool")
    def test_clean_docker(self, mock_run):
        mock_run.return_value = ""
        result = _build_clean("--docker")
        assert "[success]" in result


class TestBuildPush:
    def test_no_args(self):
        assert "Usage" in _build_push()

    @patch("moneymaker_console.commands.build.run_tool_live")
    def test_push_service(self, mock_run):
        mock_run.return_value = "pushed"
        _build_push("algo-engine")
        assert mock_run.called


class TestBuildTag:
    def test_no_args(self):
        assert "Usage" in _build_tag()

    @patch("moneymaker_console.commands.build.run_tool")
    def test_tag_version(self, mock_run):
        mock_run.side_effect = [
            "abc1234",  # git rev-parse
            "moneymaker-brain:latest\nmoneymaker-bridge:latest\n",  # docker images
            "",  # docker tag 1
            "",  # docker tag 2
            "",  # docker tag 3
            "",  # docker tag 4
        ]
        result = _build_tag("v1.0.0")
        assert "v1.0.0" in result


class TestBuildRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "build" in reg.categories
        expected = [
            "all",
            "brain",
            "ingestion",
            "bridge",
            "dashboard",
            "external",
            "status",
            "clean",
        ]
        for cmd in expected:
            assert cmd in reg._commands["build"]
