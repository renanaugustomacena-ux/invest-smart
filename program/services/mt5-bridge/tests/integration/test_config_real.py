"""Integration tests for MT5BridgeSettings with real environment variables.

Uses monkeypatch.setenv (NOT unittest.mock.patch.dict) to verify that
MT5BridgeSettings correctly reads configuration from the environment.

NO MOCKS: monkeypatch.setenv sets real environment variables in the
process; pydantic-settings reads them directly via os.environ.
"""

from __future__ import annotations

import pytest

from mt5_bridge.config import MT5BridgeSettings


class TestMT5BridgeSettingsDefaults:
    """Verify default values when no environment variables are set."""

    def test_default_grpc_port(self, monkeypatch):
        """Default gRPC port should be 50055."""
        monkeypatch.delenv("MONEYMAKER_MT5_BRIDGE_GRPC_PORT", raising=False)
        settings = MT5BridgeSettings()
        assert settings.moneymaker_mt5_bridge_grpc_port == 50055

    def test_default_metrics_port(self, monkeypatch):
        """Default metrics port should be 9094."""
        monkeypatch.delenv("MONEYMAKER_MT5_BRIDGE_METRICS_PORT", raising=False)
        settings = MT5BridgeSettings()
        assert settings.moneymaker_mt5_bridge_metrics_port == 9094

    def test_default_mt5_account_empty(self, monkeypatch):
        """Default MT5 account should be empty string."""
        monkeypatch.delenv("MT5_ACCOUNT", raising=False)
        settings = MT5BridgeSettings()
        assert settings.mt5_account == ""

    def test_default_mt5_server_empty(self, monkeypatch):
        """Default MT5 server should be empty string."""
        monkeypatch.delenv("MT5_SERVER", raising=False)
        settings = MT5BridgeSettings()
        assert settings.mt5_server == ""

    def test_default_mt5_timeout(self, monkeypatch):
        """Default MT5 timeout should be 10000ms."""
        monkeypatch.delenv("MT5_TIMEOUT_MS", raising=False)
        settings = MT5BridgeSettings()
        assert settings.mt5_timeout_ms == 10000

    def test_default_max_position_count(self, monkeypatch):
        """Default max position count should be 5."""
        monkeypatch.delenv("MAX_POSITION_COUNT", raising=False)
        settings = MT5BridgeSettings()
        assert settings.max_position_count == 5

    def test_default_max_lot_size(self, monkeypatch):
        """Default max lot size should be '1.0'."""
        monkeypatch.delenv("MAX_LOT_SIZE", raising=False)
        settings = MT5BridgeSettings()
        assert settings.max_lot_size == "1.0"

    def test_default_max_daily_loss_pct(self, monkeypatch):
        """Default max daily loss should be '2.0'%."""
        monkeypatch.delenv("MAX_DAILY_LOSS_PCT", raising=False)
        settings = MT5BridgeSettings()
        assert settings.max_daily_loss_pct == "2.0"

    def test_default_max_drawdown_pct(self, monkeypatch):
        """Default max drawdown should be '10.0'%."""
        monkeypatch.delenv("MAX_DRAWDOWN_PCT", raising=False)
        settings = MT5BridgeSettings()
        assert settings.max_drawdown_pct == "10.0"

    def test_default_signal_dedup_window(self, monkeypatch):
        """Default signal dedup window should be 60 seconds."""
        monkeypatch.delenv("SIGNAL_DEDUP_WINDOW_SEC", raising=False)
        settings = MT5BridgeSettings()
        assert settings.signal_dedup_window_sec == 60

    def test_default_signal_max_age(self, monkeypatch):
        """Default signal max age should be 30 seconds."""
        monkeypatch.delenv("SIGNAL_MAX_AGE_SEC", raising=False)
        settings = MT5BridgeSettings()
        assert settings.signal_max_age_sec == 30

    def test_default_max_spread_points(self, monkeypatch):
        """Default max spread points should be 30."""
        monkeypatch.delenv("MAX_SPREAD_POINTS", raising=False)
        settings = MT5BridgeSettings()
        assert settings.max_spread_points == 30

    def test_default_trailing_stop_enabled(self, monkeypatch):
        """Default trailing stop should be enabled."""
        monkeypatch.delenv("TRAILING_STOP_ENABLED", raising=False)
        settings = MT5BridgeSettings()
        assert settings.trailing_stop_enabled is True

    def test_default_rate_limit_enabled(self, monkeypatch):
        """Default rate limit should be enabled."""
        monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
        settings = MT5BridgeSettings()
        assert settings.rate_limit_enabled is True

    def test_default_rate_limit_requests_per_minute(self, monkeypatch):
        """Default rate limit should be 10 requests/minute."""
        monkeypatch.delenv("RATE_LIMIT_REQUESTS_PER_MINUTE", raising=False)
        settings = MT5BridgeSettings()
        assert settings.rate_limit_requests_per_minute == 10


