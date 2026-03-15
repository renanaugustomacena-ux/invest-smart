"""Real-time market data poller via ZMQ SUB socket.

Subscribes to the Data Ingestion ZMQ PUB socket on port 5555
for live tick and bar data. Thread-safe price cache.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any


class MarketPoller:
    """Daemon thread that subscribes to ZMQ PUB for real-time prices.

    Thread-safe cache accessed via ``get_prices()``.
    """

    def __init__(self) -> None:
        self._prices: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._available = True

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3)

    def get_prices(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return dict(self._prices)

    def _poll_loop(self) -> None:
        try:
            import zmq
        except ImportError:
            self._available = False
            return

        zmq_host = os.environ.get("MONEYMAKER_ZMQ_HOST", "localhost")
        zmq_port = os.environ.get("MONEYMAKER_ZMQ_PORT", "5555")
        endpoint = f"tcp://{zmq_host}:{zmq_port}"

        ctx = zmq.Context()
        sock = ctx.socket(zmq.SUB)
        sock.setsockopt(zmq.RCVTIMEO, 2000)
        sock.setsockopt_string(zmq.SUBSCRIBE, "")

        try:
            sock.connect(endpoint)
        except zmq.ZMQError:
            self._available = False
            return

        while not self._stop.is_set():
            try:
                raw = sock.recv_string(zmq.NOBLOCK)
                self._process_message(raw)
            except zmq.Again:
                # Timeout — no message, loop continues
                pass
            except zmq.ZMQError:
                break
            self._stop.wait(0.05)

        sock.close()
        ctx.term()

    def _process_message(self, raw: str) -> None:
        """Parse a ZMQ message and update the price cache."""
        try:
            # Messages may be topic + payload separated by space
            parts = raw.split(" ", 1)
            if len(parts) == 2:
                topic, payload = parts
            else:
                payload = parts[0]
                topic = ""

            data = json.loads(payload)
            symbol = data.get("symbol", topic.split(".")[-1] if "." in topic else "")

            if symbol:
                with self._lock:
                    self._prices[symbol] = {
                        "bid": data.get("bid"),
                        "ask": data.get("ask"),
                        "last": data.get("close", data.get("price")),
                        "spread": data.get("spread"),
                        "timestamp": data.get("timestamp", data.get("open_time")),
                    }
        except (json.JSONDecodeError, KeyError) as exc:
            from moneymaker_console.console_logging import log_event

            log_event("market_poller_parse_error", error=str(exc), raw=raw[:80])

    @property
    def is_available(self) -> bool:
        return self._available
