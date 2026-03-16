"""Tests for gRPC server mapping constants and utility methods."""

from __future__ import annotations

from unittest.mock import MagicMock

from mt5_bridge.grpc_server import (
    ExecutionServicer,
    GRPCExecutionServicer,
    ExecutionServer,
    _PROTO_DIRECTION_TO_STR,
    _STATUS_STR_TO_PROTO,
)


class TestProtoDirectionMapping:
    def test_unspecified_maps_to_hold(self):
        assert _PROTO_DIRECTION_TO_STR[0] == "HOLD"

    def test_buy_maps_correctly(self):
        assert _PROTO_DIRECTION_TO_STR[1] == "BUY"

    def test_sell_maps_correctly(self):
        assert _PROTO_DIRECTION_TO_STR[2] == "SELL"

    def test_hold_maps_correctly(self):
        assert _PROTO_DIRECTION_TO_STR[3] == "HOLD"


class TestStatusStrToProto:
    def test_pending(self):
        assert _STATUS_STR_TO_PROTO["PENDING"] == 1

    def test_filled(self):
        assert _STATUS_STR_TO_PROTO["FILLED"] == 2

    def test_partially_filled(self):
        assert _STATUS_STR_TO_PROTO["PARTIALLY_FILLED"] == 3

    def test_rejected(self):
        assert _STATUS_STR_TO_PROTO["REJECTED"] == 4

    def test_cancelled(self):
        assert _STATUS_STR_TO_PROTO["CANCELLED"] == 5

    def test_expired(self):
        assert _STATUS_STR_TO_PROTO["EXPIRED"] == 6

    def test_error(self):
        assert _STATUS_STR_TO_PROTO["ERROR"] == 7

    def test_unknown(self):
        assert _STATUS_STR_TO_PROTO["UNKNOWN"] == 0


class TestExecutionServicerInit:
    def test_stores_order_manager(self):
        mock_om = MagicMock()
        servicer = ExecutionServicer(mock_om)
        assert servicer._order_manager is mock_om


class TestGRPCExecutionServicerInit:
    def test_stores_servicer_and_limiter(self):
        mock_servicer = MagicMock()
        mock_limiter = MagicMock()
        grpc_servicer = GRPCExecutionServicer(mock_servicer, rate_limiter=mock_limiter)
        assert grpc_servicer._servicer is mock_servicer
        assert grpc_servicer._rate_limiter is mock_limiter

    def test_rate_limiter_defaults_to_none(self):
        mock_servicer = MagicMock()
        grpc_servicer = GRPCExecutionServicer(mock_servicer)
        assert grpc_servicer._rate_limiter is None


class TestExtractClientId:
    def _make_servicer(self):
        return GRPCExecutionServicer(MagicMock())

    def test_ipv4_extraction(self):
        s = self._make_servicer()
        ctx = MagicMock()
        ctx.peer.return_value = "ipv4:192.168.1.1:50051"
        assert s._extract_client_id(ctx) == "192.168.1.1"

    def test_ipv6_extraction(self):
        s = self._make_servicer()
        ctx = MagicMock()
        ctx.peer.return_value = "ipv6:[::1]:50051"
        assert s._extract_client_id(ctx) == "::1"

    def test_returns_unknown_on_none_peer(self):
        s = self._make_servicer()
        ctx = MagicMock()
        ctx.peer.return_value = None
        assert s._extract_client_id(ctx) == "unknown"

    def test_returns_unknown_on_exception(self):
        s = self._make_servicer()
        ctx = MagicMock()
        ctx.peer.side_effect = Exception("fail")
        assert s._extract_client_id(ctx) == "unknown"


class TestExecutionServerInit:
    def test_default_port(self):
        mock_servicer = MagicMock()
        server = ExecutionServer(mock_servicer)
        assert server._port == 50055
        assert server._server is None

    def test_custom_port(self):
        mock_servicer = MagicMock()
        server = ExecutionServer(mock_servicer, port=50060)
        assert server._port == 50060