class TestMT5BridgeSettingsFromEnv:
    """Verify that settings are correctly read from environment variables."""

    def test_grpc_port_from_env(self, monkeypatch):
        """gRPC port should be overridden by env var."""
        monkeypatch.setenv("MONEYMAKER_MT5_BRIDGE_GRPC_PORT", "50099")
        settings = MT5BridgeSettings()
        assert settings.moneymaker_mt5_bridge_grpc_port == 50099

    def test_metrics_port_from_env(self, monkeypatch):
        """Metrics port should be overridden by env var."""
        monkeypatch.setenv("MONEYMAKER_MT5_BRIDGE_METRICS_PORT", "9199")
        settings = MT5BridgeSettings()
        assert settings.moneymaker_mt5_bridge_metrics_port == 9199

    def test_mt5_account_from_env(self, monkeypatch):
        """MT5 account should be read from env."""
        monkeypatch.setenv("MT5_ACCOUNT", "12345678")
        settings = MT5BridgeSettings()
        assert settings.mt5_account == "12345678"

    def test_mt5_password_from_env(self, monkeypatch):
        """MT5 password should be read from env."""
        monkeypatch.setenv("MT5_PASSWORD", "s3cret!")
        settings = MT5BridgeSettings()
        assert settings.mt5_password == "s3cret!"

    def test_mt5_server_from_env(self, monkeypatch):
        """MT5 server should be read from env."""
        monkeypatch.setenv("MT5_SERVER", "MetaQuotes-Demo")
        settings = MT5BridgeSettings()
        assert settings.mt5_server == "MetaQuotes-Demo"

    def test_mt5_timeout_from_env(self, monkeypatch):
        """MT5 timeout should be read from env."""
        monkeypatch.setenv("MT5_TIMEOUT_MS", "30000")
        settings = MT5BridgeSettings()
        assert settings.mt5_timeout_ms == 30000

    def test_max_position_count_from_env(self, monkeypatch):
        """Max position count should be overridden by env."""
        monkeypatch.setenv("MAX_POSITION_COUNT", "10")
        settings = MT5BridgeSettings()
        assert settings.max_position_count == 10

    def test_max_lot_size_from_env(self, monkeypatch):
        """Max lot size should be overridden by env."""
        monkeypatch.setenv("MAX_LOT_SIZE", "2.5")
        settings = MT5BridgeSettings()
        assert settings.max_lot_size == "2.5"

    def test_max_daily_loss_pct_from_env(self, monkeypatch):
        """Max daily loss % should be overridden by env."""
        monkeypatch.setenv("MAX_DAILY_LOSS_PCT", "5.0")
        settings = MT5BridgeSettings()
        assert settings.max_daily_loss_pct == "5.0"

    def test_max_drawdown_pct_from_env(self, monkeypatch):
        """Max drawdown % should be overridden by env."""
        monkeypatch.setenv("MAX_DRAWDOWN_PCT", "15.0")
        settings = MT5BridgeSettings()
        assert settings.max_drawdown_pct == "15.0"

    def test_signal_dedup_window_from_env(self, monkeypatch):
        """Signal dedup window should be overridden by env."""
        monkeypatch.setenv("SIGNAL_DEDUP_WINDOW_SEC", "120")
        settings = MT5BridgeSettings()
        assert settings.signal_dedup_window_sec == 120

    def test_max_spread_points_from_env(self, monkeypatch):
        """Max spread points should be overridden by env."""
        monkeypatch.setenv("MAX_SPREAD_POINTS", "50")
        settings = MT5BridgeSettings()
        assert settings.max_spread_points == 50

    def test_trailing_stop_disabled_from_env(self, monkeypatch):
        """Trailing stop can be disabled via env."""
        monkeypatch.setenv("TRAILING_STOP_ENABLED", "false")
        settings = MT5BridgeSettings()
        assert settings.trailing_stop_enabled is False

    def test_trailing_stop_pips_from_env(self, monkeypatch):
        """Trailing stop pips should be overridden by env."""
        monkeypatch.setenv("TRAILING_STOP_PIPS", "75.0")
        settings = MT5BridgeSettings()
        assert settings.trailing_stop_pips == "75.0"

    def test_trailing_activation_pips_from_env(self, monkeypatch):
        """Trailing activation pips should be overridden by env."""
        monkeypatch.setenv("TRAILING_ACTIVATION_PIPS", "40.0")
        settings = MT5BridgeSettings()
        assert settings.trailing_activation_pips == "40.0"

    def test_rate_limit_disabled_from_env(self, monkeypatch):
        """Rate limit can be disabled via env."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        settings = MT5BridgeSettings()
        assert settings.rate_limit_enabled is False

    def test_rate_limit_requests_per_minute_from_env(self, monkeypatch):
        """Rate limit requests/minute should be overridden by env."""
        monkeypatch.setenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "30")
        settings = MT5BridgeSettings()
        assert settings.rate_limit_requests_per_minute == 30

    def test_rate_limit_burst_size_from_env(self, monkeypatch):
        """Rate limit burst size should be overridden by env."""
        monkeypatch.setenv("RATE_LIMIT_BURST_SIZE", "15")
        settings = MT5BridgeSettings()
        assert settings.rate_limit_burst_size == 15


class TestMT5BridgeSettingsInherited:
    """Verify inherited MoneyMakerBaseSettings fields work correctly."""

    def test_database_url_property(self, monkeypatch):
        """database_url property should compose a valid PostgreSQL URL."""
        monkeypatch.setenv("MONEYMAKER_DB_HOST", "db.example.com")
        monkeypatch.setenv("MONEYMAKER_DB_PORT", "5433")
        monkeypatch.setenv("MONEYMAKER_DB_NAME", "testdb")
        monkeypatch.setenv("MONEYMAKER_DB_USER", "testuser")
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "testpass")
        monkeypatch.setenv("MONEYMAKER_ENV", "development")

        settings = MT5BridgeSettings()
        url = settings.database_url
        assert "db.example.com" in url
        assert "5433" in url
        assert "testdb" in url
        assert "testuser" in url

    def test_redis_url_property(self, monkeypatch):
        """redis_url property should compose a valid Redis URL."""
        monkeypatch.setenv("MONEYMAKER_REDIS_HOST", "redis.example.com")
        monkeypatch.setenv("MONEYMAKER_REDIS_PORT", "6380")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "")
        monkeypatch.setenv("MONEYMAKER_ENV", "development")

        settings = MT5BridgeSettings()
        url = settings.redis_url
        assert "redis.example.com" in url
        assert "6380" in url

    def test_env_defaults_to_development(self, monkeypatch):
        """Default environment should be 'development'."""
        monkeypatch.delenv("MONEYMAKER_ENV", raising=False)
        settings = MT5BridgeSettings()
        assert settings.moneymaker_env == "development"
