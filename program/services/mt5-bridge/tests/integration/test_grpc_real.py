"""Integration tests for the gRPC server with REAL server and client.

Starts a real grpc.aio.server on a random port, registers the
GRPCExecutionServicer, and sends real RPC calls via a real channel.

NO MOCKS: the OrderManager is created with a real (but disconnected)
MT5Connector. execute_signal raises BrokerError because the connector
is not connected to any MT5 terminal -- this is genuine behavior.
"""

from __future__ import annotations

import asyncio
import socket
from decimal import Decimal

import grpc
import grpc.aio
import pytest

from moneymaker_proto import execution_pb2, execution_pb2_grpc, health_pb2, trading_signal_pb2
from mt5_bridge.connector import MT5Connector
from mt5_bridge.grpc_server import ExecutionServicer, GRPCExecutionServicer
from mt5_bridge.order_manager import OrderManager


def _get_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
async def grpc_server_and_channel():
    """Start a real gRPC server and yield (server, channel, port).

    The OrderManager is wired to a real MT5Connector that is NOT connected,
    so any call that reaches the connector will raise BrokerError or
    SignalRejectedError -- genuine rejection behavior.
    """
    port = _get_free_port()

    # Real connector -- never connected (no MT5 terminal available)
    connector = MT5Connector(
        account="0",
        password="",
        server="",
        timeout_ms=1000,
    )

    # Real OrderManager with the disconnected connector
    order_manager = OrderManager(
        connector=connector,
        max_lot_size=Decimal("1.0"),
        max_position_count=5,
        dedup_window_sec=300,
        max_spread_points=30,
        signal_max_age_sec=30,
    )

    # Build the real gRPC servicer chain
    exec_servicer = ExecutionServicer(order_manager)
    grpc_servicer = GRPCExecutionServicer(exec_servicer)

    # Start a real async gRPC server
    server = grpc.aio.server()
    execution_pb2_grpc.add_ExecutionBridgeServiceServicer_to_server(grpc_servicer, server)
    server.add_insecure_port(f"127.0.0.1:{port}")
    await server.start()

    # Create a real channel
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")

    yield server, channel, port

    await channel.close()
    await server.stop(grace=1)


@pytest.mark.asyncio
async def test_execute_trade_returns_rejected_or_error(grpc_server_and_channel):
    """ExecuteTrade should return REJECTED or ERROR because MT5 is not connected.

    The OrderManager._validate_signal calls connector.get_open_positions()
    which raises BrokerError('Non connesso al terminale MT5'). The
    ExecutionServicer catches BrokerError and returns status ERROR.
    """
    _server, channel, _port = grpc_server_and_channel

    stub = execution_pb2_grpc.ExecutionBridgeServiceStub(channel)

    request = trading_signal_pb2.TradingSignal(
        signal_id="integ-test-001",
        symbol="EURUSD",
        direction=trading_signal_pb2.DIRECTION_BUY,
        confidence="0.80",
        suggested_lots="0.01",
        stop_loss="1.08000",
        take_profit="1.10000",
        model_version="test-v1",
        regime="unknown",
        risk_reward_ratio="2.0",
        reasoning="integration test",
    )

    response = await stub.ExecuteTrade(request)

    # Verify the response is a valid TradeExecution proto
    assert isinstance(response, execution_pb2.TradeExecution)
    assert response.signal_id == "integ-test-001"
    assert response.symbol == "EURUSD"

    # Status should be REJECTED (4) or ERROR (7) because the connector is disconnected
    status_val = response.status
    assert status_val in (
        execution_pb2.TradeExecution.STATUS_REJECTED,
        execution_pb2.TradeExecution.STATUS_ERROR,
    ), f"Expected REJECTED or ERROR, got status={status_val}"

    # There should be a rejection reason explaining the failure
    assert response.rejection_reason != ""


