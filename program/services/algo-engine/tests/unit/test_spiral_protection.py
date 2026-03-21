"""Tests for algo_engine.signals.spiral_protection — SpiralProtection."""

import time
from decimal import Decimal

from algo_engine.signals.spiral_protection import SpiralProtection


class TestSpiralProtection:
    def test_initial_state_no_reduction(self):
        sp = SpiralProtection()
        assert sp.get_sizing_multiplier() == Decimal("1.0")
        assert sp.is_in_cooldown() is False
        assert sp.consecutive_losses == 0

    def test_win_resets_counter(self):
        sp = SpiralProtection()
        sp.record_trade_result(is_win=False)
        sp.record_trade_result(is_win=False)
        assert sp.consecutive_losses == 2
        sp.record_trade_result(is_win=True)
        assert sp.consecutive_losses == 0
        assert sp.get_sizing_multiplier() == Decimal("1.0")

    def test_three_losses_reduces_to_half(self):
        sp = SpiralProtection(consecutive_loss_threshold=3)
        for _ in range(3):
            sp.record_trade_result(is_win=False)
        assert sp.get_sizing_multiplier() == Decimal("0.5")

    def test_four_losses_reduces_to_quarter(self):
        sp = SpiralProtection(consecutive_loss_threshold=3)
        for _ in range(4):
            sp.record_trade_result(is_win=False)
        assert sp.get_sizing_multiplier() == Decimal("0.25")

    def test_five_losses_triggers_cooldown(self):
        sp = SpiralProtection(
            consecutive_loss_threshold=3,
            max_consecutive_loss=5,
            cooldown_minutes=60,
        )
        for _ in range(5):
            sp.record_trade_result(is_win=False)
        assert sp.get_sizing_multiplier() == Decimal("0")
        assert sp.is_in_cooldown() is True

    def test_cooldown_expires_after_duration(self):
        sp = SpiralProtection(
            max_consecutive_loss=3,
            cooldown_minutes=60,
        )
        for _ in range(3):
            sp.record_trade_result(is_win=False)
        assert sp.is_in_cooldown() is True

        # Fast-forward 61 minutes
        sp._cooldown_start = time.monotonic() - 3660
        assert sp.is_in_cooldown() is False
        # After cooldown expires, consecutive_losses resets to 0 (clean slate)
        # so sizing returns to full (1.0) — correct safety behavior
        assert sp.get_sizing_multiplier() == Decimal("1.0")

    def test_reset_clears_everything(self):
        sp = SpiralProtection(max_consecutive_loss=2)
        sp.record_trade_result(is_win=False)
        sp.record_trade_result(is_win=False)
        assert sp.is_in_cooldown() is True
        sp.reset()
        assert sp.consecutive_losses == 0
        assert sp.is_in_cooldown() is False
        assert sp.get_sizing_multiplier() == Decimal("1.0")

    def test_losses_below_threshold_no_reduction(self):
        sp = SpiralProtection(consecutive_loss_threshold=3)
        sp.record_trade_result(is_win=False)
        sp.record_trade_result(is_win=False)
        assert sp.get_sizing_multiplier() == Decimal("1.0")

    def test_custom_reduction_factor(self):
        sp = SpiralProtection(
            consecutive_loss_threshold=2,
            size_reduction_factor=Decimal("0.6"),
        )
        sp.record_trade_result(is_win=False)
        sp.record_trade_result(is_win=False)
        assert sp.get_sizing_multiplier() == Decimal("0.6")
