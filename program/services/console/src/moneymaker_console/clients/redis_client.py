"""Lazy Redis client for state reads, kill switch, and pub/sub."""

from __future__ import annotations

import json
import os
from typing import Any

from moneymaker_console.console_logging import log_event


class RedisClient:
    """Lazy Redis connection with graceful fallback."""

    def __init__(self) -> None:
        self._client = None
        self._available = True

    def _connect(self):
        if not self._available:
            return None
        if self._client is not None:
            return self._client
        try:
            import redis

            host = os.environ.get("MONEYMAKER_REDIS_HOST", "localhost")
            port = int(os.environ.get("MONEYMAKER_REDIS_PORT", "6379"))
            password = os.environ.get("MONEYMAKER_REDIS_PASSWORD", None)

            self._client = redis.Redis(
                host=host,
                port=port,
                password=password if password else None,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._client.ping()
            log_event("redis_connected", host=host, port=port)
            return self._client
        except ImportError:
            self._available = False
            log_event("redis_unavailable", reason="redis package not installed")
            return None
        except Exception as exc:
            log_event("redis_connect_error", error=str(exc))
            self._client = None
            return None

    def ping(self) -> bool:
        """Check Redis connectivity."""
        client = self._connect()
        if client is None:
            return False
        try:
            return client.ping()
        except Exception as exc:
            log_event("redis_ping_error", error=str(exc))
            self._client = None
            return False

    def get(self, key: str) -> str | None:
        """Get a string value by key."""
        client = self._connect()
        if client is None:
            return None
        try:
            return client.get(key)
        except Exception as exc:
            log_event("redis_get_error", key=key, error=str(exc))
            return None

    def get_json(self, key: str) -> dict | None:
        """Get and parse a JSON value."""
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            log_event("redis_json_decode_error", key=key, error=str(exc))
            return None

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """Set a string value."""
        client = self._connect()
        if client is None:
            return False
        try:
            client.set(key, value, ex=ex)
            return True
        except Exception as exc:
            log_event("redis_set_error", key=key, error=str(exc))
            return False

    def set_json(self, key: str, data: dict, ex: int | None = None) -> bool:
        """Set a JSON value."""
        return self.set(key, json.dumps(data, default=str), ex=ex)

    def delete(self, key: str) -> bool:
        """Delete a key."""
        client = self._connect()
        if client is None:
            return False
        try:
            client.delete(key)
            return True
        except Exception as exc:
            log_event("redis_delete_error", key=key, error=str(exc))
            return False

    def publish(self, channel: str, message: str) -> bool:
        """Publish a message to a pub/sub channel."""
        client = self._connect()
        if client is None:
            return False
        try:
            client.publish(channel, message)
            return True
        except Exception as exc:
            log_event("redis_publish_error", channel=channel, error=str(exc))
            return False

    def info(self, section: str | None = None) -> dict[str, Any]:
        """Return Redis INFO as a dict."""
        client = self._connect()
        if client is None:
            return {}
        try:
            return client.info(section) if section else client.info()
        except Exception as exc:
            log_event("redis_info_error", error=str(exc))
            return {}

    @property
    def is_available(self) -> bool:
        return self._available