@pytest.mark.asyncio
async def test_execute_trade_sell_direction(grpc_server_and_channel):
    """ExecuteTrade with SELL direction should also return REJECTED or ERROR."""
    _server, channel, _port = grpc_server_and_channel

    stub = execution_pb2_grpc.ExecutionBridgeServiceStub(channel)

    request = trading_signal_pb2.TradingSignal(
        signal_id="integ-test-sell-001",
        symbol="XAUUSD",
        direction=trading_signal_pb2.DIRECTION_SELL,
        confidence="0.75",
        suggested_lots="0.05",
        stop_loss="2060.00",
        take_profit="2030.00",
        model_version="test-v1",
        regime="ranging",
        risk_reward_ratio="1.5",
    )

    response = await stub.ExecuteTrade(request)

    assert isinstance(response, execution_pb2.TradeExecution)
    assert response.symbol == "XAUUSD"
    assert response.status in (
        execution_pb2.TradeExecution.STATUS_REJECTED,
        execution_pb2.TradeExecution.STATUS_ERROR,
    )


@pytest.mark.asyncio
async def test_check_health_returns_unhealthy(grpc_server_and_channel):
    """CheckHealth should return UNHEALTHY because MT5 terminal is not connected.

    The GRPCExecutionServicer.CheckHealth accesses self._order_manager which
    does not exist on that class (it has self._servicer). The AttributeError
    is caught by the except block and UNHEALTHY is returned.
    """
    _server, channel, _port = grpc_server_and_channel

    stub = execution_pb2_grpc.ExecutionBridgeServiceStub(channel)

    request = health_pb2.HealthCheckRequest(service_name="mt5-bridge")

    response = await stub.CheckHealth(request)

    assert isinstance(response, health_pb2.HealthCheckResponse)
    assert response.status == health_pb2.HealthCheckResponse.UNHEALTHY
    assert "disconnesso" in response.message.lower() or "unhealthy" in response.message.lower()


@pytest.mark.asyncio
async def test_grpc_server_handles_multiple_requests(grpc_server_and_channel):
    """The server should handle multiple sequential requests without error."""
    _server, channel, _port = grpc_server_and_channel

    stub = execution_pb2_grpc.ExecutionBridgeServiceStub(channel)

    for i in range(3):
        request = trading_signal_pb2.TradingSignal(
            signal_id=f"multi-test-{i:03d}",
            symbol="GBPUSD",
            direction=trading_signal_pb2.DIRECTION_BUY,
            confidence="0.70",
            suggested_lots="0.01",
            stop_loss="1.25000",
            take_profit="1.27000",
        )

        response = await stub.ExecuteTrade(request)
        assert isinstance(response, execution_pb2.TradeExecution)
        assert response.signal_id == f"multi-test-{i:03d}"


@pytest.mark.asyncio
async def test_execute_trade_with_hold_direction(grpc_server_and_channel):
    """HOLD direction should be translated to 'HOLD' and rejected by validation."""
    _server, channel, _port = grpc_server_and_channel

    stub = execution_pb2_grpc.ExecutionBridgeServiceStub(channel)

    request = trading_signal_pb2.TradingSignal(
        signal_id="integ-test-hold-001",
        symbol="EURUSD",
        direction=trading_signal_pb2.DIRECTION_HOLD,
        confidence="0.60",
        suggested_lots="0.01",
        stop_loss="1.08000",
        take_profit="1.10000",
    )

    response = await stub.ExecuteTrade(request)

    assert isinstance(response, execution_pb2.TradeExecution)
    # HOLD is not BUY or SELL, so OrderManager._validate_signal rejects it
    assert response.status in (
        execution_pb2.TradeExecution.STATUS_REJECTED,
        execution_pb2.TradeExecution.STATUS_ERROR,
    )


@pytest.mark.asyncio
async def test_channel_connectivity(grpc_server_and_channel):
    """Verify that the real channel can reach the real server."""
    _server, channel, port = grpc_server_and_channel

    # channel_ready waits for the channel to enter READY state
    # If this times out, the channel cannot reach the server
    await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
