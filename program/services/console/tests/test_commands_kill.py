"""Tests for kill switch commands."""

from __future__ import annotations

from unittest.mock import patch

from moneymaker_console.commands.kill import (
    _kill_activate,
    _kill_deactivate,
    _kill_history,
    _kill_history_from_db,
    _kill_history_from_files,
    _kill_status,
    _kill_test,
    register,
)
from moneymaker_console.registry import CommandRegistry


@patch("moneymaker_console.commands.kill.ClientFactory")
class TestKillStatus:
    def test_active(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.get_json.return_value = {
            "active": True,
            "reason": "Manual test",
            "activated_at": "2024-01-15",
        }
        result = _kill_status()
        assert "KILL SWITCH ACTIVE" in result
        assert "Manual test" in result

    def test_inactive(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.get_json.return_value = None
        result = _kill_status()
        assert "INACTIVE" in result

    def test_redis_down(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.ping.return_value = False
        result = _kill_status()
        assert "warning" in result.lower()


@patch("moneymaker_console.commands.kill._persist_to_audit_log")
@patch("moneymaker_console.commands.kill.log_event")
@patch("moneymaker_console.commands.kill.ClientFactory")
class TestKillActivate:
    def test_activate_success(self, mock_cf, mock_log, mock_audit, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        result = _kill_activate("emergency", "test")
        assert "ACTIVATED" in result
        mock_redis_client.set_json.assert_called_once()
        mock_redis_client.publish.assert_called_once()
        mock_log.assert_called_once()

    def test_activate_default_reason(self, mock_cf, mock_log, mock_audit, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        result = _kill_activate()
        assert "Manual activation" in result

    def test_activate_redis_down(self, mock_cf, mock_log, mock_audit, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.ping.return_value = False
        result = _kill_activate()
        assert "[error]" in result


@patch("moneymaker_console.commands.kill._persist_to_audit_log")
@patch("moneymaker_console.commands.kill.log_event")
@patch("moneymaker_console.commands.kill.ClientFactory")
class TestKillDeactivate:
    def test_deactivate_success(self, mock_cf, mock_log, mock_audit, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        result = _kill_deactivate()
        assert "deactivated" in result.lower()
        mock_redis_client.delete.assert_called()
        mock_redis_client.publish.assert_called()

    def test_deactivate_redis_down(self, mock_cf, mock_log, mock_audit, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.ping.return_value = False
        result = _kill_deactivate()
        assert "[error]" in result


@patch("moneymaker_console.commands.kill.ClientFactory")
class TestKillTest:
    def test_all_ok(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = "test"
        mock_redis_client.get_json.return_value = None
        result = _kill_test()
        assert "[OK] Redis connection" in result
        assert "[OK] Redis write/read" in result

    def test_redis_down(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.ping.return_value = False
        result = _kill_test()
        assert "[FAIL] Redis not connected" in result

    def test_write_read_fail(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = "wrong_value"
        mock_redis_client.get_json.return_value = None
        result = _kill_test()
        assert "[FAIL] Redis write/read" in result

    def test_kill_active_warning(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = "test"
        mock_redis_client.get_json.return_value = {"active": True}
        result = _kill_test()
        assert "[WARN]" in result


class TestKillHistoryFromDb:
    @patch("moneymaker_console.commands.kill.ClientFactory")
    def test_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("2024-01-15 10:00:00", "kill_switch_activated", {"reason": "test"}),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _kill_history_from_db()
        assert result is not None
        assert len(result) == 1
        assert "ACTIVATED" in result[0]

    @patch("moneymaker_console.commands.kill.ClientFactory")
    def test_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _kill_history_from_db()
        assert result is None

    @patch("moneymaker_console.commands.kill.ClientFactory")
    def test_db_down(self, mock_cf, mock_db):
        mock_db.ping.return_value = False
        mock_cf.get_postgres.return_value = mock_db
        result = _kill_history_from_db()
        assert result is None


class TestKillHistoryFromFiles:
    def test_returns_list(self):
        # The function references a hard-coded path relative to the source file;
        # just verify it returns a list (may be empty if log dir doesn't exist)
        result = _kill_history_from_files()
        assert isinstance(result, list)


class TestKillHistory:
    @patch("moneymaker_console.commands.kill._kill_history_from_files")
    @patch("moneymaker_console.commands.kill._kill_history_from_db")
    def test_from_db(self, mock_db_hist, mock_file_hist):
        mock_db_hist.return_value = ["  2024-01-15  ACTIVATED  test"]
        result = _kill_history()
        assert "audit_log" in result
        assert "ACTIVATED" in result

    @patch("moneymaker_console.commands.kill._kill_history_from_files")
    @patch("moneymaker_console.commands.kill._kill_history_from_db")
    def test_from_files(self, mock_db_hist, mock_file_hist):
        mock_db_hist.return_value = None
        mock_file_hist.return_value = ["  2024-01-15  ACTIVATED  test"]
        result = _kill_history()
        assert "console logs" in result

    @patch("moneymaker_console.commands.kill._kill_history_from_files")
    @patch("moneymaker_console.commands.kill._kill_history_from_db")
    def test_no_history(self, mock_db_hist, mock_file_hist):
        mock_db_hist.return_value = None
        mock_file_hist.return_value = []
        result = _kill_history()
        assert "No kill switch events" in result


class TestKillRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "kill" in reg.categories
        cmds = reg._commands["kill"]
        assert "status" in cmds
        assert "activate" in cmds
        assert "deactivate" in cmds
        assert "history" in cmds
        assert "test" in cmds
        # Check dangerous flag
        assert cmds["activate"].dangerous is True
        assert cmds["activate"].requires_confirmation is True
