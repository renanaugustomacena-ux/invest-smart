"""Tests for risk management commands."""

from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

from moneymaker_console.commands.risk import (
    _risk_circuit_breaker,
    _risk_correlation,
    _risk_exposure,
    _risk_history,
    _risk_limits,
    _risk_set_daily_loss,
    _risk_set_max_dd,
    _risk_set_max_lot,
    _risk_set_max_pos,
    _risk_status,
    _risk_validation,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestRiskArgValidation:
    def test_set_max_dd_no_args(self):
        assert "[error]" in _risk_set_max_dd()
        assert "Usage" in _risk_set_max_dd()

    def test_set_max_dd_valid(self):
        result = _risk_set_max_dd("5.0")
        assert "5.0" in result

    def test_set_max_dd_too_high(self):
        result = _risk_set_max_dd("60")
        assert "[error]" in result

    def test_set_max_dd_negative(self):
        result = _risk_set_max_dd("-1")
        assert "[error]" in result

    def test_set_max_dd_invalid(self):
        result = _risk_set_max_dd("abc")
        assert "[error]" in result

    def test_set_max_pos_no_args(self):
        assert "[error]" in _risk_set_max_pos()

    def test_set_max_pos_valid(self):
        result = _risk_set_max_pos("3")
        assert "3" in result

    def test_set_max_pos_too_high(self):
        assert "[error]" in _risk_set_max_pos("25")

    def test_set_max_pos_invalid(self):
        assert "[error]" in _risk_set_max_pos("abc")

    def test_set_max_lot_no_args(self):
        assert "[error]" in _risk_set_max_lot()

    def test_set_max_lot_valid(self):
        result = _risk_set_max_lot("0.5")
        assert "0.5" in result

    def test_set_max_lot_too_high(self):
        assert "[error]" in _risk_set_max_lot("15")

    def test_set_max_lot_invalid(self):
        assert "[error]" in _risk_set_max_lot("abc")

    def test_set_daily_loss_no_args(self):
        assert "[error]" in _risk_set_daily_loss()

    def test_set_daily_loss_valid(self):
        result = _risk_set_daily_loss("2.0")
        assert "2.0" in result

    def test_set_daily_loss_too_high(self):
        assert "[error]" in _risk_set_daily_loss("25")

    def test_set_daily_loss_invalid(self):
        assert "[error]" in _risk_set_daily_loss("abc")


class TestRiskLimits:
    def test_shows_defaults(self):
        result = _risk_limits()
        assert "Risk Limits" in result
        assert "Max Drawdown" in result
        assert "Max Positions" in result


class TestRiskValidation:
    def test_shows_checklist(self):
        result = _risk_validation()
        assert "11 points" in result
        assert "HOLD direction" in result


@patch("moneymaker_console.commands.risk.ClientFactory")
class TestRiskWithClients:
    def test_status(self, mock_cf, mock_db, mock_redis_client):
        mock_db.query_one.side_effect = [(3,), (Decimal("150.00"),)]
        mock_cf.get_postgres.return_value = mock_db
        mock_redis_client.get_json.side_effect = [None, None]
        mock_redis_client.get.return_value = "ARMED"
        mock_cf.get_redis.return_value = mock_redis_client
        result = _risk_status()
        assert "Risk Dashboard" in result
        assert "ARMED" in result

    def test_status_spiral_active(self, mock_cf, mock_db, mock_redis_client):
        mock_db.query_one.side_effect = [(0,), (Decimal("0"),)]
        mock_cf.get_postgres.return_value = mock_db
        mock_redis_client.get_json.side_effect = [
            {"active": True, "consecutive_losses": 5},
            None,
        ]
        mock_redis_client.get.return_value = None
        mock_cf.get_redis.return_value = mock_redis_client
        result = _risk_status()
        assert "ACTIVE" in result

    def test_exposure_found(self, mock_cf, mock_db):
        mock_db.query_dict.return_value = [
            {"symbol": "EURUSD", "direction": "BUY", "total_lots": 0.5, "positions": 2},
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _risk_exposure()
        assert "EURUSD" in result

    def test_exposure_empty(self, mock_cf, mock_db):
        mock_db.query_dict.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _risk_exposure()
        assert "No open exposure" in result

    def test_correlation_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [("EURUSD",), ("GBPUSD",)]
        mock_cf.get_postgres.return_value = mock_db
        result = _risk_correlation()
        assert "Correlation" in result

    def test_correlation_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _risk_correlation()
        assert "Not enough" in result

    def test_circuit_breaker_status(self, mock_cf, mock_redis_client):
        mock_redis_client.get.return_value = "ARMED"
        mock_cf.get_redis.return_value = mock_redis_client
        result = _risk_circuit_breaker()
        assert "ARMED" in result

    def test_circuit_breaker_arm(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        result = _risk_circuit_breaker("arm")
        assert "ARMED" in result

    def test_circuit_breaker_disarm(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        result = _risk_circuit_breaker("disarm")
        assert "DISARMED" in result

    def test_history_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("EURUSD", "BUY", 0.85, "max_positions", "2024-01-15"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _risk_history()
        assert "EURUSD" in result

    def test_history_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _risk_history()
        assert "No rejected" in result

    def test_history_custom_days(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _risk_history("--days", "14")
        assert "14" in result


class TestRiskRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "risk" in reg.categories
        expected = [
            "status",
            "limits",
            "set-max-dd",
            "set-max-pos",
            "set-max-lot",
            "set-daily-loss",
            "exposure",
            "correlation",
            "kill-switch",
            "circuit-breaker",
            "validation",
            "history",
            "spiral",
        ]
        for cmd in expected:
            assert cmd in reg._commands["risk"]
