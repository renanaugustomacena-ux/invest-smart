"""gRPC contract tests: verify algo-engine client and mt5-bridge servicer agree.

These tests verify that proto-generated message types serialize/deserialize
correctly and that field types match between services.
"""

import pytest
from decimal import Decimal

try:
    from moneymaker_proto import (
        trading_signal_pb2,
        execution_pb2,
        health_pb2,
        market_data_pb2,
    )

    PROTO_AVAILABLE = True
except ImportError:
    PROTO_AVAILABLE = False


@pytest.mark.skipif(not PROTO_AVAILABLE, reason="Proto stubs not installed")
class TestTradingSignalContract:
    """Verify TradingSignal proto contract between algo-engine and mt5-bridge."""

    def test_trading_signal_roundtrip(self):
        """Construct a TradingSignal, serialize, deserialize, verify fields."""
        signal = trading_signal_pb2.TradingSignal(
            signal_id="contract-test-001",
            symbol="XAUUSD",
            confidence="0.72",
            suggested_lots="0.05",
            stop_loss="2645.00",
            take_profit="2665.00",
            regime="trending_up",
            reasoning="Contract test signal",
        )

        # Serialize to bytes and back
        data = signal.SerializeToString()
        restored = trading_signal_pb2.TradingSignal()
        restored.ParseFromString(data)

        assert restored.signal_id == "contract-test-001"
        assert restored.symbol == "XAUUSD"
        assert restored.confidence == "0.72"
        assert restored.suggested_lots == "0.05"
        assert restored.stop_loss == "2645.00"
        assert restored.take_profit == "2665.00"
        assert restored.regime == "trending_up"
        assert restored.reasoning == "Contract test signal"

    def test_trading_signal_decimal_precision(self):
        """Verify string-encoded Decimals survive proto roundtrip."""
        precision_value = "2650.123456789012345678"
        signal = trading_signal_pb2.TradingSignal(
            signal_id="precision-test",
            symbol="XAUUSD",
            confidence="0.999999999",
            stop_loss=precision_value,
        )
        data = signal.SerializeToString()
        restored = trading_signal_pb2.TradingSignal()
        restored.ParseFromString(data)

        # String encoding preserves full precision
        assert Decimal(restored.stop_loss) == Decimal(precision_value)
        assert Decimal(restored.confidence) == Decimal("0.999999999")

    def test_empty_optional_fields(self):
        """Verify signal with minimal fields doesn't crash."""
        signal = trading_signal_pb2.TradingSignal(
            signal_id="minimal-test",
            symbol="XAUUSD",
        )
        data = signal.SerializeToString()
        restored = trading_signal_pb2.TradingSignal()
        restored.ParseFromString(data)

        assert restored.signal_id == "minimal-test"
        assert restored.confidence == ""
        assert restored.stop_loss == ""


@pytest.mark.skipif(not PROTO_AVAILABLE, reason="Proto stubs not installed")
class TestMarketDataContract:
    """Verify MarketTick and OHLCVBar proto contracts."""

    def test_ohlcv_bar_roundtrip(self):
        """OHLCVBar serialization preserves all fields."""
        bar = market_data_pb2.OHLCVBar(
            symbol="XAUUSD",
            timeframe="M1",
            open="2650.50",
            high="2651.80",
            low="2649.20",
            close="2651.00",
            volume="1500",
            tick_count=45,
            complete=True,
            spread_avg="0.30",
        )
        data = bar.SerializeToString()
        restored = market_data_pb2.OHLCVBar()
        restored.ParseFromString(data)

        assert restored.symbol == "XAUUSD"
        assert restored.timeframe == "M1"
        assert Decimal(restored.open) == Decimal("2650.50")
        assert Decimal(restored.close) == Decimal("2651.00")
        assert restored.tick_count == 45
        assert restored.complete is True


@pytest.mark.skipif(not PROTO_AVAILABLE, reason="Proto stubs not installed")
class TestHealthContract:
    """Verify health check proto contract."""

    def test_health_request_response(self):
        """Health check request/response roundtrip."""
        request = health_pb2.HealthCheckRequest(service="algo-engine")
        data = request.SerializeToString()
        restored = health_pb2.HealthCheckRequest()
        restored.ParseFromString(data)

        assert restored.service == "algo-engine"
