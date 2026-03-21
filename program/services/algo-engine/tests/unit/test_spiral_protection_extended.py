"""Extended tests for spiral_protection.py — DrawdownEnforcer + edge cases."""

import asyncio
import time
from decimal import Decimal

from algo_engine.kill_switch import KillSwitch
from algo_engine.signals.spiral_protection import DrawdownEnforcer, SpiralProtection


def _run(coro):
    return asyncio.run(coro)


class TestSpiralProtectionSizingMultiplier:
    def test_no_losses_full_size(self):
        sp = SpiralProtection(consecutive_loss_threshold=3)
        assert sp.get_sizing_multiplier() == Decimal("1.0")

    def test_below_threshold_full_size(self):
        sp = SpiralProtection(consecutive_loss_threshold=3)
        sp.record_loss()
        sp.record_loss()
        assert sp.consecutive_losses == 2
        assert sp.get_sizing_multiplier() == Decimal("1.0")

    def test_at_threshold_reduces(self):
        sp = SpiralProtection(
            consecutive_loss_threshold=3,
            size_reduction_factor=Decimal("0.5"),
        )
        sp.record_loss()
        sp.record_loss()
        sp.record_loss()
        assert sp.consecutive_losses == 3
        assert sp.get_sizing_multiplier() == Decimal("0.50")

    def test_one_over_threshold(self):
        sp = SpiralProtection(
            consecutive_loss_threshold=3,
            size_reduction_factor=Decimal("0.5"),
        )
        for _ in range(4):
            sp.record_loss()
        # 1 step over → 0.5 * 0.5 = 0.25
        assert sp.get_sizing_multiplier() == Decimal("0.25")

    def test_many_losses_floors_to_zero(self):
        sp = SpiralProtection(
            consecutive_loss_threshold=2,
            size_reduction_factor=Decimal("0.5"),
        )
        for _ in range(20):
            sp.record_loss()
        # After many halvings, multiplier < 0.01 → 0
        assert sp.get_sizing_multiplier() == Decimal("0")


class TestSpiralProtectionCooldown:
    def test_cooldown_activates_at_max(self):
        sp = SpiralProtection(
            consecutive_loss_threshold=2,
            max_consecutive_loss=3,
            cooldown_minutes=1,
        )
        sp.record_loss()
        sp.record_loss()
        sp.record_loss()
        assert sp.is_in_cooldown() is True
        assert sp.get_sizing_multiplier() == Decimal("0")

    def test_win_resets_streak(self):
        sp = SpiralProtection(consecutive_loss_threshold=3)
        sp.record_loss()
        sp.record_loss()
        sp.record_win()
        assert sp.consecutive_losses == 0
        assert sp.get_sizing_multiplier() == Decimal("1.0")

    def test_win_clears_cooldown(self):
        sp = SpiralProtection(
            consecutive_loss_threshold=2,
            max_consecutive_loss=2,
            cooldown_minutes=60,
        )
        sp.record_loss()
        sp.record_loss()
        assert sp.is_in_cooldown() is True
        sp.record_win()
        assert sp.is_in_cooldown() is False

    def test_reset_clears_everything(self):
        sp = SpiralProtection(
            consecutive_loss_threshold=2,
            max_consecutive_loss=2,
        )
        sp.record_loss()
        sp.record_loss()
        sp.reset()
        assert sp.consecutive_losses == 0
        assert sp.is_in_cooldown() is False
        assert sp.get_sizing_multiplier() == Decimal("1.0")


class TestSpiralProtectionAliasInterface:
    def test_max_consecutive_losses_alias(self):
        """The max_consecutive_losses kwarg should unify threshold and max."""
        sp = SpiralProtection(max_consecutive_losses=4)
        assert sp._threshold == 4
        assert sp._max_losses == 4


class TestSpiralProtectionRedisNoop:
    def test_no_redis_schedule_noop(self):
        """Without Redis, _schedule_persist should be a no-op."""
        sp = SpiralProtection()
        sp.record_loss()  # Should not raise

    def test_sync_without_redis_noop(self):
        sp = SpiralProtection()
        _run(sp.sync_from_redis())  # Should not raise


# ---------------------------------------------------------------------------
# DrawdownEnforcer
# ---------------------------------------------------------------------------


class TestDrawdownEnforcer:
    def test_below_threshold_no_activation(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        enforcer = DrawdownEnforcer(ks, max_drawdown_pct=Decimal("10"))
        _run(enforcer.check(
            current_equity=Decimal("9500"),
            peak_equity=Decimal("10000"),
        ))
        # 5% < 10% → no activation
        assert ks._cached_active is False

    def test_at_threshold_activates(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        enforcer = DrawdownEnforcer(ks, max_drawdown_pct=Decimal("10"))
        _run(enforcer.check(
            current_equity=Decimal("9000"),
            peak_equity=Decimal("10000"),
        ))
        # 10% >= 10% → activated
        assert ks._cached_active is True

    def test_above_threshold_activates(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        enforcer = DrawdownEnforcer(ks, max_drawdown_pct=Decimal("5"))
        _run(enforcer.check(
            current_equity=Decimal("9000"),
            peak_equity=Decimal("10000"),
        ))
        # 10% >= 5% → activated
        assert ks._cached_active is True

    def test_zero_peak_raises(self):
        ks = KillSwitch()
        enforcer = DrawdownEnforcer(ks, max_drawdown_pct=Decimal("10"))
        import pytest
        with pytest.raises(ValueError, match="peak_equity"):
            _run(enforcer.check(
                current_equity=Decimal("9000"),
                peak_equity=Decimal("0"),
            ))

    def test_negative_peak_raises(self):
        ks = KillSwitch()
        enforcer = DrawdownEnforcer(ks, max_drawdown_pct=Decimal("10"))
        import pytest
        with pytest.raises(ValueError, match="peak_equity"):
            _run(enforcer.check(
                current_equity=Decimal("9000"),
                peak_equity=Decimal("-1"),
            ))

    def test_no_drawdown(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        enforcer = DrawdownEnforcer(ks, max_drawdown_pct=Decimal("10"))
        _run(enforcer.check(
            current_equity=Decimal("10000"),
            peak_equity=Decimal("10000"),
        ))
        # 0% < 10% → no activation
        assert ks._cached_active is False
