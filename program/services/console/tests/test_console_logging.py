"""Tests for console_logging module."""

from __future__ import annotations

import json

from moneymaker_console.console_logging import (
    _SECRET_PATTERN,
    init_log_dir,
    log_event,
    mask_dict,
    mask_secrets,
)


class TestMaskSecrets:
    def test_short_text(self):
        assert mask_secrets("abc") == "****"

    def test_exact_four(self):
        assert mask_secrets("1234") == "****"

    def test_longer_text(self):
        assert mask_secrets("my-secret-key") == "****-key"

    def test_empty(self):
        assert mask_secrets("") == "****"


class TestMaskDict:
    def test_masks_secret_keys(self):
        d = {"API_KEY": "abcdef1234", "name": "hello"}
        result = mask_dict(d)
        assert result["API_KEY"] == "****1234"
        assert result["name"] == "hello"

    def test_masks_password(self):
        d = {"DB_PASSWORD": "supersecret"}
        result = mask_dict(d)
        assert result["DB_PASSWORD"] == "****cret"

    def test_masks_token(self):
        d = {"AUTH_TOKEN": "tok_12345678"}
        result = mask_dict(d)
        assert result["AUTH_TOKEN"] == "****5678"

    def test_non_string_values_untouched(self):
        d = {"SECRET_COUNT": 42, "API_KEY": "abcdef"}
        result = mask_dict(d)
        assert result["SECRET_COUNT"] == 42
        assert result["API_KEY"] == "****cdef"

    def test_case_insensitive(self):
        d = {"api_key": "test1234"}
        result = mask_dict(d)
        assert result["api_key"] == "****1234"

    def test_dsn_masked(self):
        d = {"SENTRY_DSN": "https://abc@sentry.io/123"}
        result = mask_dict(d)
        assert "****" in result["SENTRY_DSN"]

    def test_credential_masked(self):
        d = {"CREDENTIAL_FILE": "/path/to/creds.json"}
        result = mask_dict(d)
        assert "****" in result["CREDENTIAL_FILE"]


class TestSecretPattern:
    def test_matches_key(self):
        assert _SECRET_PATTERN.search("API_KEY")

    def test_matches_secret(self):
        assert _SECRET_PATTERN.search("MY_SECRET")

    def test_matches_password(self):
        assert _SECRET_PATTERN.search("DB_PASSWORD")

    def test_matches_token(self):
        assert _SECRET_PATTERN.search("AUTH_TOKEN")

    def test_no_match_normal(self):
        assert not _SECRET_PATTERN.search("USERNAME")


class TestInitLogDir:
    def test_creates_dir(self, tmp_path):
        log_dir = tmp_path / "logs"
        init_log_dir(log_dir)
        assert log_dir.exists()

    def test_existing_dir(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        init_log_dir(log_dir)
        assert log_dir.exists()


class TestLogEvent:
    def test_log_event_writes_json(self, tmp_path):
        log_dir = tmp_path / "logs"
        init_log_dir(log_dir)
        log_event("test_event", key="value")

        log_files = list(log_dir.glob("console_*.json"))
        assert len(log_files) == 1
        with open(log_files[0]) as f:
            entry = json.loads(f.readline())
        assert entry["event"] == "test_event"
        assert entry["key"] == "value"
        assert "ts" in entry

    def test_log_event_no_dir(self):
        """log_event should not crash when _LOG_DIR is None."""
        import moneymaker_console.console_logging as cl

        old = cl._LOG_DIR
        cl._LOG_DIR = None
        try:
            log_event("should_not_crash")
        finally:
            cl._LOG_DIR = old

    def test_log_event_appends(self, tmp_path):
        log_dir = tmp_path / "logs"
        init_log_dir(log_dir)
        log_event("event1")
        log_event("event2")

        log_files = list(log_dir.glob("console_*.json"))
        with open(log_files[0]) as f:
            lines = f.readlines()
        assert len(lines) == 2
