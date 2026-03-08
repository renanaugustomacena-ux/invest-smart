"""Tests for WebSocket manager logic (unit tests, no WS connection)."""

from __future__ import annotations

import pytest

from backend.ws.manager import ConnectionManager


def test_manager_starts_empty():
    mgr = ConnectionManager()
    assert mgr.connection_count == 0


def test_disconnect_nonexistent_channel():
    """Disconnecting from a channel that doesn't exist is safe."""
    mgr = ConnectionManager()
    # Should not raise
    mgr.disconnect("nonexistent", None)  # type: ignore[arg-type]
