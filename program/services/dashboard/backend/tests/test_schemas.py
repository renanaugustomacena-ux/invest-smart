# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Comprehensive tests for dashboard Pydantic response schemas.

Covers default values, required field enforcement, optional fields,
full construction, and JSON serialization round-trips for every model.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.models.schemas import (
    EconomicEvent,
    MacroSnapshot,
    MarketDataResponse,
    OHLCVBar,
    OverviewKPIs,
    OverviewResponse,
    RiskMetrics,
    ServiceHealth,
    StrategyPerformance,
    SystemStatus,
    TradeExecution,
    TradingResponse,
    TradingSignal,
)


NOW = datetime(2026, 3, 21, 12, 0, 0, tzinfo=timezone.utc)


# ── ServiceHealth ────────────────────────────────────────────────────────────


class TestServiceHealth:
    def test_required_fields_only(self):
        sh = ServiceHealth(name="postgres", status="connected")
        assert sh.name == "postgres"
        assert sh.status == "connected"
        assert sh.latency_ms is None
        assert sh.error is None

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            ServiceHealth(name="redis")  # missing status

    def test_full_construction(self):
        sh = ServiceHealth(
            name="redis", status="disconnected", latency_ms=1.23, error="timeout"
        )
        assert sh.latency_ms == 1.23
        assert sh.error == "timeout"

    def test_json_round_trip(self):
        original = ServiceHealth(name="db", status="connected", latency_ms=0.5)
        rebuilt = ServiceHealth.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── OverviewKPIs ─────────────────────────────────────────────────────────────


class TestOverviewKPIs:
    def test_defaults(self):
        kpis = OverviewKPIs()
        assert kpis.signals_today == 0
        assert kpis.signals_per_hour == 0.0
        assert kpis.daily_pnl == "0.00"
        assert kpis.daily_pnl_pct == "0.00"
        assert kpis.open_positions == 0
        assert kpis.drawdown_pct == "0.00"
        assert kpis.kill_switch_active is False
        assert kpis.win_rate == "0.00"
        assert kpis.total_trades_today == 0

    def test_full_construction(self):
        kpis = OverviewKPIs(
            signals_today=15,
            signals_per_hour=2.5,
            daily_pnl="123.45",
            daily_pnl_pct="1.25",
            open_positions=3,
            drawdown_pct="0.80",
            kill_switch_active=True,
            win_rate="65.00",
            total_trades_today=10,
        )
        assert kpis.signals_today == 15
        assert kpis.kill_switch_active is True
        assert kpis.win_rate == "65.00"

    def test_json_round_trip(self):
        original = OverviewKPIs(signals_today=5, daily_pnl="50.00")
        rebuilt = OverviewKPIs.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── OverviewResponse ─────────────────────────────────────────────────────────


class TestOverviewResponse:
    def test_full_construction(self):
        resp = OverviewResponse(
            kpis=OverviewKPIs(),
            services=[ServiceHealth(name="db", status="connected")],
            recent_signals=[{"id": "sig-1", "direction": "buy"}],
            timestamp=NOW,
        )
        assert resp.timestamp == NOW
        assert len(resp.services) == 1
        assert len(resp.recent_signals) == 1

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            OverviewResponse(
                kpis=OverviewKPIs(),
                services=[],
                recent_signals=[],
                # missing timestamp
            )

    def test_json_round_trip(self):
        original = OverviewResponse(
            kpis=OverviewKPIs(),
            services=[],
            recent_signals=[],
            timestamp=NOW,
        )
        rebuilt = OverviewResponse.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── TradingSignal ────────────────────────────────────────────────────────────


class TestTradingSignal:
    def test_required_fields_only(self):
        sig = TradingSignal(
            signal_id="sig-001",
            created_at=NOW,
            symbol="EURUSD",
            direction="buy",
            confidence="0.85",
        )
        assert sig.signal_id == "sig-001"
        assert sig.suggested_lots is None
        assert sig.stop_loss is None
        assert sig.reasoning is None

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            TradingSignal(
                signal_id="sig-001",
                created_at=NOW,
                symbol="EURUSD",
                # missing direction and confidence
            )

    def test_full_construction(self):
        sig = TradingSignal(
            signal_id="sig-002",
            created_at=NOW,
            symbol="GBPUSD",
            direction="sell",
            confidence="0.92",
            suggested_lots="0.10",
            stop_loss="1.2650",
            take_profit="1.2450",
            model_version="v3.1",
            regime="trending",
            source_tier="tier1",
            reasoning="Strong momentum divergence",
            risk_reward="2.5",
        )
        assert sig.regime == "trending"
        assert sig.risk_reward == "2.5"

    def test_json_round_trip(self):
        original = TradingSignal(
            signal_id="sig-rt",
            created_at=NOW,
            symbol="USDJPY",
            direction="buy",
            confidence="0.70",
            stop_loss="149.50",
        )
        rebuilt = TradingSignal.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── TradeExecution ───────────────────────────────────────────────────────────


