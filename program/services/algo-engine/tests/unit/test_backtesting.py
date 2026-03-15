"""Tests for BacktestMetrics and TradeSimulator."""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.backtesting.metrics import BacktestMetrics, BacktestResult, _quantize
from algo_engine.backtesting.simulator import OpenPosition, TradeSimulator
from algo_engine.features.pipeline import OHLCVBar

D = Decimal


# ===========================================================================
# _quantize
# ===========================================================================


class TestQuantize:
    def test_default_precision(self):
        assert _quantize(D("1.23456")) == D("1.2346")

    def test_custom_precision(self):
        assert _quantize(D("1.23456"), "0.01") == D("1.23")


# ===========================================================================
# BacktestResult defaults
# ===========================================================================


class TestBacktestResult:
    def test_defaults_zero(self):
        r = BacktestResult()
        assert r.sharpe_ratio == D("0")
        assert r.total_trades == 0
        assert r.equity_curve == []


# ===========================================================================
# BacktestMetrics._compute_returns
# ===========================================================================


class TestComputeReturns:
    def test_simple_returns(self):
        m = BacktestMetrics()
        curve = [D("10000"), D("10100"), D("10000")]
        ret = m._compute_returns(curve)
        assert len(ret) == 2
        # 10100/10000 - 1 = 0.01
        assert ret[0] == _quantize(D("0.01"), "0.00000001")
        # 10000/10100 - 1 ~= -0.0099
        assert ret[1] < D("0")

    def test_single_value_empty(self):
        m = BacktestMetrics()
        assert m._compute_returns([D("10000")]) == []

    def test_zero_prev_returns_zero(self):
        m = BacktestMetrics()
        ret = m._compute_returns([D("0"), D("100")])
        assert ret[0] == D("0")


# ===========================================================================
# BacktestMetrics._total_return_pct
# ===========================================================================


class TestTotalReturn:
    def test_positive_return(self):
        r = BacktestMetrics._total_return_pct(D("10000"), D("12000"))
        assert r == D("20.0000")

    def test_negative_return(self):
        r = BacktestMetrics._total_return_pct(D("10000"), D("9000"))
        assert r == D("-10.0000")

    def test_zero_initial(self):
        assert BacktestMetrics._total_return_pct(D("0"), D("100")) == D("0")


# ===========================================================================
# BacktestMetrics._max_drawdown
# ===========================================================================


class TestMaxDrawdown:
    def test_no_drawdown(self):
        curve = [D("100"), D("110"), D("120"), D("130")]
        pct, val = BacktestMetrics._max_drawdown(curve)
        assert pct == D("0")
        assert val == D("0")

    def test_with_drawdown(self):
        curve = [D("100"), D("120"), D("90"), D("110")]
        pct, val = BacktestMetrics._max_drawdown(curve)
        # Peak=120, trough=90 → 25% DD
        assert pct == D("25.0000")
        assert val == D("30.0000")

    def test_empty_curve(self):
        pct, val = BacktestMetrics._max_drawdown([])
        assert pct == D("0")


# ===========================================================================
# BacktestMetrics._sharpe_ratio
# ===========================================================================


class TestSharpeRatio:
    def test_single_return_zero(self):
        m = BacktestMetrics()
        assert m._sharpe_ratio([D("0.01")]) == D("0")

    def test_constant_returns_zero_std(self):
        m = BacktestMetrics()
        ret = [D("0.01")] * 20
        assert m._sharpe_ratio(ret) == D("0")

    def test_positive_returns_positive_sharpe(self):
        m = BacktestMetrics(risk_free_rate=D("0"))
        ret = [
            D("0.005"),
            D("0.003"),
            D("0.007"),
            D("0.002"),
            D("0.004"),
            D("0.006"),
            D("0.001"),
            D("0.008"),
            D("0.005"),
            D("0.004"),
        ]
        sharpe = m._sharpe_ratio(ret)
        assert sharpe > D("0")


# ===========================================================================
# BacktestMetrics._sortino_ratio
# ===========================================================================


class TestSortinoRatio:
    def test_no_negative_returns_zero(self):
        m = BacktestMetrics()
        ret = [D("0.01"), D("0.02"), D("0.03")]
        assert m._sortino_ratio(ret) == D("0")

    def test_mixed_returns(self):
        m = BacktestMetrics(risk_free_rate=D("0"))
        ret = [
            D("0.01"),
            D("-0.005"),
            D("0.02"),
            D("-0.01"),
            D("0.015"),
            D("-0.003"),
            D("0.005"),
            D("-0.008"),
        ]
        sortino = m._sortino_ratio(ret)
        assert sortino > D("0")


