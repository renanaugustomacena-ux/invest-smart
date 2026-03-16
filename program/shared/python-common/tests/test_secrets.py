"""Tests for moneymaker_common.secrets — Secrets management module."""

import pytest
from unittest.mock import patch
from pathlib import Path

from moneymaker_common.secrets import (
    SecretsValidationError,
    _get_min_length,
    _has_sufficient_complexity,
    _is_weak_password,
    generate_secure_password,
    load_secret,
    mask_secret,
    validate_required_secrets,
)


# ============================================================
# mask_secret tests
# ============================================================


class TestMaskSecret:
    """Test mask_secret function."""

    def test_mask_long_secret(self):
        result = mask_secret("mysecretpassword", visible_chars=4)
        assert result == "************word"

    def test_mask_short_secret(self):
        result = mask_secret("abc", visible_chars=4)
        assert result == "***"

    def test_mask_exact_length(self):
        result = mask_secret("abcd", visible_chars=4)
        assert result == "****"

    def test_mask_empty(self):
        result = mask_secret("", visible_chars=4)
        assert result == ""

    def test_mask_custom_visible(self):
        result = mask_secret("mysecretpassword", visible_chars=6)
        assert result == "**********ssword"

    def test_mask_default_visible_chars(self):
        result = mask_secret("0123456789")
        # default visible_chars=4
        assert result == "******6789"


# ============================================================
# _is_weak_password tests
# ============================================================


class TestIsWeakPassword:
    """Test _is_weak_password function."""

    def test_password_pattern(self):
        is_weak, pattern = _is_weak_password("mypassword123")
        assert is_weak is True
        assert pattern == "password"

    def test_admin_pattern(self):
        is_weak, pattern = _is_weak_password("SuperAdmin99!")
        assert is_weak is True
        assert pattern == "admin"

    def test_changeme_pattern(self):
        is_weak, pattern = _is_weak_password("CHANGE_ME_please")
        assert is_weak is True
        assert pattern == "CHANGE_ME"

    def test_qwerty_pattern(self):
        is_weak, pattern = _is_weak_password("qwerty12345!")
        assert is_weak is True
        assert pattern == "qwerty"

    def test_test_pattern(self):
        is_weak, pattern = _is_weak_password("testing123")
        assert is_weak is True
        assert pattern == "test"

    def test_strong_password(self):
        is_weak, pattern = _is_weak_password("Xr9$kL2@mNpQ7vZw")
        assert is_weak is False
        assert pattern is None

    def test_case_insensitive_check(self):
        is_weak, _ = _is_weak_password("PASSWORD123")
        assert is_weak is True

    def test_default_pattern(self):
        is_weak, pattern = _is_weak_password("default_value_here")
        assert is_weak is True
        assert pattern == "default"

    def test_example_pattern(self):
        is_weak, pattern = _is_weak_password("example_key_abc")
        assert is_weak is True
        assert pattern == "example"

    def test_secret_pattern(self):
        is_weak, pattern = _is_weak_password("my_secret_key")
        assert is_weak is True
        assert pattern == "secret"

    def test_123456_pattern(self):
        is_weak, pattern = _is_weak_password("abc123456def")
        assert is_weak is True
        assert pattern == "123456"


# ============================================================
# _has_sufficient_complexity tests
# ============================================================


class TestHasSufficientComplexity:
    """Test _has_sufficient_complexity function."""

    def test_all_four_categories(self):
        assert _has_sufficient_complexity("aA1!") is True

    def test_three_categories_no_special(self):
        assert _has_sufficient_complexity("aA1") is True

    def test_three_categories_no_digits(self):
        assert _has_sufficient_complexity("aA!") is True

    def test_two_categories_only(self):
        assert _has_sufficient_complexity("abc123") is False

    def test_one_category_only(self):
        assert _has_sufficient_complexity("abcdef") is False

    def test_upper_lower_special(self):
        assert _has_sufficient_complexity("Hello!World") is True

    def test_lower_digits_special(self):
        assert _has_sufficient_complexity("abc123!@#") is True

    def test_only_uppercase(self):
        assert _has_sufficient_complexity("ABCDEF") is False


# ============================================================
# _get_min_length tests
# ============================================================


class TestGetMinLength:
    """Test _get_min_length function."""

    def test_db_password(self):
        assert _get_min_length("db_password") == 16

    def test_redis_password(self):
        assert _get_min_length("redis_password") == 16

    def test_grafana_password(self):
        assert _get_min_length("grafana_password") == 12

    def test_mt5_password(self):
        assert _get_min_length("mt5_password") == 8

    def test_api_key(self):
        assert _get_min_length("api_key") == 20

    def test_unknown_returns_default(self):
        assert _get_min_length("something_else") == 16


# ============================================================
# load_secret tests
# ============================================================


