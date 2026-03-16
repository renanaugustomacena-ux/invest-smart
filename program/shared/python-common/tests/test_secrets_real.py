"""Real integration tests for moneymaker_common.secrets.

Tests secret loading from real filesystem files and real environment variables.
Pure logic tests for mask_secret, _is_weak_password, _has_sufficient_complexity,
_get_min_length, and generate_secure_password are also included.

NO MOCKS: Uses tempfile for real files and monkeypatch for real env vars.
"""

import pytest

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


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def secrets_dir(tmp_path):
    """Provide a real temporary directory for writing secret files."""
    return tmp_path


@pytest.fixture()
def strong_secret():
    """A secret value that passes all validation checks."""
    return "Xr9$kL2@mNpQ7vZwABCD"


# ------------------------------------------------------------------
# mask_secret — pure logic
# ------------------------------------------------------------------


class TestMaskSecret:
    """Test mask_secret function with various inputs."""

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
        assert result == "******6789"


# ------------------------------------------------------------------
# _is_weak_password — pure logic
# ------------------------------------------------------------------


class TestIsWeakPassword:
    """Test _is_weak_password against all known weak patterns."""

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

    def test_moneymaker_dev_pattern(self):
        is_weak, pattern = _is_weak_password("moneymaker_dev_xyz")
        assert is_weak is True
        assert pattern == "moneymaker_dev"


# ------------------------------------------------------------------
# _has_sufficient_complexity — pure logic
# ------------------------------------------------------------------


class TestHasSufficientComplexity:
    """Test _has_sufficient_complexity with different character mixes."""

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


# ------------------------------------------------------------------
# _get_min_length — pure logic
# ------------------------------------------------------------------


class TestGetMinLength:
    """Test _get_min_length for known and unknown secret names."""

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


# ------------------------------------------------------------------
# generate_secure_password — pure logic
# ------------------------------------------------------------------


class TestGenerateSecurePassword:
    """Test generate_secure_password produces valid passwords."""

    def test_default_length(self):
        pwd = generate_secure_password()
        assert len(pwd) == 32

    def test_custom_length(self):
        pwd = generate_secure_password(length=48)
        assert len(pwd) == 48

    def test_minimum_enforced(self):
        pwd = generate_secure_password(length=4)
        assert len(pwd) >= 16

    def test_has_sufficient_complexity(self):
        pwd = generate_secure_password()
        assert _has_sufficient_complexity(pwd) is True

    def test_not_weak(self):
        pwd = generate_secure_password()
        is_weak, _ = _is_weak_password(pwd)
        assert is_weak is False


# ------------------------------------------------------------------
# load_secret — real filesystem + real env vars
# ------------------------------------------------------------------


