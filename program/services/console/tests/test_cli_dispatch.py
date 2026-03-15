"""Tests for CLI dispatch logic."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

import pytest

from moneymaker_console.cli.dispatch import (
    EXIT_BAD_ARGS,
    EXIT_CANCELLED,
    EXIT_ERROR,
    EXIT_OK,
    EXIT_SERVICE_UNAVAIL,
    run_cli,
)
from moneymaker_console.registry import CommandRegistry


@pytest.fixture()
def reg():
    r = CommandRegistry()
    r.register("svc", "status", lambda: "all running", "Show status")
    r.register("svc", "fail", lambda: "[error] something broke", "Fail cmd")
    r.register("svc", "cancel", lambda: "[cancelled] aborted", "Cancel cmd")
    r.register(
        "svc", "unavail",
        lambda: "[error] service unavailable — not connected",
        "Unavail cmd",
    )
    return r


class TestRunCli:
    def test_valid_command(self, reg):
        code = run_cli(reg, ["svc", "status"])
        assert code == EXIT_OK

    def test_no_category(self, reg):
        code = run_cli(reg, [])
        assert code == EXIT_BAD_ARGS

    def test_error_result(self, reg):
        code = run_cli(reg, ["svc", "fail"])
        assert code == EXIT_ERROR

    def test_cancelled_result(self, reg):
        code = run_cli(reg, ["svc", "cancel"])
        assert code == EXIT_CANCELLED

    def test_service_unavailable(self, reg):
        code = run_cli(reg, ["svc", "unavail"])
        assert code == EXIT_SERVICE_UNAVAIL

    def test_json_output(self, reg, capsys):
        code = run_cli(reg, ["--json", "svc", "status"])
        assert code == EXIT_OK
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["category"] == "svc"
        assert payload["subcmd"] == "status"
        assert payload["result"] == "all running"
        assert payload["exit_code"] == EXIT_OK
        assert "duration_ms" in payload

    def test_json_error_output(self, reg, capsys):
        code = run_cli(reg, ["--json", "svc", "fail"])
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["exit_code"] == EXIT_ERROR

    def test_yes_flag_sets_auto_confirm(self, reg):
        reg.register("danger", "go", lambda: "done", "Dangerous",
                     requires_confirmation=True, dangerous=True)
        code = run_cli(reg, ["--yes", "danger", "go"])
        assert code == EXIT_OK

    def test_error_printed_to_stderr(self, reg, capsys):
        run_cli(reg, ["svc", "fail"])
        captured = capsys.readouterr()
        assert "[error]" in captured.err

    def test_success_printed_to_stdout(self, reg, capsys):
        run_cli(reg, ["svc", "status"])
        captured = capsys.readouterr()
        assert "all running" in captured.out


class TestExitCodes:
    def test_exit_ok(self):
        assert EXIT_OK == 0

    def test_exit_error(self):
        assert EXIT_ERROR == 1

    def test_exit_bad_args(self):
        assert EXIT_BAD_ARGS == 2

    def test_exit_service_unavail(self):
        assert EXIT_SERVICE_UNAVAIL == 3

    def test_exit_cancelled(self):
        assert EXIT_CANCELLED == 4
