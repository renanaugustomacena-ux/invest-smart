"""Tests for market intelligence commands."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from moneymaker_console.commands.market import (
    _market_calendar,
    _market_correlation,
    _market_dashboard,
    _market_indicators,
    _market_macro,
    _market_macro_status,
    _market_news,
    _market_regime,
    _market_session,
    _market_spread,
    _market_symbols,
    _market_volatility,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestMarketSession:
    def test_returns_session(self):
        result = _market_session()
        assert "Trading Session" in result
        assert "UTC Time" in result


class TestMarketDashboard:
    def test_default_port(self):
        with patch.dict(os.environ, {}, clear=False):
            if "DASHBOARD_PORT" in os.environ:
                del os.environ["DASHBOARD_PORT"]
            result = _market_dashboard()
            assert "8000" in result

    def test_custom_port(self):
        with patch.dict(os.environ, {"DASHBOARD_PORT": "3000"}):
            result = _market_dashboard()
            assert "3000" in result


class TestMarketArgValidation:
    def test_spread_no_args(self):
        result = _market_spread()
        assert "Usage" in result

    def test_indicators_no_args(self):
        result = _market_indicators()
        assert "Usage" in result


@patch("moneymaker_console.clients.ClientFactory")
class TestMarketWithClients:
    def test_regime_from_redis(self, mock_cf, mock_redis_client):
        mock_redis_client.get.return_value = '{"regime": "TRENDING"}'
        mock_cf.get_redis.return_value = mock_redis_client
        result = _market_regime()
        assert "TRENDING" in result

    def test_regime_from_db(self, mock_cf, mock_redis_client, mock_db):
        mock_redis_client.get.return_value = None
        mock_cf.get_redis.return_value = mock_redis_client
        mock_db.query_one.return_value = ("VOLATILE", 0.8, "2024-01-15")
        mock_cf.get_postgres.return_value = mock_db
        result = _market_regime()
        assert "VOLATILE" in result

    def test_regime_no_data(self, mock_cf, mock_redis_client, mock_db):
        mock_redis_client.get.return_value = None
        mock_cf.get_redis.return_value = mock_redis_client
        mock_db.query_one.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _market_regime()
        assert "No regime" in result

    def test_regime_redis_error(self, mock_cf, mock_redis_client, mock_db):
        mock_redis_client.get.side_effect = Exception("redis down")
        mock_cf.get_redis.return_value = mock_redis_client
        mock_db.query_one.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _market_regime()
        assert "No regime" in result or "[error]" not in result

    def test_symbols_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("EURUSD", "2024-01-15 10:00"),
            ("GBPUSD", "2024-01-15 10:00"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _market_symbols()
        assert "EURUSD" in result
        assert "GBPUSD" in result

    def test_symbols_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _market_symbols()
        assert "No active" in result

    def test_spread_found(self, mock_cf, mock_db):
        mock_db.query_one.return_value = (1.08500, 1.08520, 0.00020, "2024-01-15")
        mock_cf.get_postgres.return_value = mock_db
        result = _market_spread("EURUSD")
        assert "EURUSD" in result

    def test_spread_no_data(self, mock_cf, mock_db):
        mock_db.query_one.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _market_spread("EURUSD")
        assert "No tick" in result

    def test_calendar_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("2024-01-15 14:30", "USD", "HIGH", "NFP"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _market_calendar()
        assert "NFP" in result
        assert "!!!" in result  # HIGH impact marker

    def test_calendar_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _market_calendar()
        assert "No economic events" in result

    def test_calendar_custom_days(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _market_calendar("14")
        assert "14" in result

    def test_volatility_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("EURUSD", 0.00125, 0.00050, 500),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _market_volatility()
        assert "EURUSD" in result

    def test_volatility_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _market_volatility()
        assert "No volatility" in result

    def test_correlation_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [("EURUSD",), ("GBPUSD",)]
        mock_cf.get_postgres.return_value = mock_db
        result = _market_correlation()
        assert "Correlation" in result
        assert "EURUSD" in result

    def test_correlation_not_enough(self, mock_cf, mock_db):
        mock_db.query.return_value = [("EURUSD",)]
        mock_cf.get_postgres.return_value = mock_db
        result = _market_correlation()
        assert "Not enough" in result

    def test_news_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("2024-01-15 14:30", "USD", "HIGH", "NFP"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _market_news()
        assert "NFP" in result

    def test_news_empty(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _market_news()
        assert "No recent" in result

    def test_indicators_found(self, mock_cf, mock_db):
        mock_db.query_one.return_value = (
            {"rsi_14": 55.0, "atr_14": 0.0012},
            "2024-01-15",
        )
        mock_cf.get_postgres.return_value = mock_db
        result = _market_indicators("EURUSD")
        assert "EURUSD" in result

    def test_indicators_no_data(self, mock_cf, mock_db):
        mock_db.query_one.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _market_indicators("EURUSD")
        assert "No feature" in result

    def test_macro_with_data(self, mock_cf, mock_redis_client):
        mock_redis_client.get.side_effect = lambda k: {
            "moneymaker:macro:vix": "18.5",
            "moneymaker:macro:dxy": "104.2",
        }.get(k)
        mock_cf.get_redis.return_value = mock_redis_client
        result = _market_macro()
        assert "18.5" in result
        assert "104.2" in result

    def test_macro_no_data(self, mock_cf, mock_redis_client):
        mock_redis_client.get.return_value = None
        mock_cf.get_redis.return_value = mock_redis_client
        result = _market_macro()
        assert "N/A" in result


class TestMarketMacroStatus:
    @patch("httpx.get")
    def test_success(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"status": "ok"}
        mock_get.return_value = resp
        result = _market_macro_status()
        assert "OK" in result

    @patch("httpx.get")
    def test_http_error(self, mock_get):
        resp = MagicMock()
        resp.status_code = 500
        mock_get.return_value = resp
        result = _market_macro_status()
        assert "500" in result

    @patch("httpx.get")
    def test_connection_error(self, mock_get):
        mock_get.side_effect = Exception("conn refused")
        result = _market_macro_status()
        assert "not available" in result


class TestMarketRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "market" in reg.categories
        expected = ["regime", "symbols", "spread", "calendar", "volatility",
                    "correlation", "session", "news", "indicators",
                    "macro", "macro-status", "dashboard"]
        for cmd in expected:
            assert cmd in reg._commands["market"]
