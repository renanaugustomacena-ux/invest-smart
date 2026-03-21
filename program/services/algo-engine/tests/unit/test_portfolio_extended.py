"""Extended tests for portfolio.py — win rate, equity, margin, trade recording, sync."""

import asyncio
from decimal import Decimal

from algo_engine.portfolio import PortfolioStateManager


def _run(coro):
    return asyncio.run(coro)


class TestWinRate:
    def test_no_trades_returns_050(self):
        pm = PortfolioStateManager()
        assert pm.win_rate == Decimal("0.50")

    def test_all_wins(self):
        pm = PortfolioStateManager()
        pm.record_trade_result(Decimal("100"))
        pm.record_trade_result(Decimal("50"))
        assert pm.win_rate == Decimal("1")

    def test_all_losses(self):
        pm = PortfolioStateManager()
        pm.record_trade_result(Decimal("-100"))
        pm.record_trade_result(Decimal("-50"))
        assert pm.win_rate == Decimal("0")

    def test_mixed_results(self):
        pm = PortfolioStateManager()
        pm.record_trade_result(Decimal("100"))
        pm.record_trade_result(Decimal("-50"))
        pm.record_trade_result(Decimal("75"))
        # 2 wins, 1 loss → 2/3
        expected = Decimal("2") / Decimal("3")
        assert abs(pm.win_rate - expected) < Decimal("0.001")

    def test_zero_profit_not_counted(self):
        pm = PortfolioStateManager()
        pm.record_trade_result(Decimal("0"))
        # Zero profit is neither win nor loss
        assert pm.win_rate == Decimal("0.50")


class TestRecordFillAndClose:
    def test_fill_tracks_symbol(self):
        pm = PortfolioStateManager()
        pm.record_fill(symbol="EURUSD", lots=Decimal("0.10"), direction="BUY")
        state = pm.get_state()
        assert "EURUSD" in state["symbols_exposed"]
        assert len(state["positions_detail"]) == 1

    def test_close_removes_position_detail(self):
        pm = PortfolioStateManager()
        pm.record_fill(symbol="EURUSD", lots=Decimal("0.10"), direction="BUY")
        pm.record_close(symbol="EURUSD", lots=Decimal("0.10"), profit=Decimal("50"), direction="BUY")
        state = pm.get_state()
        assert len(state["positions_detail"]) == 0

    def test_close_with_loss(self):
        pm = PortfolioStateManager()
        pm.record_fill(symbol="GBPUSD", lots=Decimal("0.05"), direction="SELL")
        pm.record_close(symbol="GBPUSD", lots=Decimal("0.05"), profit=Decimal("-25"))
        assert pm._last_trade_result == "loss"

    def test_multiple_fills_same_symbol(self):
        pm = PortfolioStateManager()
        pm.record_fill(symbol="EURUSD", lots=Decimal("0.10"), direction="BUY")
        pm.record_fill(symbol="EURUSD", lots=Decimal("0.05"), direction="BUY")
        assert pm.open_position_count == 2
        state = pm.get_state()
        assert len(state["positions_detail"]) == 2

    def test_close_only_removes_first_matching(self):
        pm = PortfolioStateManager()
        pm.record_fill(symbol="EURUSD", lots=Decimal("0.10"), direction="BUY")
        pm.record_fill(symbol="EURUSD", lots=Decimal("0.05"), direction="BUY")
        pm.record_close(symbol="EURUSD", lots=Decimal("0.10"), profit=Decimal("10"), direction="BUY")
        assert pm.open_position_count == 1
        state = pm.get_state()
        assert len(state["positions_detail"]) == 1


class TestEquityAndMargin:
    def test_update_equity(self):
        pm = PortfolioStateManager()
        pm.update_equity(Decimal("50000"))
        state = pm.get_state()
        assert state["equity"] == Decimal("50000")

    def test_update_used_margin(self):
        pm = PortfolioStateManager()
        pm.update_used_margin(Decimal("5000"))
        state = pm.get_state()
        assert state["used_margin"] == Decimal("5000")

    def test_update_unrealized_pnl(self):
        pm = PortfolioStateManager()
        pm.update_unrealized_pnl(Decimal("-200"))
        state = pm.get_state()
        assert state["unrealized_pnl"] == Decimal("-200")


class TestSyncRedis:
    def test_sync_without_redis_noop(self):
        pm = PortfolioStateManager()
        _run(pm.sync_from_redis())  # Should not raise

    def test_persist_without_redis_noop(self):
        pm = PortfolioStateManager()
        _run(pm.persist_to_redis())  # Should not raise


class TestGetStateFormat:
    def test_all_keys_present(self):
        pm = PortfolioStateManager()
        state = pm.get_state()
        required_keys = [
            "open_position_count",
            "current_drawdown_pct",
            "daily_loss_pct",
            "total_exposure",
            "unrealized_pnl",
            "symbols_exposed",
            "win_rate",
            "last_trade_result",
            "positions_detail",
            "equity",
            "used_margin",
        ]
        for key in required_keys:
            assert key in state, f"Missing key: {key}"

    def test_symbols_exposed_sorted(self):
        pm = PortfolioStateManager()
        pm.record_fill(symbol="GBPUSD", lots=Decimal("0.10"), direction="BUY")
        pm.record_fill(symbol="AUDUSD", lots=Decimal("0.10"), direction="BUY")
        pm.record_fill(symbol="EURUSD", lots=Decimal("0.10"), direction="BUY")
        state = pm.get_state()
        assert state["symbols_exposed"] == ["AUDUSD", "EURUSD", "GBPUSD"]

    def test_exposure_decrements_on_close(self):
        pm = PortfolioStateManager()
        pm.record_fill(symbol="EURUSD", lots=Decimal("0.10"))
        pm.record_close(symbol="EURUSD", lots=Decimal("0.10"), profit=Decimal("10"))
        state = pm.get_state()
        assert state["total_exposure"] == Decimal("0")
