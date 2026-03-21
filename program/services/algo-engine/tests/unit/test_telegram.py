"""Tests for TelegramChannel — async Telegram Bot API alert sender.

All tests use REAL objects — no MagicMock, no @patch, no unittest.mock.
- httpx.MockTransport intercepts HTTP requests (real httpx feature)
- monkeypatch controls environment variables
- Direct client injection via _client attribute
"""

from __future__ import annotations

import httpx
import pytest

from algo_engine.alerting.dispatcher import AlertLevel
from algo_engine.alerting.telegram import TELEGRAM_API_URL, TelegramChannel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_channel_with_transport(handler, bot_token="test-token", chat_id="12345"):
    """Create a TelegramChannel with a custom MockTransport-backed client."""
    channel = TelegramChannel(bot_token=bot_token, chat_id=chat_id)
    transport = httpx.MockTransport(handler)
    channel._client = httpx.AsyncClient(transport=transport)
    return channel


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTelegramChannelSuccess:
    """Successful send scenarios."""

    async def test_successful_send_returns_true(self) -> None:
        captured_requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json={"ok": True})

        channel = _make_channel_with_transport(handler)
        result = await channel.send(AlertLevel.INFO, "Test Title", "Test body")

        assert result is True
        assert len(captured_requests) == 1

    async def test_request_url_contains_bot_token(self) -> None:
        captured_requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json={"ok": True})

        channel = _make_channel_with_transport(handler, bot_token="MY-SECRET-TOKEN")
        await channel.send(AlertLevel.INFO, "Title", "Body")

        url = str(captured_requests[0].url)
        assert "MY-SECRET-TOKEN" in url

    async def test_html_formatting_title_bold(self) -> None:
        import json as json_module

        captured_payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json_module.loads(request.content)
            captured_payloads.append(payload)
            return httpx.Response(200, json={"ok": True})

        channel = _make_channel_with_transport(handler)
        await channel.send(AlertLevel.CRITICAL, "Kill Switch Activated", "Drawdown 5%")

        assert len(captured_payloads) == 1
        text = captured_payloads[0]["text"]
        assert "<b>Kill Switch Activated</b>" in text
        assert "Drawdown 5%" in text
        assert captured_payloads[0]["parse_mode"] == "HTML"

    async def test_payload_includes_chat_id(self) -> None:
        import json as json_module

        captured_payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json_module.loads(request.content)
            captured_payloads.append(payload)
            return httpx.Response(200, json={"ok": True})

        channel = _make_channel_with_transport(handler, chat_id="-999888777")
        await channel.send(AlertLevel.WARNING, "Test", "Body")

        assert captured_payloads[0]["chat_id"] == "-999888777"


class TestTelegramChannelFailures:
    """Error handling scenarios."""

    async def test_api_error_returns_false(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"ok": False, "description": "Bad Request"})

        channel = _make_channel_with_transport(handler)
        result = await channel.send(AlertLevel.INFO, "Title", "Body")

        assert result is False

    async def test_server_error_returns_false(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "Internal Server Error"})

        channel = _make_channel_with_transport(handler)
        result = await channel.send(AlertLevel.CRITICAL, "Title", "Body")

        assert result is False

    async def test_transport_exception_returns_false(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        channel = _make_channel_with_transport(handler)
        result = await channel.send(AlertLevel.WARNING, "Title", "Body")

        assert result is False


class TestTelegramChannelConfig:
    """Configuration and environment variable fallback."""

    async def test_no_bot_token_warns_but_no_crash(self) -> None:
        # Empty token means _get_client() will create a client,
        # but URL will be malformed — should not crash
        channel = TelegramChannel(bot_token="", chat_id="123")
        # The channel has empty token, but calling send should not raise
        # It will try to send to an invalid URL and fail gracefully
        # We need a mock transport to avoid real HTTP
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"ok": False})

        transport = httpx.MockTransport(handler)
        channel._client = httpx.AsyncClient(transport=transport)
        result = await channel.send(AlertLevel.INFO, "Test", "Body")
        assert result is False

    async def test_env_var_fallback_for_token(self, monkeypatch) -> None:
        monkeypatch.setenv("MONEYMAKER_TELEGRAM_BOT_TOKEN", "env-token-123")
        monkeypatch.setenv("MONEYMAKER_TELEGRAM_CHAT_ID", "env-chat-456")

        channel = TelegramChannel()
        assert channel._bot_token == "env-token-123"
        assert channel._chat_id == "env-chat-456"

    async def test_explicit_params_override_env_vars(self, monkeypatch) -> None:
        monkeypatch.setenv("MONEYMAKER_TELEGRAM_BOT_TOKEN", "env-token")
        monkeypatch.setenv("MONEYMAKER_TELEGRAM_CHAT_ID", "env-chat")

        channel = TelegramChannel(bot_token="explicit-token", chat_id="explicit-chat")
        assert channel._bot_token == "explicit-token"
        assert channel._chat_id == "explicit-chat"
