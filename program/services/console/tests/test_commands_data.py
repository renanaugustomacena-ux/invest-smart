"""Tests for data ingestion commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from moneymaker_console.commands.data import (
    _data_add,
    _data_backfill,
    _data_buffer,
    _data_gaps,
    _data_latency,
    _data_providers,
    _data_reconnect,
    _data_remove,
    _data_start,
    _data_status,
    _data_stop,
    _data_symbols,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestDataArgValidation:
    def test_add_no_args(self):
        result = _data_add()
        assert "Usage" in result

    def test_add_with_symbol(self):
        result = _data_add("eurusd")
        assert "EURUSD" in result

    def test_remove_no_args(self):
        result = _data_remove()
        assert "Usage" in result

    def test_remove_with_symbol(self):
        result = _data_remove("gbpusd")
        assert "GBPUSD" in result

    def test_backfill_no_args(self):
        result = _data_backfill()
        assert "Usage" in result

    def test_backfill_one_arg(self):
        result = _data_backfill("EURUSD")
        assert "Usage" in result

    def test_backfill_valid(self):
        result = _data_backfill("EURUSD", "30")
        assert "EURUSD" in result
        assert "30" in result


@patch("moneymaker_console.clients.ClientFactory")
class TestDataWithClients:
    def test_start_success(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _data_start()
        assert "[success]" in result

    def test_start_error(self, mock_cf):
        mock_cf.get_docker.side_effect = Exception("conn error")
        result = _data_start()
        assert "[error]" in result

    def test_stop_success(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _data_stop()
        assert "[success]" in result

    def test_stop_error(self, mock_cf):
        mock_cf.get_docker.side_effect = Exception("conn error")
        result = _data_stop()
        assert "[error]" in result

    def test_status_health_ok(self, mock_cf, mock_data_client):
        mock_data_client.get_health.return_value = {"status": "ok"}
        mock_cf.get_data.return_value = mock_data_client
        mock_cf.get_postgres.return_value = MagicMock(query_one=MagicMock(return_value=None))
        result = _data_status()
        assert "OK" in result

    def test_status_not_connected(self, mock_cf, mock_data_client):
        mock_data_client.get_health.return_value = None
        mock_cf.get_data.return_value = mock_data_client
        result = _data_status()
        assert "NOT CONNECTED" in result

    def test_status_error(self, mock_cf):
        mock_cf.get_data.side_effect = Exception("fail")
        result = _data_status()
        assert "ERROR" in result

    def test_symbols_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("EURUSD", "{M1,M5}", "2024-01-15 10:00"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _data_symbols()
        assert "EURUSD" in result

    def test_symbols_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _data_symbols()
        assert "No symbols" in result

    def test_symbols_error(self, mock_cf):
        mock_cf.get_postgres.side_effect = Exception("db error")
        result = _data_symbols()
        assert "[error]" in result

    def test_gaps_no_gaps(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _data_gaps()
        assert "No data gaps" in result

    def test_gaps_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("2024-01-15 10:00", "EURUSD", 2),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _data_gaps()
        assert "EURUSD" in result

    def test_gaps_custom_days(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _data_gaps("14")
        assert "14" in result

    def test_providers_available(self, mock_cf, mock_data_client):
        mock_data_client.get_health.return_value = {"providers": {"binance": "ok", "mt5": "ok"}}
        mock_cf.get_data.return_value = mock_data_client
        result = _data_providers()
        assert "binance" in result

    def test_providers_no_data(self, mock_cf, mock_data_client):
        mock_data_client.get_health.return_value = None
        mock_cf.get_data.return_value = mock_data_client
        result = _data_providers()
        assert "not available" in result

    def test_reconnect_success(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _data_reconnect()
        assert "[success]" in result

    def test_reconnect_error(self, mock_cf):
        mock_cf.get_docker.side_effect = Exception("fail")
        result = _data_reconnect()
        assert "[error]" in result

    def test_buffer_with_data(self, mock_cf, mock_data_client):
        mock_data_client.get_metrics.return_value = "buffer_size 100\npending_writes 5\nother 1"
        mock_cf.get_data.return_value = mock_data_client
        result = _data_buffer()
        assert "buffer" in result.lower() or "pending" in result.lower()

    def test_buffer_no_metrics(self, mock_cf, mock_data_client):
        mock_data_client.get_metrics.return_value = None
        mock_cf.get_data.return_value = mock_data_client
        result = _data_buffer()
        assert "not available" in result

    def test_latency_with_data(self, mock_cf, mock_data_client):
        mock_data_client.get_metrics.return_value = "latency_ms 5\nduration_avg 10\n# comment"
        mock_cf.get_data.return_value = mock_data_client
        result = _data_latency()
        assert "latency" in result.lower() or "duration" in result.lower()

    def test_latency_no_metrics(self, mock_cf, mock_data_client):
        mock_data_client.get_metrics.return_value = None
        mock_cf.get_data.return_value = mock_data_client
        result = _data_latency()
        assert "not available" in result


class TestDataRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "data" in reg.categories
        cmds = reg._commands["data"]
        expected = [
            "start",
            "stop",
            "status",
            "symbols",
            "add",
            "remove",
            "backfill",
            "gaps",
            "providers",
            "reconnect",
            "buffer",
            "latency",
        ]
        for cmd in expected:
            assert cmd in cmds
