"""Tests for portfolio management commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from moneymaker_console.commands.portfolio import (
    _portfolio_allocation,
    _portfolio_compare,
    _portfolio_cvar,
    _portfolio_heat_map,
    _portfolio_optimize,
    _portfolio_overview,
    _portfolio_stress_test,
    _portfolio_var,
    register,
)
from moneymaker_console.registry import CommandRegistry


@patch("moneymaker_console.clients.ClientFactory")
class TestPortfolioOverview:
    def test_with_positions(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (3, 0.30, 150.0)
        mock_cf.get_postgres.return_value = mock_db
        result = _portfolio_overview()
        assert "Portfolio" in result or "3" in result

    def test_no_positions(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (0, None, None)
        mock_cf.get_postgres.return_value = mock_db
        result = _portfolio_overview()
        assert "No open" in result

    def test_error(self, mock_cf):
        mock_cf.get_postgres.side_effect = Exception("db err")
        result = _portfolio_overview()
        assert "[error]" in result


@patch("moneymaker_console.clients.ClientFactory")
class TestPortfolioAllocation:
    def test_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [("EURUSD", "BUY", 0.20, 2)]
        mock_cf.get_postgres.return_value = mock_db
        result = _portfolio_allocation()
        assert "EURUSD" in result

    def test_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _portfolio_allocation()
        assert "No open" in result


@patch("moneymaker_console.clients.ClientFactory")
class TestPortfolioHeatMap:
    def test_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [("EURUSD", 50.0), ("XAUUSD", -30.0)]
        mock_cf.get_postgres.return_value = mock_db
        result = _portfolio_heat_map()
        assert "EURUSD" in result

    def test_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _portfolio_heat_map()
        assert "No open" in result


class TestPortfolioStatic:
    def test_optimize(self):
        result = _portfolio_optimize()
        assert "info" in result.lower()

    def test_var_default(self):
        result = _portfolio_var()
        assert "95" in result

    def test_var_custom(self):
        result = _portfolio_var("--confidence", "99")
        assert "99" in result

    def test_cvar(self):
        result = _portfolio_cvar()
        assert "info" in result.lower()

    def test_stress_test_default(self):
        result = _portfolio_stress_test()
        assert "flash-crash" in result

    def test_stress_test_custom(self):
        result = _portfolio_stress_test("rate-hike")
        assert "rate-hike" in result

    def test_stress_test_unknown(self):
        result = _portfolio_stress_test("alien-invasion")
        assert "alien-invasion" in result


@patch("moneymaker_console.clients.ClientFactory")
class TestPortfolioCompare:
    def test_with_data(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (5000.0, 100)
        mock_cf.get_postgres.return_value = mock_db
        result = _portfolio_compare()
        assert "5,000" in result or "Portfolio" in result

    def test_no_data(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (None, 0)
        mock_cf.get_postgres.return_value = mock_db
        result = _portfolio_compare()
        assert "No closed" in result


class TestPortfolioRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "portfolio" in reg.categories
        expected = ["overview", "allocation", "heat-map", "optimize",
                    "var", "cvar", "stress-test", "compare"]
        for cmd in expected:
            assert cmd in reg._commands["portfolio"]