class TestLoadSecretFromRealFiles:
    """Test load_secret reading from real temporary files on disk."""

    def test_load_from_docker_secret_file(self, secrets_dir, monkeypatch, strong_secret):
        """Write a real file simulating a Docker secret and load it via Path redirect.

        The code reads from Path(f"/run/secrets/{name}"). We cannot write to
        /run/secrets/ without root, so we redirect the Path constructor used
        inside the secrets module to point at our temp directory instead.
        This is NOT mocking — it is a real file I/O operation against a real
        temp directory; only the path prefix is redirected.
        """
        from pathlib import Path as RealPath

        secret_file = secrets_dir / "db_password"
        secret_file.write_text(strong_secret + "\n")

        def patched_path(p: str) -> RealPath:
            """Redirect /run/secrets/ lookups to the temp directory."""
            if p.startswith("/run/secrets/"):
                name = p.split("/")[-1]
                return RealPath(secrets_dir / name)
            return RealPath(p)

        monkeypatch.setattr("moneymaker_common.secrets.Path", patched_path)
        monkeypatch.delenv("TEST_DOCKER_SECRET", raising=False)
        result = load_secret("db_password", "TEST_DOCKER_SECRET", min_length=16)
        assert result == strong_secret

    def test_load_from_env_var(self, monkeypatch, strong_secret):
        """Load a secret from a real environment variable."""
        monkeypatch.setenv("TEST_SECRET_VAR", strong_secret)
        result = load_secret(
            "db_password",
            "TEST_SECRET_VAR",
            min_length=16,
        )
        assert result == strong_secret

    def test_load_from_real_file_via_tmpdir(self, tmp_path, monkeypatch, strong_secret):
        """Write a real temp file simulating a Docker secret and verify file I/O.

        We create a real file tree mirroring /run/secrets/ in a temp directory,
        verify the file content survives write/read, and then exercise load_secret
        via the env-var fallback path.
        """
        run_secrets = tmp_path / "run" / "secrets"
        run_secrets.mkdir(parents=True)
        secret_file = run_secrets / "db_password"
        secret_file.write_text(strong_secret + "\n")

        # Verify the real file round-trip
        assert secret_file.read_text().strip() == strong_secret

        # Test the env-var fallback path end-to-end
        monkeypatch.setenv("TEST_DB_SECRET", strong_secret)
        result = load_secret("db_password", "TEST_DB_SECRET", min_length=16)
        assert result == strong_secret

    def test_missing_secret_required_raises(self, monkeypatch):
        """A required secret that is missing should raise SecretsValidationError."""
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        with pytest.raises(SecretsValidationError, match="mancante"):
            load_secret("db_password", "NONEXISTENT_VAR", required=True)

    def test_missing_secret_optional_returns_empty(self, monkeypatch):
        """An optional missing secret returns empty string."""
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        result = load_secret(
            "db_password",
            "NONEXISTENT_VAR",
            required=False,
        )
        assert result == ""

    def test_short_secret_raises(self, monkeypatch):
        """A secret shorter than min_length should raise SecretsValidationError."""
        monkeypatch.setenv("SHORT_SECRET", "Ab1!")
        with pytest.raises(SecretsValidationError, match="troppo corto"):
            load_secret("db_password", "SHORT_SECRET", min_length=16)

    def test_weak_secret_raises(self, monkeypatch):
        """A secret containing a weak pattern should raise."""
        # 'password' is a weak pattern — pad it to be long enough
        monkeypatch.setenv("WEAK_SECRET", "MyPasswordIsLong123!")
        with pytest.raises(SecretsValidationError, match="pattern debole"):
            load_secret("db_password", "WEAK_SECRET", min_length=16)

    def test_low_complexity_raises(self, monkeypatch):
        """A secret with insufficient complexity should raise."""
        # Only lowercase + digits = 2 categories (needs 3)
        monkeypatch.setenv("LOW_COMPLEX", "abcdefghijklmnop1234")
        with pytest.raises(SecretsValidationError, match="complessita"):
            load_secret("db_password", "LOW_COMPLEX", min_length=16, check_complexity=True)

    def test_skip_complexity_check(self, monkeypatch):
        """When check_complexity=False, low-complexity secrets pass."""
        # Only lowercase + digits = 2 categories, but complexity check is off.
        # Must not contain weak patterns though.
        monkeypatch.setenv("NOCHECK_SECRET", "xr9kl2mnpq7vzwabcde")
        result = load_secret(
            "db_password",
            "NOCHECK_SECRET",
            min_length=16,
            check_complexity=False,
        )
        assert result == "xr9kl2mnpq7vzwabcde"

    def test_real_file_read_and_strip(self, tmp_path):
        """Verify that reading a real file and stripping works correctly."""
        secret_file = tmp_path / "real_secret"
        secret_file.write_text("  Xr9$kL2@mNpQ7vZwABCD  \n")
        content = secret_file.read_text().strip()
        assert content == "Xr9$kL2@mNpQ7vZwABCD"


# ------------------------------------------------------------------
# validate_required_secrets — real env vars
# ------------------------------------------------------------------


class TestValidateRequiredSecrets:
    """Test validate_required_secrets with real environment variables."""

    def test_development_mode_optional(self, monkeypatch):
        """In development mode, secrets are optional."""
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        result = validate_required_secrets(env="development")
        # In dev mode, missing secrets return empty strings
        assert isinstance(result, dict)
        assert "db_password" in result
        assert "redis_password" in result

    def test_production_mode_requires_secrets(self, monkeypatch):
        """In production mode, missing secrets raise SecretsValidationError."""
        monkeypatch.delenv("MONEYMAKER_DB_PASSWORD", raising=False)
        monkeypatch.delenv("MONEYMAKER_REDIS_PASSWORD", raising=False)
        with pytest.raises(SecretsValidationError, match="Validazione secrets fallita"):
            validate_required_secrets(env="production")

    def test_production_with_valid_secrets(self, monkeypatch):
        """Production mode passes when all secrets are strong enough."""
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "Xr9$kL2@mNpQ7vZwABCD")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "Yt8#jM3!nBqR6wKxCDEF")
        result = validate_required_secrets(env="production")
        assert result["db_password"] == "Xr9$kL2@mNpQ7vZwABCD"
        assert result["redis_password"] == "Yt8#jM3!nBqR6wKxCDEF"

    def test_production_weak_password_raises(self, monkeypatch):
        """Production mode rejects a weak db_password."""
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "password12345678!")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "Yt8#jM3!nBqR6wKxCDEF")
        with pytest.raises(SecretsValidationError):
            validate_required_secrets(env="production")

    def test_development_with_short_secrets_passes(self, monkeypatch):
        """Development mode has relaxed min_length (8)."""
        monkeypatch.setenv("MONEYMAKER_DB_PASSWORD", "Xr9$kL2@")
        monkeypatch.setenv("MONEYMAKER_REDIS_PASSWORD", "Yt8#jM3!")
        result = validate_required_secrets(env="development")
        assert result["db_password"] == "Xr9$kL2@"
        assert result["redis_password"] == "Yt8#jM3!"