class TestTradeExecution:
    def test_required_fields_only(self):
        exe = TradeExecution(
            id=1,
            executed_at=NOW,
            symbol="EURUSD",
            direction="buy",
            status="filled",
        )
        assert exe.id == 1
        assert exe.signal_id is None
        assert exe.profit is None

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            TradeExecution(
                id=1,
                executed_at=NOW,
                symbol="EURUSD",
                direction="buy",
                # missing status
            )

    def test_full_construction(self):
        exe = TradeExecution(
            id=42,
            signal_id="sig-001",
            executed_at=NOW,
            symbol="GBPUSD",
            direction="sell",
            requested_price="1.2600",
            executed_price="1.2601",
            quantity="0.10",
            status="filled",
            slippage_pips="0.1",
            profit="-15.30",
        )
        assert exe.executed_price == "1.2601"
        assert exe.slippage_pips == "0.1"

    def test_json_round_trip(self):
        original = TradeExecution(
            id=7,
            executed_at=NOW,
            symbol="XAUUSD",
            direction="buy",
            status="partial",
            profit="200.00",
        )
        rebuilt = TradeExecution.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── TradingResponse ──────────────────────────────────────────────────────────


class TestTradingResponse:
    def test_empty_lists(self):
        resp = TradingResponse(
            signals=[],
            executions=[],
            positions=[],
            total_signals=0,
            total_executions=0,
        )
        assert resp.signals == []
        assert resp.total_signals == 0

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            TradingResponse(
                signals=[],
                executions=[],
                positions=[],
                # missing total_signals and total_executions
            )

    def test_json_round_trip(self):
        sig = TradingSignal(
            signal_id="s1",
            created_at=NOW,
            symbol="EURUSD",
            direction="buy",
            confidence="0.80",
        )
        exe = TradeExecution(
            id=1,
            executed_at=NOW,
            symbol="EURUSD",
            direction="buy",
            status="filled",
        )
        original = TradingResponse(
            signals=[sig],
            executions=[exe],
            positions=[{"symbol": "EURUSD", "lots": 0.1}],
            total_signals=1,
            total_executions=1,
        )
        rebuilt = TradingResponse.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── RiskMetrics ──────────────────────────────────────────────────────────────


class TestRiskMetrics:
    def test_defaults(self):
        rm = RiskMetrics()
        assert rm.daily_loss_pct == "0.00"
        assert rm.drawdown_pct == "0.00"
        assert rm.kill_switch_active is False
        assert rm.kill_switch_reason is None
        assert rm.open_positions == 0
        assert rm.max_positions == 5
        assert rm.symbols_exposed == []
        assert rm.maturity_state is None
        assert rm.regime is None

    def test_full_construction(self):
        rm = RiskMetrics(
            daily_loss_pct="2.50",
            drawdown_pct="4.10",
            kill_switch_active=True,
            kill_switch_reason="portfolio drawdown exceeded 3%",
            open_positions=3,
            max_positions=10,
            symbols_exposed=["EURUSD", "GBPUSD", "XAUUSD"],
            maturity_state="mature",
            regime="mean_reverting",
        )
        assert rm.kill_switch_active is True
        assert len(rm.symbols_exposed) == 3

    def test_json_round_trip(self):
        original = RiskMetrics(
            symbols_exposed=["EURUSD"], kill_switch_active=True
        )
        rebuilt = RiskMetrics.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── OHLCVBar & MarketDataResponse ────────────────────────────────────────────


class TestOHLCVBar:
    def test_construction(self):
        bar = OHLCVBar(
            time=NOW,
            open="1.1000",
            high="1.1050",
            low="1.0980",
            close="1.1020",
            volume="15000",
        )
        assert bar.time == NOW
        assert bar.close == "1.1020"

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            OHLCVBar(time=NOW, open="1.10", high="1.11", low="1.09", close="1.10")
            # missing volume

    def test_json_round_trip(self):
        original = OHLCVBar(
            time=NOW,
            open="1.10",
            high="1.11",
            low="1.09",
            close="1.10",
            volume="5000",
        )
        rebuilt = OHLCVBar.model_validate_json(original.model_dump_json())
        assert rebuilt == original


