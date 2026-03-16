"""Tests for the runner module (subprocess execution)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from moneymaker_console.runner import (
    BUILD_TIMEOUT_S,
    OUTPUT_TRIM_LINES,
    SUBPROCESS_TIMEOUT_S,
    _build_env,
    run_tool,
    run_tool_live,
)


class TestBuildEnv:
    def test_includes_pythonpath(self):
        env = _build_env()
        assert "PYTHONPATH" in env

    def test_includes_existing_env(self):
        env = _build_env()
        assert "PATH" in env

    def test_extra_vars(self):
        env = _build_env({"MY_VAR": "123"})
        assert env["MY_VAR"] == "123"

    def test_extra_none(self):
        env = _build_env(None)
        assert "PYTHONPATH" in env


class TestRunTool:
    @patch("moneymaker_console.runner.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo"], returncode=0, stdout="hello\n", stderr=""
        )
        result = run_tool(["echo", "hello"])
        assert "[success]" in result
        assert "hello" in result

    @patch("moneymaker_console.runner.subprocess.run")
    def test_error_returncode(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["false"], returncode=1, stdout="", stderr="failed\n"
        )
        result = run_tool(["false"])
        assert "[error]" in result
        assert "failed" in result

    @patch("moneymaker_console.runner.subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["slow"], timeout=300)
        result = run_tool(["slow"])
        assert "[error]" in result
        assert "Timeout" in result

    @patch("moneymaker_console.runner.subprocess.run")
    def test_command_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        result = run_tool(["nonexistent"])
        assert "[error]" in result
        assert "Command not found" in result

    @patch("moneymaker_console.runner.subprocess.run")
    def test_generic_exception(self, mock_run):
        mock_run.side_effect = OSError("disk error")
        result = run_tool(["cmd"])
        assert "[error]" in result
        assert "disk error" in result

    @patch("moneymaker_console.runner.subprocess.run")
    def test_output_trimming(self, mock_run):
        long_output = "\n".join(f"line {i}" for i in range(200))
        mock_run.return_value = subprocess.CompletedProcess(
            args=["cmd"], returncode=0, stdout=long_output, stderr=""
        )
        result = run_tool(["cmd"])
        assert "[success]" in result
        assert "omitted" in result

    @patch("moneymaker_console.runner.subprocess.run")
    def test_custom_timeout(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["cmd"], returncode=0, stdout="ok\n", stderr=""
        )
        run_tool(["cmd"], timeout=10)
        mock_run.assert_called_once()
        assert mock_run.call_args[1]["timeout"] == 10

    @patch("moneymaker_console.runner.subprocess.run")
    def test_custom_cwd(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["cmd"], returncode=0, stdout="ok\n", stderr=""
        )
        run_tool(["cmd"], cwd=tmp_path)
        assert mock_run.call_args[1]["cwd"] == str(tmp_path)

    @patch("moneymaker_console.runner.subprocess.run")
    def test_env_extra(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["cmd"], returncode=0, stdout="ok\n", stderr=""
        )
        run_tool(["cmd"], env_extra={"FOO": "bar"})
        env = mock_run.call_args[1]["env"]
        assert env["FOO"] == "bar"


class TestRunToolLive:
    @patch("moneymaker_console.runner.subprocess.Popen")
    def test_success(self, mock_popen):
        proc = MagicMock()
        proc.stdout = iter(["line1\n", "line2\n"])
        proc.wait.return_value = None
        proc.returncode = 0
        mock_popen.return_value = proc

        result = run_tool_live(["cmd"])
        assert "[success]" in result
        assert "exit code: 0" in result

    @patch("moneymaker_console.runner.subprocess.Popen")
    def test_failure(self, mock_popen):
        proc = MagicMock()
        proc.stdout = iter(["err\n"])
        proc.wait.return_value = None
        proc.returncode = 1
        mock_popen.return_value = proc

        result = run_tool_live(["cmd"])
        assert "[error]" in result
        assert "exit code: 1" in result

    @patch("moneymaker_console.runner.subprocess.Popen")
    def test_timeout(self, mock_popen):
        proc = MagicMock()
        proc.stdout = iter([])
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd=["cmd"], timeout=600)
        proc.kill = MagicMock()
        mock_popen.return_value = proc

        result = run_tool_live(["cmd"])
        assert "[error]" in result
        assert "Timeout" in result
        proc.kill.assert_called_once()

    @patch("moneymaker_console.runner.subprocess.Popen")
    def test_command_not_found(self, mock_popen):
        mock_popen.side_effect = FileNotFoundError()
        result = run_tool_live(["nonexistent"])
        assert "[error]" in result
        assert "Command not found" in result

    @patch("moneymaker_console.runner.subprocess.Popen")
    def test_generic_exception(self, mock_popen):
        mock_popen.side_effect = OSError("popen error")
        result = run_tool_live(["cmd"])
        assert "[error]" in result
        assert "popen error" in result


class TestConstants:
    def test_output_trim_lines(self):
        assert OUTPUT_TRIM_LINES == 80

    def test_subprocess_timeout(self):
        assert SUBPROCESS_TIMEOUT_S == 300

    def test_build_timeout(self):
        assert BUILD_TIMEOUT_S == 600
