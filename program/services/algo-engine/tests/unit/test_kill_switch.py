"""Tests for algo_engine.kill_switch — KillSwitch."""

from decimal import Decimal

import pytest

from algo_engine.kill_switch import KillSwitch


class TestKillSwitch:
    def test_constructor_accepts_only_redis_url(self):
        """KillSwitch constructor only takes redis_url, not risk params."""
        ks = KillSwitch(redis_url="redis://localhost:6379")
        assert ks._redis_url == "redis://localhost:6379"

    def test_constructor_rejects_unexpected_kwargs(self):
        """Passing max_daily_loss_pct to constructor must raise TypeError."""
        with pytest.raises(TypeError):
            KillSwitch(
                redis_url="redis://localhost:6379",
                max_daily_loss_pct=Decimal("2.0"),
                max_drawdown_pct=Decimal("5.0"),
            )

    @pytest.mark.asyncio
    async def test_auto_check_activates_on_critical_daily_loss(self):
        """auto_check should activate when daily_loss >= 2x limit."""
        ks = KillSwitch()
        await ks.auto_check(
            daily_loss_pct=Decimal("4.5"),
            max_daily_loss_pct=Decimal("2.0"),
            drawdown_pct=Decimal("1.0"),
            max_drawdown_pct=Decimal("5.0"),
        )
        active, reason = await ks.is_active()
        assert active is True
        assert "giornaliera" in reason.lower()

    @pytest.mark.asyncio
    async def test_auto_check_activates_on_max_drawdown(self):
        """auto_check should activate when drawdown >= limit."""
        ks = KillSwitch()
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
    async def test_auto_check_does_not_activate_within_limits(self):
        """auto_check should NOT activate when within limits."""
        ks = KillSwitch()
        await ks.deactivate()  # Reset fail-closed default (no Redis)
        await ks.auto_check(
            daily_loss_pct=Decimal("1.0"),
            max_daily_loss_pct=Decimal("2.0"),
            drawdown_pct=Decimal("3.0"),
            max_drawdown_pct=Decimal("5.0"),
        )
        active, _ = await ks.is_active()
        assert active is False

    @pytest.mark.asyncio
    async def test_activate_deactivate_cycle(self):
        """Activate then deactivate should return to inactive."""
        ks = KillSwitch()
        await ks.activate("test reason")
        active, reason = await ks.is_active()
        assert active is True
        assert reason == "test reason"

        await ks.deactivate()
        active, _ = await ks.is_active()
        assert active is False
