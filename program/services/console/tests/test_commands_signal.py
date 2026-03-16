"""Tests for signal pipeline commands."""

from __future__ import annotations

from unittest.mock import patch

from moneymaker_console.commands.signal import (
    _signal_confidence,
    _signal_last,
    _signal_pending,
    _signal_rate,
    _signal_rejected,
    _signal_replay,
    _signal_status,
    _signal_strategy,
    _signal_validate,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestSignalArgValidation:
    def test_validate_no_args(self):
        result = _signal_validate()
        assert "Usage" in result

    def test_replay_no_args(self):
        result = _signal_replay()
        assert "Usage" in result

    def test_replay_with_id(self):
        result = _signal_replay("42")
        assert "42" in result


@patch("moneymaker_console.clients.ClientFactory")
class TestSignalWithClients:
    def test_status_success(self, mock_cf, mock_db):
        mock_db.query_one.side_effect = [(100,), (80,), (20,)]
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_status()
        assert "100" in result
        assert "80" in result
        assert "20" in result

    def test_status_error(self, mock_cf):
        mock_cf.get_postgres.side_effect = Exception("db down")
        result = _signal_status()
        assert "[error]" in result

    def test_last_default(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            (1, "EURUSD", "BUY", 0.85, "coper", "2024-01-15", "validated"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_last()
        assert "EURUSD" in result

    def test_last_custom_count(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_last("10")
        assert "No signals" in result

    def test_last_error(self, mock_cf):
        mock_cf.get_postgres.side_effect = Exception("fail")
        result = _signal_last()
        assert "[error]" in result

    def test_pending_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            (1, "EURUSD", "SELL", 0.72, "2024-01-15"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_pending()
        assert "EURUSD" in result

    def test_pending_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_pending()
        assert "No pending" in result

    def test_rejected_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            (1, "EURUSD", "BUY", 0.5, "max_positions", "2024-01-15"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_rejected()
        assert "EURUSD" in result

    def test_rejected_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_rejected()
        assert "No rejected" in result

    def test_confidence_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [(5, 10), (7, 20)]
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_confidence()
        assert "Confidence" in result
        assert "#" in result

    def test_confidence_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_confidence()
        assert "No confidence" in result

    def test_rate_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("2024-01-15 10:00", 15),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_rate()
        assert "15" in result

    def test_rate_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_rate()
        assert "No signals" in result

    def test_strategy_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("coper", 50, 0.78),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_strategy()
        assert "coper" in result

    def test_strategy_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_strategy()
        assert "No strategy" in result

    def test_validate_found(self, mock_cf, mock_db):
        mock_db.query_one.return_value = (
            42,
            "EURUSD",
            "BUY",
            0.85,
            "validated",
            None,
            "coper",
        )
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_validate("42")
        assert "EURUSD" in result
        assert "validated" in result

    def test_validate_not_found(self, mock_cf, mock_db):
        mock_db.query_one.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _signal_validate("999")
        assert "not found" in result


class TestSignalRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "signal" in reg.categories
        expected = [
            "status",
            "last",
            "pending",
            "rejected",
            "confidence",
            "rate",
            "strategy",
            "validate",
            "replay",
        ]
        for cmd in expected:
            assert cmd in reg._commands["signal"]
