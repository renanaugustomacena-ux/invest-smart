# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Tests for _serialize / _serialize_list helpers across route modules.

These are module-level private functions imported directly from each route
module. The pattern is the same everywhere: datetime -> isoformat(),
non-None -> str(), None -> None.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from backend.api.routes.macro import _serialize as macro_serialize
from backend.api.routes.macro import _serialize_list as macro_serialize_list
from backend.api.routes.strategy import _serialize_list as strategy_serialize_list
from backend.api.routes.trading import _serialize as trading_serialize


class TestMacroSerialize:
    """Test _serialize from macro routes."""

    def test_datetime_becomes_isoformat(self):
        dt = datetime(2026, 3, 21, 14, 30, 0, tzinfo=timezone.utc)
        row = {"created_at": dt}
        result = macro_serialize(row)
        assert result["created_at"] == dt.isoformat()

    def test_decimal_becomes_string(self):
        row = {"price": Decimal("1234.5678")}
        result = macro_serialize(row)
        assert result["price"] == "1234.5678"

    def test_none_stays_none(self):
        row = {"missing_field": None}
        result = macro_serialize(row)
        assert result["missing_field"] is None

    def test_integer_becomes_string(self):
        row = {"count": 42}
        result = macro_serialize(row)
        assert result["count"] == "42"

    def test_string_stays_string(self):
        row = {"symbol": "EURUSD"}
        result = macro_serialize(row)
        assert result["symbol"] == "EURUSD"

    def test_mixed_row(self):
        dt = datetime(2026, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        row = {
            "ts": dt,
            "vix": Decimal("18.75"),
            "label": "low_vol",
            "note": None,
            "priority": 3,
        }
        result = macro_serialize(row)
        assert result["ts"] == dt.isoformat()
        assert result["vix"] == "18.75"
        assert result["label"] == "low_vol"
        assert result["note"] is None
        assert result["priority"] == "3"

    def test_empty_dict(self):
        result = macro_serialize({})
        assert result == {}


class TestMacroSerializeList:
    """Test _serialize_list from macro routes."""

    def test_empty_list_returns_empty(self):
        result = macro_serialize_list([])
        assert result == []

    def test_multiple_rows(self):
        dt1 = datetime(2026, 3, 1, tzinfo=timezone.utc)
        dt2 = datetime(2026, 3, 2, tzinfo=timezone.utc)
        rows = [
            {"ts": dt1, "val": Decimal("100.00")},
            {"ts": dt2, "val": None},
        ]
        result = macro_serialize_list(rows)
        assert len(result) == 2
        assert result[0]["ts"] == dt1.isoformat()
        assert result[0]["val"] == "100.00"
        assert result[1]["ts"] == dt2.isoformat()
        assert result[1]["val"] is None


class TestStrategySerializeList:
    """Test _serialize_list from strategy routes (inline comprehension variant)."""

    def test_empty_list(self):
        result = strategy_serialize_list([])
        assert result == []

    def test_datetime_and_decimal(self):
        dt = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        rows = [{"date": dt, "pnl": Decimal("-45.20"), "name": "mean_reversion"}]
        result = strategy_serialize_list(rows)
        assert len(result) == 1
        assert result[0]["date"] == dt.isoformat()
        assert result[0]["pnl"] == "-45.20"
        assert result[0]["name"] == "mean_reversion"

    def test_none_in_list(self):
        rows = [{"a": None, "b": None}]
        result = strategy_serialize_list(rows)
        assert result[0]["a"] is None
        assert result[0]["b"] is None


class TestTradingSerialize:
    """Test _serialize from trading routes (imperative for-loop variant)."""

    def test_datetime_isoformat(self):
        dt = datetime(2026, 3, 21, 8, 45, 30, tzinfo=timezone.utc)
        row = {"executed_at": dt}
        result = trading_serialize(row)
        assert result["executed_at"] == dt.isoformat()

    def test_decimal_to_string(self):
        row = {"entry_price": Decimal("1.08542"), "sl": Decimal("1.08200")}
        result = trading_serialize(row)
        assert result["entry_price"] == "1.08542"
        assert result["sl"] == "1.08200"

    def test_none_preserved(self):
        row = {"tp": None}
        result = trading_serialize(row)
        assert result["tp"] is None

    def test_bool_becomes_string(self):
        row = {"is_filled": True}
        result = trading_serialize(row)
        assert result["is_filled"] == "True"

    def test_full_trade_row(self):
        dt = datetime(2026, 2, 10, 16, 30, 0, tzinfo=timezone.utc)
        row = {
            "signal_id": 1001,
            "symbol": "GBPUSD",
            "direction": "BUY",
            "price": Decimal("1.25430"),
            "created_at": dt,
            "tp": None,
            "confidence": Decimal("0.82"),
        }
        result = trading_serialize(row)
        assert result["signal_id"] == "1001"
        assert result["symbol"] == "GBPUSD"
        assert result["direction"] == "BUY"
        assert result["price"] == "1.25430"
        assert result["created_at"] == dt.isoformat()
        assert result["tp"] is None
        assert result["confidence"] == "0.82"
