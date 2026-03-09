"""Tests for MaturityGate state machine and ConvictionIndex scorer."""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.maturity_gate import (
    ConvictionIndex,
    ConvictionSnapshot,
    MaturityGate,
    MaturityState,
    STATE_MULTIPLIERS,
)


# ---- ConvictionIndex tests ----

class TestConvictionIndex:
    def test_perfect_metrics(self):
        ci = ConvictionIndex()
        snap = ci.compute(
            win_rate=Decimal("1.0"),
            sharpe_ratio=Decimal("3.0"),
            profit_factor=Decimal("3.0"),
            drawdown_pct=Decimal("0"),
        )
        assert snap.conviction_index == Decimal("1.0000")

    def test_worst_metrics(self):
        ci = ConvictionIndex()
        snap = ci.compute(
            win_rate=Decimal("0"),
            sharpe_ratio=Decimal("0"),
            profit_factor=Decimal("0"),
            drawdown_pct=Decimal("100"),
        )
        assert snap.conviction_index == Decimal("0.0000")

    def test_moderate_metrics(self):
        ci = ConvictionIndex()
        snap = ci.compute(
            win_rate=Decimal("0.55"),
            sharpe_ratio=Decimal("1.5"),
            profit_factor=Decimal("1.8"),
            drawdown_pct=Decimal("10"),
        )
        # 0.35*0.55 + 0.30*0.50 + 0.20*0.40 + 0.15*0.90
        # = 0.1925 + 0.15 + 0.08 + 0.135 = 0.5575
        assert abs(snap.conviction_index - Decimal("0.5575")) < Decimal("0.001")

    def test_sharpe_clamped_above_3(self):
        ci = ConvictionIndex()
        snap = ci.compute(
            win_rate=Decimal("0.5"),
            sharpe_ratio=Decimal("10.0"),
            profit_factor=Decimal("2.0"),
            drawdown_pct=Decimal("5"),
        )
        assert snap.sharpe_norm == Decimal("1")

    def test_negative_sharpe_clamped_to_zero(self):
        ci = ConvictionIndex()
        snap = ci.compute(
            win_rate=Decimal("0.5"),
            sharpe_ratio=Decimal("-2.0"),
            profit_factor=Decimal("2.0"),
            drawdown_pct=Decimal("5"),
        )
        assert snap.sharpe_norm == Decimal("0")

    def test_profit_factor_below_one(self):
        ci = ConvictionIndex()
        snap = ci.compute(
            win_rate=Decimal("0.4"),
            sharpe_ratio=Decimal("0.5"),
            profit_factor=Decimal("0.8"),
            drawdown_pct=Decimal("20"),
        )
        assert snap.profit_factor_norm == Decimal("0")

    def test_output_bounded(self):
        ci = ConvictionIndex()
        for wr in (Decimal("0"), Decimal("0.5"), Decimal("1.5")):
            for sr in (Decimal("-5"), Decimal("0"), Decimal("10")):
                for pf in (Decimal("0"), Decimal("1.5"), Decimal("50")):
                    for dd in (Decimal("0"), Decimal("50"), Decimal("200")):
                        snap = ci.compute(wr, sr, pf, dd)
                        assert Decimal("0") <= snap.conviction_index <= Decimal("1"), (
                            f"Out of bounds: {snap.conviction_index}"
                        )

    def test_returns_frozen_snapshot(self):
        ci = ConvictionIndex()
        snap = ci.compute(Decimal("0.5"), Decimal("1"), Decimal("1.5"), Decimal("5"))
        assert isinstance(snap, ConvictionSnapshot)
        with pytest.raises(AttributeError):
            snap.conviction_index = Decimal("0")  # type: ignore[misc]


# ---- MaturityGate state machine tests ----

class TestMaturityGateInitial:
    def test_starts_in_doubt(self):
        mg = MaturityGate()
        assert mg.state == MaturityState.DOUBT
        assert mg.sizing_multiplier == Decimal("0.05")
        assert mg.check_count == 0

    def test_custom_initial_state(self):
        mg = MaturityGate(initial_state=MaturityState.CONVICTION)
        assert mg.state == MaturityState.CONVICTION
        assert mg.sizing_multiplier == Decimal("0.80")


class TestMaturityPromotion:
    def test_promote_after_3_positive(self):
        mg = MaturityGate(promote_threshold=Decimal("0.60"), promote_count=3)
        for _ in range(3):
            mg.evaluate(Decimal("0.70"))
        assert mg.state == MaturityState.LEARNING

    def test_promote_twice_to_conviction(self):
        mg = MaturityGate(promote_threshold=Decimal("0.60"), promote_count=3)
        for _ in range(6):
            mg.evaluate(Decimal("0.70"))
        assert mg.state == MaturityState.CONVICTION

    def test_promote_three_times_to_mature(self):
        mg = MaturityGate(promote_threshold=Decimal("0.60"), promote_count=3)
        for _ in range(9):
            mg.evaluate(Decimal("0.70"))
        assert mg.state == MaturityState.MATURE

    def test_cannot_promote_past_mature(self):
        mg = MaturityGate(promote_threshold=Decimal("0.60"), promote_count=3)
        for _ in range(15):
            mg.evaluate(Decimal("0.70"))
        assert mg.state == MaturityState.MATURE

    def test_interrupted_promotion_resets(self):
        """A value in the neutral zone resets the consecutive counter."""
        mg = MaturityGate(promote_threshold=Decimal("0.60"), promote_count=3)
        mg.evaluate(Decimal("0.70"))
        mg.evaluate(Decimal("0.70"))
        mg.evaluate(Decimal("0.45"))  # neutral zone — resets
        mg.evaluate(Decimal("0.70"))
        mg.evaluate(Decimal("0.70"))
        # Only 2 consecutive after reset — no promotion yet
        assert mg.state == MaturityState.DOUBT


