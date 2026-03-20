# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""WebSocket connection manager."""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if channel not in self._connections:
            self._connections[channel] = []
        self._connections[channel].append(websocket)

    def disconnect(self, channel: str, websocket: WebSocket) -> None:
        if channel in self._connections:
            self._connections[channel] = [
                ws for ws in self._connections[channel] if ws is not websocket
            ]

    async def broadcast(self, channel: str, data: dict[str, Any]) -> None:
        if channel not in self._connections:
            return
        message = json.dumps(data, default=str)
        disconnected = []
        for ws in self._connections[channel]:
            try:
                await ws.send_text(message)
            except Exception:
                logger.debug("ws_client_send_failed", channel=channel)
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(channel, ws)

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


manager = ConnectionManager()
