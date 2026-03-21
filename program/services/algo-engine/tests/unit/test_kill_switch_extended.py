"""Extended tests for kill_switch.py — hierarchical check + audit log + edge cases."""

import asyncio
from decimal import Decimal

from algo_engine.kill_switch import (
    HierarchicalAction,
    KillSwitch,
    KillSwitchAuditEntry,
)


def _run(coro):
    return asyncio.run(coro)


class TestHierarchicalCheck:
    """Tests for the 3-level hierarchical risk escalation."""

    def test_level0_all_within_limits(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        result = _run(ks.hierarchical_check(drawdown_pct=Decimal("1.0")))
        assert result.level == 0
        assert result.action == "NONE"
        assert result.sizing_multiplier == Decimal("1")
        assert result.pause_strategy is None

    def test_level1_strategy_pause(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        result = _run(
            ks.hierarchical_check(
                drawdown_pct=Decimal("2.0"),
                strategy_name="momentum_v1",
                strategy_dd_pct=Decimal("6.0"),
            )
        )
        assert result.level == 1
        assert result.action == "PAUSE_STRATEGY"
        assert result.sizing_multiplier == Decimal("1")
        assert result.pause_strategy == "momentum_v1"

    def test_level1_strategy_below_threshold(self):
        """Strategy DD < 5% → no pause, level 0."""
        ks = KillSwitch()
        _run(ks.deactivate())
        result = _run(
            ks.hierarchical_check(
                drawdown_pct=Decimal("2.0"),
                strategy_name="momentum_v1",
                strategy_dd_pct=Decimal("4.5"),
            )
        )
        assert result.level == 0
        assert result.action == "NONE"

    def test_level2_portfolio_reduction(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        result = _run(ks.hierarchical_check(drawdown_pct=Decimal("3.5")))
        assert result.level == 2
        assert result.action == "REDUCE_SIZING"
        assert result.sizing_multiplier == Decimal("0.50")

    def test_level2_at_boundary(self):
        """Exactly 3% → level 2."""
        ks = KillSwitch()
        _run(ks.deactivate())
        result = _run(ks.hierarchical_check(drawdown_pct=Decimal("3")))
        assert result.level == 2
        assert result.action == "REDUCE_SIZING"

    def test_level3_global_kill(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        result = _run(ks.hierarchical_check(drawdown_pct=Decimal("5.0")))
        assert result.level == 3
        assert result.action == "FLATTEN_ALL"
        assert result.sizing_multiplier == Decimal("0")

    def test_level3_extreme_drawdown(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        result = _run(ks.hierarchical_check(drawdown_pct=Decimal("15.0")))
        assert result.level == 3
        assert result.action == "FLATTEN_ALL"

    def test_level3_overrides_level1(self):
        """Portfolio DD > 5% takes priority even if strategy also breached."""
        ks = KillSwitch()
        _run(ks.deactivate())
        result = _run(
            ks.hierarchical_check(
                drawdown_pct=Decimal("6.0"),
                strategy_name="momentum_v1",
                strategy_dd_pct=Decimal("8.0"),
            )
        )
        assert result.level == 3
        assert result.action == "FLATTEN_ALL"

    def test_level2_overrides_level1(self):
        """Portfolio DD > 3% takes priority over strategy pause."""
        ks = KillSwitch()
        _run(ks.deactivate())
        result = _run(
            ks.hierarchical_check(
                drawdown_pct=Decimal("3.5"),
                strategy_name="momentum_v1",
                strategy_dd_pct=Decimal("6.0"),
            )
        )
        assert result.level == 2
        assert result.action == "REDUCE_SIZING"


class TestKillSwitchAudit:
    """Tests for audit log persistence without Redis."""

    def test_audit_log_grows(self):
        ks = KillSwitch()
        _run(ks.activate("Test reason"))
        assert len(ks._audit_log) >= 1
        assert ks._audit_log[-1].action == "ACTIVATED"

    def test_deactivate_creates_audit_entry(self):
        ks = KillSwitch()
        _run(ks.activate("Test"))
        _run(ks.deactivate())
        actions = [e.action for e in ks._audit_log]
        assert "DEACTIVATED" in actions

    def test_get_audit_log_local_fallback(self):
        ks = KillSwitch()
        _run(ks.activate("Test reason"))
        log = _run(ks.get_audit_log(limit=10))
        assert len(log) >= 1
        assert log[-1]["action"] == "ACTIVATED"
        assert log[-1]["reason"] == "Test reason"

    def test_audit_trim(self):
        """Audit log should trim beyond MAX_AUDIT_ENTRIES."""
        ks = KillSwitch()
        ks._MAX_AUDIT_ENTRIES = 5  # Override for test
        for i in range(10):
            _run(ks.activate(f"Reason {i}"))
        assert len(ks._audit_log) <= 5

    def test_auto_check_creates_audit_entries(self):
        ks = KillSwitch()
        _run(
            ks.auto_check(
                daily_loss_pct=Decimal("3.0"),
                max_daily_loss_pct=Decimal("2.0"),
                drawdown_pct=Decimal("1.0"),
                max_drawdown_pct=Decimal("5.0"),
            )
        )
        actions = [e.action for e in ks._audit_log]
        assert "AUTO_CHECK_TRIGGERED" in actions


class TestKillSwitchEdgeCases:
    """Edge cases for is_active, check_or_raise, cache TTL."""

    def test_fail_closed_default(self):
        """New KillSwitch should fail-closed (active=True) before connect."""
        ks = KillSwitch()
        assert ks._cached_active is True

    def test_is_active_returns_cached_within_ttl(self):
        ks = KillSwitch(cache_ttl=100.0)  # Very long TTL
        _run(ks.deactivate())  # Sets cache
        active, reason = _run(ks.is_active())
        assert active is False

    def test_check_or_raise_when_active(self):
        from moneymaker_common.exceptions import RiskLimitExceededError

        ks = KillSwitch()
        _run(ks.activate("Emergency"))
        try:
            _run(ks.check_or_raise())
            assert False, "Should have raised"
        except RiskLimitExceededError as e:
            assert "Emergency" in str(e)

    def test_check_or_raise_when_inactive(self):
        ks = KillSwitch(cache_ttl=100.0)
        _run(ks.deactivate())
        # Should not raise
        _run(ks.check_or_raise())

    def test_auto_check_drawdown_triggers(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        _run(
            ks.auto_check(
                daily_loss_pct=Decimal("1.0"),
                max_daily_loss_pct=Decimal("5.0"),
                drawdown_pct=Decimal("6.0"),
                max_drawdown_pct=Decimal("5.0"),
            )
        )
        assert ks._cached_active is True

    def test_auto_check_safe(self):
        ks = KillSwitch()
        _run(ks.deactivate())
        _run(
            ks.auto_check(
                daily_loss_pct=Decimal("1.0"),
                max_daily_loss_pct=Decimal("5.0"),
                drawdown_pct=Decimal("2.0"),
                max_drawdown_pct=Decimal("5.0"),
            )
        )
        assert ks._cached_active is False


class TestHierarchicalActionDataclass:
    def test_fields(self):
        action = HierarchicalAction(
            level=2,
            action="REDUCE_SIZING",
            sizing_multiplier=Decimal("0.50"),
            reason="test",
            pause_strategy=None,
        )
        assert action.level == 2
        assert action.action == "REDUCE_SIZING"
        assert action.sizing_multiplier == Decimal("0.50")

    def test_audit_entry_defaults(self):
        entry = KillSwitchAuditEntry(
            timestamp=1234567890.0,
            action="ACTIVATED",
            reason="test",
        )
        assert entry.actor == "system"
        assert entry.daily_loss_pct == ""
        assert entry.drawdown_pct == ""
