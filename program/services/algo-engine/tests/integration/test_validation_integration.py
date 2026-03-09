"""Integration test: signal validator confidence gate and data quality.

Verifies that the validator correctly rejects signals below the
confidence threshold and that the data quality checker filters out
bars with invalid OHLC relationships.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.features.data_quality import DataQualityChecker
from algo_engine.features.pipeline import OHLCVBar
from algo_engine.signals.validator import SignalValidator


class TestDataQualityIntegration:
    """Verify DataQualityChecker rejects structurally invalid bars."""

    def test_accepts_valid_bar(self):
        """Well-formed bar passes quality checks."""
        checker = DataQualityChecker()
        ok, reason = checker.validate_bar(
            bar_open=Decimal("2340.00"),
            bar_high=Decimal("2345.00"),
            bar_low=Decimal("2338.00"),
            bar_close=Decimal("2342.50"),
            bar_volume=Decimal("1200"),
            bar_timestamp_ms=1700000000000,
        )
        assert ok is True, f"Valid bar rejected: {reason}"

    def test_rejects_high_below_low(self):
        """Bar where high < low is structurally invalid."""
        checker = DataQualityChecker()
        ok, reason = checker.validate_bar(
            bar_open=Decimal("2340.00"),
            bar_high=Decimal("2335.00"),  # below low
            bar_low=Decimal("2338.00"),
            bar_close=Decimal("2337.00"),
            bar_volume=Decimal("1000"),
            bar_timestamp_ms=1700000000000,
        )
        assert ok is False

    def test_warns_on_negative_volume(self):
        """Negative volume logs a warning but bar is still accepted.

        DataQualityChecker treats zero/negative volume as potentially
        missing data, not structural invalidity — consistent with how
        some exchanges report after-hours or synthetic bars.
        """
        checker = DataQualityChecker()
        ok, reason = checker.validate_bar(
            bar_open=Decimal("2340.00"),
            bar_high=Decimal("2345.00"),
            bar_low=Decimal("2338.00"),
            bar_close=Decimal("2342.00"),
            bar_volume=Decimal("-100"),
            bar_timestamp_ms=1700000000000,
        )
        # DataQualityChecker accepts this with a warning log
        assert ok is True

    def test_rejects_zero_price(self):
        """Zero prices are invalid."""
        checker = DataQualityChecker()
        ok, reason = checker.validate_bar(
            bar_open=Decimal("0"),
            bar_high=Decimal("2345.00"),
            bar_low=Decimal("2338.00"),
            bar_close=Decimal("2342.00"),
            bar_volume=Decimal("1000"),
            bar_timestamp_ms=1700000000000,
        )
        assert ok is False


class TestConfidenceGateIntegration:
    """Verify SignalValidator enforces minimum confidence threshold."""

    def test_rejects_low_confidence_signal(self):
        """Signal below min_confidence should be rejected."""
        validator = SignalValidator(min_confidence=Decimal("0.65"))
        signal = {
            "signal_id": "test-001",
            "symbol": "XAUUSD",
            "direction": "BUY",
            "suggested_lots": "0.05",
            "stop_loss": "2330.00",
            "take_profit": "2360.00",
            "confidence": "0.40",
        }
        portfolio_state = {
            "open_position_count": 0,
            "current_drawdown_pct": "0.5",
            "daily_loss_pct": "0.1",
            "equity": "10000.00",
        }

        is_valid, reason = validator.validate(signal, portfolio_state)
        assert is_valid is False
        assert "confidenza" in reason.lower() or "confidence" in reason.lower()

    def test_accepts_high_confidence_signal(self):
        """Signal above min_confidence should pass all validation gates."""
        validator = SignalValidator(min_confidence=Decimal("0.65"))
        signal = {
            "signal_id": "test-002",
            "symbol": "XAUUSD",
            "direction": "BUY",
            "suggested_lots": "0.05",
            "entry_price": "2345.00",
            "stop_loss": "2330.00",
            "take_profit": "2360.00",
            "confidence": "0.85",
            "risk_reward_ratio": "1.0",
        }
        portfolio_state = {
            "open_position_count": 0,
            "current_drawdown_pct": "0.5",
            "daily_loss_pct": "0.1",
            "equity": "10000.00",
        }

        is_valid, reason = validator.validate(signal, portfolio_state)
        assert is_valid is True, f"High confidence signal rejected: {reason}"

    def test_rejects_when_max_positions_reached(self):
        """Signal should be rejected when position limit is reached."""
        validator = SignalValidator(
            min_confidence=Decimal("0.50"),
            max_open_positions=3,
        )
        signal = {
            "signal_id": "test-003",
            "symbol": "XAUUSD",
            "direction": "SELL",
            "suggested_lots": "0.05",
            "stop_loss": "2360.00",
            "take_profit": "2330.00",
            "confidence": "0.80",
        }
        portfolio_state = {
            "open_position_count": 3,
            "current_drawdown_pct": "0.5",
            "daily_loss_pct": "0.1",
            "equity": "10000.00",
        }

        is_valid, reason = validator.validate(signal, portfolio_state)
        assert is_valid is False
        assert "posizion" in reason.lower() or "position" in reason.lower()

    def test_rejects_when_drawdown_exceeded(self):
        """Signal rejected when portfolio drawdown exceeds limit."""
        validator = SignalValidator(
            min_confidence=Decimal("0.50"),
            max_drawdown_pct=Decimal("5.0"),
        )
        signal = {
            "signal_id": "test-004",
            "symbol": "XAUUSD",
            "direction": "BUY",
            "suggested_lots": "0.05",
            "stop_loss": "2330.00",
            "take_profit": "2360.00",
            "confidence": "0.80",
        }
        portfolio_state = {
            "open_position_count": 1,
            "current_drawdown_pct": "6.0",
            "daily_loss_pct": "0.5",
            "equity": "9400.00",
        }

        is_valid, reason = validator.validate(signal, portfolio_state)
        assert is_valid is False
        assert "drawdown" in reason.lower()
