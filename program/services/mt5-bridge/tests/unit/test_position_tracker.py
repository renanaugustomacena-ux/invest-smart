"""Tests for PositionTracker — pip size heuristic, trailing stops, close detection.

No unittest.mock — uses a real FakeConnector implementing the MT5Connector interface
with deterministic returns for positions and symbol info.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO

from mt5_bridge.position_tracker import PositionTracker


# ---------------------------------------------------------------------------
# FakeConnector — real implementation, NOT a mock
# ---------------------------------------------------------------------------


class FakeConnector:
    """Deterministic connector for testing. Returns configurable positions."""

    def __init__(
        self,
        open_positions: list[dict] | None = None,
        symbol_info: dict[str, Any] | None = None,
    ):
        self._open_positions = open_positions or []
        self._symbol_info = symbol_info
        self.sl_modifications: list[tuple[int, float]] = []

    def get_open_positions(self) -> list[dict]:
        return list(self._open_positions)

    def get_symbol_info(self, symbol: str) -> dict[str, Any] | None:
        return self._symbol_info

    def modify_position_sl(self, ticket: int, new_sl: float) -> bool:
        self.sl_modifications.append((ticket, new_sl))
        return True


# ---------------------------------------------------------------------------
# Pip size heuristic
# ---------------------------------------------------------------------------


class TestPipSize:
    def test_standard_forex_no_symbol_info(self):
        """Fallback: EURUSD without MT5 info → 0.0001."""
        conn = FakeConnector(symbol_info=None)
        tracker = PositionTracker(connector=conn)
        assert tracker._get_pip_size("EURUSD") == Decimal("0.0001")

    def test_jpy_pair_fallback(self):
        """Fallback: USDJPY without MT5 info → 0.01."""
        conn = FakeConnector(symbol_info=None)
        tracker = PositionTracker(connector=conn)
        assert tracker._get_pip_size("USDJPY") == Decimal("0.01")

    def test_gold_fallback(self):
        """Fallback: XAUUSD without MT5 info → 0.01."""
        conn = FakeConnector(symbol_info=None)
        tracker = PositionTracker(connector=conn)
        assert tracker._get_pip_size("XAUUSD") == Decimal("0.01")

    def test_btc_fallback(self):
        """Fallback: BTCUSD without MT5 info → 0.01."""
        conn = FakeConnector(symbol_info=None)
        tracker = PositionTracker(connector=conn)
        assert tracker._get_pip_size("BTCUSD") == Decimal("0.01")

    def test_5_digits_via_symbol_info(self):
        """5-digit forex → pip = 0.0001."""
        conn = FakeConnector(symbol_info={"digits": 5})
        tracker = PositionTracker(connector=conn)
        assert tracker._get_pip_size("EURUSD") == Decimal("0.0001")

    def test_3_digits_via_symbol_info(self):
        """3-digit symbol → pip = 0.01."""
        conn = FakeConnector(symbol_info={"digits": 3})
        tracker = PositionTracker(connector=conn)
        assert tracker._get_pip_size("USDJPY") == Decimal("0.01")

    def test_4_digits_via_symbol_info(self):
        """4-digit symbol → pip = 0.0001."""
        conn = FakeConnector(symbol_info={"digits": 4})
        tracker = PositionTracker(connector=conn)
        assert tracker._get_pip_size("EURUSD") == Decimal("0.0001")

    def test_2_digits_via_symbol_info(self):
        """2-digit symbol → pip = 0.01."""
        conn = FakeConnector(symbol_info={"digits": 2})
        tracker = PositionTracker(connector=conn)
        assert tracker._get_pip_size("XAUUSD") == Decimal("0.01")


# ---------------------------------------------------------------------------
# Close detection
# ---------------------------------------------------------------------------


class TestCloseDetection:
    def test_no_positions_returns_empty(self):
        conn = FakeConnector(open_positions=[])
        tracker = PositionTracker(connector=conn)
        closed = tracker.update()
        assert closed == []

    def test_detects_newly_closed_position(self):
        """Position disappears from MT5 → detected as closed."""
        pos = {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": "BUY",
            "profit": Decimal("50"),
            "price_open": "1.10000",
            "price_current": "1.10500",
            "sl": "1.09500",
            "tp": "1.11000",
            "volume": "0.10",
        }
        # First update: position exists
        conn = FakeConnector(open_positions=[pos])
        tracker = PositionTracker(connector=conn, trailing_stop_enabled=False)
        tracker.update()
        assert tracker.position_count == 1

        # Second update: position gone
        conn._open_positions = []
        closed = tracker.update()
        assert len(closed) == 1
        assert closed[0]["ticket"] == 12345
        assert closed[0]["status"] == "CLOSED"
        assert "closed_at" in closed[0]
        assert tracker.position_count == 0

    def test_position_still_open_not_detected(self):
        pos = {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": "BUY",
            "profit": Decimal("10"),
            "price_open": "1.10000",
            "price_current": "1.10100",
            "sl": "0",
            "tp": "0",
            "volume": "0.10",
        }
        conn = FakeConnector(open_positions=[pos])
        tracker = PositionTracker(connector=conn, trailing_stop_enabled=False)
        tracker.update()
        closed = tracker.update()
        assert closed == []
        assert tracker.position_count == 1


# ---------------------------------------------------------------------------
# get_open_positions / get_recently_closed
# ---------------------------------------------------------------------------


class TestPositionQueries:
    def test_get_open_positions(self):
        pos = {
            "ticket": 111,
            "symbol": "GBPUSD",
            "type": "SELL",
            "profit": ZERO,
            "price_open": "1.30000",
            "price_current": "1.30000",
            "sl": "0",
            "tp": "0",
            "volume": "0.05",
        }
        conn = FakeConnector(open_positions=[pos])
        tracker = PositionTracker(connector=conn, trailing_stop_enabled=False)
        tracker.update()
        open_pos = tracker.get_open_positions()
        assert len(open_pos) == 1
        assert open_pos[0]["ticket"] == 111

    def test_get_recently_closed(self):
        pos = {
            "ticket": 222,
            "symbol": "EURUSD",
            "type": "BUY",
            "profit": Decimal("25"),
            "price_open": "1.10000",
            "price_current": "1.10250",
            "sl": "0",
            "tp": "0",
            "volume": "0.10",
        }
        conn = FakeConnector(open_positions=[pos])
        tracker = PositionTracker(connector=conn, trailing_stop_enabled=False)
        tracker.update()
        conn._open_positions = []
        tracker.update()

        recent = tracker.get_recently_closed(since_seconds=3600)
        assert len(recent) == 1
        assert recent[0]["ticket"] == 222

    def test_get_recently_closed_filters_old(self):
        """Positions closed > since_seconds ago are filtered out."""
        conn = FakeConnector(open_positions=[])
        tracker = PositionTracker(connector=conn, trailing_stop_enabled=False)
        # Inject an old closed position
        tracker._closed_positions.append({
            "ticket": 999,
            "closed_at": int(time.time()) - 7200,  # 2 hours ago
        })
        recent = tracker.get_recently_closed(since_seconds=3600)
        assert len(recent) == 0


# ---------------------------------------------------------------------------
# build_trade_result
# ---------------------------------------------------------------------------


class TestBuildTradeResult:
    def test_result_format(self):
        conn = FakeConnector()
        tracker = PositionTracker(connector=conn)
        closed_pos = {
            "ticket": 12345,
            "symbol": "EURUSD",
            "type": "BUY",
            "volume": "0.10",
            "price_open": "1.10000",
            "price_current": "1.10500",
            "sl": "1.09500",
            "tp": "1.11000",
            "profit": "50.00",
            "swap": "-2.50",
            "commission": "-1.00",
            "time": 1700000000,
            "closed_at": 1700003600,
            "magic": 123456,
            "comment": "MONEYMAKER:abc12345",
        }
        result = tracker.build_trade_result(closed_pos)

        assert result["ticket"] == 12345
        assert result["symbol"] == "EURUSD"
        assert result["direction"] == "BUY"
        assert result["volume"] == "0.10"
        assert result["price_open"] == "1.10000"
        assert result["price_close"] == "1.10500"
        assert result["stop_loss"] == "1.09500"
        assert result["take_profit"] == "1.11000"
        assert result["profit"] == "50.00"
        assert result["swap"] == "-2.50"
        assert result["commission"] == "-1.00"
        assert result["open_time"] == 1700000000
        assert result["close_time"] == 1700003600
        assert result["magic"] == 123456
        assert result["comment"] == "MONEYMAKER:abc12345"

    def test_result_missing_fields_default(self):
        conn = FakeConnector()
        tracker = PositionTracker(connector=conn)
        minimal_pos = {
            "ticket": 1,
            "symbol": "XAUUSD",
            "type": "SELL",
        }
        result = tracker.build_trade_result(minimal_pos)
        assert result["volume"] == "0"
        assert result["profit"] == "0"
        assert result["swap"] == "0"


# ---------------------------------------------------------------------------
# Trailing stop
# ---------------------------------------------------------------------------


class TestTrailingStop:
    def test_buy_trailing_activated(self):
        """BUY position with profit > activation threshold → SL moved up."""
        conn = FakeConnector(
            symbol_info={"digits": 5},  # pip = 0.0001
            open_positions=[
                {
                    "ticket": 100,
                    "symbol": "EURUSD",
                    "type": "BUY",
                    "profit": Decimal("100"),
                    "price_open": "1.10000",
                    "price_current": "1.10500",  # 50 pips profit
                    "sl": "1.09500",
                    "tp": "1.11000",
                    "volume": "0.10",
                }
            ],
        )
        tracker = PositionTracker(
            connector=conn,
            trailing_stop_enabled=True,
            trailing_activation_pips=Decimal("30"),
            trailing_stop_pips=Decimal("20"),
        )
        tracker.update()

        # SL should have been moved: 1.10500 - 20 pips = 1.10500 - 0.0020 = 1.10300
        assert len(conn.sl_modifications) == 1
        ticket, new_sl = conn.sl_modifications[0]
        assert ticket == 100
        assert abs(new_sl - 1.10300) < 0.00001

    def test_buy_trailing_not_activated_below_threshold(self):
        """BUY with only 20 pips profit < 30 pip activation → no trailing."""
        conn = FakeConnector(
            symbol_info={"digits": 5},
            open_positions=[
                {
                    "ticket": 101,
                    "symbol": "EURUSD",
                    "type": "BUY",
                    "profit": Decimal("20"),
                    "price_open": "1.10000",
                    "price_current": "1.10200",  # 20 pips < 30 activation
                    "sl": "1.09500",
                    "tp": "1.11000",
                    "volume": "0.10",
                }
            ],
        )
        tracker = PositionTracker(
            connector=conn,
            trailing_stop_enabled=True,
            trailing_activation_pips=Decimal("30"),
        )
        tracker.update()
        assert len(conn.sl_modifications) == 0

    def test_buy_trailing_not_moved_if_worse(self):
        """BUY: new SL below current SL → don't move (would worsen protection)."""
        conn = FakeConnector(
            symbol_info={"digits": 5},
            open_positions=[
                {
                    "ticket": 102,
                    "symbol": "EURUSD",
                    "type": "BUY",
                    "profit": Decimal("50"),
                    "price_open": "1.10000",
                    "price_current": "1.10400",  # 40 pips profit
                    "sl": "1.10350",  # SL already very tight
                    "tp": "1.11000",
                    "volume": "0.10",
                }
            ],
        )
        tracker = PositionTracker(
            connector=conn,
            trailing_stop_enabled=True,
            trailing_activation_pips=Decimal("30"),
            trailing_stop_pips=Decimal("50"),  # new_sl = 1.10400 - 0.0050 = 1.09900 < 1.10350
        )
        tracker.update()
        assert len(conn.sl_modifications) == 0

    def test_sell_trailing_activated(self):
        """SELL position with profit > activation → SL moved down."""
        conn = FakeConnector(
            symbol_info={"digits": 5},
            open_positions=[
                {
                    "ticket": 200,
                    "symbol": "EURUSD",
                    "type": "SELL",
                    "profit": Decimal("100"),
                    "price_open": "1.10500",
                    "price_current": "1.10000",  # 50 pips profit
                    "sl": "1.11000",
                    "tp": "1.09500",
                    "volume": "0.10",
                }
            ],
        )
        tracker = PositionTracker(
            connector=conn,
            trailing_stop_enabled=True,
            trailing_activation_pips=Decimal("30"),
            trailing_stop_pips=Decimal("20"),
        )
        tracker.update()

        # SL should be: 1.10000 + 20 pips = 1.10000 + 0.0020 = 1.10200
        assert len(conn.sl_modifications) == 1
        ticket, new_sl = conn.sl_modifications[0]
        assert ticket == 200
        assert abs(new_sl - 1.10200) < 0.00001

    def test_losing_position_no_trailing(self):
        """Position with negative profit → trailing not applied."""
        conn = FakeConnector(
            symbol_info={"digits": 5},
            open_positions=[
                {
                    "ticket": 300,
                    "symbol": "EURUSD",
                    "type": "BUY",
                    "profit": Decimal("-20"),
                    "price_open": "1.10000",
                    "price_current": "1.09800",
                    "sl": "1.09500",
                    "tp": "1.11000",
                    "volume": "0.10",
                }
            ],
        )
        tracker = PositionTracker(connector=conn, trailing_stop_enabled=True)
        tracker.update()
        assert len(conn.sl_modifications) == 0

    def test_trailing_disabled(self):
        """When trailing_stop_enabled=False, no SL modifications."""
        conn = FakeConnector(
            symbol_info={"digits": 5},
            open_positions=[
                {
                    "ticket": 400,
                    "symbol": "EURUSD",
                    "type": "BUY",
                    "profit": Decimal("200"),
                    "price_open": "1.10000",
                    "price_current": "1.11000",
                    "sl": "1.09500",
                    "tp": "1.12000",
                    "volume": "0.10",
                }
            ],
        )
        tracker = PositionTracker(connector=conn, trailing_stop_enabled=False)
        tracker.update()
        assert len(conn.sl_modifications) == 0
