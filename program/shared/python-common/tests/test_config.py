"""Tests for moneymaker_common.config — MoneyMakerBaseSettings."""

import pytest
from urllib.parse import quote_plus


class TestMoneyMakerBaseSettingsDefaults:
    """Test default values when no env vars are set."""

    def test_default_env_is_development(self, monkeypatch):
        monkeypatch.delenv("MONEYMAKER_ENV", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.moneymaker_env == "development"

    def test_default_db_settings(self, monkeypatch):
        monkeypatch.delenv("MONEYMAKER_DB_HOST", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PORT", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_NAME", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_USER", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_ENV", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.moneymaker_db_host == "localhost"
        assert settings.moneymaker_db_port == 5432
        assert settings.moneymaker_db_name == "moneymaker"
        assert settings.moneymaker_db_user == "moneymaker"
        assert settings.moneymaker_db_password == ""

    def test_default_redis_settings(self, monkeypatch):
        monkeypatch.delenv("MONEYMAKER_REDIS_HOST", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PORT", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_ENV", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.moneymaker_redis_host == "localhost"
        assert settings.moneymaker_redis_port == 6379
        assert settings.moneymaker_redis_password == ""

    def test_default_zmq_addr(self, monkeypatch):
        monkeypatch.delenv("MONEYMAKER_ZMQ_PUB_ADDR", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_ENV", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.moneymaker_zmq_pub_addr == "tcp://localhost:5555"

    def test_default_metrics_port(self, monkeypatch):
        monkeypatch.delenv("MONEYMAKER_METRICS_PORT", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_ENV", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.moneymaker_metrics_port == 9090

    def test_default_tls_disabled(self, monkeypatch):
        monkeypatch.delenv("MONEYMAKER_TLS_ENABLED", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_CA_CERT", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_ENV", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.moneymaker_tls_enabled is False
        assert settings.moneymaker_tls_ca_cert == ""


class TestMoneyMakerBaseSettingsEnvOverrides:
    """Test reading values from environment variables."""

    def test_override_all_from_env(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "staging")
        monkeypatch.setenv("MONEYMAKER_DB_HOST", "db.example.com")
        monkeypatch.setenv("MONEYMAKER_DB_PORT", "5433")
        monkeypatch.setenv("MONEYMAKER_DB_NAME", "mydb")
        monkeypatch.setenv("MONEYMAKER_DB_USER", "myuser")
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "secretpass")
        monkeypatch.setenv("MONEYMAKER_REDIS_HOST", "redis.example.com")
        monkeypatch.setenv("MONEYMAKER_REDIS_PORT", "6380")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "redispass")
        monkeypatch.setenv("MONEYMAKER_ZMQ_PUB_ADDR", "tcp://zmq:1234")
        monkeypatch.setenv("MONEYMAKER_METRICS_PORT", "8080")
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "True")
        monkeypatch.setenv("MONEYMAKER_TLS_CA_CERT", "/my/ca.crt")
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.moneymaker_env == "staging"
        assert settings.moneymaker_db_host == "db.example.com"
        assert settings.moneymaker_db_port == 5433
        assert settings.moneymaker_db_name == "mydb"
        assert settings.moneymaker_db_user == "myuser"
        assert settings.moneymaker_db_password == "secretpass"
        assert settings.moneymaker_redis_host == "redis.example.com"
        assert settings.moneymaker_redis_port == 6380
        assert settings.moneymaker_redis_password == "redispass"
        assert settings.moneymaker_zmq_pub_addr == "tcp://zmq:1234"
        assert settings.moneymaker_metrics_port == 8080
        assert settings.moneymaker_tls_enabled is True
        assert settings.moneymaker_tls_ca_cert == "/my/ca.crt"


class TestProductionValidation:
    """Test the model_validator that enforces passwords in production."""

    def test_production_requires_db_password(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "production")
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "something")
        from moneymaker_common.config import MoneyMakerBaseSettings

        with pytest.raises(ValueError, match="MONEYMAKER_DB_PASSWORD"):
            MoneyMakerBaseSettings()

    def test_production_requires_redis_password(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "production")
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "dbpass")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "")
        from moneymaker_common.config import MoneyMakerBaseSettings

        with pytest.raises(ValueError, match="MONEYMAKER_REDIS_PASSWORD"):
            MoneyMakerBaseSettings()

    def test_production_passes_with_all_passwords(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "production")
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "dbpass")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "redispass")
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.is_production is True

    def test_development_warns_on_empty_db_password(self, monkeypatch, capfd):
        """In development, empty DB password logs a warning but does not raise."""
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        # Should NOT raise
        settings = MoneyMakerBaseSettings()
        assert settings.moneymaker_env == "development"

    def test_staging_warns_on_empty_db_password(self, monkeypatch):
        """In staging, empty DB password logs a warning but does not raise."""
        monkeypatch.setenv("MONEYMAKER_ENV", "staging")
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.moneymaker_env == "staging"


