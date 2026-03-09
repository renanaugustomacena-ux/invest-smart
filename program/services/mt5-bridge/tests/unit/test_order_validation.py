"""Tests for OrderManager signal validation and lot clamping."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from moneymaker_common.exceptions import SignalRejectedError
from mt5_bridge.order_manager import OrderManager


@pytest.fixture()
def connector():
    mock = MagicMock()
    mock.get_open_positions.return_value = []
    mock.get_symbol_info.return_value = {
        "spread": 10,
        "volume_min": Decimal("0.01"),
        "volume_step": Decimal("0.01"),
        "volume_max": Decimal("100"),
    }
    mock.check_margin.return_value = None
    mock.get_account_info.return_value = {
        "balance": Decimal("10000"),
        "equity": Decimal("10000"),
        "profit": Decimal("0"),
    }
    return mock


@pytest.fixture()
def manager(connector):
    return OrderManager(
        connector=connector,
        max_lot_size=Decimal("1.00"),
        max_position_count=5,
        max_spread_points=30,
    )


def _make_signal(**overrides):
    base = {
        "signal_id": "test-sig-001",
        "symbol": "EURUSD",
        "direction": "BUY",
        "suggested_lots": "0.10",
        "stop_loss": "1.0800",
        "take_profit": "1.1000",
        "confidence": "0.85",
    }
    base.update(overrides)
    return base


class TestValidateSignal:
    def test_rejects_invalid_direction(self, manager):
        sig = _make_signal(direction="HOLD")
        with pytest.raises(SignalRejectedError):
            manager._validate_signal(sig)

    def test_rejects_empty_direction(self, manager):
        sig = _make_signal(direction="")
        with pytest.raises(SignalRejectedError):
            manager._validate_signal(sig)

    def test_rejects_zero_lots(self, manager):
        sig = _make_signal(suggested_lots="0")
        with pytest.raises(SignalRejectedError):
            manager._validate_signal(sig)

    def test_rejects_negative_lots(self, manager):
        sig = _make_signal(suggested_lots="-0.01")
        with pytest.raises(SignalRejectedError):
            manager._validate_signal(sig)

    def test_rejects_missing_stop_loss(self, manager):
        sig = _make_signal(stop_loss="0")
        with pytest.raises(SignalRejectedError):
            manager._validate_signal(sig)

    def test_rejects_position_limit(self, manager, connector):
        connector.get_open_positions.return_value = [
            {"ticket": i} for i in range(5)
        ]
        sig = _make_signal()
        with pytest.raises(SignalRejectedError, match="limite posizioni"):
            manager._validate_signal(sig)

    def test_rejects_excessive_spread(self, manager, connector):
        connector.get_symbol_info.return_value = {"spread": 50, "volume_min": Decimal("0.01"), "volume_step": Decimal("0.01")}
        sig = _make_signal()
        with pytest.raises(SignalRejectedError, match="spread"):
            manager._validate_signal(sig)

    def test_rejects_buy_sl_above_entry(self, manager):
        sig = _make_signal(direction="BUY", entry_price="1.0900", stop_loss="1.0950")
        with pytest.raises(SignalRejectedError, match="stop loss.*sotto entry"):
            manager._validate_signal(sig)

    def test_rejects_buy_tp_below_entry(self, manager):
        sig = _make_signal(direction="BUY", entry_price="1.0900", stop_loss="1.0800", take_profit="1.0850")
        with pytest.raises(SignalRejectedError, match="take profit.*sopra entry"):
            manager._validate_signal(sig)

    def test_rejects_sell_sl_below_entry(self, manager):
        sig = _make_signal(direction="SELL", entry_price="1.0900", stop_loss="1.0850")
        with pytest.raises(SignalRejectedError, match="stop loss.*sopra entry"):
            manager._validate_signal(sig)

    def test_rejects_sell_tp_above_entry(self, manager):
        sig = _make_signal(direction="SELL", entry_price="1.0900", stop_loss="1.1000", take_profit="1.0950")
        with pytest.raises(SignalRejectedError, match="take profit.*sotto entry"):
            manager._validate_signal(sig)

    def test_skips_sl_tp_check_without_entry_price(self, manager):
        sig = _make_signal(direction="BUY", stop_loss="1.0950")
        manager._validate_signal(sig)  # should not raise (no entry_price to compare)

    def test_accepts_valid_signal(self, manager):
        sig = _make_signal()
        manager._validate_signal(sig)  # should not raise


class TestClampLotSize:
    def test_clamps_above_max(self, manager):
        result = manager._clamp_lot_size(Decimal("5.00"), "EURUSD")
        assert result == Decimal("1.00")

    def test_clamps_below_min(self, manager, connector):
        connector.get_symbol_info.return_value = {
            "volume_min": Decimal("0.01"),
            "volume_step": Decimal("0.01"),
        }
        result = manager._clamp_lot_size(Decimal("0.001"), "EURUSD")
        assert result == Decimal("0.01")

    def test_rounds_to_step(self, manager, connector):
        connector.get_symbol_info.return_value = {
            "volume_min": Decimal("0.01"),
            "volume_step": Decimal("0.01"),
        }
        result = manager._clamp_lot_size(Decimal("0.155"), "EURUSD")
        assert result == Decimal("0.15")

    def test_passes_valid_size(self, manager):
        result = manager._clamp_lot_size(Decimal("0.50"), "EURUSD")
        assert result == Decimal("0.50")


class TestCleanupOldSignals:
    def test_removes_expired_signals(self, manager):
        import time
        manager._recent_signals = {
            "old": time.time() - 600,
            "fresh": time.time(),
        }
        manager._cleanup_old_signals()
        assert "old" not in manager._recent_signals
        assert "fresh" in manager._recent_signals


class TestDeduplication:
    def test_rejects_duplicate_signal(self, manager):
        sig = _make_signal()
        with patch.object(manager, "_submit_order", return_value={"retcode": 10009, "status": "FILLED"}):
            manager.execute_signal(sig)
        with pytest.raises(SignalRejectedError, match="duplicato"):
            manager.execute_signal(sig)
