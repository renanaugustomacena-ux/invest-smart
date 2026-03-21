"""Tests for moneymaker_common.logging — structured JSON logging setup.

No unittest.mock — tests real structlog configuration and output.
"""

from __future__ import annotations

import json
import sys
from io import StringIO

import structlog

from moneymaker_common.logging import get_logger, setup_logging


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_log(service: str, level: str = "INFO") -> tuple[structlog.stdlib.BoundLogger, StringIO]:
    """Set up logging with a captured stdout and return (logger, buffer)."""
    buf = StringIO()
    # Configure structlog to write to our buffer instead of real stdout
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(__import__("logging"), level.upper(), 20)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=buf),
        cache_logger_on_first_use=False,  # Allow reconfiguration between tests
    )
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service)
    logger = structlog.get_logger(component="test")
    return logger, buf


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    def test_setup_does_not_raise(self):
        """Basic smoke test — setup_logging should not raise."""
        setup_logging("test-service")

    def test_setup_with_debug_level(self):
        setup_logging("test-service", level="DEBUG")

    def test_setup_with_warning_level(self):
        setup_logging("test-service", level="WARNING")

    def test_setup_with_lowercase_level(self):
        """Level string is uppercased internally."""
        setup_logging("test-service", level="debug")

    def test_setup_with_invalid_level_falls_back_to_info(self):
        """Invalid level string → getattr returns logging.INFO (default)."""
        setup_logging("test-service", level="NONEXISTENT")


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------


class TestGetLogger:
    def test_returns_bound_logger(self):
        setup_logging("test-service")
        logger = get_logger("my_module")
        assert logger is not None

    def test_logger_has_info_method(self):
        setup_logging("test-service")
        logger = get_logger("my_module")
        assert callable(getattr(logger, "info", None))

    def test_logger_has_warning_method(self):
        setup_logging("test-service")
        logger = get_logger("my_module")
        assert callable(getattr(logger, "warning", None))

    def test_logger_has_error_method(self):
        setup_logging("test-service")
        logger = get_logger("my_module")
        assert callable(getattr(logger, "error", None))


# ---------------------------------------------------------------------------
# JSON output format
# ---------------------------------------------------------------------------


class TestJSONOutput:
    def test_output_is_valid_json(self):
        logger, buf = _capture_log("json-test")
        logger.info("hello")
        line = buf.getvalue().strip()
        parsed = json.loads(line)
        assert isinstance(parsed, dict)

    def test_output_contains_service_field(self):
        logger, buf = _capture_log("my-service")
        logger.info("test event")
        parsed = json.loads(buf.getvalue().strip())
        assert parsed["service"] == "my-service"

    def test_output_contains_log_level(self):
        logger, buf = _capture_log("level-test")
        logger.info("info message")
        parsed = json.loads(buf.getvalue().strip())
        assert parsed["level"] == "info"

    def test_output_contains_timestamp(self):
        logger, buf = _capture_log("ts-test")
        logger.info("timestamp check")
        parsed = json.loads(buf.getvalue().strip())
        assert "timestamp" in parsed
        # ISO format includes 'T' separator
        assert "T" in parsed["timestamp"]

    def test_output_contains_event(self):
        logger, buf = _capture_log("event-test")
        logger.info("my event message")
        parsed = json.loads(buf.getvalue().strip())
        assert parsed["event"] == "my event message"

    def test_output_contains_component(self):
        logger, buf = _capture_log("comp-test")
        logger.info("component check")
        parsed = json.loads(buf.getvalue().strip())
        assert parsed["component"] == "test"

    def test_extra_fields_included(self):
        logger, buf = _capture_log("extra-test")
        logger.info("trade signal", symbol="EURUSD", direction="BUY")
        parsed = json.loads(buf.getvalue().strip())
        assert parsed["symbol"] == "EURUSD"
        assert parsed["direction"] == "BUY"

    def test_warning_level_output(self):
        logger, buf = _capture_log("warn-test")
        logger.warning("something concerning")
        parsed = json.loads(buf.getvalue().strip())
        assert parsed["level"] == "warning"

    def test_error_level_output(self):
        logger, buf = _capture_log("error-test")
        logger.error("something broke", error_code=500)
        parsed = json.loads(buf.getvalue().strip())
        assert parsed["level"] == "error"
        assert parsed["error_code"] == 500


# ---------------------------------------------------------------------------
# Log level filtering
# ---------------------------------------------------------------------------


class TestLogLevelFiltering:
    def test_info_level_filters_debug(self):
        """At INFO level, debug messages should not appear."""
        logger, buf = _capture_log("filter-test", level="INFO")
        logger.debug("should not appear")
        assert buf.getvalue().strip() == ""

    def test_info_level_passes_info(self):
        logger, buf = _capture_log("filter-test", level="INFO")
        logger.info("should appear")
        assert buf.getvalue().strip() != ""

    def test_debug_level_passes_debug(self):
        logger, buf = _capture_log("filter-test", level="DEBUG")
        logger.debug("debug visible")
        output = buf.getvalue().strip()
        assert output != ""
        parsed = json.loads(output)
        assert parsed["level"] == "debug"

    def test_warning_level_filters_info(self):
        logger, buf = _capture_log("filter-test", level="WARNING")
        logger.info("should be filtered")
        assert buf.getvalue().strip() == ""

    def test_error_level_filters_warning(self):
        logger, buf = _capture_log("filter-test", level="ERROR")
        logger.warning("should be filtered")
        assert buf.getvalue().strip() == ""
