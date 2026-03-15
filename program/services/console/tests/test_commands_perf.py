"""Tests for performance analytics commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from moneymaker_console.commands.perf import (
    _perf_by_regime,
    _perf_by_session,
    _perf_by_strategy,
    _perf_by_symbol,
    _perf_correlation_pnl,
    _perf_daily,
    _perf_drawdown,
    _perf_equity,
    _perf_expectancy,
    _perf_monthly,
    _perf_risk_adjusted,
    _perf_summary,
    _perf_trades,
    _perf_weekly,
    register,
)
from moneymaker_console.registry import CommandRegistry


@patch("moneymaker_console.clients.ClientFactory")
class TestPerfCommands:
    def test_summary_found(self, mock_cf):
        mock_db = MagicMock()
        # query_one returns single row: (total, total_pnl, avg_win, avg_loss, wr, pf, max_win, max_loss)
        mock_db.query_one.return_value = (100, 5000.0, 80.0, -30.0, 0.6, 2.5, 500.0, -200.0)
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_summary()
        assert "Performance" in result
        assert "100" in result

    def test_summary_no_trades(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (0, None, None, None, None, None, None, None)
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_summary()
        assert "No closed trades" in result

    def test_summary_none_row(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_summary()
        assert "No closed trades" in result

    def test_summary_with_days_arg(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (10, 200.0, 50.0, -20.0, 0.7, 3.0, 100.0, -50.0)
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_summary("7")
        assert "7 days" in result

    def test_daily_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [
            ("2024-01-15", 150.0, 3),
            ("2024-01-16", -50.0, 2),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_daily()
        assert "Daily" in result

    def test_daily_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_daily()
        assert "No" in result

    def test_weekly_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [("2024-W03", 500.0, 15)]
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_weekly()
        assert "Weekly" in result

    def test_weekly_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_weekly()
        assert "No" in result

    def test_monthly_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [("2024-01", 2000.0, 50)]
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_monthly()
        assert "Monthly" in result

    def test_monthly_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_monthly()
        assert "No" in result

    def test_by_symbol_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [("EURUSD", 1500.0, 30, 0.67)]
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_by_symbol()
        assert "EURUSD" in result

    def test_by_symbol_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_by_symbol()
        assert "No" in result

    def test_by_strategy_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [("coper", 800.0, 20)]
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_by_strategy()
        assert "coper" in result or "Strategy" in result

    def test_by_strategy_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_by_strategy()
        assert "No" in result

    def test_by_session_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [("LONDON", 1000.0, 25)]
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_by_session()
        assert "LONDON" in result or "Session" in result

    def test_by_session_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_by_session()
        assert "No" in result

    def test_by_regime_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [("TRENDING", 1200.0, 30)]
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_by_regime()
        assert "TRENDING" in result or "Regime" in result

    def test_by_regime_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_by_regime()
        assert "No" in result

    def test_drawdown_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [
            ("2024-01-15", 100.0),
            ("2024-01-16", -50.0),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_drawdown()
        assert "Drawdown" in result

    def test_drawdown_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_drawdown()
        assert "No" in result

    def test_equity_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [
            ("2024-01-15", 100.0),
            ("2024-01-16", 250.0),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_equity()
        assert "Equity" in result

    def test_equity_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_equity()
        assert "No" in result

    def test_trades_found(self, mock_cf):
        mock_db = MagicMock()
        # Columns: symbol, direction, volume, entry_price, exit_price, pnl, commission, opened_at, closed_at
        mock_db.query.return_value = [
            ("EURUSD", "BUY", 0.10, 1.0850, 1.0900, 50.0, -2.0, "2024-01-15", "2024-01-16"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_trades()
        assert "EURUSD" in result

    def test_trades_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_trades()
        assert "No" in result

    def test_expectancy_found(self, mock_cf):
        mock_db = MagicMock()
        # query_one returns: (avg_win, avg_loss, win_rate)
        mock_db.query_one.return_value = (80.0, -30.0, 0.6)
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_expectancy()
        assert "Expectancy" in result

    def test_expectancy_no_data(self, mock_cf):
        mock_db = MagicMock()
        # row[2] is None -> "Not enough data"
        mock_db.query_one.return_value = (None, None, None)
        mock_cf.get_postgres.return_value = mock_db
        result = _perf_expectancy()
        assert "Not enough" in result


class TestPerfStaticCommands:
    def test_risk_adjusted(self):
        result = _perf_risk_adjusted()
        assert "info" in result.lower()

    def test_correlation_pnl(self):
        result = _perf_correlation_pnl()
        assert "pandas" in result.lower() or "info" in result.lower()


class TestPerfRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "perf" in reg.categories
        expected = ["summary", "daily", "weekly", "monthly", "by-symbol",
                    "by-strategy", "by-session", "by-regime", "drawdown",
                    "equity", "trades", "expectancy"]
        for cmd in expected:
            assert cmd in reg._commands["perf"]
