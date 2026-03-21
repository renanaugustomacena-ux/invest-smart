"""Tests for AlertDispatcher — the alert routing hub with rate limiting.

All tests use REAL class instances — no MagicMock, no @patch, no unittest.mock.
- RecordingChannel: real AlertChannel subclass that records sent messages
- FailingChannel: real AlertChannel subclass that always raises
- Rate limiting tested by direct manipulation of _last_sent timestamps
"""

from __future__ import annotations

import time

import pytest

from algo_engine.alerting.dispatcher import (
    LEVEL_EMOJI,
    AlertChannel,
    AlertDispatcher,
    AlertLevel,
)

# ---------------------------------------------------------------------------
# Helpers — real channel implementations (no mocking)
# ---------------------------------------------------------------------------


class RecordingChannel(AlertChannel):
    """Records every message sent through this channel."""

    def __init__(self) -> None:
        self.messages: list[tuple[AlertLevel, str, str]] = []

    async def send(self, level: AlertLevel, title: str, body: str) -> bool:
        self.messages.append((level, title, body))
        return True


class FailingChannel(AlertChannel):
    """Always raises RuntimeError on send."""

    async def send(self, level: AlertLevel, title: str, body: str) -> bool:
        raise RuntimeError("Channel connection lost")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAlertDispatcherNoChannels:
    """Dispatcher with zero channels should silently do nothing."""

    async def test_send_with_no_channels_completes(self) -> None:
        dispatcher = AlertDispatcher()
        # Must not raise
        await dispatcher.send(AlertLevel.INFO, "Test", "body")

    async def test_send_critical_with_no_channels(self) -> None:
        dispatcher = AlertDispatcher()
        await dispatcher.send(AlertLevel.CRITICAL, "Emergency", "big problem")


class TestAlertDispatcherFormatting:
    """Verify the formatted title includes emoji and level tag."""

    async def test_info_title_format(self) -> None:
        channel = RecordingChannel()
        dispatcher = AlertDispatcher()
        dispatcher.add_channel(channel)

        await dispatcher.send(AlertLevel.INFO, "Server Up", "All good")

        assert len(channel.messages) == 1
        level, title, body = channel.messages[0]
        emoji = LEVEL_EMOJI[AlertLevel.INFO]
        assert title == f"{emoji} [INFO] Server Up"
        assert body == "All good"
        assert level == AlertLevel.INFO

    async def test_warning_title_format(self) -> None:
        channel = RecordingChannel()
        dispatcher = AlertDispatcher()
        dispatcher.add_channel(channel)

        await dispatcher.send(AlertLevel.WARNING, "High Spread", "Spread > 5 pips")

        _, title, _ = channel.messages[0]
        emoji = LEVEL_EMOJI[AlertLevel.WARNING]
        assert title == f"{emoji} [WARNING] High Spread"

    async def test_critical_title_format(self) -> None:
        channel = RecordingChannel()
        dispatcher = AlertDispatcher()
        dispatcher.add_channel(channel)

        await dispatcher.send(AlertLevel.CRITICAL, "Kill Switch", "Drawdown exceeded")

        _, title, _ = channel.messages[0]
        emoji = LEVEL_EMOJI[AlertLevel.CRITICAL]
        assert title == f"{emoji} [CRITICAL] Kill Switch"


