"""Tests for algo_engine.portfolio — PortfolioStateManager.

No unittest.mock — uses freezegun for time-dependent day-change logic.
"""

import datetime
from decimal import Decimal

from freezegun import freeze_time

from algo_engine.portfolio import PortfolioStateManager


class TestPortfolioStateManager:
    def test_initial_state_all_zeros(self):
        mgr = PortfolioStateManager()
        state = mgr.get_state()
        assert state["open_position_count"] == 0
        assert state["current_drawdown_pct"] == Decimal("0")
        assert state["daily_loss_pct"] == Decimal("0")

    def test_key_names_match_validator(self):
        """Keys must match SignalValidator.validate() expectations."""
        mgr = PortfolioStateManager()
        state = mgr.get_state()
        assert "open_position_count" in state
        assert "current_drawdown_pct" in state
        assert "daily_loss_pct" in state
        # Bug was: main.py used "open_positions" which doesn't match
        assert "open_positions" not in state

    def test_record_fill_increments(self):
        mgr = PortfolioStateManager()
        mgr.record_fill()
        assert mgr.get_state()["open_position_count"] == 1

    def test_multiple_fills(self):
        mgr = PortfolioStateManager()
        mgr.record_fill()
        mgr.record_fill()
        mgr.record_fill()
        assert mgr.get_state()["open_position_count"] == 3

    def test_record_close_decrements(self):
        mgr = PortfolioStateManager()
        mgr.record_fill()
        mgr.record_fill()
        mgr.record_close()
        assert mgr.get_state()["open_position_count"] == 1

    def test_close_floor_at_zero(self):
        mgr = PortfolioStateManager()
        mgr.record_close()
        assert mgr.get_state()["open_position_count"] == 0

    def test_close_floor_after_fill(self):
        mgr = PortfolioStateManager()
        mgr.record_fill()
        mgr.record_close()
        mgr.record_close()
        assert mgr.get_state()["open_position_count"] == 0

    def test_update_drawdown(self):
        mgr = PortfolioStateManager()
        mgr.update_drawdown(Decimal("3.5"))
        assert mgr.get_state()["current_drawdown_pct"] == Decimal("3.5")

    def test_update_daily_loss(self):
        mgr = PortfolioStateManager()
        mgr.update_daily_loss(Decimal("1.2"))
        assert mgr.get_state()["daily_loss_pct"] == Decimal("1.2")

    def test_open_position_count_property(self):
        mgr = PortfolioStateManager()
        assert mgr.open_position_count == 0
        mgr.record_fill()
        assert mgr.open_position_count == 1

    @freeze_time("2026-03-21 15:00:00", tz_offset=0)
    def test_daily_loss_resets_on_new_day(self):
        """Daily loss must reset to zero when the date changes."""
        mgr = PortfolioStateManager()
        mgr.update_daily_loss(Decimal("1.5"))
        assert mgr.get_state()["daily_loss_pct"] == Decimal("1.5")

        # Simulate next day by moving freeze_time forward
        with freeze_time("2026-03-22 10:00:00", tz_offset=0):
            state = mgr.get_state()
            assert state["daily_loss_pct"] == Decimal("0")

    def test_daily_loss_persists_within_same_day(self):
        """Daily loss must NOT reset within the same trading day."""
        mgr = PortfolioStateManager()
        mgr.update_daily_loss(Decimal("1.0"))
        mgr.update_daily_loss(Decimal("1.8"))
        assert mgr.get_state()["daily_loss_pct"] == Decimal("1.8")

    @freeze_time("2026-03-21 15:00:00", tz_offset=0)
    def test_daily_loss_resets_even_after_losses(self):
        """Daily loss resets on new day even if there were prior losing trades."""
        mgr = PortfolioStateManager()
        mgr.record_trade_result(Decimal("-10"))  # loss
        mgr.record_trade_result(Decimal("-10"))  # loss
        mgr.update_daily_loss(Decimal("1.8"))
        assert mgr.win_rate == Decimal("0")  # 0/2 — win_rate is lifetime, NOT reset

        with freeze_time("2026-03-22 10:00:00", tz_offset=0):
            state = mgr.get_state()
            assert state["daily_loss_pct"] == Decimal("0")
        # win_rate stays at 0 — it's a lifetime metric, not daily
        assert mgr.win_rate == Decimal("0")
