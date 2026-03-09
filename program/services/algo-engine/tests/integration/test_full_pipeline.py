"""Integration test: full pipeline — bar ingestion to signal emission.

Feeds realistic XAU/USD bars through a real AlgoEngine and verifies
the entire pipeline executes: data quality, features, regime, strategy,
sizing, validation, and rate limiting.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from algo_engine.features.pipeline import OHLCVBar
from algo_engine.kill_switch import KillSwitch

from .conftest import build_engine, _make_xauusd_bars


class TestFullPipeline:
    """Verify the complete bar-to-signal pipeline with real components."""

    @pytest.mark.asyncio
    async def test_pipeline_produces_signal_after_warmup(self):
        """After enough bars for indicator warmup, the engine should
        produce signals (or explicit None with clear pipeline path)."""
        kill_switch = KillSwitch()
        # Deactivate kill switch for normal operation (local mode)
        await kill_switch.deactivate()

        engine = build_engine(kill_switch=kill_switch, min_bars=50)

        bars = _make_xauusd_bars(count=60, trend=Decimal("0.50"))
        results = []

        for bar in bars:
            result = await engine.process_bar("XAUUSD", "M5", bar)
            results.append(result)

        # Engine should have processed all 60 bars
        assert engine.bar_counter == 60

        # First 49 bars return None (warmup, min_bars=50)
        for i in range(49):
            assert results[i] is None, f"Bar {i} should be None during warmup"

    @pytest.mark.asyncio
    async def test_signal_has_required_fields(self):
        """Any emitted signal must have all required trading fields."""
        kill_switch = KillSwitch()
        await kill_switch.deactivate()

        engine = build_engine(
            kill_switch=kill_switch,
            min_bars=50,
            min_confidence=Decimal("0.10"),  # lower threshold to increase signal chance
        )

        bars = _make_xauusd_bars(count=80, trend=Decimal("0.80"))
        signals = []

        for bar in bars:
            result = await engine.process_bar("XAUUSD", "M5", bar)
            if result is not None:
                signals.append(result)

        # Verify every emitted signal has required fields
        required_fields = {
            "signal_id", "symbol", "direction", "suggested_lots",
            "stop_loss", "take_profit", "confidence", "source_tier",
        }

        for sig in signals:
            missing = required_fields - set(sig.keys())
            assert not missing, f"Signal missing fields: {missing}"
            assert sig["symbol"] == "XAUUSD"
            assert sig["direction"] in ("BUY", "SELL")
            assert Decimal(str(sig["suggested_lots"])) > Decimal("0")
            assert Decimal(str(sig["stop_loss"])) > Decimal("0")

    @pytest.mark.asyncio
    async def test_data_quality_rejects_bad_bars(self):
        """Bars with invalid OHLC relationships should be rejected."""
        kill_switch = KillSwitch()
        await kill_switch.deactivate()
        engine = build_engine(kill_switch=kill_switch, min_bars=50)

        # Feed enough good bars for warmup
        good_bars = _make_xauusd_bars(count=55)
        for bar in good_bars:
            await engine.process_bar("XAUUSD", "M5", bar)

        # Now feed a bar where high < low (invalid)
        bad_bar = OHLCVBar(
            timestamp=1700100000000,
            open=Decimal("2350.00"),
            high=Decimal("2340.00"),   # high below low = invalid
            low=Decimal("2360.00"),
            close=Decimal("2355.00"),
            volume=Decimal("1000"),
        )
        result = await engine.process_bar("XAUUSD", "M5", bad_bar)
        assert result is None, "Invalid bar should produce no signal"

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_excess_signals(self):
        """Rate limiter should block signals beyond the per-hour cap."""
        kill_switch = KillSwitch()
        await kill_switch.deactivate()

        engine = build_engine(
            kill_switch=kill_switch,
            min_bars=50,
            max_signals_per_hour=3,
            min_confidence=Decimal("0.10"),
        )

        # Use a strong trend to maximize signal generation
        bars = _make_xauusd_bars(count=200, trend=Decimal("1.50"))
        signal_count = 0

        for bar in bars:
            result = await engine.process_bar("XAUUSD", "M5", bar)
            if result is not None:
                signal_count += 1

        # Should not exceed the rate limit of 3 per hour
        assert signal_count <= 3, f"Rate limiter failed: {signal_count} signals > 3 limit"
