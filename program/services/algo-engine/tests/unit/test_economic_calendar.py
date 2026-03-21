"""Tests for EconomicCalendarFilter — blackout periods around macro events.

All tests use REAL class instances — no MagicMock, no @patch, no unittest.mock.
- freezegun: controls datetime.now() for time-dependent NFP detection
- tmp_path: creates real JSON event files on disk
- Direct datetime injection via utc_now parameter
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from freezegun import freeze_time

from algo_engine.features.economic_calendar import (
    EVENT_CURRENCY_MAP,
    EconomicCalendarFilter,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_events_file(tmp_path, events: list[dict]) -> str:
    """Write events to a JSON file and return the path as string."""
    filepath = tmp_path / "events.json"
    filepath.write_text(json.dumps(events))
    return str(filepath)


# ---------------------------------------------------------------------------
# Tests — No events file
# ---------------------------------------------------------------------------


class TestEconomicCalendarNoFile:
    """Without an events file, only recurring patterns (NFP) are checked."""

    def test_no_events_file_not_blocked_on_random_day(self) -> None:
        cal = EconomicCalendarFilter()
        # A Wednesday at 10:00 UTC — no NFP, no events
        utc_now = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)  # Wednesday
        blocked, reason = cal.is_blackout("EURUSD", utc_now)
        assert blocked is False
        assert reason == ""

    def test_no_events_file_not_blocked_for_any_symbol(self) -> None:
        cal = EconomicCalendarFilter()
        utc_now = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)
        for symbol in ["EURUSD", "GBPUSD", "USDJPY", "EURGBP"]:
            blocked, _ = cal.is_blackout(symbol, utc_now)
            assert blocked is False


# ---------------------------------------------------------------------------
# Tests — NFP recurring pattern
# ---------------------------------------------------------------------------


class TestNFPBlackout:
    """NFP: first Friday of the month (day <= 7, weekday == 4), 13:30 UTC."""

    def test_first_friday_at_nfp_time_blocks_usd_pair(self) -> None:
        # 2026-03-06 is a Friday and day <= 7 → first Friday
        cal = EconomicCalendarFilter(blackout_minutes_before=15, blackout_minutes_after=15)
        utc_now = datetime(2026, 3, 6, 13, 30, tzinfo=timezone.utc)
        blocked, reason = cal.is_blackout("EURUSD", utc_now)
        assert blocked is True
        assert "NFP" in reason

    def test_first_friday_nfp_blocks_usdjpy(self) -> None:
        cal = EconomicCalendarFilter()
        utc_now = datetime(2026, 3, 6, 13, 30, tzinfo=timezone.utc)
        blocked, reason = cal.is_blackout("USDJPY", utc_now)
        assert blocked is True

    def test_first_friday_nfp_does_not_block_eurgbp(self) -> None:
        # EURGBP is not a USD pair
        cal = EconomicCalendarFilter()
        utc_now = datetime(2026, 3, 6, 13, 30, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("EURGBP", utc_now)
        assert blocked is False

    def test_second_friday_not_blocked(self) -> None:
        # 2026-03-13 is a Friday but day > 7 → not first Friday
        cal = EconomicCalendarFilter()
        utc_now = datetime(2026, 3, 13, 13, 30, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("EURUSD", utc_now)
        assert blocked is False

    def test_first_friday_outside_window_not_blocked(self) -> None:
        # 10:00 UTC — far from 13:30
        cal = EconomicCalendarFilter()
        utc_now = datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("EURUSD", utc_now)
        assert blocked is False

    def test_first_friday_within_before_window_blocked(self) -> None:
        # 13:20 is 10 minutes before 13:30, within 15-min before window
        cal = EconomicCalendarFilter(blackout_minutes_before=15)
        utc_now = datetime(2026, 3, 6, 13, 20, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("EURUSD", utc_now)
        assert blocked is True

    def test_first_friday_within_after_window_blocked(self) -> None:
        # 13:40 is 10 minutes after 13:30, within 15-min after window
        cal = EconomicCalendarFilter(blackout_minutes_after=15)
        utc_now = datetime(2026, 3, 6, 13, 40, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("EURUSD", utc_now)
        assert blocked is True


# ---------------------------------------------------------------------------
# Tests — JSON events file
# ---------------------------------------------------------------------------


class TestJSONEventsBlackout:
    """Events loaded from a JSON file."""

    def test_high_impact_event_within_window_blocks(self, tmp_path) -> None:
        events = [
            {
                "datetime": "2026-03-18T14:30:00",
                "currency": "USD",
                "impact": "high",
                "name": "CPI Release",
            }
        ]
        filepath = _write_events_file(tmp_path, events)
        cal = EconomicCalendarFilter(events_file=filepath)

        utc_now = datetime(2026, 3, 18, 14, 30, tzinfo=timezone.utc)
        blocked, reason = cal.is_blackout("EURUSD", utc_now)
        assert blocked is True
        assert "CPI" in reason

    def test_low_impact_event_not_blocked(self, tmp_path) -> None:
        events = [
            {
                "datetime": "2026-03-18T14:30:00",
                "currency": "USD",
                "impact": "low",
                "name": "Minor Report",
            }
        ]
        filepath = _write_events_file(tmp_path, events)
        cal = EconomicCalendarFilter(events_file=filepath)

        utc_now = datetime(2026, 3, 18, 14, 30, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("EURUSD", utc_now)
        assert blocked is False

    def test_high_impact_wrong_currency_not_blocked(self, tmp_path) -> None:
        events = [
            {
                "datetime": "2026-03-18T14:30:00",
                "currency": "GBP",
                "impact": "high",
                "name": "BoE Rate Decision",
            }
        ]
        filepath = _write_events_file(tmp_path, events)
        cal = EconomicCalendarFilter(events_file=filepath)

        # USDJPY is not a GBP pair
        utc_now = datetime(2026, 3, 18, 14, 30, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("USDJPY", utc_now)
        assert blocked is False

    def test_high_impact_outside_time_window_not_blocked(self, tmp_path) -> None:
        events = [
            {
                "datetime": "2026-03-18T14:30:00",
                "currency": "USD",
                "impact": "high",
                "name": "CPI Release",
            }
        ]
        filepath = _write_events_file(tmp_path, events)
        cal = EconomicCalendarFilter(
            blackout_minutes_before=15,
            blackout_minutes_after=15,
            events_file=filepath,
        )

        # 2 hours before the event — well outside 15-min window
        utc_now = datetime(2026, 3, 18, 12, 0, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("EURUSD", utc_now)
        assert blocked is False

    def test_critical_impact_event_blocks(self, tmp_path) -> None:
        events = [
            {
                "datetime": "2026-03-18T19:00:00",
                "currency": "USD",
                "impact": "critical",
                "name": "FOMC Decision",
            }
        ]
        filepath = _write_events_file(tmp_path, events)
        cal = EconomicCalendarFilter(events_file=filepath)

        utc_now = datetime(2026, 3, 18, 19, 0, tzinfo=timezone.utc)
        blocked, reason = cal.is_blackout("EURUSD", utc_now)
        assert blocked is True
        assert "FOMC" in reason

    def test_configurable_wider_blackout_window(self, tmp_path) -> None:
        events = [
            {
                "datetime": "2026-03-18T14:30:00",
                "currency": "USD",
                "impact": "high",
                "name": "CPI Release",
            }
        ]
        filepath = _write_events_file(tmp_path, events)
        # 30-minute window each side
        cal = EconomicCalendarFilter(
            blackout_minutes_before=30,
            blackout_minutes_after=30,
            events_file=filepath,
        )

        # 25 minutes before — outside default 15 but inside 30
        utc_now = datetime(2026, 3, 18, 14, 5, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("EURUSD", utc_now)
        assert blocked is True


# ---------------------------------------------------------------------------
# Tests — Error handling
# ---------------------------------------------------------------------------


class TestEconomicCalendarErrorHandling:
    """Graceful handling of missing/invalid files."""

    def test_missing_events_file_no_crash(self) -> None:
        # Non-existent path should warn but not raise
        cal = EconomicCalendarFilter(events_file="/nonexistent/path/events.json")
        assert cal._events == []

        # Should still work for NFP checks
        utc_now = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("EURUSD", utc_now)
        assert blocked is False

    def test_invalid_json_file_no_crash(self, tmp_path) -> None:
        filepath = tmp_path / "bad_events.json"
        filepath.write_text("this is not valid JSON {{{{")

        cal = EconomicCalendarFilter(events_file=str(filepath))
        assert cal._events == []

        utc_now = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)
        blocked, _ = cal.is_blackout("EURUSD", utc_now)
        assert blocked is False
