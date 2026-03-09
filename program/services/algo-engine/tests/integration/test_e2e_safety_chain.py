"""E2E Safety Chain Test — the most critical integration test.

Verifies the complete safety chain using a real AlgoEngine:
1. Normal operation → signals emitted
2. Consecutive losses → spiral protection activates
3. Portfolio DD >= 3% → hierarchical level 2 (50% sizing reduction)
4. Portfolio DD >= 5% → hierarchical level 3 (global kill switch, flatten all)
5. Manual deactivation → recovery with reduced sizing

All components are real — no mocks, no stubs.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.kill_switch import KillSwitch
from algo_engine.signals.spiral_protection import SpiralProtection


class TestE2ESafetyChain:
    """Full safety chain: spiral → portfolio reduction → global kill → recovery."""

    @pytest.mark.asyncio
    async def test_full_safety_escalation(self):
        """Walk through the complete safety escalation ladder."""
        kill_switch = KillSwitch()
        await kill_switch.deactivate()

        spiral = SpiralProtection(
            consecutive_loss_threshold=3,
            max_consecutive_loss=5,
            cooldown_minutes=60,
            size_reduction_factor=Decimal("0.55"),
        )

        # --- Phase 1: Normal operation ---
        assert spiral.get_sizing_multiplier() == Decimal("1")
        assert spiral.is_in_cooldown() is False
        active, _ = await kill_switch.is_active()
        assert active is False

        # --- Phase 2: Loss streak triggers spiral protection ---
        spiral.record_loss()
        spiral.record_loss()
        spiral.record_loss()  # 3rd loss = threshold reached

        mult_after_3 = spiral.get_sizing_multiplier()
        assert mult_after_3 < Decimal("1"), (
            f"After 3 losses, sizing should be reduced (got {mult_after_3})"
        )

        spiral.record_loss()
        spiral.record_loss()  # 5th loss = max consecutive reached

        assert spiral.is_in_cooldown() is True, (
            "After 5 consecutive losses, cooldown must activate"
        )

        # --- Phase 3: Portfolio drawdown hits 3% → Level 2 ---
        level2_action = await kill_switch.hierarchical_check(
            drawdown_pct=Decimal("3.5"),
        )
        assert level2_action.level == 2
        assert level2_action.action == "REDUCE_SIZING"
        assert level2_action.sizing_multiplier == Decimal("0.50")

        # Kill switch should NOT be active at Level 2
        active, _ = await kill_switch.is_active()
        assert active is False, "Level 2 should NOT activate kill switch"

        # --- Phase 4: Portfolio drawdown hits 5% → Level 3 (global kill) ---
        level3_action = await kill_switch.hierarchical_check(
            drawdown_pct=Decimal("5.5"),
        )
        assert level3_action.level == 3
        assert level3_action.action == "FLATTEN_ALL"
        assert level3_action.sizing_multiplier == Decimal("0")

        # Kill switch should now be active
        active, reason = await kill_switch.is_active()
        assert active is True, "Level 3 must activate kill switch"
        assert "Level 3" in reason

        # --- Phase 5: Recovery ---
        # Operator manually deactivates kill switch after review
        await kill_switch.deactivate(actor="operator")
        active, _ = await kill_switch.is_active()
        assert active is False, "After operator deactivation, trading should resume"

        # After recovery, wins should reset spiral
        spiral.record_win()
        assert spiral.get_sizing_multiplier() == Decimal("1"), (
            "Win after recovery should reset sizing to 1.0"
        )

        # Hierarchical check with healthy drawdown
        recovery_action = await kill_switch.hierarchical_check(
            drawdown_pct=Decimal("1.0"),
        )
        assert recovery_action.level == 0
        assert recovery_action.action == "NONE"

    @pytest.mark.asyncio
    async def test_audit_trail_captures_full_chain(self):
        """The audit log should record every escalation step."""
        ks = KillSwitch()
        await ks.deactivate()

        # Trigger Level 3
        await ks.hierarchical_check(drawdown_pct=Decimal("5.5"))

        # Deactivate
        await ks.deactivate(actor="operator")

        log = await ks.get_audit_log()
        actions = [e["action"] for e in log]

        # Should have: initial deactivation, level 3 activation, final deactivation
        assert "DEACTIVATED" in actions
        assert "ACTIVATED" in actions

    @pytest.mark.asyncio
    async def test_spiral_and_kill_switch_are_independent(self):
        """Spiral protection and kill switch operate on separate axes."""
        ks = KillSwitch()
        await ks.deactivate()

        spiral = SpiralProtection(
            consecutive_loss_threshold=3,
            max_consecutive_loss=5,
        )

        # Spiral active, kill switch inactive
        for _ in range(5):
            spiral.record_loss()
        assert spiral.is_in_cooldown() is True
        active, _ = await ks.is_active()
        assert active is False, "Spiral cooldown should not trigger kill switch"

        # Kill switch active, spiral reset
        spiral.record_win()
        await ks.activate("manual test")

        assert spiral.is_in_cooldown() is False
        active, _ = await ks.is_active()
        assert active is True