class TestMaturityDemotion:
    def test_demote_after_2_negative(self):
        mg = MaturityGate(
            demote_threshold=Decimal("0.35"),
            demote_count=2,
            initial_state=MaturityState.LEARNING,
        )
        for _ in range(2):
            mg.evaluate(Decimal("0.20"))
        assert mg.state == MaturityState.DOUBT

    def test_demote_from_mature(self):
        mg = MaturityGate(
            demote_threshold=Decimal("0.35"),
            demote_count=2,
            initial_state=MaturityState.MATURE,
        )
        for _ in range(2):
            mg.evaluate(Decimal("0.10"))
        assert mg.state == MaturityState.CONVICTION

    def test_cannot_demote_past_doubt(self):
        mg = MaturityGate(
            demote_threshold=Decimal("0.35"),
            demote_count=2,
            initial_state=MaturityState.DOUBT,
        )
        for _ in range(10):
            mg.evaluate(Decimal("0.10"))
        assert mg.state == MaturityState.DOUBT


class TestMaturityHysteresis:
    def test_neutral_zone_no_transition(self):
        """Values between thresholds cause no state change."""
        mg = MaturityGate(
            promote_threshold=Decimal("0.60"),
            demote_threshold=Decimal("0.35"),
            initial_state=MaturityState.LEARNING,
        )
        for _ in range(20):
            mg.evaluate(Decimal("0.45"))
        assert mg.state == MaturityState.LEARNING

    def test_alternating_values_no_transition(self):
        """Alternating high/low values never accumulate enough for transition."""
        mg = MaturityGate(
            promote_threshold=Decimal("0.60"),
            demote_threshold=Decimal("0.35"),
            promote_count=3,
            demote_count=2,
        )
        for _ in range(20):
            mg.evaluate(Decimal("0.70"))
            mg.evaluate(Decimal("0.20"))
        assert mg.state == MaturityState.DOUBT

    def test_full_lifecycle(self):
        """DOUBT → promote → LEARNING → promote → CONVICTION → demote → LEARNING."""
        mg = MaturityGate(
            promote_threshold=Decimal("0.60"),
            demote_threshold=Decimal("0.35"),
            promote_count=3,
            demote_count=2,
        )
        # DOUBT → LEARNING
        for _ in range(3):
            mg.evaluate(Decimal("0.70"))
        assert mg.state == MaturityState.LEARNING

        # LEARNING → CONVICTION
        for _ in range(3):
            mg.evaluate(Decimal("0.75"))
        assert mg.state == MaturityState.CONVICTION

        # CONVICTION → LEARNING (demotion)
        for _ in range(2):
            mg.evaluate(Decimal("0.10"))
        assert mg.state == MaturityState.LEARNING


class TestForceState:
    def test_force_overrides_state(self):
        mg = MaturityGate()
        mg.force_state(MaturityState.MATURE)
        assert mg.state == MaturityState.MATURE
        assert mg.sizing_multiplier == Decimal("1.00")

    def test_force_resets_counters(self):
        mg = MaturityGate(promote_count=3)
        mg.evaluate(Decimal("0.70"))
        mg.evaluate(Decimal("0.70"))
        mg.force_state(MaturityState.DOUBT)
        # Counter reset — one more positive shouldn't promote
        mg.evaluate(Decimal("0.70"))
        assert mg.state == MaturityState.DOUBT


class TestStateMultipliers:
    def test_all_states_have_multipliers(self):
        for state in MaturityState:
            assert state in STATE_MULTIPLIERS
            assert Decimal("0") <= STATE_MULTIPLIERS[state] <= Decimal("1")

    def test_multipliers_monotonic(self):
        """Higher states must have higher or equal multipliers."""
        vals = [STATE_MULTIPLIERS[s] for s in [
            MaturityState.DOUBT, MaturityState.LEARNING,
            MaturityState.CONVICTION, MaturityState.MATURE,
        ]]
        for i in range(len(vals) - 1):
            assert vals[i] < vals[i + 1]


class TestCheckCount:
    def test_increments_on_evaluate(self):
        mg = MaturityGate()
        assert mg.check_count == 0
        mg.evaluate(Decimal("0.50"))
        assert mg.check_count == 1
        mg.evaluate(Decimal("0.50"))
        assert mg.check_count == 2
