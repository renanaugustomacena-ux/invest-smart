"""Integration test: hierarchical kill switch drawdown enforcement.

Verifies the 3-level hierarchical risk escalation:
- Level 1 (strategy DD >= 5%): pause that strategy
- Level 2 (portfolio DD >= 3%): reduce sizing by 50%
- Level 3 (portfolio DD >= 5%): flatten all, activate global kill switch
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.kill_switch import KillSwitch


class TestDrawdownEnforcement:
    """Verify hierarchical kill switch escalation levels."""

    @pytest.mark.asyncio
    async def test_no_action_within_limits(self):
        """Below all thresholds, no action should be taken."""
        ks = KillSwitch()
        await ks.deactivate()

        action = await ks.hierarchical_check(drawdown_pct=Decimal("1.5"))
        assert action.level == 0
        assert action.action == "NONE"
        assert action.sizing_multiplier == Decimal("1")

    @pytest.mark.asyncio
    async def test_level1_strategy_pause(self):
        """Strategy DD >= 5% should pause that specific strategy."""
        ks = KillSwitch()
        await ks.deactivate()

        action = await ks.hierarchical_check(
            drawdown_pct=Decimal("2.0"),
            strategy_name="trend_following",
            strategy_dd_pct=Decimal("6.0"),
        )
        assert action.level == 1
        assert action.action == "PAUSE_STRATEGY"
        assert action.pause_strategy == "trend_following"
        assert action.sizing_multiplier == Decimal("1")

    @pytest.mark.asyncio
    async def test_level2_portfolio_reduction(self):
        """Portfolio DD >= 3% should reduce sizing by 50%."""
        ks = KillSwitch()
        await ks.deactivate()

        action = await ks.hierarchical_check(drawdown_pct=Decimal("3.5"))
        assert action.level == 2
        assert action.action == "REDUCE_SIZING"
        assert action.sizing_multiplier == Decimal("0.50")

    @pytest.mark.asyncio
    async def test_level3_global_kill(self):
        """Portfolio DD >= 5% should flatten all and activate kill switch."""
        ks = KillSwitch()
        await ks.deactivate()

        action = await ks.hierarchical_check(drawdown_pct=Decimal("5.5"))
        assert action.level == 3
        assert action.action == "FLATTEN_ALL"
        assert action.sizing_multiplier == Decimal("0")

        # Kill switch should now be active
        active, reason = await ks.is_active()
        assert active is True
        assert "Level 3" in reason

    @pytest.mark.asyncio
    async def test_level3_overrides_level1(self):
        """Level 3 (global) takes priority over Level 1 (strategy)."""
        ks = KillSwitch()
        await ks.deactivate()

        action = await ks.hierarchical_check(
            drawdown_pct=Decimal("6.0"),
            strategy_name="mean_reversion",
            strategy_dd_pct=Decimal("8.0"),
        )
        # Level 3 fires first (portfolio DD >= 5%)
        assert action.level == 3
        assert action.action == "FLATTEN_ALL"

    @pytest.mark.asyncio
    async def test_recovery_after_deactivation(self):
        """After kill switch deactivation, trading should resume."""
        ks = KillSwitch()
        await ks.deactivate()

        # Trigger level 3
        await ks.hierarchical_check(drawdown_pct=Decimal("5.5"))
        active, _ = await ks.is_active()
        assert active is True

        # Manual deactivation (operator recovery)
        await ks.deactivate()
        active, _ = await ks.is_active()
        assert active is False

        # Normal check after recovery
        action = await ks.hierarchical_check(drawdown_pct=Decimal("1.0"))
        assert action.level == 0
        assert action.action == "NONE"
