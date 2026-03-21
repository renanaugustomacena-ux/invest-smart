"""Tests for OrderManager — signal validation, dedup, lot clamping, risk limits.

No unittest.mock — uses a real FakeConnector implementing the MT5Connector interface
with deterministic returns. The _submit_order/_submit_limit_order methods require
the MetaTrader5 Windows package, so we test everything up to submission.
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

import pytest

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.exceptions import BrokerError, SignalRejectedError

from mt5_bridge.order_manager import OrderManager


# ---------------------------------------------------------------------------
# FakeConnector — real implementation, NOT a mock
# ---------------------------------------------------------------------------


class FakeConnector:
    """Deterministic connector for testing. Returns known data."""

    def __init__(
        self,
        open_positions: list[dict] | None = None,
        symbol_info: dict[str, Any] | None = None,
        account_info: dict[str, Any] | None = None,
        margin_error: bool = False,
    ):
        self._open_positions = open_positions or []
        self._symbol_info = symbol_info or {
            "spread": 15,
            "volume_min": Decimal("0.01"),
            "volume_max": Decimal("100.0"),
            "volume_step": Decimal("0.01"),
            "digits": 5,
        }
        self._account_info = account_info or {
            "balance": Decimal("10000"),
            "equity": Decimal("9800"),
            "profit": Decimal("-50"),
        }
        self._margin_error = margin_error
        self.sl_modifications: list[tuple[int, float]] = []

    def get_open_positions(self) -> list[dict]:
        return self._open_positions

    def get_symbol_info(self, symbol: str) -> dict[str, Any] | None:
        return self._symbol_info

    def get_account_info(self) -> dict[str, Any]:
        return self._account_info

    def check_margin(self, symbol: str, direction: str, lots: float) -> dict | None:
        if self._margin_error:
            raise BrokerError("margine insufficiente")
        return {"margin": 100.0}

    def modify_position_sl(self, ticket: int, new_sl: float) -> bool:
        self.sl_modifications.append((ticket, new_sl))
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(**overrides) -> dict:
    """Valid BUY signal dict."""
    base = {
        "signal_id": "test-sig-001",
        "symbol": "EURUSD",
        "direction": "BUY",
        "suggested_lots": "0.10",
        "entry_price": "1.10000",
        "stop_loss": "1.09500",
        "take_profit": "1.10800",
        "confidence": "0.80",
        "timestamp_ms": str(int(time.time() * 1000)),
    }
    base.update(overrides)
    return base


def _make_manager(connector: FakeConnector | None = None, **kwargs) -> OrderManager:
    """Create OrderManager with FakeConnector."""
    conn = connector or FakeConnector()
    defaults = {
        "connector": conn,
        "max_lot_size": Decimal("1.0"),
        "max_position_count": 5,
    }
    defaults.update(kwargs)
    return OrderManager(**defaults)


# ---------------------------------------------------------------------------
# Signal validation
# ---------------------------------------------------------------------------


class TestSignalValidation:
    def test_invalid_direction_rejected(self):
        mgr = _make_manager()
        with pytest.raises(SignalRejectedError, match="direzione"):
            mgr._validate_signal(_make_signal(direction="HOLD"))

    def test_buy_direction_accepted(self):
        mgr = _make_manager()
        mgr._validate_signal(_make_signal(direction="BUY"))

    def test_sell_direction_accepted(self):
        mgr = _make_manager()
        mgr._validate_signal(
            _make_signal(
                direction="SELL",
                stop_loss="1.10500",
                take_profit="1.09200",
            )
        )

    def test_zero_lots_rejected(self):
        mgr = _make_manager()
        with pytest.raises(SignalRejectedError, match="lotti"):
            mgr._validate_signal(_make_signal(suggested_lots="0"))

    def test_negative_lots_rejected(self):
        mgr = _make_manager()
        with pytest.raises(SignalRejectedError, match="lotti"):
            mgr._validate_signal(_make_signal(suggested_lots="-0.1"))

    def test_missing_stop_loss_rejected(self):
        mgr = _make_manager()
        with pytest.raises(SignalRejectedError, match="stop loss"):
            mgr._validate_signal(_make_signal(stop_loss="0"))

    def test_buy_sl_above_entry_rejected(self):
        mgr = _make_manager()
        with pytest.raises(SignalRejectedError, match="BUY.*stop loss"):
            mgr._validate_signal(
                _make_signal(direction="BUY", entry_price="1.10000", stop_loss="1.11000")
            )

    def test_buy_tp_below_entry_rejected(self):
        mgr = _make_manager()
        with pytest.raises(SignalRejectedError, match="BUY.*take profit"):
            mgr._validate_signal(
                _make_signal(direction="BUY", entry_price="1.10000", take_profit="1.09000")
            )

    def test_sell_sl_below_entry_rejected(self):
        mgr = _make_manager()
        with pytest.raises(SignalRejectedError, match="SELL.*stop loss"):
            mgr._validate_signal(
                _make_signal(
                    direction="SELL",
                    entry_price="1.10000",
                    stop_loss="1.09000",
                    take_profit="1.09200",
                )
            )

    def test_sell_tp_above_entry_rejected(self):
        mgr = _make_manager()
        with pytest.raises(SignalRejectedError, match="SELL.*take profit"):
            mgr._validate_signal(
                _make_signal(
                    direction="SELL",
                    entry_price="1.10000",
                    stop_loss="1.10500",
                    take_profit="1.11000",
                )
            )


# ---------------------------------------------------------------------------
# Signal age
# ---------------------------------------------------------------------------


class TestSignalAge:
    def test_old_signal_rejected(self):
        mgr = _make_manager(signal_max_age_sec=10)
        old_ts = str(int((time.time() - 60) * 1000))
        with pytest.raises(SignalRejectedError, match="troppo vecchio"):
            mgr._validate_signal(_make_signal(timestamp_ms=old_ts))

    def test_fresh_signal_accepted(self):
        mgr = _make_manager(signal_max_age_sec=30)
        fresh_ts = str(int(time.time() * 1000))
        mgr._validate_signal(_make_signal(timestamp_ms=fresh_ts))

    def test_no_timestamp_accepted(self):
        """Signal without timestamp_ms skips age check."""
        mgr = _make_manager(signal_max_age_sec=10)
        sig = _make_signal()
        del sig["timestamp_ms"]
        mgr._validate_signal(sig)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_duplicate_signal_rejected(self):
        mgr = _make_manager()
        mgr._recent_signals["test-sig-001"] = time.time()
        with pytest.raises(SignalRejectedError, match="duplicato"):
            mgr._execute_signal_locked(_make_signal())

    def test_different_signal_id_accepted(self):
        mgr = _make_manager()
        mgr._recent_signals["other-signal"] = time.time()
        # Should not raise for different signal_id
        # Will fail at _submit_order (MetaTrader5 not available) but dedup passes
        with pytest.raises(BrokerError):
            mgr._execute_signal_locked(_make_signal(signal_id="test-sig-002"))

    def test_cleanup_removes_old_entries(self):
        mgr = _make_manager(dedup_window_sec=60)
        mgr._recent_signals["old-sig"] = time.time() - 120
        mgr._recent_signals["new-sig"] = time.time()
        mgr._cleanup_old_signals()
        assert "old-sig" not in mgr._recent_signals
        assert "new-sig" in mgr._recent_signals


# ---------------------------------------------------------------------------
# Lot clamping
# ---------------------------------------------------------------------------


class TestLotClamping:
    def test_clamp_to_max(self):
        mgr = _make_manager(max_lot_size=Decimal("0.50"))
        result = mgr._clamp_lot_size(Decimal("1.0"), "EURUSD")
        assert result <= Decimal("0.50")

    def test_clamp_to_symbol_min(self):
        conn = FakeConnector(
            symbol_info={
                "spread": 10,
                "volume_min": Decimal("0.01"),
                "volume_max": Decimal("100.0"),
                "volume_step": Decimal("0.01"),
                "digits": 5,
            }
        )
        mgr = _make_manager(connector=conn)
        result = mgr._clamp_lot_size(Decimal("0.001"), "EURUSD")
        assert result == Decimal("0.01")

    def test_clamp_to_volume_step(self):
        conn = FakeConnector(
            symbol_info={
                "spread": 10,
                "volume_min": Decimal("0.01"),
                "volume_max": Decimal("100.0"),
                "volume_step": Decimal("0.10"),
                "digits": 5,
            }
        )
        mgr = _make_manager(connector=conn)
        result = mgr._clamp_lot_size(Decimal("0.35"), "EURUSD")
        assert result == Decimal("0.30")

    def test_within_limits_unchanged(self):
        mgr = _make_manager(max_lot_size=Decimal("1.0"))
        result = mgr._clamp_lot_size(Decimal("0.10"), "EURUSD")
        assert result == Decimal("0.10")


# ---------------------------------------------------------------------------
# Risk limits
# ---------------------------------------------------------------------------


class TestRiskLimits:
    def test_position_limit_reached(self):
        positions = [{"ticket": i} for i in range(5)]
        conn = FakeConnector(open_positions=positions)
        mgr = _make_manager(connector=conn, max_position_count=5)
        with pytest.raises(SignalRejectedError, match="limite posizioni"):
            mgr._validate_signal(_make_signal())

    def test_spread_too_high(self):
        conn = FakeConnector(
            symbol_info={
                "spread": 50,
                "volume_min": Decimal("0.01"),
                "volume_max": Decimal("100"),
                "volume_step": Decimal("0.01"),
                "digits": 5,
            }
        )
        mgr = _make_manager(connector=conn, max_spread_points=30)
        with pytest.raises(SignalRejectedError, match="spread"):
            mgr._validate_signal(_make_signal())

    def test_margin_insufficient(self):
        conn = FakeConnector(margin_error=True)
        mgr = _make_manager(connector=conn)
        with pytest.raises(SignalRejectedError, match="margine"):
            mgr._validate_signal(_make_signal())

    def test_drawdown_exceeded(self):
        conn = FakeConnector(
            account_info={
                "balance": Decimal("10000"),
                "equity": Decimal("8000"),
                "profit": Decimal("-100"),
            }
        )
        mgr = _make_manager(connector=conn, max_drawdown_pct=Decimal("10.0"))
        # Drawdown = (10000 - 8000) / 10000 * 100 = 20% > 10%
        with pytest.raises(SignalRejectedError, match="drawdown"):
            mgr._validate_signal(_make_signal())

    def test_daily_loss_exceeded(self):
        conn = FakeConnector(
            account_info={
                "balance": Decimal("10000"),
                "equity": Decimal("9900"),
                "profit": Decimal("-500"),
            }
        )
        mgr = _make_manager(connector=conn, max_daily_loss_pct=Decimal("2.0"))
        # Daily loss = (500 / 10000) * 100 = 5.0% > 2.0%
        with pytest.raises(SignalRejectedError, match="perdita giornaliera"):
            mgr._validate_signal(_make_signal())