# ===========================================================================
# BacktestMetrics._compute_trade_metrics
# ===========================================================================


class TestTradeMetrics:
    def test_win_rate(self):
        m = BacktestMetrics()
        trades = [
            {"pnl": "100"},
            {"pnl": "50"},
            {"pnl": "-30"},
            {"pnl": "80"},
            {"pnl": "-20"},
        ]
        result = BacktestResult(total_trades=5, trade_log=trades)
        m._compute_trade_metrics(trades, result)
        assert result.winning_trades == 3
        assert result.losing_trades == 2
        assert result.win_rate == D("60.0000")

    def test_profit_factor(self):
        m = BacktestMetrics()
        trades = [{"pnl": "100"}, {"pnl": "-50"}]
        result = BacktestResult(total_trades=2, trade_log=trades)
        m._compute_trade_metrics(trades, result)
        assert result.profit_factor == D("2.0000")

    def test_empty_trades(self):
        m = BacktestMetrics()
        result = BacktestResult()
        m._compute_trade_metrics([], result)
        assert result.win_rate == D("0")

    def test_all_winners(self):
        m = BacktestMetrics()
        trades = [{"pnl": "100"}, {"pnl": "200"}]
        result = BacktestResult(total_trades=2, trade_log=trades)
        m._compute_trade_metrics(trades, result)
        assert result.win_rate == D("100.0000")
        assert result.gross_loss == D("0")


# ===========================================================================
# BacktestMetrics.compute (full integration)
# ===========================================================================


class TestComputeFull:
    def test_minimal_curve(self):
        m = BacktestMetrics()
        result = m.compute(
            equity_curve=[D("10000"), D("10100"), D("10200")],
            trade_log=[{"pnl": "100"}, {"pnl": "100"}],
            bars_processed=2,
            initial_equity=D("10000"),
        )
        assert result.total_return_pct == D("2.0000")
        assert result.total_trades == 2
        assert result.max_drawdown_pct == D("0")

    def test_empty_curve(self):
        m = BacktestMetrics()
        result = m.compute([], [], 0, D("10000"))
        assert result.final_equity == D("10000")
        assert result.sharpe_ratio == D("0")


# ===========================================================================
# TradeSimulator
# ===========================================================================


def _make_bar(ts=1700000000000, o="1.10000", h="1.10200", l="1.09800", c="1.10100", v="1000"):
    return OHLCVBar(timestamp=ts, open=D(o), high=D(h), low=D(l), close=D(c), volume=D(v))


class TestTradeSimulatorInit:
    def test_initial_state(self):
        sim = TradeSimulator(initial_equity=D("10000"))
        assert sim.equity == D("10000")
        assert sim.open_position_count == 0
        assert len(sim.equity_curve) == 1

    def test_equity_curve_starts_with_initial(self):
        sim = TradeSimulator(initial_equity=D("50000"))
        assert sim.equity_curve[0] == D("50000")


class TestTradeSimulatorOpenPosition:
    def test_buy_fill_above_market(self):
        sim = TradeSimulator(
            initial_equity=D("10000"),
            spread_pips=D("2.0"),
            slippage_pips=D("1.0"),
            commission_per_lot=D("7"),
        )
        signal = {
            "signal_id": "s1",
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": "1.10000",
            "stop_loss": "1.09500",
            "take_profit": "1.10800",
            "suggested_lots": "0.10",
        }
        bar = _make_bar()
        sim.open_position(signal, bar)
        assert sim.open_position_count == 1
        # Commission: 7 * 0.10 = 0.70
        assert sim.equity < D("10000")

    def test_sell_fill_below_market(self):
        sim = TradeSimulator(
            initial_equity=D("10000"),
            spread_pips=D("2.0"),
            slippage_pips=D("0"),
            pip_value=D("0.0001"),
        )
        fill = sim._fill_price(D("1.10000"), "SELL")
        assert fill < D("1.10000")