class TestLoadSecret:
    """Test load_secret function."""

    def test_load_from_env_var(self, monkeypatch):
        # No docker secret, load from env
        monkeypatch.setenv("MY_SECRET", "Xr9$kL2@mNpQ7vZwABCD")
        with patch.object(Path, "exists", return_value=False):
            result = load_secret("db_password", "MY_SECRET", min_length=16)
        assert result == "Xr9$kL2@mNpQ7vZwABCD"

    def test_load_from_docker_secret(self, monkeypatch):
        monkeypatch.delenv("MY_SECRET", raising=False)
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value="Xr9$kL2@mNpQ7vZwABCD\n"),
        ):
            result = load_secret("db_password", "MY_SECRET", min_length=16)
        assert result == "Xr9$kL2@mNpQ7vZwABCD"

    def test_docker_secret_read_failure_falls_back_to_env(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "Xr9$kL2@mNpQ7vZwABCD")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", side_effect=OSError("Permission denied")),
        ):
            result = load_secret("db_password", "MY_SECRET", min_length=16)
        assert result == "Xr9$kL2@mNpQ7vZwABCD"

    def test_missing_required_raises(self, monkeypatch):
        monkeypatch.delenv("MY_SECRET", raising=False)
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(SecretsValidationError, match="mancante"):
                load_secret("db_password", "MY_SECRET", required=True)

    def test_missing_not_required_returns_empty(self, monkeypatch):
        monkeypatch.delenv("MY_SECRET", raising=False)
        with patch.object(Path, "exists", return_value=False):
            result = load_secret("db_password", "MY_SECRET", required=False)
        assert result == ""

    def test_too_short_raises(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "short")
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(SecretsValidationError, match="troppo corto"):
                load_secret("db_password", "MY_SECRET", min_length=16)

    def test_weak_password_raises(self, monkeypatch):
        # Long enough, but contains "password" which is weak
        monkeypatch.setenv("MY_SECRET", "mypassword123456ABCD!")
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(SecretsValidationError, match="pattern debole"):
                load_secret("db_password", "MY_SECRET", min_length=16)

    def test_insufficient_complexity_raises(self, monkeypatch):
        # Long enough, not weak, but only lowercase+digits (2 categories)
        monkeypatch.setenv("MY_SECRET", "abcdefghijklmnop1234")
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(SecretsValidationError, match="complessita"):
                load_secret("db_password", "MY_SECRET", min_length=16)

    def test_skip_complexity_check(self, monkeypatch):
        # Only lowercase+digits, but check_complexity=False
        monkeypatch.setenv("MY_SECRET", "abcdefghijklmnop1234")
        with patch.object(Path, "exists", return_value=False):
            result = load_secret("db_password", "MY_SECRET", min_length=16, check_complexity=False)
        assert result == "abcdefghijklmnop1234"

    def test_default_min_length_from_name(self, monkeypatch):
        """When min_length is not given, _get_min_length(name) is used."""
        # mt5_password has min_length=8
        monkeypatch.setenv("MY_SECRET", "Ab1!XyZw")
        with patch.object(Path, "exists", return_value=False):
            result = load_secret("mt5_password", "MY_SECRET")
        assert result == "Ab1!XyZw"


# ============================================================
# validate_required_secrets tests
# ============================================================


class TestValidateRequiredSecrets:
    """Test validate_required_secrets function."""

    def test_development_empty_secrets_ok(self, monkeypatch):
        """In development, secrets are not required."""
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        with patch.object(Path, "exists", return_value=False):
            result = validate_required_secrets(env="development")
        assert isinstance(result, dict)
        # Empty strings for non-required secrets
        assert result["db_password"] == ""
        assert result["redis_password"] == ""

    def test_production_missing_secrets_raises(self, monkeypatch):
        """In production, missing secrets should raise."""
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(SecretsValidationError, match="Validazione secrets fallita"):
                validate_required_secrets(env="production")

    def test_production_valid_secrets_pass(self, monkeypatch):
        """In production, valid secrets should pass."""
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "Xr9$kL2@mNpQ7vZwABCD")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "Yw4&jH8#qRsT6uVx!@AB")
        with patch.object(Path, "exists", return_value=False):
            result = validate_required_secrets(env="production")
        assert "db_password" in result
        assert "redis_password" in result

    def test_development_reduced_min_length(self, monkeypatch):
        """Development uses min_length=8 instead of 16."""
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "Ab1!XyZw")  # 8 chars
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "Cd3@WvUt")  # 8 chars
        with patch.object(Path, "exists", return_value=False):
            result = validate_required_secrets(env="development")
        assert result["db_password"] == "Ab1!XyZw"
        assert result["redis_password"] == "Cd3@WvUt"


# ============================================================
# generate_secure_password tests
# ============================================================


class TestGenerateSecurePassword:
    """Test generate_secure_password function."""

    def test_default_length(self):
        pw = generate_secure_password()
        assert len(pw) == 32

    def test_custom_length(self):
        pw = generate_secure_password(length=64)
        assert len(pw) == 64

    def test_minimum_length_enforced(self):
        pw = generate_secure_password(length=5)
        assert len(pw) == 16  # minimum is 16

    def test_always_complex(self):
        for _ in range(10):
            pw = generate_secure_password()
            assert _has_sufficient_complexity(pw)

    def test_generated_is_string(self):
        assert isinstance(generate_secure_password(), str)


# ============================================================
# SecretsValidationError tests
# ============================================================


class TestSecretsValidationError:
    """Test the custom exception class."""

    def test_is_exception(self):
        assert issubclass(SecretsValidationError, Exception)

    def test_message(self):
        err = SecretsValidationError("test message")
        assert str(err) == "test message"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(SecretsValidationError):
            raise SecretsValidationError("boom")
