"""Tests for alerting and notification commands."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from moneymaker_console.commands.alert import (
    _alert_add_rule,
    _alert_channels,
    _alert_history,
    _alert_mute,
    _alert_remove_rule,
    _alert_rules,
    _alert_status,
    _alert_telegram,
    _alert_test,
    _alert_unmute,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestAlertStatus:
    @patch("moneymaker_console.clients.ClientFactory")
    def test_status_configured(self, mock_cf):
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_cf.get_redis.return_value = mock_redis
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "tok",
                "TELEGRAM_CHAT_ID": "123",
                "SENTRY_DSN": "https://abc@sentry.io/1",
            },
        ):
            result = _alert_status()
            assert "CONFIGURED" in result
            assert "CONNECTED" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_status_unconfigured(self, mock_cf):
        mock_redis = MagicMock()
        mock_redis.ping.return_value = False
        mock_cf.get_redis.return_value = mock_redis
        env = {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": "", "SENTRY_DSN": ""}
        with patch.dict(os.environ, env, clear=False):
            if "TELEGRAM_BOT_TOKEN" in os.environ:
                del os.environ["TELEGRAM_BOT_TOKEN"]
            if "SENTRY_DSN" in os.environ:
                del os.environ["SENTRY_DSN"]
            result = _alert_status()
            assert "NOT CONFIGURED" in result or "NOT CONNECTED" in result


class TestAlertChannels:
    def test_channels_list(self):
        result = _alert_channels()
        assert "Channel" in result or "channel" in result


class TestAlertTest:
    @patch("moneymaker_console.clients.ClientFactory")
    def test_redis_channel(self, mock_cf):
        mock_redis = MagicMock()
        mock_cf.get_redis.return_value = mock_redis
        result = _alert_test("redis")
        assert "SENT" in result or "redis" in result.lower()


class TestAlertRules:
    def test_rules_list(self):
        result = _alert_rules()
        assert "Alert Rules" in result
        assert "Kill switch" in result


class TestAlertAddRule:
    def test_no_args(self):
        assert "Usage" in _alert_add_rule()

    def test_one_arg(self):
        assert "Usage" in _alert_add_rule("CONDITION")

    def test_valid(self):
        result = _alert_add_rule("max_dd > 5", "CRITICAL")
        assert "info" in result.lower()


class TestAlertRemoveRule:
    def test_no_args(self):
        assert "Usage" in _alert_remove_rule()

    def test_valid(self):
        result = _alert_remove_rule("rule-1")
        assert "rule-1" in result


class TestAlertHistory:
    @patch("moneymaker_console.clients.ClientFactory")
    def test_found(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = [
            ("2024-01-15", "CRITICAL", "Kill switch activated", "telegram"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _alert_history()
        assert "History" in result or "CRITICAL" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_empty(self, mock_cf):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _alert_history()
        assert "No alerts" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_error(self, mock_cf):
        mock_cf.get_postgres.side_effect = Exception("db error")
        result = _alert_history()
        assert "info" in result.lower() or "error" in result.lower()


class TestAlertMute:
    @patch("moneymaker_console.clients.ClientFactory")
    def test_mute_success(self, mock_cf):
        mock_redis = MagicMock()
        mock_cf.get_redis.return_value = mock_redis
        result = _alert_mute()
        assert "[success]" in result
        assert "60" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_mute_custom(self, mock_cf):
        mock_redis = MagicMock()
        mock_cf.get_redis.return_value = mock_redis
        result = _alert_mute("30")
        assert "30" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_mute_error(self, mock_cf):
        mock_cf.get_redis.side_effect = Exception("redis err")
        result = _alert_mute()
        assert "[error]" in result


class TestAlertUnmute:
    @patch("moneymaker_console.clients.ClientFactory")
    def test_unmute_success(self, mock_cf):
        mock_redis = MagicMock()
        mock_cf.get_redis.return_value = mock_redis
        result = _alert_unmute()
        assert "[success]" in result

    @patch("moneymaker_console.clients.ClientFactory")
    def test_unmute_error(self, mock_cf):
        mock_cf.get_redis.side_effect = Exception("redis err")
        result = _alert_unmute()
        assert "[error]" in result


class TestAlertTelegram:
    def test_no_args_no_token(self):
        result = _alert_telegram()
        assert "Telegram" in result or "telegram" in result or "NOT CONFIGURED" in result

    def test_usage(self):
        result = _alert_telegram("--bot-token", "tok123")
        assert "Usage" in result


class TestAlertRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "alert" in reg.categories
        expected = [
            "status",
            "channels",
            "test",
            "rules",
            "add-rule",
            "remove-rule",
            "history",
            "mute",
            "unmute",
        ]
        for cmd in expected:
            assert cmd in reg._commands["alert"]