class TestTradeSimulatorProcessBar:
    def test_buy_sl_hit(self):
        sim = TradeSimulator(
            initial_equity=D("10000"),
            spread_pips=D("0"),
            slippage_pips=D("0"),
            commission_per_lot=D("0"),
        )
        signal = {
            "direction": "BUY",
            "entry_price": "1.10000",
            "stop_loss": "1.09500",
            "take_profit": "1.11000",
            "suggested_lots": "0.10",
        }
        sim.open_position(signal, _make_bar())
        # Bar low touches SL
        sim.process_bar(_make_bar(ts=1700000060000, l="1.09400"))
        assert sim.open_position_count == 0
        assert len(sim.trade_log) == 1
        assert sim.trade_log[0]["exit_reason"] == "stop_loss"

    def test_buy_tp_hit(self):
        sim = TradeSimulator(
            initial_equity=D("10000"),
            spread_pips=D("0"),
            slippage_pips=D("0"),
            commission_per_lot=D("0"),
        )
        signal = {
            "direction": "BUY",
            "entry_price": "1.10000",
            "stop_loss": "1.09500",
            "take_profit": "1.10500",
            "suggested_lots": "0.10",
        }
        sim.open_position(signal, _make_bar())
        # Bar high touches TP
        sim.process_bar(_make_bar(ts=1700000060000, h="1.10600"))
        assert sim.trade_log[0]["exit_reason"] == "take_profit"

    def test_sell_sl_hit(self):
        sim = TradeSimulator(
            initial_equity=D("10000"),
            spread_pips=D("0"),
            slippage_pips=D("0"),
            commission_per_lot=D("0"),
        )
        signal = {
            "direction": "SELL",
            "entry_price": "1.10000",
            "stop_loss": "1.10500",
            "take_profit": "1.09000",
            "suggested_lots": "0.10",
        }
        sim.open_position(signal, _make_bar())
        sim.process_bar(_make_bar(ts=1700000060000, h="1.10600"))
        assert sim.trade_log[0]["exit_reason"] == "stop_loss"

    def test_no_hit_stays_open(self):
        sim = TradeSimulator(
            initial_equity=D("10000"),
            spread_pips=D("0"),
            slippage_pips=D("0"),
            commission_per_lot=D("0"),
        )
        signal = {
            "direction": "BUY",
            "entry_price": "1.10000",
            "stop_loss": "1.09500",
            "take_profit": "1.11000",
            "suggested_lots": "0.10",
        }
        sim.open_position(signal, _make_bar())
        sim.process_bar(_make_bar(ts=1700000060000))
        assert sim.open_position_count == 1


class TestTradeSimulatorCloseAll:
    def test_close_all_at_end(self):
        sim = TradeSimulator(
            initial_equity=D("10000"),
            spread_pips=D("0"),
            slippage_pips=D("0"),
            commission_per_lot=D("0"),
        )
        signal = {
            "direction": "BUY",
            "entry_price": "1.10000",
            "stop_loss": "1.09500",
            "take_profit": "1.11000",
            "suggested_lots": "0.10",
        }
        sim.open_position(signal, _make_bar())
        sim.close_all_positions(_make_bar(c="1.10300"))
        assert sim.open_position_count == 0
        assert len(sim.trade_log) == 1
        assert sim.trade_log[0]["exit_reason"] == "end_of_backtest"


class TestTradeSimulatorPnL:
    def test_buy_profit(self):
        sim = TradeSimulator(
            initial_equity=D("10000"),
            spread_pips=D("0"),
            slippage_pips=D("0"),
            commission_per_lot=D("0"),
            pip_value=D("0.0001"),
        )
        signal = {
            "direction": "BUY",
            "entry_price": "1.10000",
            "stop_loss": "1.09500",
            "take_profit": "1.10500",
            "suggested_lots": "1.0",
        }
        sim.open_position(signal, _make_bar())
        sim.process_bar(_make_bar(ts=1700000060000, h="1.10600"))
        # 50 pips * $10/pip * 1 lot = $500
        assert sim.trade_log[0]["pnl"] == D("500.00")

    def test_sell_profit(self):
        sim = TradeSimulator(
            initial_equity=D("10000"),
            spread_pips=D("0"),
            slippage_pips=D("0"),
            commission_per_lot=D("0"),
            pip_value=D("0.0001"),
        )
        signal = {
            "direction": "SELL",
            "entry_price": "1.10000",
            "stop_loss": "1.10500",
            "take_profit": "1.09500",
            "suggested_lots": "1.0",
        }
        sim.open_position(signal, _make_bar())
        sim.process_bar(_make_bar(ts=1700000060000, l="1.09400"))
        # 50 pips * $10/pip * 1 lot = $500
        assert sim.trade_log[0]["pnl"] == D("500.00")
