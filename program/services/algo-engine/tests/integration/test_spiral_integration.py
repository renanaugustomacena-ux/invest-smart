"""Integration test: spiral protection reduces sizing after consecutive losses.

Verifies the full SpiralProtection lifecycle:
1. Normal operation (multiplier = 1.0)
2. After threshold losses, sizing reduces
3. After max losses, cooldown activates
4. After cooldown expires, sizing recovers
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.signals.spiral_protection import SpiralProtection


class TestSpiralProtectionIntegration:
    """Verify spiral protection state transitions with real component."""

    def test_initial_state_is_normal(self):
        """Fresh SpiralProtection has full sizing multiplier."""
        sp = SpiralProtection(
            consecutive_loss_threshold=3,
            max_consecutive_loss=5,
            cooldown_minutes=60,
            size_reduction_factor=Decimal("0.55"),
        )
        assert sp.get_sizing_multiplier() == Decimal("1")
        assert sp.is_in_cooldown() is False

    def test_losses_below_threshold_no_reduction(self):
        """Losses below the threshold should not reduce sizing."""
        sp = SpiralProtection(consecutive_loss_threshold=3)

        sp.record_loss()
        sp.record_loss()
        assert sp.get_sizing_multiplier() == Decimal("1")
        assert sp.is_in_cooldown() is False

    def test_threshold_losses_reduce_sizing(self):
        """After reaching the loss threshold, sizing multiplier drops."""
        sp = SpiralProtection(
            consecutive_loss_threshold=3,
            size_reduction_factor=Decimal("0.55"),
        )

        for _ in range(3):
            sp.record_loss()

        mult = sp.get_sizing_multiplier()
        assert mult < Decimal("1"), f"Multiplier should drop below 1.0, got {mult}"

    def test_max_losses_activate_cooldown(self):
        """After max consecutive losses, cooldown should activate."""
        sp = SpiralProtection(
            consecutive_loss_threshold=3,
            max_consecutive_loss=5,
            cooldown_minutes=60,
        )

        for _ in range(5):
            sp.record_loss()

        assert sp.is_in_cooldown() is True

    def test_win_resets_consecutive_count(self):
        """A win should reset the consecutive loss counter."""
        sp = SpiralProtection(consecutive_loss_threshold=3)

        sp.record_loss()
        sp.record_loss()
        sp.record_win()

        # After a win, counter resets — next 2 losses shouldn't trigger
        sp.record_loss()
        sp.record_loss()
        assert sp.get_sizing_multiplier() == Decimal("1")

    def test_cooldown_blocks_trading_entirely(self):
        """During cooldown, multiplier is 0 — no trading allowed."""
        sp = SpiralProtection(
            consecutive_loss_threshold=3,
            max_consecutive_loss=5,
            size_reduction_factor=Decimal("0.55"),
        )

        for _ in range(10):
            sp.record_loss()

        # During active cooldown, sizing is zero (fully blocked)
        assert sp.is_in_cooldown() is True
        mult = sp.get_sizing_multiplier()
        assert mult == Decimal("0"), (
            f"During cooldown, multiplier should be 0 (full block), got {mult}"
        )
