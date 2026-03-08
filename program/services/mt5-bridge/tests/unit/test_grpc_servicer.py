"""Tests for mt5_bridge.grpc_server — GRPCExecutionServicer proto translation."""

from unittest.mock import AsyncMock

import pytest

from mt5_bridge.grpc_server import GRPCExecutionServicer, ExecutionServicer


class TestGRPCExecutionServicer:
    """Test proto-to-dict and dict-to-proto conversion in GRPCExecutionServicer."""

    @pytest.fixture
    def mock_servicer(self):
        """Create an ExecutionServicer with a mocked OrderManager."""
        from unittest.mock import MagicMock

        order_manager = MagicMock()
        servicer = ExecutionServicer(order_manager)
        return servicer

    @pytest.fixture
    def grpc_servicer(self, mock_servicer):
        return GRPCExecutionServicer(mock_servicer)

    def _make_proto_request(self):
        from moneymaker_proto import trading_signal_pb2

        return trading_signal_pb2.TradingSignal(
            signal_id="sig-001",
            symbol="XAUUSD",
            direction=1,  # DIRECTION_BUY
            confidence="0.85",
            suggested_lots="0.10",
            stop_loss="2040.00",
            take_profit="2080.00",
            timestamp=1704067200000000000,
            reasoning="Test signal",
            regime="trending_up",
            risk_reward_ratio="2.67",
        )

    @pytest.mark.asyncio
    async def test_execute_trade_converts_proto_to_dict(
        self, grpc_servicer, mock_servicer
    ):
        """Verify proto TradingSignal is correctly converted to dict."""
        mock_servicer.execute_trade = AsyncMock(
            return_value={
                "status": "FILLED",
                "order_id": "ord-123",
                "signal_id": "sig-001",
                "executed_price": "2055.00",
                "volume": "0.10",
                "slippage": "0.5",
            }
        )

        request = self._make_proto_request()
        await grpc_servicer.ExecuteTrade(request, context=None)

        # Check the dict passed to the inner servicer
        call_args = mock_servicer.execute_trade.call_args[0][0]
        assert call_args["signal_id"] == "sig-001"
        assert call_args["symbol"] == "XAUUSD"
        assert call_args["direction"] == "BUY"
        assert call_args["confidence"] == "0.85"
        assert call_args["suggested_lots"] == "0.10"

    @pytest.mark.asyncio
    async def test_execute_trade_returns_proto_response(
        self, grpc_servicer, mock_servicer
    ):
        """Verify dict result is correctly converted to proto TradeExecution."""
        mock_servicer.execute_trade = AsyncMock(
            return_value={
                "status": "FILLED",
                "order_id": "ord-456",
                "signal_id": "sig-002",
                "executed_price": "1.10500",
                "volume": "0.50",
                "slippage": "0.2",
            }
        )

        request = self._make_proto_request()
        response = await grpc_servicer.ExecuteTrade(request, context=None)

        assert response.order_id == "ord-456"
        assert response.signal_id == "sig-002"
        assert response.status == 2  # STATUS_FILLED
        assert response.executed_price == "1.10500"

    @pytest.mark.asyncio
    async def test_execute_trade_rejected(self, grpc_servicer, mock_servicer):
        """Verify rejection flows through correctly."""
        mock_servicer.execute_trade = AsyncMock(
            return_value={
                "status": "REJECTED",
                "order_id": "",
                "signal_id": "sig-003",
                "rejection_reason": "Market closed",
            }
        )

        request = self._make_proto_request()
        response = await grpc_servicer.ExecuteTrade(request, context=None)

        assert response.status == 4  # STATUS_REJECTED
        assert response.rejection_reason == "Market closed"

    @pytest.mark.asyncio
    async def test_direction_mapping_sell(self, grpc_servicer, mock_servicer):
        """Verify DIRECTION_SELL maps to 'SELL' string."""
        from moneymaker_proto import trading_signal_pb2

        mock_servicer.execute_trade = AsyncMock(
            return_value={"status": "FILLED", "order_id": "ord-789"}
        )

        request = trading_signal_pb2.TradingSignal(
            signal_id="sig-004",
            symbol="EURUSD",
            direction=2,  # DIRECTION_SELL
            confidence="0.70",
        )
        await grpc_servicer.ExecuteTrade(request, context=None)

        call_args = mock_servicer.execute_trade.call_args[0][0]
        assert call_args["direction"] == "SELL"

    @pytest.mark.asyncio
    async def test_default_suggested_lots(self, grpc_servicer, mock_servicer):
        """When suggested_lots is empty, default to 0.01."""
        from moneymaker_proto import trading_signal_pb2

        mock_servicer.execute_trade = AsyncMock(
            return_value={"status": "FILLED", "order_id": "ord-999"}
        )

        request = trading_signal_pb2.TradingSignal(
            signal_id="sig-005",
            symbol="XAUUSD",
            direction=1,
            suggested_lots="",  # empty
        )
        await grpc_servicer.ExecuteTrade(request, context=None)

        call_args = mock_servicer.execute_trade.call_args[0][0]
        assert call_args["suggested_lots"] == "0.01"
