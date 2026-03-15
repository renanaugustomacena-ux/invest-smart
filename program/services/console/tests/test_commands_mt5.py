"""Tests for MT5 bridge commands."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from moneymaker_console.commands.mt5 import (
    _mt5_account,
    _mt5_autotrading,
    _mt5_close,
    _mt5_close_all,
    _mt5_connect,
    _mt5_disconnect,
    _mt5_history,
    _mt5_modify,
    _mt5_orders,
    _mt5_positions,
    _mt5_rate_limit,
    _mt5_status,
    _mt5_sync,
    _mt5_trailing,
    _mt5_trailing_config,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestMt5ArgValidation:
    def test_close_no_args(self):
        result = _mt5_close()
        assert "[error]" in result or "Usage" in result

    def test_close_with_id(self):
        result = _mt5_close("12345")
        assert "12345" in result

    def test_close_all(self):
        result = _mt5_close_all()
        assert isinstance(result, str)

    def test_modify_no_args(self):
        result = _mt5_modify()
        assert "[error]" in result or "Usage" in result

    def test_modify_with_id(self):
        result = _mt5_modify("12345")
        assert "12345" in result


class TestMt5TrailingConfig:
    def test_trailing_config(self):
        result = _mt5_trailing_config()
        assert "Trailing" in result or "trailing" in result

    def test_trailing_on(self):
        result = _mt5_trailing("on")
        assert isinstance(result, str)

    def test_trailing_off(self):
        result = _mt5_trailing("off")
        assert isinstance(result, str)

    def test_trailing_status(self):
        result = _mt5_trailing()
        assert isinstance(result, str)


# MT5 imports ClientFactory at module level, so patch at the command module
@patch("moneymaker_console.commands.mt5.ClientFactory")
class TestMt5WithClients:
    def test_connect(self, mock_cf):
        mock_docker = MagicMock()
        mock_docker.restart.return_value = "[success] Restarted mt5-bridge"
        mock_cf.get_docker.return_value = mock_docker
        result = _mt5_connect()
        assert isinstance(result, str)

    def test_status_health_ok(self, mock_cf):
        mock_mt5 = MagicMock()
        mock_mt5.check_health.return_value = {"status": "connected", "message": "OK", "uptime_seconds": 3600}
        mock_cf.get_mt5.return_value = mock_mt5
        result = _mt5_status()
        assert "connected" in result or "MT5" in result

    def test_status_fallback_db(self, mock_cf):
        mock_mt5 = MagicMock()
        mock_mt5.check_health.return_value = None
        mock_cf.get_mt5.return_value = mock_mt5
        mock_db = MagicMock()
        mock_db.ping.return_value = True
        mock_db.query_one.return_value = (5,)
        mock_cf.get_postgres.return_value = mock_db
        result = _mt5_status()
        assert "5" in result

    def test_status_unavailable(self, mock_cf):
        mock_mt5 = MagicMock()
        mock_mt5.check_health.return_value = None
        mock_cf.get_mt5.return_value = mock_mt5
        mock_db = MagicMock()
        mock_db.ping.return_value = False
        mock_cf.get_postgres.return_value = mock_db
        result = _mt5_status()
        assert "warning" in result.lower()

    def test_positions_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.ping.return_value = True
        mock_db.query_dict.return_value = [
            {"order_id": 1, "symbol": "EURUSD", "direction": "BUY",
             "quantity": 0.1, "executed_price": 1.0850,
             "stop_loss": 1.0800, "take_profit": 1.0950},
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _mt5_positions()
        assert "EURUSD" in result

    def test_positions_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.ping.return_value = True
        mock_db.query_dict.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _mt5_positions()
        assert "No" in result or "position" in result.lower()

    def test_positions_unavailable(self, mock_cf):
        mock_db = MagicMock()
        mock_db.ping.return_value = False
        mock_cf.get_postgres.return_value = mock_db
        result = _mt5_positions()
        assert "warning" in result.lower()

    def test_history_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.ping.return_value = True
        mock_db.query_dict.return_value = [
            {"order_id": 1, "symbol": "EURUSD", "direction": "BUY",
             "quantity": 0.1, "executed_price": 1.0850, "pnl": 50.0,
             "commission": -2.0, "swap": 0, "opened_at": "2024-01-15",
             "closed_at": "2024-01-16"},
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _mt5_history()
        assert "EURUSD" in result

    def test_history_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.ping.return_value = True
        mock_db.query_dict.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _mt5_history()
        assert "No" in result

    def test_account(self, mock_cf):
        mock_db = MagicMock()
        mock_cf.get_postgres.return_value = mock_db
        with patch.dict(os.environ, {"MT5_ACCOUNT": "12345"}):
            result = _mt5_account()
            assert "12345" in result or "Account" in result

    def test_sync(self, mock_cf):
        mock_redis = MagicMock()
        mock_redis.publish.return_value = True
        mock_cf.get_redis.return_value = mock_redis
        result = _mt5_sync()
        assert "[success]" in result or "sync" in result.lower()

    def test_orders_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_dict.return_value = [
            {"order_id": 1, "symbol": "EURUSD", "direction": "BUY_LIMIT",
             "quantity": 0.1, "requested_price": 1.0800,
             "status": "PENDING", "created_at": "2024-01-15"},
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _mt5_orders()
        assert "EURUSD" in result or "Order" in result

    def test_orders_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_dict.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _mt5_orders()
        assert "No" in result

    def test_autotrading_on(self, mock_cf):
        mock_redis = MagicMock()
        mock_cf.get_redis.return_value = mock_redis
        result = _mt5_autotrading("on")
        assert isinstance(result, str)

    def test_autotrading_off(self, mock_cf):
        mock_redis = MagicMock()
        mock_cf.get_redis.return_value = mock_redis
        result = _mt5_autotrading("off")
        assert isinstance(result, str)

    def test_autotrading_status(self, mock_cf):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "true"
        mock_cf.get_redis.return_value = mock_redis
        result = _mt5_autotrading()
        assert isinstance(result, str)

    def test_rate_limit_status(self, mock_cf):
        mock_redis = MagicMock()
        mock_redis.get_json.return_value = {"current": 3}
        mock_cf.get_redis.return_value = mock_redis
        result = _mt5_rate_limit()
        assert "Rate" in result or "rate" in result


class TestMt5Disconnect:
    @patch("moneymaker_console.commands.mt5.ClientFactory")
    @patch("moneymaker_console.runner.subprocess.run")
    def test_disconnect(self, mock_run, mock_cf):
        import subprocess
        mock_run.return_value = subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout="stopped\n", stderr=""
        )
        result = _mt5_disconnect()
        assert mock_run.called


class TestMt5Register:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "mt5" in reg.categories
        expected = ["connect", "disconnect", "status", "positions",
                    "history", "close", "close-all", "modify",
                    "account", "sync", "orders"]
        for cmd in expected:
            assert cmd in reg._commands["mt5"]