class TestMarketDataResponse:
    def test_full_construction(self):
        bar = OHLCVBar(
            time=NOW,
            open="1.10",
            high="1.11",
            low="1.09",
            close="1.105",
            volume="8000",
        )
        resp = MarketDataResponse(
            symbol="EURUSD", timeframe="H1", bars=[bar], total_bars=1
        )
        assert resp.symbol == "EURUSD"
        assert resp.total_bars == 1
        assert len(resp.bars) == 1

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            MarketDataResponse(symbol="EURUSD", timeframe="H1", bars=[])
            # missing total_bars

    def test_json_round_trip(self):
        original = MarketDataResponse(
            symbol="XAUUSD", timeframe="M15", bars=[], total_bars=0
        )
        rebuilt = MarketDataResponse.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── MacroSnapshot ────────────────────────────────────────────────────────────


class TestMacroSnapshot:
    def test_all_defaults_none(self):
        ms = MacroSnapshot()
        assert ms.vix_spot is None
        assert ms.vix_regime is None
        assert ms.vix_contango is None
        assert ms.yield_slope is None
        assert ms.curve_inverted is None
        assert ms.real_rate_10y is None
        assert ms.dxy_value is None
        assert ms.dxy_trend is None
        assert ms.recession_prob is None
        assert ms.updated_at is None

    def test_full_construction(self):
        ms = MacroSnapshot(
            vix_spot="18.50",
            vix_regime="low",
            vix_contango=True,
            yield_slope="0.45",
            curve_inverted=False,
            real_rate_10y="1.80",
            dxy_value="104.25",
            dxy_trend="bullish",
            recession_prob="0.15",
            updated_at=NOW,
        )
        assert ms.vix_contango is True
        assert ms.curve_inverted is False
        assert ms.updated_at == NOW

    def test_json_round_trip(self):
        original = MacroSnapshot(vix_spot="20.00", updated_at=NOW)
        rebuilt = MacroSnapshot.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── StrategyPerformance ──────────────────────────────────────────────────────


class TestStrategyPerformance:
    def test_defaults(self):
        sp = StrategyPerformance(strategy_name="momentum_breakout")
        assert sp.strategy_name == "momentum_breakout"
        assert sp.symbol is None
        assert sp.total_signals == 0
        assert sp.wins == 0
        assert sp.losses == 0
        assert sp.total_profit == "0.00"
        assert sp.avg_confidence == "0.00"
        assert sp.win_rate == "0.00"

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            StrategyPerformance()  # missing strategy_name

    def test_full_construction_and_round_trip(self):
        original = StrategyPerformance(
            strategy_name="mean_reversion",
            symbol="EURUSD",
            total_signals=100,
            wins=62,
            losses=38,
            total_profit="1540.25",
            avg_confidence="0.78",
            win_rate="62.00",
        )
        assert original.wins == 62
        rebuilt = StrategyPerformance.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── EconomicEvent ────────────────────────────────────────────────────────────


class TestEconomicEvent:
    def test_required_fields_only(self):
        ev = EconomicEvent(event_time=NOW, event_name="NFP")
        assert ev.event_name == "NFP"
        assert ev.country is None
        assert ev.actual is None

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            EconomicEvent(event_time=NOW)  # missing event_name

    def test_full_construction_and_round_trip(self):
        original = EconomicEvent(
            event_time=NOW,
            event_name="CPI YoY",
            country="US",
            currency="USD",
            impact="high",
            previous="3.2%",
            forecast="3.1%",
            actual="3.0%",
        )
        assert original.impact == "high"
        rebuilt = EconomicEvent.model_validate_json(original.model_dump_json())
        assert rebuilt == original


# ── SystemStatus ─────────────────────────────────────────────────────────────


class TestSystemStatus:
    def test_construction(self):
        db = ServiceHealth(name="postgres", status="connected", latency_ms=2.1)
        redis = ServiceHealth(name="redis", status="connected", latency_ms=0.3)
        ss = SystemStatus(database=db, redis=redis, services=[db, redis])
        assert ss.database.name == "postgres"
        assert ss.uptime_seconds is None
        assert len(ss.services) == 2

    def test_missing_required_raises(self):
        db = ServiceHealth(name="postgres", status="connected")
        with pytest.raises(ValidationError):
            SystemStatus(database=db, services=[])
            # missing redis

    def test_full_construction_and_round_trip(self):
        db = ServiceHealth(name="postgres", status="connected", latency_ms=1.5)
        redis = ServiceHealth(name="redis", status="connected", latency_ms=0.2)
        algo = ServiceHealth(
            name="algo-engine", status="disconnected", error="unreachable"
        )
        original = SystemStatus(
            database=db,
            redis=redis,
            services=[db, redis, algo],
            uptime_seconds=86400.0,
        )
        assert original.uptime_seconds == 86400.0
        rebuilt = SystemStatus.model_validate_json(original.model_dump_json())
        assert rebuilt == original
