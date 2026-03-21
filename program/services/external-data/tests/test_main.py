"""Tests for ExternalDataService — initialization, save guards, and lifecycle.

No unittest.mock — tests the service class directly with None connections
(simulating startup without DB/Redis) and real async behavior.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from external_data.config import ExternalDataSettings
from external_data.main import ExternalDataService


# ---------------------------------------------------------------------------
# Test data objects — real instances, NOT mocks
# ---------------------------------------------------------------------------


@dataclass
class FakeVIXData:
    """Deterministic VIX data for testing."""

    time: datetime = datetime(2026, 3, 20, 14, 0, tzinfo=timezone.utc)
    vix_spot: Decimal = Decimal("18.50")
    vix_1m: Decimal | None = Decimal("19.20")
    vix_2m: Decimal | None = Decimal("20.10")
    vix_3m: Decimal | None = Decimal("21.00")
    regime: str = "normal"
    is_contango: bool = True


@dataclass
class FakeYieldData:
    """Deterministic yield curve data for testing."""

    time: datetime = datetime(2026, 3, 20, 14, 0, tzinfo=timezone.utc)
    rate_2y: Decimal | None = Decimal("4.25")
    rate_5y: Decimal | None = Decimal("4.10")
    rate_10y: Decimal = Decimal("4.35")
    rate_30y: Decimal | None = Decimal("4.55")
    spread_2s10s: Decimal | None = Decimal("0.10")
    is_inverted: bool = False


@dataclass
class FakeRealRatesData:
    """Deterministic real rates data for testing."""

    time: datetime = datetime(2026, 3, 20, 14, 0, tzinfo=timezone.utc)
    nominal_10y: Decimal = Decimal("4.35")
    breakeven_10y: Decimal = Decimal("2.30")
    real_rate_10y: Decimal = Decimal("2.05")
    nominal_5y: Decimal | None = Decimal("4.10")
    breakeven_5y: Decimal | None = Decimal("2.25")
    real_rate_5y: Decimal | None = Decimal("1.85")


@dataclass
class FakeRecessionData:
    """Deterministic recession probability data."""

    time: datetime = datetime(2026, 3, 20, 14, 0, tzinfo=timezone.utc)
    probability_12m: Decimal = Decimal("0.15")
    signal_level: str = "low"


@dataclass
class FakeCOTReport:
    """Deterministic COT report for testing."""

    time: datetime = datetime(2026, 3, 18, tzinfo=timezone.utc)
    market: str = "EURO FX"
    asset_mgr_long: int = 150000
    asset_mgr_short: int = 80000
    asset_mgr_net: int = 70000
    asset_mgr_pct_oi: Decimal = Decimal("0.45")
    lev_funds_long: int = 120000
    lev_funds_short: int = 90000
    lev_funds_net: int = 30000
    lev_funds_pct_oi: Decimal = Decimal("0.35")
    total_oi: int = 500000
    cot_sentiment: str = "bullish"
    extreme_reading: bool = False


# ---------------------------------------------------------------------------
# Fake Redis — real implementation with tracking, NOT a mock
# ---------------------------------------------------------------------------


class FakeRedis:
    """In-memory Redis replacement for testing save operations."""

    def __init__(self):
        self.store: dict[str, tuple[int, str]] = {}  # key -> (ttl, value)
        self.closed = False

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = (ttl, value)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self.closed = True


class FailingRedis:
    """Redis that raises on setex — for error path testing."""

    async def setex(self, key: str, ttl: int, value: str) -> None:
        raise ConnectionError("Redis connection lost")

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(monkeypatch) -> ExternalDataSettings:
    """Create settings with test env vars."""
    monkeypatch.setenv("FRED_API_KEY", "test-key")
    monkeypatch.setenv("MONEYMAKER_REDIS_HOST", "localhost")
    monkeypatch.setenv("MONEYMAKER_REDIS_PORT", "6379")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "test")
    monkeypatch.setenv("DB_PASSWORD", "test")
    monkeypatch.setenv("DB_NAME", "testdb")
    return ExternalDataSettings()


# ---------------------------------------------------------------------------
# Service initialization
# ---------------------------------------------------------------------------


class TestServiceInit:
    def test_creates_service(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        assert service.settings is settings
        assert service.scheduler is not None
        assert service._db_pool is None
        assert service._redis is None
        assert service._running is False

    def test_creates_providers(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        assert service.fred is not None
        assert service.cboe is not None
        assert service.cboe_backup is not None
        assert service.cftc is not None

    def test_shutdown_event_not_set(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        assert not service._shutdown_event.is_set()


# ---------------------------------------------------------------------------
# Save guards (None connections → early return, no crash)
# ---------------------------------------------------------------------------


class TestSaveGuards:
    async def test_save_to_redis_none_noop(self, monkeypatch):
        """When redis is None, _save_to_redis returns silently."""
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        service._redis = None
        # Should not raise
        await service._save_to_redis("macro:vix", {"spot": 18.5})

    async def test_save_vix_to_db_none_pool_noop(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        service._db_pool = None
        await service._save_vix_to_db(FakeVIXData())

    async def test_save_vix_to_db_none_data_noop(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        service._db_pool = None
        await service._save_vix_to_db(None)

    async def test_save_yield_to_db_none_pool_noop(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        service._db_pool = None
        await service._save_yield_to_db(FakeYieldData())

    async def test_save_real_rates_to_db_none_pool_noop(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        service._db_pool = None
        await service._save_real_rates_to_db(FakeRealRatesData())

    async def test_save_cot_to_db_none_pool_noop(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        service._db_pool = None
        await service._save_cot_to_db(FakeCOTReport())


# ---------------------------------------------------------------------------
# Save to Redis (with FakeRedis)
# ---------------------------------------------------------------------------


class TestSaveToRedis:
    async def test_saves_data(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        fake_redis = FakeRedis()
        service._redis = fake_redis

        await service._save_to_redis("macro:vix", {"spot": 18.5})

        assert "macro:vix" in fake_redis.store
        ttl, value = fake_redis.store["macro:vix"]
        assert ttl == settings.redis_cache_ttl_seconds
        parsed = json.loads(value)
        assert parsed["spot"] == 18.5

    async def test_saves_with_default_serializer(self, monkeypatch):
        """Decimal and datetime are serialized via default=str."""
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        fake_redis = FakeRedis()
        service._redis = fake_redis

        await service._save_to_redis("macro:test", {
            "value": Decimal("1.2345"),
            "time": datetime(2026, 3, 20, tzinfo=timezone.utc),
        })

        _, value = fake_redis.store["macro:test"]
        parsed = json.loads(value)
        assert parsed["value"] == "1.2345"
        assert "2026" in parsed["time"]

    async def test_save_error_does_not_crash(self, monkeypatch):
        """Redis errors are caught and logged, not raised."""
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        service._redis = FailingRedis()

        # Should not raise
        await service._save_to_redis("macro:vix", {"spot": 18.5})


# ---------------------------------------------------------------------------
# Trigger shutdown
# ---------------------------------------------------------------------------


class TestTriggerShutdown:
    def test_sets_shutdown_event(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        assert not service._shutdown_event.is_set()
        service.trigger_shutdown()
        assert service._shutdown_event.is_set()


# ---------------------------------------------------------------------------
# Stop lifecycle
# ---------------------------------------------------------------------------


class TestStopLifecycle:
    async def test_stop_when_not_running_noop(self, monkeypatch):
        """stop() is a no-op when service hasn't started."""
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        assert not service._running
        await service.stop()
        # Should not crash or change state
        assert not service._running

    async def test_stop_closes_redis(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        fake_redis = FakeRedis()
        service._redis = fake_redis
        service._running = True
        await service.stop()
        assert fake_redis.closed

    async def test_stop_sets_running_false(self, monkeypatch):
        settings = _make_settings(monkeypatch)
        service = ExternalDataService(settings)
        service._running = True
        await service.stop()
        assert not service._running
