"""Tests for configuration management commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from moneymaker_console.commands.config import (
    _config_broker,
    _config_decrypt,
    _config_diff,
    _config_encrypt,
    _config_export,
    _config_get,
    _config_import,
    _config_reload,
    _config_risk,
    _config_set,
    _config_template,
    _config_validate,
    _config_view,
    _is_secret,
    _read_env_file,
    register,
)
from moneymaker_console.registry import CommandRegistry


class TestIsSecret:
    def test_api_key(self):
        assert _is_secret("API_KEY") is True

    def test_password(self):
        assert _is_secret("DB_PASSWORD") is True

    def test_token(self):
        assert _is_secret("AUTH_TOKEN") is True

    def test_secret(self):
        assert _is_secret("MY_SECRET") is True

    def test_dsn(self):
        assert _is_secret("SENTRY_DSN") is True

    def test_normal_key(self):
        assert _is_secret("DB_HOST") is False

    def test_port(self):
        assert _is_secret("DB_PORT") is False


class TestReadEnvFile:
    def test_file_not_exists(self, tmp_path):
        result = _read_env_file(tmp_path / "nonexistent")
        assert result == {}

    def test_basic_env(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\nOTHER=123\n")
        result = _read_env_file(env_file)
        assert result == {"KEY": "value", "OTHER": "123"}

    def test_comments_and_blank_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nKEY=value\n")
        result = _read_env_file(env_file)
        assert result == {"KEY": "value"}

    def test_quoted_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=\"hello world\"\nOTHER='test'\n")
        result = _read_env_file(env_file)
        assert result["KEY"] == "hello world"
        assert result["OTHER"] == "test"


class TestConfigView:
    def test_no_env_file(self):
        with patch("moneymaker_console.commands.config._ENV_FILE", Path("/nonexistent/.env")):
            result = _config_view()
            assert "warning" in result.lower()

    def test_with_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("DB_HOST=localhost\nAPI_KEY=secret123\n")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            result = _config_view()
            assert "localhost" in result
            assert "secret123" not in result  # Should be masked
            assert "****" in result

    def test_with_category_filter(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("MONEYMAKER_DB_HOST=localhost\nBRAIN_PORT=8082\n")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            result = _config_view("db")
            assert "localhost" in result
            assert "BRAIN_PORT" not in result

    def test_category_no_match(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("DB_HOST=localhost\n")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            # "tls" category prefix only matches TLS_ and MONEYMAKER_TLS
            result = _config_view("tls")
            assert "No configuration" in result


class TestConfigValidate:
    def test_no_example(self):
        with patch("moneymaker_console.commands.config._ENV_EXAMPLE", Path("/nonexistent")):
            result = _config_validate()
            assert "warning" in result.lower()

    def test_all_present(self, tmp_path):
        example = tmp_path / ".env.example"
        example.write_text("KEY=default\n")
        env = tmp_path / ".env"
        env.write_text("KEY=value\n")
        with (
            patch("moneymaker_console.commands.config._ENV_EXAMPLE", example),
            patch("moneymaker_console.commands.config._ENV_FILE", env),
        ):
            result = _config_validate()
            assert "[OK]" in result
            assert "All required" in result

    def test_missing(self, tmp_path):
        example = tmp_path / ".env.example"
        example.write_text("KEY=default\nMISSING_KEY=required\n")
        env = tmp_path / ".env"
        env.write_text("KEY=value\n")
        with (
            patch("moneymaker_console.commands.config._ENV_EXAMPLE", example),
            patch("moneymaker_console.commands.config._ENV_FILE", env),
        ):
            result = _config_validate()
            assert "[MISSING]" in result

    def test_empty_value(self, tmp_path):
        example = tmp_path / ".env.example"
        example.write_text("KEY=default\n")
        env = tmp_path / ".env"
        env.write_text("KEY=\n")
        with (
            patch("moneymaker_console.commands.config._ENV_EXAMPLE", example),
            patch("moneymaker_console.commands.config._ENV_FILE", env),
        ):
            result = _config_validate()
            assert "[EMPTY]" in result


class TestConfigSet:
    def test_no_args(self):
        assert "Usage" in _config_set()

    def test_one_arg(self):
        assert "Usage" in _config_set("KEY")

    def test_invalid_key(self):
        result = _config_set("bad key!", "value")
        assert "[error]" in result

    def test_newline_in_value(self):
        result = _config_set("KEY", "val\nue")
        assert "[error]" in result

    def test_numeric_key_non_numeric(self):
        result = _config_set("MONEYMAKER_DB_PORT", "abc")
        assert "[error]" in result

    def test_set_existing(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=old\n")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            result = _config_set("KEY", "new")
            assert "[success]" in result
            content = env_file.read_text()
            assert "KEY=new" in content

    def test_set_new_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER=value\n")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            result = _config_set("NEW_KEY", "val")
            assert "[success]" in result
            content = env_file.read_text()
            assert "NEW_KEY=val" in content

    def test_set_no_env_file(self):
        with patch("moneymaker_console.commands.config._ENV_FILE", Path("/nonexistent/.env")):
            result = _config_set("KEY", "value")
            assert "[error]" in result


class TestConfigGet:
    def test_no_args(self):
        assert "Usage" in _config_get()

    def test_from_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("DB_HOST=localhost\n")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            result = _config_get("DB_HOST")
            assert "localhost" in result

    def test_not_found(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            result = _config_get("MISSING")
            assert "not found" in result


class TestConfigDiff:
    def test_no_example(self):
        with patch("moneymaker_console.commands.config._ENV_EXAMPLE", Path("/nonexistent")):
            result = _config_diff()
            assert "warning" in result.lower()

    def test_same_keys(self, tmp_path):
        example = tmp_path / ".env.example"
        example.write_text("KEY=default\n")
        env = tmp_path / ".env"
        env.write_text("KEY=value\n")
        with (
            patch("moneymaker_console.commands.config._ENV_EXAMPLE", example),
            patch("moneymaker_console.commands.config._ENV_FILE", env),
        ):
            result = _config_diff()
            assert "same keys" in result

    def test_missing_and_extra(self, tmp_path):
        example = tmp_path / ".env.example"
        example.write_text("REQUIRED=val\n")
        env = tmp_path / ".env"
        env.write_text("EXTRA=val\n")
        with (
            patch("moneymaker_console.commands.config._ENV_EXAMPLE", example),
            patch("moneymaker_console.commands.config._ENV_FILE", env),
        ):
            result = _config_diff()
            assert "Missing" in result
            assert "Extra" in result


class TestConfigMisc:
    def test_broker_no_args(self):
        assert "Usage" in _config_broker()

    def test_risk_no_args(self):
        assert "Usage" in _config_risk()

    def test_risk_one_arg(self):
        assert "Usage" in _config_risk("KEY")

    def test_import_no_args(self):
        assert "Usage" in _config_import()

    def test_import_with_file(self):
        result = _config_import("config.json")
        assert "manual review" in result

    def test_encrypt(self):
        result = _config_encrypt()
        assert "Not yet implemented" in result

    def test_decrypt(self):
        result = _config_decrypt()
        assert "Not yet implemented" in result

    def test_template_no_example(self):
        with patch("moneymaker_console.commands.config._ENV_EXAMPLE", Path("/nonexistent")):
            result = _config_template()
            assert "[error]" in result

    def test_template_with_example(self, tmp_path):
        example = tmp_path / ".env.example"
        example.write_text("KEY=default\n")
        with patch("moneymaker_console.commands.config._ENV_EXAMPLE", example):
            result = _config_template()
            assert "development" in result

    def test_reload_with_dotenv(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\n")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            result = _config_reload()
            # Either success or warning about dotenv not installed
            assert "[success]" in result or "warning" in result.lower()

    def test_export_json(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("DB_HOST=localhost\nAPI_KEY=secret\n")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            result = _config_export("json")
            data = json.loads(result)
            assert data["DB_HOST"] == "localhost"
            assert "****" in data["API_KEY"]

    def test_export_yaml(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("DB_HOST=localhost\n")
        with patch("moneymaker_console.commands.config._ENV_FILE", env_file):
            result = _config_export("yaml")
            assert "DB_HOST: localhost" in result


class TestConfigRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "config" in reg.categories
        expected = [
            "view",
            "validate",
            "set",
            "get",
            "diff",
            "broker",
            "risk",
            "reload",
            "export",
            "import",
            "template",
            "encrypt",
            "decrypt",
        ]
        for cmd in expected:
            assert cmd in reg._commands["config"]
