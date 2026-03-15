"""Tests for ExternalDataSettings configuration."""

from __future__ import annotations

from external_data.config import ExternalDataSettings


class TestExternalDataSettings:
    def test_defaults(self, monkeypatch):
        # Clear env vars that might interfere
        for key in [
            "FRED_API_KEY",
            "POLYGON_API_KEY",
            "REDIS_URL",
            "DB_HOST",
            "DB_PORT",
            "DB_USER",
            "DB_PASSWORD",
            "DB_NAME",
        ]:
            monkeypatch.delenv(key, raising=False)

        settings = ExternalDataSettings()

        assert settings.external_data_service_name == "external-data"
        assert settings.external_data_metrics_port == 9095
        assert settings.fred_api_key == ""
        assert settings.fred_base_url == "https://api.stlouisfed.org/fred"
        assert settings.fred_rate_limit_per_min == 120
        assert settings.polygon_api_key == ""
        assert settings.redis_cache_ttl_seconds == 300
        assert settings.vix_fetch_interval_minutes == 1
        assert settings.yield_fetch_interval_minutes == 60
        assert settings.cot_fetch_interval_hours == 24
        assert settings.retry_attempts == 3
        assert settings.retry_delay_seconds == 2.0
        assert settings.request_timeout_seconds == 30

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("FRED_API_KEY", "my-fred-key")
        monkeypatch.setenv("VIX_FETCH_INTERVAL_MINUTES", "5")
        monkeypatch.setenv("RETRY_ATTEMPTS", "5")

        settings = ExternalDataSettings()

        assert settings.fred_api_key == "my-fred-key"
        assert settings.vix_fetch_interval_minutes == 5
        assert settings.retry_attempts == 5

    def test_db_settings(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "db.prod.com")
        monkeypatch.setenv("DB_PORT", "5433")
        monkeypatch.setenv("DB_USER", "admin")
        monkeypatch.setenv("DB_PASSWORD", "secret")
        monkeypatch.setenv("DB_NAME", "trading")

        settings = ExternalDataSettings()

        assert settings.db_host == "db.prod.com"
        assert settings.db_port == 5433
        assert settings.db_user == "admin"
        assert settings.db_password == "secret"
        assert settings.db_name == "trading"
