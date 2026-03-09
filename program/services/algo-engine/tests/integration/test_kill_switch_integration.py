"""Integration test: kill switch blocks all signal emission.

Verifies that when the kill switch is active (local mode), the main
loop in main.py would skip process_bar entirely. Since we test the
KillSwitch independently here, we verify its state transitions and
their effect on the engine via the is_active() check.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from algo_engine.kill_switch import KillSwitch

from .conftest import build_engine, _make_xauusd_bars


class TestKillSwitchBlocking:
    """Kill switch must block trading when active."""

    @pytest.mark.asyncio
    async def test_kill_switch_starts_fail_closed(self):
        """Without connect(), kill switch defaults to active (fail-closed)."""
        ks = KillSwitch()
        active, reason = await ks.is_active()
        assert active is True, "Kill switch must default to active (fail-closed)"

    @pytest.mark.asyncio
    async def test_deactivated_kill_switch_allows_trading(self):
        """After deactivation, is_active() returns False."""
        ks = KillSwitch()
        await ks.deactivate()
        active, _ = await ks.is_active()
        assert active is False

    @pytest.mark.asyncio
    async def test_activated_kill_switch_blocks_signals(self):
        """With kill switch active, the engine check should report active."""
        ks = KillSwitch()
        await ks.deactivate()
        await ks.activate("Integration test: manual activation")
        active, reason = await ks.is_active()
        assert active is True
        assert "manual activation" in reason

    @pytest.mark.asyncio
    async def test_auto_check_activates_on_daily_loss(self):
        """auto_check() triggers when daily loss exceeds limit."""
        ks = KillSwitch()
        await ks.deactivate()

        await ks.auto_check(
            daily_loss_pct=Decimal("2.5"),
            max_daily_loss_pct=Decimal("2.0"),
            drawdown_pct=Decimal("1.0"),
            max_drawdown_pct=Decimal("5.0"),
        )

        active, reason = await ks.is_active()
        assert active is True
        assert "giornaliera" in reason.lower() or "daily" in reason.lower()

    @pytest.mark.asyncio
    async def test_auto_check_activates_on_drawdown(self):
        """auto_check() triggers when drawdown exceeds limit."""
        ks = KillSwitch()
        await ks.deactivate()

        await ks.auto_check(
            daily_loss_pct=Decimal("0.5"),
            max_daily_loss_pct=Decimal("2.0"),
            drawdown_pct=Decimal("5.5"),
            max_drawdown_pct=Decimal("5.0"),
        )

        active, reason = await ks.is_active()
        assert active is True
        assert "drawdown" in reason.lower()

    @pytest.mark.asyncio
    async def test_audit_log_records_activations(self):
        """Every activation/deactivation should be recorded in audit log."""
        ks = KillSwitch()
        await ks.deactivate()
        await ks.activate("test reason")
        await ks.deactivate()

        log = await ks.get_audit_log()
        actions = [entry["action"] for entry in log]
        assert "ACTIVATED" in actions
        assert "DEACTIVATED" in actions