class TestSSLParams:
    """Test _ssl_params method."""

    def test_tls_enabled_without_ca_cert(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "True")
        monkeypatch.delenv("MONEYMAKER_TLS_CA_CERT", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings._ssl_params() == "?sslmode=verify-full"

    def test_tls_enabled_with_ca_cert(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "True")
        monkeypatch.setenv("MONEYMAKER_TLS_CA_CERT", "/path/to/ca.crt")
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        result = settings._ssl_params()
        assert result == "?sslmode=verify-full&sslrootcert=/path/to/ca.crt"

    def test_production_without_tls_returns_require(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "production")
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "dbpass")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "redispass")
        monkeypatch.delenv("MONEYMAKER_TLS_ENABLED", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings._ssl_params() == "?sslmode=require"

    def test_development_without_tls_returns_prefer(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.delenv("MONEYMAKER_TLS_ENABLED", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings._ssl_params() == "?sslmode=prefer"


class TestDatabaseURL:
    """Test database_url and database_url_async properties."""

    def test_database_url_basic(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.setenv("MONEYMAKER_DB_HOST", "myhost")
        monkeypatch.setenv("MONEYMAKER_DB_PORT", "5432")
        monkeypatch.setenv("MONEYMAKER_DB_NAME", "mydb")
        monkeypatch.setenv("MONEYMAKER_DB_USER", "user1")
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "p@ss")
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_ENABLED", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        url = settings.database_url
        expected_pw = quote_plus("p@ss")
        assert url == f"postgresql://user1:{expected_pw}@myhost:5432/mydb?sslmode=prefer"

    def test_database_url_async(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.setenv("MONEYMAKER_DB_HOST", "myhost")
        monkeypatch.setenv("MONEYMAKER_DB_PORT", "5432")
        monkeypatch.setenv("MONEYMAKER_DB_NAME", "mydb")
        monkeypatch.setenv("MONEYMAKER_DB_USER", "user1")
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "p@ss")
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_ENABLED", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        url = settings.database_url_async
        expected_pw = quote_plus("p@ss")
        assert url == f"postgresql+asyncpg://user1:{expected_pw}@myhost:5432/mydb?sslmode=prefer"

    def test_database_url_special_characters_in_password(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "p@ss w/ord!#$")
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_ENABLED", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        url = settings.database_url
        # The special chars should be URL-encoded
        assert quote_plus("p@ss w/ord!#$") in url


class TestRedisURL:
    """Test redis_url property."""

    def test_redis_url_no_password(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_ENABLED", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.redis_url == "redis://localhost:6379/0"

    def test_redis_url_with_password(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "myredispass")
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_TLS_ENABLED", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.redis_url == "redis://:myredispass@localhost:6379/0"

    def test_redis_url_tls_enabled(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "True")
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.redis_url.startswith("rediss://")

    def test_redis_url_tls_with_password(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "True")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "secure")
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.redis_url == "rediss://:secure@localhost:6379/0"


class TestBooleanProperties:
    """Test is_production and is_tls_enabled properties."""

    def test_is_production_true(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "production")
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "dbpass")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "redispass")
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.is_production is True

    def test_is_production_false(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.is_production is False

    def test_is_tls_enabled_false(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.delenv("MONEYMAKER_TLS_ENABLED", raising=False)
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.is_tls_enabled is False

    def test_is_tls_enabled_true(self, monkeypatch):
        monkeypatch.setenv("MONEYMAKER_ENV", "development")
        monkeypatch.setenv("MONEYMAKER_TLS_ENABLED", "True")
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        from moneymaker_common.config import MoneyMakerBaseSettings

        settings = MoneyMakerBaseSettings()
        assert settings.is_tls_enabled is True
