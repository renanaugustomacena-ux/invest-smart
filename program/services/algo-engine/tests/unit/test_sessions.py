"""Tests for SessionClassifier and TradingSession.

All tests use real class instances — no unittest.mock.
"""

from __future__ import annotations

import pytest

from algo_engine.features.sessions import (
    SESSION_CONFIGS,
    SessionClassifier,
    TradingSession,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def classifier() -> SessionClassifier:
    """Return a real SessionClassifier instance."""
    return SessionClassifier()


# ---------------------------------------------------------------------------
# classify() — boundary-hour tests for all 5 sessions
# ---------------------------------------------------------------------------


class TestClassifyBoundaries:
    """Test classify() returns the correct session at each boundary hour."""

    def test_hour_0_is_asian(self, classifier: SessionClassifier) -> None:
        assert classifier.classify(0) == TradingSession.ASIAN

    def test_hour_7_is_asian(self, classifier: SessionClassifier) -> None:
        assert classifier.classify(7) == TradingSession.ASIAN

    def test_hour_8_is_london(self, classifier: SessionClassifier) -> None:
        assert classifier.classify(8) == TradingSession.LONDON

    def test_hour_12_is_london(self, classifier: SessionClassifier) -> None:
        assert classifier.classify(12) == TradingSession.LONDON

    def test_hour_13_is_overlap(self, classifier: SessionClassifier) -> None:
        assert classifier.classify(13) == TradingSession.LONDON_US_OVERLAP

    def test_hour_15_is_overlap(self, classifier: SessionClassifier) -> None:
        assert classifier.classify(15) == TradingSession.LONDON_US_OVERLAP

    def test_hour_16_is_us(self, classifier: SessionClassifier) -> None:
        assert classifier.classify(16) == TradingSession.US

    def test_hour_20_is_us(self, classifier: SessionClassifier) -> None:
        assert classifier.classify(20) == TradingSession.US

    def test_hour_21_is_off_hours(self, classifier: SessionClassifier) -> None:
        assert classifier.classify(21) == TradingSession.OFF_HOURS

    def test_hour_23_is_off_hours(self, classifier: SessionClassifier) -> None:
        assert classifier.classify(23) == TradingSession.OFF_HOURS


# ---------------------------------------------------------------------------
# get_confidence_boost() — correct float for each session
# ---------------------------------------------------------------------------


class TestGetConfidenceBoost:
    """Test get_confidence_boost() returns the right value per session."""

    def test_asian_boost_negative(self, classifier: SessionClassifier) -> None:
        assert classifier.get_confidence_boost(TradingSession.ASIAN) == -0.05

    def test_london_boost_zero(self, classifier: SessionClassifier) -> None:
        assert classifier.get_confidence_boost(TradingSession.LONDON) == 0.0

    def test_overlap_boost_positive(self, classifier: SessionClassifier) -> None:
        assert classifier.get_confidence_boost(TradingSession.LONDON_US_OVERLAP) == 0.05

    def test_us_boost_zero(self, classifier: SessionClassifier) -> None:
        assert classifier.get_confidence_boost(TradingSession.US) == 0.0

    def test_off_hours_boost_negative(self, classifier: SessionClassifier) -> None:
        assert classifier.get_confidence_boost(TradingSession.OFF_HOURS) == -0.10

    def test_unknown_session_returns_zero(self, classifier: SessionClassifier) -> None:
        """A value not found in SESSION_CONFIGS should default to 0.0."""
        assert classifier.get_confidence_boost("NONEXISTENT_SESSION") == 0.0
