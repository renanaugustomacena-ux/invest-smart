"""Tests for TrailingStopManager and PositionTracker."""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.signals.trailing_stop import (
    PositionTracker,
    TrailingMode,
    TrailingStopManager,
    TrailingStopState,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

D = Decimal


# ---------------------------------------------------------------------------
# TrailingStopState
# ---------------------------------------------------------------------------


class TestTrailingStopState:
    def test_frozen(self):
        state = TrailingStopState(
            symbol="EURUSD",
            direction="BUY",
            entry_price=D("1.10000"),
            current_stop=D("1.09500"),
            highest_price=D("1.10000"),
            lowest_price=D("1.10000"),
            mode=TrailingMode.ATR_TRAIL,
        )
        with pytest.raises(AttributeError):
            state.current_stop = D("1.0")  # type: ignore[misc]

    def test_default_not_break_even(self):
        state = TrailingStopState(
            symbol="EURUSD",
            direction="BUY",
            entry_price=D("1.10000"),
            current_stop=D("1.09500"),
            highest_price=D("1.10000"),
            lowest_price=D("1.10000"),
            mode=TrailingMode.ATR_TRAIL,
        )
        assert state.is_break_even is False


# ---------------------------------------------------------------------------
# open_position
# ---------------------------------------------------------------------------


class TestOpenPosition:
    def test_creates_state(self):
        mgr = TrailingStopManager()
        state = mgr.open_position("XAUUSD", "BUY", D("2000"), D("1990"))
        assert state.symbol == "XAUUSD"
        assert state.direction == "BUY"
        assert state.entry_price == D("2000")
        assert state.current_stop == D("1990")
        assert state.highest_price == D("2000")
        assert state.lowest_price == D("2000")

    def test_custom_mode(self):
        mgr = TrailingStopManager()
        state = mgr.open_position(
            "EURUSD",
            "SELL",
            D("1.1"),
            D("1.12"),
            mode=TrailingMode.CHANDELIER,
        )
        assert state.mode == TrailingMode.CHANDELIER


# ---------------------------------------------------------------------------
# ATR Trailing
# ---------------------------------------------------------------------------


class TestATRTrail:
    def test_buy_stop_moves_up(self):
        mgr = TrailingStopManager(atr_multiplier=D("2.0"))
        state = mgr.open_position("EURUSD", "BUY", D("1.10000"), D("1.09000"))
        # Price rises: high = 1.11000, ATR = 0.00300
        # Candidate = 1.11000 - 2.0 * 0.00300 = 1.10400
        # 1.10400 > 1.09000 → moves up
        new = mgr.update(state, D("1.10800"), D("1.11000"), D("1.10500"), D("0.00300"))
        assert new.current_stop > state.current_stop

    def test_buy_stop_never_moves_down(self):
        mgr = TrailingStopManager(atr_multiplier=D("2.0"))
        state = mgr.open_position("EURUSD", "BUY", D("1.10000"), D("1.09500"))
        # Price drops: candidate would be below current stop
        new = mgr.update(state, D("1.09600"), D("1.09700"), D("1.09400"), D("0.00300"))
        assert new.current_stop >= state.current_stop

    def test_sell_stop_moves_down(self):
        mgr = TrailingStopManager(atr_multiplier=D("2.0"))
        state = mgr.open_position("EURUSD", "SELL", D("1.10000"), D("1.11000"))
        # Price drops: low = 1.09000
        # Candidate = 1.09000 + 2.0 * 0.00300 = 1.09600
        # 1.09600 < 1.11000 → moves down (tighter)
        new = mgr.update(state, D("1.09200"), D("1.09500"), D("1.09000"), D("0.00300"))
        assert new.current_stop < state.current_stop

    def test_sell_stop_never_moves_up(self):
        mgr = TrailingStopManager(atr_multiplier=D("2.0"))
        state = mgr.open_position("EURUSD", "SELL", D("1.10000"), D("1.10500"))
        # Price rises: candidate would be above current stop
        new = mgr.update(state, D("1.11000"), D("1.11500"), D("1.10800"), D("0.00300"))
        assert new.current_stop <= state.current_stop


# ---------------------------------------------------------------------------
# Chandelier
# ---------------------------------------------------------------------------


class TestChandelier:
    def test_buy_chandelier_trail(self):
        mgr = TrailingStopManager(chandelier_multiplier=D("3.0"))
        state = mgr.open_position(
            "EURUSD",
            "BUY",
            D("1.10000"),
            D("1.09000"),
            mode=TrailingMode.CHANDELIER,
        )
        # High = 1.12000, ATR = 0.00200
        # Candidate = 1.12000 - 3.0 * 0.00200 = 1.11400
        new = mgr.update(state, D("1.11500"), D("1.12000"), D("1.11000"), D("0.00200"))
        assert new.current_stop > state.current_stop


# ---------------------------------------------------------------------------
# Break Even
# ---------------------------------------------------------------------------


class TestBreakEven:
    def test_promotes_to_break_even(self):
        mgr = TrailingStopManager(break_even_atr_profit=D("2.0"))
        state = mgr.open_position(
            "EURUSD",
            "BUY",
            D("1.10000"),
            D("1.09500"),
            mode=TrailingMode.BREAK_EVEN,
        )
        # Profit threshold = 2.0 * ATR (0.00200) = 0.00400
        # Price at 1.10500, profit = 0.00500 > 0.00400 → break even
        new = mgr.update(state, D("1.10500"), D("1.10600"), D("1.10400"), D("0.00200"))
        assert new.is_break_even is True
        assert new.mode == TrailingMode.ATR_TRAIL  # switches to ATR
        assert new.current_stop >= state.entry_price

    def test_not_enough_profit_stays(self):
        mgr = TrailingStopManager(break_even_atr_profit=D("2.0"))
        state = mgr.open_position(
            "EURUSD",
            "BUY",
            D("1.10000"),
            D("1.09500"),
            mode=TrailingMode.BREAK_EVEN,
        )
        # Profit = 0.00100, threshold = 0.00400 → no promotion
        new = mgr.update(state, D("1.10100"), D("1.10200"), D("1.10000"), D("0.00200"))
        assert new.is_break_even is False
        assert new.mode == TrailingMode.BREAK_EVEN

    def test_sell_break_even(self):
        mgr = TrailingStopManager(break_even_atr_profit=D("2.0"))
        state = mgr.open_position(
            "EURUSD",
            "SELL",
            D("1.10000"),
            D("1.10500"),
            mode=TrailingMode.BREAK_EVEN,
        )
        # Profit = entry - price = 1.10000 - 1.09400 = 0.00600 > threshold 0.00400
        new = mgr.update(state, D("1.09400"), D("1.09600"), D("1.09300"), D("0.00200"))
        assert new.is_break_even is True


# ---------------------------------------------------------------------------
# Percentage
# ---------------------------------------------------------------------------


class TestPercentageTrail:
    def test_buy_percentage_trail(self):
        mgr = TrailingStopManager(pct_trail=D("1.0"))
        state = mgr.open_position(
            "EURUSD",
            "BUY",
            D("100.00"),
            D("98.00"),
            mode=TrailingMode.PERCENTAGE,
        )
        # Highest = 105.00, candidate = 105.00 * (1 - 0.01) = 103.95
        # 103.95 > 98.00 → moves up
        new = mgr.update(state, D("104.00"), D("105.00"), D("103.50"), D("1.0"))
        assert new.current_stop > state.current_stop

    def test_sell_percentage_trail(self):
        mgr = TrailingStopManager(pct_trail=D("1.0"))
        state = mgr.open_position(
            "EURUSD",
            "SELL",
            D("100.00"),
            D("102.00"),
            mode=TrailingMode.PERCENTAGE,
        )
        # Lowest = 95.00, candidate = 95.00 * (1 + 0.01) = 95.95
        # 95.95 < 102.00 → moves down (tighter)
        new = mgr.update(state, D("96.00"), D("97.00"), D("95.00"), D("1.0"))
        assert new.current_stop < state.current_stop


# ---------------------------------------------------------------------------
# Stopped out
# ---------------------------------------------------------------------------


class TestStoppedOut:
    def test_buy_stopped_out_at_stop(self):
        mgr = TrailingStopManager()
        state = mgr.open_position("EURUSD", "BUY", D("1.10000"), D("1.09500"))
        assert mgr.is_stopped_out(state, D("1.09500"))

    def test_buy_stopped_out_below_stop(self):
        mgr = TrailingStopManager()
        state = mgr.open_position("EURUSD", "BUY", D("1.10000"), D("1.09500"))
        assert mgr.is_stopped_out(state, D("1.09000"))

    def test_buy_not_stopped_above_stop(self):
        mgr = TrailingStopManager()
        state = mgr.open_position("EURUSD", "BUY", D("1.10000"), D("1.09500"))
        assert not mgr.is_stopped_out(state, D("1.10000"))

    def test_sell_stopped_out_at_stop(self):
        mgr = TrailingStopManager()
        state = mgr.open_position("EURUSD", "SELL", D("1.10000"), D("1.10500"))
        assert mgr.is_stopped_out(state, D("1.10500"))

    def test_sell_not_stopped_below_stop(self):
        mgr = TrailingStopManager()
        state = mgr.open_position("EURUSD", "SELL", D("1.10000"), D("1.10500"))
        assert not mgr.is_stopped_out(state, D("1.10000"))


# ---------------------------------------------------------------------------
# PositionTracker
# ---------------------------------------------------------------------------


class TestPositionTracker:
    def test_open_and_get(self):
        mgr = TrailingStopManager()
        tracker = PositionTracker(mgr)
        tracker.open("EURUSD", "BUY", D("1.10000"), D("1.09500"))
        pos = tracker.get_position("EURUSD")
        assert pos is not None
        assert pos.symbol == "EURUSD"

    def test_close_removes(self):
        mgr = TrailingStopManager()
        tracker = PositionTracker(mgr)
        tracker.open("EURUSD", "BUY", D("1.10000"), D("1.09500"))
        tracker.close("EURUSD")
        assert tracker.get_position("EURUSD") is None

    def test_update_all_returns_stopped(self):
        mgr = TrailingStopManager()
        tracker = PositionTracker(mgr)
        tracker.open("EURUSD", "BUY", D("1.10000"), D("1.09500"))
        bars = {
            "EURUSD": {
                "price": D("1.09000"),  # below stop
                "high": D("1.09200"),
                "low": D("1.08800"),
                "atr": D("0.00200"),
            },
        }
        stopped = tracker.update_all(bars)
        assert "EURUSD" in stopped

    def test_update_all_no_bar_skips(self):
        mgr = TrailingStopManager()
        tracker = PositionTracker(mgr)
        tracker.open("EURUSD", "BUY", D("1.10000"), D("1.09500"))
        stopped = tracker.update_all({})  # no bar data
        assert stopped == []

    def test_get_nonexistent_returns_none(self):
        mgr = TrailingStopManager()
        tracker = PositionTracker(mgr)
        assert tracker.get_position("GBPUSD") is None

    def test_multiple_positions(self):
        mgr = TrailingStopManager()
        tracker = PositionTracker(mgr)
        tracker.open("EURUSD", "BUY", D("1.10000"), D("1.09500"))
        tracker.open("GBPUSD", "SELL", D("1.30000"), D("1.30500"))
        assert tracker.get_position("EURUSD") is not None
        assert tracker.get_position("GBPUSD") is not None
