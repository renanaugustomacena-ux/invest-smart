"""Tests for BeliefState — EMA-smoothed temporal context accumulators."""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.features.belief_state import BeliefState


class TestBeliefStateBasics:
    def test_initial_beliefs_are_zero(self):
        bs = BeliefState()
        beliefs = bs.get_beliefs()
        assert beliefs.trend == Decimal("0")
        assert beliefs.momentum == Decimal("0")
        assert beliefs.regime == Decimal("0")
        assert beliefs.edge == Decimal("0")

    def test_update_count_increments(self):
        bs = BeliefState()
        assert bs.update_count == 0
        bs.update(trend_score=Decimal("0.5"))
        assert bs.update_count == 1
        bs.update(trend_score=Decimal("0.5"))
        assert bs.update_count == 2


class TestEMAConvergence:
    def test_trend_converges_toward_input(self):
        """With constant input, EMA should converge toward that value."""
        bs = BeliefState(alpha=Decimal("0.20"))
        for _ in range(50):
            bs.update(trend_score=Decimal("0.80"))

        beliefs = bs.get_beliefs()
        assert beliefs.trend > Decimal(
            "0.75"
        ), f"After 50 updates of 0.80, trend should converge near 0.80, got {beliefs.trend}"

    def test_momentum_converges_toward_negative(self):
        bs = BeliefState(alpha=Decimal("0.20"))
        for _ in range(50):
            bs.update(momentum_score=Decimal("-0.60"))

        beliefs = bs.get_beliefs()
        assert beliefs.momentum < Decimal(
            "-0.55"
        ), f"Should converge near -0.60, got {beliefs.momentum}"

    def test_higher_alpha_converges_faster(self):
        slow = BeliefState(alpha=Decimal("0.05"))
        fast = BeliefState(alpha=Decimal("0.30"))

        for _ in range(10):
            slow.update(trend_score=Decimal("1"))
            fast.update(trend_score=Decimal("1"))

        # Fast alpha should be closer to 1.0 after 10 updates
        assert fast.get_beliefs().trend > slow.get_beliefs().trend

    def test_direction_reversal(self):
        """Beliefs should track direction changes over time."""
        bs = BeliefState(alpha=Decimal("0.15"))

        # Bullish for 20 bars
        for _ in range(20):
            bs.update(trend_score=Decimal("0.80"))
        assert bs.get_beliefs().trend > Decimal("0.5")

        # Then bearish for 30 bars
        for _ in range(30):
            bs.update(trend_score=Decimal("-0.80"))
        assert bs.get_beliefs().trend < Decimal(
            "-0.3"
        ), f"Trend should flip negative, got {bs.get_beliefs().trend}"


class TestEdgeBelief:
    def test_wins_increase_edge(self):
        bs = BeliefState(alpha=Decimal("0.15"))
        for _ in range(10):
            bs.update(trade_outcome=Decimal("1"))
        assert bs.get_beliefs().edge > Decimal("0.5")

    def test_losses_decrease_edge(self):
        bs = BeliefState(alpha=Decimal("0.15"))
        for _ in range(10):
            bs.update(trade_outcome=Decimal("-1"))
        assert bs.get_beliefs().edge < Decimal("-0.5")

    def test_no_outcome_preserves_edge(self):
        bs = BeliefState(alpha=Decimal("0.15"))
        bs.update(trade_outcome=Decimal("1"))
        edge_after_win = bs.get_beliefs().edge
        bs.update()  # no trade outcome
        assert bs.get_beliefs().edge == edge_after_win

    def test_mixed_outcomes(self):
        bs = BeliefState(alpha=Decimal("0.15"))
        for _ in range(5):
            bs.update(trade_outcome=Decimal("1"))
        for _ in range(5):
            bs.update(trade_outcome=Decimal("-1"))
        # Edge should be modestly negative (EMA recency bias toward recent losses)
        edge = bs.get_beliefs().edge
        assert abs(edge) < Decimal("0.5"), f"Edge too extreme after mixed outcomes: {edge}"


class TestBoundedness:
    def test_beliefs_never_exceed_bounds(self):
        bs = BeliefState(alpha=Decimal("0.50"))
        for _ in range(100):
            bs.update(
                trend_score=Decimal("5"),  # way above +1
                momentum_score=Decimal("-5"),  # way below -1
                regime_confidence=Decimal("3"),
                trade_outcome=Decimal("10"),
            )
        beliefs = bs.get_beliefs()
        assert Decimal("-1") <= beliefs.trend <= Decimal("1")
        assert Decimal("-1") <= beliefs.momentum <= Decimal("1")
        assert Decimal("-1") <= beliefs.regime <= Decimal("1")
        assert Decimal("-1") <= beliefs.edge <= Decimal("1")
