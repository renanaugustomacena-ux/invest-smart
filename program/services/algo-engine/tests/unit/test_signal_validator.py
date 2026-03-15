"""Tests for SignalValidator — the risk gate before MT5 execution."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

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
# Control 5b: Spread percentile tracker
# ---------------------------------------------------------------------------


class TestSpreadPercentile:
    def test_spread_rejected_by_tracker(self):
        tracker = MagicMock()
        tracker.check.return_value = (False, "spread at 95th percentile")
        v = SignalValidator(spread_tracker=tracker)
        valid, reason = v.validate(
            _make_signal(spread=Decimal("3.5"), symbol="EURUSD"),
            _make_portfolio(),
        )
        assert not valid
        assert "95th" in reason

    def test_spread_accepted_by_tracker(self):
        tracker = MagicMock()
        tracker.check.return_value = (True, "ok")
        v = SignalValidator(spread_tracker=tracker)
        valid, _ = v.validate(_make_signal(spread=Decimal("1.2")), _make_portfolio())
        assert valid

    def test_zero_spread_skips_tracker(self):
        tracker = MagicMock()
        v = SignalValidator(spread_tracker=tracker)
        valid, _ = v.validate(_make_signal(spread=Decimal("0")), _make_portfolio())
        assert valid
        tracker.check.assert_not_called()

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
                take_profit=Decimal("1.09000"),
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
# Control 9: Correlation checker
# ---------------------------------------------------------------------------


class TestCorrelationChecker:
    def test_correlation_rejected(self):
        checker = MagicMock()
        checker.check.return_value = (False, "EUR exposure too high")
        v = SignalValidator(correlation_checker=checker)
        valid, reason = v.validate(_make_signal(), _make_portfolio())
        assert not valid
        assert "EUR" in reason

    def test_correlation_passes(self):
        checker = MagicMock()
        checker.check.return_value = (True, "ok")
        v = SignalValidator(correlation_checker=checker)
        valid, _ = v.validate(_make_signal(), _make_portfolio())
        assert valid

    def test_no_checker_passes(self):
        v = SignalValidator(correlation_checker=None)
        valid, _ = v.validate(_make_signal(), _make_portfolio())
        assert valid


# ---------------------------------------------------------------------------
# Control 10: Session classifier
# ---------------------------------------------------------------------------


class TestSessionClassifier:
    def test_session_low_confidence_rejected(self):
        from enum import Enum

        class MockSession(Enum):
            OFF_HOURS = "OFF_HOURS"

        session_cls = MagicMock()
        session_cls.classify.return_value = MockSession.OFF_HOURS
        session_cls.get_confidence_boost.return_value = Decimal("-0.20")

        v = SignalValidator(
            min_confidence=Decimal("0.65"),
            session_classifier=session_cls,
        )
        # Adjusted threshold: max(0.30, 0.65 - (-0.20)) = max(0.30, 0.85) = 0.85
        # Confidence 0.70 < 0.85 -> rejected
        valid, reason = v.validate(_make_signal(confidence=Decimal("0.70")), _make_portfolio())
        assert not valid
        assert "sessione" in reason

    def test_no_session_classifier_passes(self):
        v = SignalValidator(session_classifier=None)
        valid, _ = v.validate(_make_signal(), _make_portfolio())
        assert valid


# ---------------------------------------------------------------------------
# Control 11: Calendar filter
# ---------------------------------------------------------------------------


class TestCalendarFilter:
    def test_blackout_period_rejected(self):
        cal = MagicMock()
        cal.is_blackout.return_value = True
        v = SignalValidator(calendar_filter=cal)
        valid, reason = v.validate(_make_signal(), _make_portfolio())
        assert not valid
        assert "Blackout" in reason

    def test_no_blackout_passes(self):
        cal = MagicMock()
        cal.is_blackout.return_value = False
        v = SignalValidator(calendar_filter=cal)
        valid, _ = v.validate(_make_signal(), _make_portfolio())
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
