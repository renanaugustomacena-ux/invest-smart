"""Tests for MT5BridgeSettings defaults and overrides."""

from __future__ import annotations

import os
from unittest.mock import patch


from mt5_bridge.config import MT5BridgeSettings


class TestMT5BridgeSettingsDefaults:
    def test_default_grpc_port(self):
        settings = MT5BridgeSettings()
        assert settings.moneymaker_mt5_bridge_grpc_port == 50055

    def test_default_metrics_port(self):
        settings = MT5BridgeSettings()
        assert settings.moneymaker_mt5_bridge_metrics_port == 9094

    def test_default_mt5_account_empty(self):
        settings = MT5BridgeSettings()
        assert settings.mt5_account == ""

    def test_default_mt5_password_empty(self):
        settings = MT5BridgeSettings()
        assert settings.mt5_password == ""

    def test_default_mt5_server_empty(self):
        settings = MT5BridgeSettings()
        assert settings.mt5_server == ""

    def test_default_timeout_ms(self):
        settings = MT5BridgeSettings()
        assert settings.mt5_timeout_ms == 10000

    def test_default_max_position_count(self):
        settings = MT5BridgeSettings()
        assert settings.max_position_count == 5

    def test_default_max_lot_size(self):
        settings = MT5BridgeSettings()
        assert settings.max_lot_size == "1.0"

    def test_default_max_daily_loss_pct(self):
        settings = MT5BridgeSettings()
        assert settings.max_daily_loss_pct == "2.0"

    def test_default_max_drawdown_pct(self):
        settings = MT5BridgeSettings()
        assert settings.max_drawdown_pct == "10.0"

    def test_default_signal_dedup_window(self):
        settings = MT5BridgeSettings()
        assert settings.signal_dedup_window_sec == 60

    def test_default_signal_max_age(self):
        settings = MT5BridgeSettings()
        assert settings.signal_max_age_sec == 30

    def test_default_max_spread_points(self):
        settings = MT5BridgeSettings()
        assert settings.max_spread_points == 30

    def test_default_trailing_stop_enabled(self):
        settings = MT5BridgeSettings()
        assert settings.trailing_stop_enabled is True

    def test_default_trailing_stop_pips(self):
        settings = MT5BridgeSettings()
        assert settings.trailing_stop_pips == "50.0"

    def test_default_trailing_activation_pips(self):
        settings = MT5BridgeSettings()
        assert settings.trailing_activation_pips == "30.0"

    def test_default_rate_limit_enabled(self):
        settings = MT5BridgeSettings()
        assert settings.rate_limit_enabled is True

    def test_default_rate_limit_requests_per_minute(self):
        settings = MT5BridgeSettings()
        assert settings.rate_limit_requests_per_minute == 10

    def test_default_rate_limit_burst_size(self):
        settings = MT5BridgeSettings()
        assert settings.rate_limit_burst_size == 5


class TestMT5BridgeSettingsOverrides:
    @patch.dict(os.environ, {"MT5_ACCOUNT": "12345"})
    def test_env_override_mt5_account(self):
        settings = MT5BridgeSettings()
        assert settings.mt5_account == "12345"

    @patch.dict(os.environ, {"MAX_POSITION_COUNT": "3"})
    def test_env_override_max_positions(self):
        settings = MT5BridgeSettings()
        assert settings.max_position_count == 3

    @patch.dict(os.environ, {"TRAILING_STOP_ENABLED": "false"})
    def test_env_override_trailing_stop_disabled(self):
        settings = MT5BridgeSettings()
        assert settings.trailing_stop_enabled is False

    @patch.dict(os.environ, {"MAX_SPREAD_POINTS": "50"})
    def test_env_override_max_spread(self):
        settings = MT5BridgeSettings()
        assert settings.max_spread_points == 50


class TestMT5BridgeSettingsType:
    def test_settings_is_instance_of_base(self):
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MT5BridgeSettings()
        assert isinstance(settings, MoneyMakerBaseSettings)