class TestAlertDispatcherRateLimiting:
    """Rate limiting based on level:title:context key."""

    async def test_second_send_within_interval_suppressed(self) -> None:
        channel = RecordingChannel()
        dispatcher = AlertDispatcher(min_interval_sec=30.0)
        dispatcher.add_channel(channel)

        await dispatcher.send(AlertLevel.INFO, "Alert", "first")
        await dispatcher.send(AlertLevel.INFO, "Alert", "second")

        assert len(channel.messages) == 1
        assert channel.messages[0][2] == "first"

    async def test_send_after_interval_passes(self) -> None:
        channel = RecordingChannel()
        dispatcher = AlertDispatcher(min_interval_sec=30.0)
        dispatcher.add_channel(channel)

        await dispatcher.send(AlertLevel.INFO, "Alert", "first")
        assert len(channel.messages) == 1

        # Manipulate _last_sent to simulate time passing
        for key in list(dispatcher._last_sent):
            dispatcher._last_sent[key] -= 31.0

        await dispatcher.send(AlertLevel.INFO, "Alert", "second")
        assert len(channel.messages) == 2
        assert channel.messages[1][2] == "second"

    async def test_critical_uses_shorter_interval(self) -> None:
        channel = RecordingChannel()
        dispatcher = AlertDispatcher(min_interval_sec=30.0, critical_min_interval_sec=5.0)
        dispatcher.add_channel(channel)

        await dispatcher.send(AlertLevel.CRITICAL, "Kill", "first")
        assert len(channel.messages) == 1

        # Shift timestamp back by 6 seconds — should be past critical interval
        for key in list(dispatcher._last_sent):
            dispatcher._last_sent[key] -= 6.0

        await dispatcher.send(AlertLevel.CRITICAL, "Kill", "second")
        assert len(channel.messages) == 2

    async def test_critical_still_rate_limited_within_short_interval(self) -> None:
        channel = RecordingChannel()
        dispatcher = AlertDispatcher(min_interval_sec=30.0, critical_min_interval_sec=5.0)
        dispatcher.add_channel(channel)

        await dispatcher.send(AlertLevel.CRITICAL, "Kill", "first")
        # Immediate second send — within 5s critical interval
        await dispatcher.send(AlertLevel.CRITICAL, "Kill", "second")

        assert len(channel.messages) == 1

    async def test_context_separates_rate_limit_keys(self) -> None:
        channel = RecordingChannel()
        dispatcher = AlertDispatcher(min_interval_sec=30.0)
        dispatcher.add_channel(channel)

        await dispatcher.send(AlertLevel.INFO, "Spread Wide", "body", context="EURUSD")
        await dispatcher.send(AlertLevel.INFO, "Spread Wide", "body", context="GBPUSD")

        # Same title, different context → both should send
        assert len(channel.messages) == 2

    async def test_different_levels_have_separate_keys(self) -> None:
        channel = RecordingChannel()
        dispatcher = AlertDispatcher(min_interval_sec=30.0)
        dispatcher.add_channel(channel)

        await dispatcher.send(AlertLevel.INFO, "Same Title", "body")
        await dispatcher.send(AlertLevel.WARNING, "Same Title", "body")

        assert len(channel.messages) == 2


class TestAlertDispatcherMultipleChannels:
    """All registered channels receive each alert."""

    async def test_all_channels_receive_message(self) -> None:
        ch1 = RecordingChannel()
        ch2 = RecordingChannel()
        dispatcher = AlertDispatcher()
        dispatcher.add_channel(ch1)
        dispatcher.add_channel(ch2)

        await dispatcher.send(AlertLevel.WARNING, "Test", "payload")

        assert len(ch1.messages) == 1
        assert len(ch2.messages) == 1
        assert ch1.messages[0][2] == "payload"
        assert ch2.messages[0][2] == "payload"

    async def test_failing_channel_does_not_prevent_others(self) -> None:
        good = RecordingChannel()
        bad = FailingChannel()
        good2 = RecordingChannel()
        dispatcher = AlertDispatcher()
        dispatcher.add_channel(good)
        dispatcher.add_channel(bad)
        dispatcher.add_channel(good2)

        # Should not raise despite FailingChannel
        await dispatcher.send(AlertLevel.CRITICAL, "Alert", "important")

        assert len(good.messages) == 1
        assert len(good2.messages) == 1

    async def test_all_channels_failing_does_not_raise(self) -> None:
        dispatcher = AlertDispatcher()
        dispatcher.add_channel(FailingChannel())
        dispatcher.add_channel(FailingChannel())

        # Must complete without raising
        await dispatcher.send(AlertLevel.INFO, "Test", "body")


class TestAlertDispatcherCleanup:
    """Old _last_sent entries are pruned (cutoff = now - 3600)."""

    async def test_old_entries_cleaned_up(self) -> None:
        channel = RecordingChannel()
        dispatcher = AlertDispatcher(min_interval_sec=10.0)
        dispatcher.add_channel(channel)

        await dispatcher.send(AlertLevel.INFO, "Msg", "first")
        assert "info:Msg" in dispatcher._last_sent

        # Simulate an entry from 2 hours ago
        dispatcher._last_sent["info:OldKey"] = time.monotonic() - 7200

        # Send another message to trigger cleanup
        for key in list(dispatcher._last_sent):
            if key == "info:Msg":
                dispatcher._last_sent[key] -= 11.0

        await dispatcher.send(AlertLevel.INFO, "Msg", "second")

        # Old entry should be cleaned up
        assert "info:OldKey" not in dispatcher._last_sent
