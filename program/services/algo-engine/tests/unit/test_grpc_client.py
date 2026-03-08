"""Tests for algo_engine.grpc_client — signal-to-proto conversion."""

from decimal import Decimal

from algo_engine.grpc_client import execution_to_dict, signal_to_proto


class TestSignalToProto:
    def _make_signal(self, **overrides):
        base = {
            "signal_id": "sig-001",
            "symbol": "XAUUSD",
            "direction": "BUY",
            "confidence": Decimal("0.85"),
            "suggested_lots": Decimal("0.10"),
            "stop_loss": Decimal("2040.00"),
            "take_profit": Decimal("2080.00"),
            "timestamp_ms": 1704067200000,
            "model_version": "",
            "regime": "trending_up",
            "source_tier": 2,
            "reasoning": "Trend following signal",
            "risk_reward_ratio": Decimal("2.67"),
        }
        base.update(overrides)
        return base

    def test_all_fields_mapped(self):
        sig = self._make_signal()
        proto = signal_to_proto(sig)
        assert proto.signal_id == "sig-001"
        assert proto.symbol == "XAUUSD"
        assert proto.confidence == "0.85"
        assert proto.reasoning == "Trend following signal"
        assert proto.regime == "trending_up"

    def test_direction_buy(self):
        proto = signal_to_proto(self._make_signal(direction="BUY"))
        assert proto.direction == 1  # DIRECTION_BUY

    def test_direction_sell(self):
        proto = signal_to_proto(self._make_signal(direction="SELL"))
        assert proto.direction == 2  # DIRECTION_SELL

    def test_direction_hold(self):
        proto = signal_to_proto(self._make_signal(direction="HOLD"))
        assert proto.direction == 3  # DIRECTION_HOLD

    def test_decimal_to_string(self):
        sig = self._make_signal(
            confidence=Decimal("0.9123"),
            stop_loss=Decimal("2039.50"),
            take_profit=Decimal("2079.50"),
        )
        proto = signal_to_proto(sig)
        assert proto.confidence == "0.9123"
        assert proto.stop_loss == "2039.50"
        assert proto.take_profit == "2079.50"

    def test_timestamp_ms_to_ns(self):
        sig = self._make_signal(timestamp_ms=1704067200000)
        proto = signal_to_proto(sig)
        assert proto.timestamp == 1704067200000 * 1_000_000


class TestExecutionToDict:
    def test_round_trip_structure(self):
        """Verify execution_to_dict returns all expected keys."""
        from moneymaker_proto import execution_pb2

        response = execution_pb2.TradeExecution(
            order_id="ord-123",
            signal_id="sig-001",
            symbol="XAUUSD",
            executed_price="2055.00",
            quantity="0.10",
            stop_loss="2040.00",
            take_profit="2080.00",
            status=2,  # STATUS_FILLED
            slippage_pips="0.5",
            commission="3.20",
            swap="0",
            executed_at=1704067200000000000,
            rejection_reason="",
        )
        result = execution_to_dict(response)
        assert result["order_id"] == "ord-123"
        assert result["signal_id"] == "sig-001"
        assert result["status"] == "FILLED"
        assert result["executed_price"] == "2055.00"
        assert result["slippage_pips"] == "0.5"

    def test_rejected_status(self):
        from moneymaker_proto import execution_pb2

        response = execution_pb2.TradeExecution(
            order_id="",
            signal_id="sig-002",
            symbol="EURUSD",
            status=4,  # STATUS_REJECTED
            rejection_reason="Market closed",
        )
        result = execution_to_dict(response)
        assert result["status"] == "REJECTED"
        assert result["rejection_reason"] == "Market closed"
