"""Tests for test suite orchestration commands."""

from __future__ import annotations

from unittest.mock import patch

from moneymaker_console.commands.test_cmds import (
    _test_all,
    _test_brain_verify,
    _test_cascade,
    _test_ci,
    _test_common,
    _test_coverage,
    _test_go,
    _test_lint,
    _test_mt5,
    _test_specific,
    _test_suite,
    _test_typecheck,
    register,
)
from moneymaker_console.registry import CommandRegistry


@patch("moneymaker_console.commands.test_cmds.run_tool_live")
class TestTestCommands:
    def test_all(self, mock_run):
        mock_run.return_value = "3 passed"
        result = _test_all()
        assert "passed" in result

    def test_brain_verify(self, mock_run):
        mock_run.return_value = "2 passed"
        result = _test_brain_verify()
        assert "passed" in result

    def test_cascade(self, mock_run):
        mock_run.return_value = "1 passed"
        result = _test_cascade()
        assert "passed" in result

    def test_go(self, mock_run):
        mock_run.return_value = "ok"
        result = _test_go()
        assert "ok" in result

    def test_mt5(self, mock_run):
        mock_run.return_value = "5 passed"
        result = _test_mt5()
        assert "passed" in result

    def test_common(self, mock_run):
        mock_run.return_value = "10 passed"
        result = _test_common()
        assert "passed" in result

    def test_lint(self, mock_run):
        mock_run.return_value = "All checks passed"
        result = _test_lint()
        assert isinstance(result, str)

    def test_typecheck(self, mock_run):
        mock_run.return_value = "Success: no issues found"
        result = _test_typecheck()
        assert "Success" in result

    def test_coverage(self, mock_run):
        mock_run.return_value = "TOTAL 80%"
        result = _test_coverage()
        assert "80" in result

    def test_specific_no_args(self, mock_run):
        result = _test_specific()
        assert "Usage" in result

    def test_specific_with_path(self, mock_run):
        mock_run.return_value = "1 passed"
        result = _test_specific("tests/test_foo.py")
        assert "passed" in result


@patch("moneymaker_console.commands.test_cmds.run_tool_live")
class TestTestSuite:
    def test_suite_all_pass(self, mock_run):
        mock_run.return_value = "3 passed"
        result = _test_suite()
        assert "PASSED" in result

    def test_suite_with_failure(self, mock_run):
        mock_run.side_effect = Exception("test failed")
        result = _test_suite()
        assert "FAILED" in result


@patch("moneymaker_console.commands.test_cmds.run_tool_live")
class TestTestCi:
    def test_ci_success(self, mock_run):
        mock_run.return_value = "passed"
        result = _test_ci()
        assert "[success]" in result

    def test_ci_failure(self, mock_run):
        mock_run.side_effect = Exception("lint failed")
        result = _test_ci()
        assert "[error]" in result


class TestTestRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "test" in reg.categories
        expected = ["all", "brain-verify", "cascade", "go", "mt5",
                    "common", "suite", "lint", "typecheck", "ci",
                    "coverage", "specific"]
        for cmd in expected:
            assert cmd in reg._commands["test"]
