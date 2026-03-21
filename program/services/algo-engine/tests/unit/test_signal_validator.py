"""Tests for SignalValidator — the risk gate before MT5 execution.

All tests use REAL class instances — no MagicMock, no @patch, no unittest.mock.
- SpreadPercentileTracker: fed with real spread data via record_spread()
- CorrelationChecker: real currency decomposition logic
- SessionClassifier: real hour → session classification
- EconomicCalendarFilter: real NFP pattern detection
- freezegun: controls datetime.now() for time-dependent checks
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from freezegun import freeze_time

from algo_engine.features.economic_calendar import EconomicCalendarFilter
from algo_engine.features.sessions import SessionClassifier
from algo_engine.features.spread_tracker import SpreadPercentileTracker
from algo_engine.signals.correlation import CorrelationChecker
from algo_engine.signals.validator import SignalValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(**overrides) -> dict:
    """Return a valid BUY signal dict, with optional overrides."""
    base = {
        "signal_id": "test-001",
        "symbol": "EURUSD",
        "direction": "BUY",
        "confidence": Decimal("0.80"),
        "entry_price": Decimal("1.10000"),
        "stop_loss": Decimal("1.09500"),
        "take_profit": Decimal("1.10800"),
        "risk_reward_ratio": Decimal("1.6"),
        "suggested_lots": Decimal("0.10"),
        "spread": Decimal("0"),
    }
    base.update(overrides)
    return base


def _make_portfolio(**overrides) -> dict:
    """Return a healthy portfolio state with optional overrides."""
    base = {
        "open_position_count": 2,
        "current_drawdown_pct": "1.5",
        "daily_loss_pct": "0.5",
        "equity": "100000.00",
        "used_margin": "5000.00",
    }
    base.update(overrides)
    return base


def _build_spread_tracker(
    symbol: str = "EURUSD",
    spreads: list[Decimal] | None = None,
    window: int = 200,
    reject_percentile: int = 90,
    min_observations: int = 20,
) -> SpreadPercentileTracker:
    """Build a SpreadPercentileTracker pre-loaded with spread history."""
    tracker = SpreadPercentileTracker(
        window=window,
        reject_percentile=reject_percentile,
        min_observations=min_observations,
    )
    if spreads:
        for s in spreads:
            tracker.record_spread(symbol, s)
    return tracker


# ---------------------------------------------------------------------------
# Control 1: HOLD rejection
# ---------------------------------------------------------------------------


class TestHoldRejection:
    def test_hold_direction_rejected(self):
        v = SignalValidator()
        valid, reason = v.validate(_make_signal(direction="HOLD"), _make_portfolio())
        assert not valid
        assert "HOLD" in reason

    def test_invalid_direction_string_treated_as_hold(self):
        v = SignalValidator()
        valid, _ = v.validate(_make_signal(direction="INVALID"), _make_portfolio())
        assert not valid

    def test_missing_direction_treated_as_hold(self):
        v = SignalValidator()
        sig = _make_signal()
        del sig["direction"]
        valid, _ = v.validate(sig, _make_portfolio())
        assert not valid


# ---------------------------------------------------------------------------
# Control 2: Max open positions
# ---------------------------------------------------------------------------


class TestMaxOpenPositions:
    def test_at_limit_rejected(self):
        v = SignalValidator(max_open_positions=5)
        valid, reason = v.validate(_make_signal(), _make_portfolio(open_position_count=5))
        assert not valid
        assert "5/5" in reason

    def test_above_limit_rejected(self):
        v = SignalValidator(max_open_positions=3)
        valid, _ = v.validate(_make_signal(), _make_portfolio(open_position_count=4))
        assert not valid

    def test_below_limit_passes(self):
        v = SignalValidator(max_open_positions=5)
        valid, _ = v.validate(_make_signal(), _make_portfolio(open_position_count=4))
        assert valid

    def test_zero_positions_passes(self):
        v = SignalValidator(max_open_positions=5)
        valid, _ = v.validate(_make_signal(), _make_portfolio(open_position_count=0))
        assert valid


# ---------------------------------------------------------------------------
# Control 3: Drawdown limit
# ---------------------------------------------------------------------------


class TestDrawdownLimit:
    def test_at_limit_rejected(self):
        v = SignalValidator(max_drawdown_pct=Decimal("5.0"))
        valid, reason = v.validate(_make_signal(), _make_portfolio(current_drawdown_pct="5.0"))
        assert not valid
        assert "Drawdown" in reason

    def test_above_limit_rejected(self):
        v = SignalValidator(max_drawdown_pct=Decimal("5.0"))
        valid, _ = v.validate(_make_signal(), _make_portfolio(current_drawdown_pct="7.0"))
        assert not valid

    def test_below_limit_passes(self):
        v = SignalValidator(max_drawdown_pct=Decimal("5.0"))
        valid, _ = v.validate(_make_signal(), _make_portfolio(current_drawdown_pct="4.9"))
        assert valid


# ---------------------------------------------------------------------------
# Control 4: Daily loss limit
# ---------------------------------------------------------------------------


class TestDailyLossLimit:
    def test_at_limit_rejected(self):
        v = SignalValidator(max_daily_loss_pct=Decimal("2.0"))
        valid, reason = v.validate(_make_signal(), _make_portfolio(daily_loss_pct="2.0"))
        assert not valid
        assert "giornaliera" in reason

    def test_below_limit_passes(self):
        v = SignalValidator(max_daily_loss_pct=Decimal("2.0"))
        valid, _ = v.validate(_make_signal(), _make_portfolio(daily_loss_pct="1.9"))
        assert valid


# ---------------------------------------------------------------------------
# Control 5: Confidence threshold
# ---------------------------------------------------------------------------


class TestConfidenceThreshold:
    def test_below_threshold_rejected(self):
        v = SignalValidator(min_confidence=Decimal("0.65"))
        valid, reason = v.validate(_make_signal(confidence=Decimal("0.50")), _make_portfolio())
        assert not valid
        assert "Confidenza" in reason

    def test_at_threshold_passes(self):
        v = SignalValidator(min_confidence=Decimal("0.65"))
        valid, _ = v.validate(_make_signal(confidence=Decimal("0.65")), _make_portfolio())
        assert valid

    def test_nan_confidence_rejected(self):
        v = SignalValidator()
        valid, reason = v.validate(_make_signal(confidence=Decimal("NaN")), _make_portfolio())
        assert not valid
        assert "non valida" in reason

    def test_inf_confidence_rejected(self):
        v = SignalValidator()
        valid, reason = v.validate(_make_signal(confidence=Decimal("Infinity")), _make_portfolio())
        assert not valid


# ---------------------------------------------------------------------------
# Control 5b: Spread percentile tracker (real SpreadPercentileTracker)
# ---------------------------------------------------------------------------


class TestSpreadPercentile:
    def test_spread_rejected_by_tracker(self):
        """Feed 20 low spreads, then check with a very high spread → rejected."""
        low_spreads = [Decimal("1.0")] * 20
        tracker = _build_spread_tracker("EURUSD", low_spreads, reject_percentile=90)
        v = SignalValidator(spread_tracker=tracker)
        # Spread 100.0 is above all 20 values → 100th percentile → rejected
        valid, reason = v.validate(
            _make_signal(spread=Decimal("100.0"), symbol="EURUSD"),
            _make_portfolio(),
        )
        assert not valid
        assert "percentile" in reason.lower()

    def test_spread_accepted_by_tracker(self):
        """Feed 20 varied spreads, then check with a normal one → accepted."""
        spreads = [Decimal(str(i)) for i in range(1, 21)]  # 1..20
        tracker = _build_spread_tracker("EURUSD", spreads, reject_percentile=90)
        v = SignalValidator(spread_tracker=tracker)
        # Spread 5.0 is below 80% of values → ~20th percentile → accepted
        valid, _ = v.validate(
            _make_signal(spread=Decimal("5.0"), symbol="EURUSD"),
            _make_portfolio(),
        )
        assert valid

    def test_zero_spread_skips_tracker(self):
        """Spread=0 skips tracker check entirely — even if tracker would reject."""
        # Tracker configured to reject everything (percentile threshold=0)
        tracker = _build_spread_tracker(
            "EURUSD",
            [Decimal("1.0")] * 5,
            reject_percentile=0,
            min_observations=1,
        )
        v = SignalValidator(spread_tracker=tracker)
        # Spread=0 → validator skips the check
        valid, _ = v.validate(_make_signal(spread=Decimal("0")), _make_portfolio())
        assert valid

    def test_no_tracker_passes(self):
        v = SignalValidator(spread_tracker=None)
        valid, _ = v.validate(_make_signal(spread=Decimal("5.0")), _make_portfolio())
        assert valid


# ---------------------------------------------------------------------------
# Control 6: Stop-loss placement
# ---------------------------------------------------------------------------


class TestStopLossPlacement:
    def test_zero_stop_loss_rejected(self):
        v = SignalValidator()
        valid, reason = v.validate(_make_signal(stop_loss=Decimal("0")), _make_portfolio())
        assert not valid
        assert "zero" in reason

    def test_buy_sl_above_entry_rejected(self):
        v = SignalValidator()
        valid, reason = v.validate(
            _make_signal(
                direction="BUY",
                entry_price=Decimal("1.10000"),
                stop_loss=Decimal("1.11000"),
            ),
            _make_portfolio(),
        )
        assert not valid
        assert "BUY" in reason

    def test_buy_sl_at_entry_rejected(self):
        v = SignalValidator()
        valid, _ = v.validate(
            _make_signal(
                direction="BUY",
                entry_price=Decimal("1.10000"),
                stop_loss=Decimal("1.10000"),
            ),
            _make_portfolio(),
        )
        assert not valid

    def test_sell_sl_below_entry_rejected(self):
        v = SignalValidator()
        valid, reason = v.validate(
            _make_signal(
                direction="SELL",
                entry_price=Decimal("1.10000"),
                stop_loss=Decimal("1.09000"),
            ),
            _make_portfolio(),
        )
        assert not valid
        assert "SELL" in reason

    def test_buy_sl_below_entry_passes(self):
        v = SignalValidator()
        valid, _ = v.validate(
            _make_signal(
                direction="BUY",
                entry_price=Decimal("1.10000"),
                stop_loss=Decimal("1.09500"),
            ),
            _make_portfolio(),
        )
        assert valid

    def test_sell_sl_above_entry_passes(self):
        v = SignalValidator()
        valid, _ = v.validate(
            _make_signal(
                direction="SELL",
                entry_price=Decimal("1.10000"),
                stop_loss=Decimal("1.10500"),
                take_profit=Decimal("1.09200"),
            ),
            _make_portfolio(),
        )
        assert valid

    def test_nan_entry_price_rejected(self):
        v = SignalValidator()
        valid, reason = v.validate(_make_signal(entry_price=Decimal("NaN")), _make_portfolio())
        assert not valid
        assert "non valido" in reason

    def test_nan_stop_loss_rejected(self):
        v = SignalValidator()
        valid, reason = v.validate(_make_signal(stop_loss=Decimal("NaN")), _make_portfolio())
        assert not valid


# ---------------------------------------------------------------------------
# Control 7: Risk/reward ratio
# ---------------------------------------------------------------------------


class TestRiskRewardRatio:
    def test_below_minimum_rejected(self):
        v = SignalValidator(min_risk_reward_ratio=Decimal("1.5"))
        valid, reason = v.validate(
            _make_signal(risk_reward_ratio=Decimal("1.0")), _make_portfolio()
        )
        assert not valid
        assert "rischio/rendimento" in reason

    def test_at_minimum_passes(self):
        v = SignalValidator(min_risk_reward_ratio=Decimal("1.5"))
        valid, _ = v.validate(_make_signal(risk_reward_ratio=Decimal("1.5")), _make_portfolio())
        assert valid

    def test_zero_minimum_disables_check(self):
        v = SignalValidator(min_risk_reward_ratio=Decimal("0"))
        valid, _ = v.validate(_make_signal(risk_reward_ratio=Decimal("0.5")), _make_portfolio())
        assert valid


# ---------------------------------------------------------------------------
# Control 8: Margin check
# ---------------------------------------------------------------------------


class TestMarginCheck:
    def test_insufficient_margin_rejected(self):
        v = SignalValidator()
        valid, reason = v.validate(
            _make_signal(
                entry_price=Decimal("1.10000"),
                suggested_lots=Decimal("10.0"),
            ),
            _make_portfolio(
                equity="10000.00",
                used_margin="9000.00",
            ),
        )
        assert not valid
        assert "Margine" in reason

    def test_sufficient_margin_passes(self):
        v = SignalValidator()
        valid, _ = v.validate(
            _make_signal(
                entry_price=Decimal("1.10000"),
                suggested_lots=Decimal("0.01"),
            ),
            _make_portfolio(
                equity="100000.00",
                used_margin="1000.00",
            ),
        )
        assert valid

    def test_gold_contract_size(self):
        v = SignalValidator(default_leverage=100)
        valid, _ = v.validate(
            _make_signal(
                symbol="XAUUSD",
                entry_price=Decimal("2000.00"),
                stop_loss=Decimal("1990.00"),
                suggested_lots=Decimal("0.01"),
            ),
            _make_portfolio(equity="10000.00", used_margin="0"),
        )
        # 0.01 lot * 100 oz * 2000 / 100 leverage = $20 margin — should pass
        assert valid

    def test_zero_equity_skips_margin_check(self):
        v = SignalValidator()
        valid, _ = v.validate(
            _make_signal(suggested_lots=Decimal("0.10")),
            _make_portfolio(equity="0"),
        )
        assert valid


# ---------------------------------------------------------------------------
# Control 9: Correlation checker (real CorrelationChecker)
# ---------------------------------------------------------------------------


class TestCorrelationChecker:
    def test_correlation_rejected(self):
        """3 BUY positions on EUR pairs → EUR exposure too high → rejected."""
        checker = CorrelationChecker(max_exposure_per_currency=2.0)
        # 2 existing BUY EURUSD positions → EUR exposure already at +2.0
        portfolio = _make_portfolio(
            positions_detail=[
                {"symbol": "EURUSD", "direction": "BUY"},
                {"symbol": "EURUSD", "direction": "BUY"},
            ]
        )
        v = SignalValidator(correlation_checker=checker)
        # Adding another BUY EURUSD → EUR would be +3.0 > 2.0
        valid, reason = v.validate(_make_signal(direction="BUY", symbol="EURUSD"), portfolio)
        assert not valid
        assert "EUR" in reason

    def test_correlation_passes(self):
        """1 existing EUR position + new one → within limit."""
        checker = CorrelationChecker(max_exposure_per_currency=2.0)
        portfolio = _make_portfolio(
            positions_detail=[
                {"symbol": "EURUSD", "direction": "BUY"},
            ]
        )
        v = SignalValidator(correlation_checker=checker)
        # Adding BUY EURUSD → EUR exposure = +2.0, exactly at limit → passes
        valid, _ = v.validate(_make_signal(direction="BUY", symbol="EURUSD"), portfolio)
        assert valid

    def test_no_checker_passes(self):
        v = SignalValidator(correlation_checker=None)
        valid, _ = v.validate(_make_signal(), _make_portfolio())
        assert valid


# ---------------------------------------------------------------------------
# Control 10: Session classifier (real SessionClassifier + freezegun)
# ---------------------------------------------------------------------------


class TestSessionClassifier:
    @freeze_time("2026-03-21 22:00:00", tz_offset=0)
    def test_session_low_confidence_rejected(self):
        """OFF_HOURS session (22:00 UTC) penalizes confidence → rejected."""
        session_cls = SessionClassifier()
        v = SignalValidator(
            min_confidence=Decimal("0.65"),
            session_classifier=session_cls,
        )
        # OFF_HOURS boost = -0.10
        # adjusted_threshold = max(0.30, 0.65 - (-0.10)) = max(0.30, 0.75) = 0.75
        # confidence 0.70 < 0.75 → rejected
        valid, reason = v.validate(_make_signal(confidence=Decimal("0.70")), _make_portfolio())
        assert not valid
        assert "sessione" in reason

    @freeze_time("2026-03-21 14:00:00", tz_offset=0)
    def test_session_overlap_does_not_reject(self):
        """LONDON_US_OVERLAP (14:00 UTC) has positive boost → no extra penalty."""
        session_cls = SessionClassifier()
        v = SignalValidator(
            min_confidence=Decimal("0.65"),
            session_classifier=session_cls,
        )
        # LONDON_US_OVERLAP boost = +0.05
        # adjusted_threshold = max(0.30, 0.65 - 0.05) = max(0.30, 0.60) = 0.60
        # confidence 0.66 passes Control 5 (>= 0.65) AND Control 10 (>= 0.60)
        valid, _ = v.validate(_make_signal(confidence=Decimal("0.66")), _make_portfolio())
        assert valid

    def test_no_session_classifier_passes(self):
        v = SignalValidator(session_classifier=None)
        valid, _ = v.validate(_make_signal(), _make_portfolio())
        assert valid


# ---------------------------------------------------------------------------
# Control 11: Calendar filter (real EconomicCalendarFilter + freezegun)
# ---------------------------------------------------------------------------


class TestCalendarFilter:
    @freeze_time("2026-03-06 13:30:00", tz_offset=0)
    def test_blackout_period_rejected(self):
        """First Friday of March 2026 at 13:30 UTC → NFP blackout for USD pairs."""
        # 2026-03-06 is Friday (weekday=4), day=6 ≤ 7 → NFP pattern triggers
        cal = EconomicCalendarFilter(blackout_minutes_before=15, blackout_minutes_after=15)
        v = SignalValidator(calendar_filter=cal)
        valid, reason = v.validate(_make_signal(symbol="EURUSD"), _make_portfolio())
        assert not valid
        assert "Blackout" in reason

    @freeze_time("2026-03-10 10:00:00", tz_offset=0)
    def test_no_blackout_passes(self):
        """Tuesday 10:00 UTC — no economic events → passes."""
        cal = EconomicCalendarFilter(blackout_minutes_before=15, blackout_minutes_after=15)
        v = SignalValidator(calendar_filter=cal)
        valid, _ = v.validate(_make_signal(symbol="EURUSD"), _make_portfolio())
        assert valid


# ---------------------------------------------------------------------------
# Full pass-through
# ---------------------------------------------------------------------------


class TestFullValidation:
    def test_valid_signal_passes_all_controls(self):
        v = SignalValidator()
        valid, reason = v.validate(_make_signal(), _make_portfolio())
        assert valid
        assert "tutti i controlli superati" == reason

    def test_sell_signal_passes_all_controls(self):
        v = SignalValidator()
        valid, _ = v.validate(
            _make_signal(
                direction="SELL",
                entry_price=Decimal("1.10000"),
                stop_loss=Decimal("1.10500"),
                take_profit=Decimal("1.09200"),
            ),
            _make_portfolio(),
        )
        assert valid

    def test_fail_fast_on_first_control(self):
        """HOLD check should be first - skips all subsequent checks."""
        v = SignalValidator()
        valid, reason = v.validate(
            _make_signal(direction="HOLD", confidence=Decimal("0.01")),
            _make_portfolio(current_drawdown_pct="99.0"),
        )
        assert not valid
        assert "HOLD" in reason
