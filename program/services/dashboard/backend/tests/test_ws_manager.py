# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Tests for the WebSocket ConnectionManager.

Uses a FakeWebSocket test double -- no unittest.mock, no MagicMock, no @patch.
Each test creates a fresh ConnectionManager so there is zero shared state.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import pytest

from backend.ws.manager import ConnectionManager

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Test double
# ---------------------------------------------------------------------------

class FakeWebSocket:
    """Real implementation of a WebSocket for testing."""

    def __init__(self, should_fail: bool = False) -> None:
        self.accepted: bool = False
        self.sent_messages: list[str] = []
        self._should_fail = should_fail

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, data: str) -> None:
        if self._should_fail:
            raise ConnectionError("Client disconnected")
        self.sent_messages.append(data)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_new_manager_starts_empty():
    """A freshly created manager has zero connections."""
    mgr = ConnectionManager()

    assert mgr.connection_count == 0


async def test_connect_accepts_websocket_and_adds_to_channel():
    """connect() must call accept() on the websocket and register it."""
    mgr = ConnectionManager()
    ws = FakeWebSocket()

    await mgr.connect("prices", ws)

    assert ws.accepted is True
    assert mgr.connection_count == 1


async def test_multiple_connections_same_channel():
    """Several websockets can join the same channel."""
    mgr = ConnectionManager()
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()
    ws3 = FakeWebSocket()

    await mgr.connect("prices", ws1)
    await mgr.connect("prices", ws2)
    await mgr.connect("prices", ws3)

    assert mgr.connection_count == 3
    # All three should have been accepted
    assert ws1.accepted and ws2.accepted and ws3.accepted


async def test_multiple_channels():
    """Connections on different channels are tracked independently."""
    mgr = ConnectionManager()
    ws_prices = FakeWebSocket()
    ws_signals = FakeWebSocket()

    await mgr.connect("prices", ws_prices)
    await mgr.connect("signals", ws_signals)

    assert mgr.connection_count == 2


async def test_disconnect_removes_specific_websocket():
    """disconnect() removes only the specified websocket from the channel."""
    mgr = ConnectionManager()
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    await mgr.connect("prices", ws1)
    await mgr.connect("prices", ws2)
    assert mgr.connection_count == 2

    mgr.disconnect("prices", ws1)

    assert mgr.connection_count == 1
    # ws2 should still be reachable via broadcast
    await mgr.broadcast("prices", {"ping": 1})
    assert len(ws2.sent_messages) == 1
    assert len(ws1.sent_messages) == 0  # ws1 was disconnected before broadcast


async def test_disconnect_unknown_channel_is_noop():
    """disconnect() on a channel that was never created does not raise."""
    mgr = ConnectionManager()
    ws = FakeWebSocket()

    # Should not raise
    mgr.disconnect("nonexistent", ws)

    assert mgr.connection_count == 0


async def test_broadcast_sends_to_all_in_channel():
    """broadcast() delivers the JSON payload to every connection on the channel."""
    mgr = ConnectionManager()
    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    await mgr.connect("orders", ws1)
    await mgr.connect("orders", ws2)

    payload = {"event": "fill", "qty": 100}
    await mgr.broadcast("orders", payload)

    expected = json.dumps(payload, default=str)
    assert ws1.sent_messages == [expected]
    assert ws2.sent_messages == [expected]


async def test_broadcast_unknown_channel_is_noop():
    """broadcast() on a channel with no connections returns silently."""
    mgr = ConnectionManager()

    # Should not raise
    await mgr.broadcast("ghost", {"data": 42})


async def test_broadcast_removes_failed_connections():
    """Connections that raise on send_text are automatically pruned."""
    mgr = ConnectionManager()
    ws_good = FakeWebSocket()
    ws_bad = FakeWebSocket(should_fail=True)

    await mgr.connect("prices", ws_good)
    await mgr.connect("prices", ws_bad)
    assert mgr.connection_count == 2

    await mgr.broadcast("prices", {"tick": 1.23})

    # The bad socket should have been removed
    assert mgr.connection_count == 1
    # Good socket received the message
    assert len(ws_good.sent_messages) == 1


async def test_connection_count_tracks_across_channels():
    """connection_count sums websockets from every channel."""
    mgr = ConnectionManager()

    await mgr.connect("prices", FakeWebSocket())
    await mgr.connect("prices", FakeWebSocket())
    await mgr.connect("signals", FakeWebSocket())
    await mgr.connect("orders", FakeWebSocket())

    assert mgr.connection_count == 4

    # Disconnect one from prices
    # We need a reference to disconnect, so use a named socket
    ws_to_remove = FakeWebSocket()
    await mgr.connect("signals", ws_to_remove)
    assert mgr.connection_count == 5

    mgr.disconnect("signals", ws_to_remove)
    assert mgr.connection_count == 4


async def test_broadcast_serialises_decimal_via_default_str():
    """json.dumps(default=str) converts Decimal to its string representation."""
    mgr = ConnectionManager()
    ws = FakeWebSocket()
    await mgr.connect("prices", ws)

    payload = {"price": Decimal("1.23456789")}
    await mgr.broadcast("prices", payload)

    received = json.loads(ws.sent_messages[0])
    assert received["price"] == "1.23456789"


async def test_broadcast_serialises_datetime_via_default_str():
    """json.dumps(default=str) converts datetime to its string representation."""
    mgr = ConnectionManager()
    ws = FakeWebSocket()
    await mgr.connect("events", ws)

    ts = datetime(2026, 3, 21, 14, 30, 0)
    payload = {"timestamp": ts, "event": "trade"}
    await mgr.broadcast("events", payload)

    received = json.loads(ws.sent_messages[0])
    assert received["timestamp"] == str(ts)
    assert received["event"] == "trade"
