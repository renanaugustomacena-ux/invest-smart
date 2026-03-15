"""Tests for ExternalDataService."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch configure_logging before importing main (it may not exist in all versions)
import moneymaker_common.logging as _mcl

if not hasattr(_mcl, "configure_logging"):
    _mcl.configure_logging = lambda *a, **kw: None

from external_data.config import ExternalDataSettings
from external_data.main import ExternalDataService


@pytest.fixture()
def settings(monkeypatch):
    for key in [
        "FRED_API_KEY", "POLYGON_API_KEY", "REDIS_URL",
        "DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME",
    ]:
        monkeypatch.delenv(key, raising=False)
    return ExternalDataSettings()


@pytest.fixture()
def service(settings):
    return ExternalDataService(settings)


class TestInit:
    def test_init(self, service):
        assert service.fred is not None
        assert service.cboe is not None
        assert service.cboe_backup is not None
        assert service.cftc is not None
        assert service.scheduler is not None
        assert service._db_pool is None
        assert service._redis is None
        assert service._running is False

    def test_init_with_custom_settings(self, monkeypatch):
        monkeypatch.setenv("FRED_API_KEY", "my-key")
        monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "10")
        settings = ExternalDataSettings()
        svc = ExternalDataService(settings)
        assert svc.fred.api_key == "my-key"
        assert svc.fred.timeout == 10


class TestSaveToRedis:
    async def test_none_redis(self, service):
        service._redis = None
        # Should not raise
        await service._save_to_redis("key", {"data": "value"})

    async def test_success(self, service):
        service._redis = AsyncMock()
        await service._save_to_redis("macro:vix", {"spot": 15.0})

        service._redis.setex.assert_awaited_once()
        call_args = service._redis.setex.call_args
        assert call_args[0][0] == "macro:vix"
        assert call_args[0][1] == service.settings.redis_cache_ttl_seconds
        data = json.loads(call_args[0][2])
        assert data["spot"] == 15.0

    async def test_error(self, service):
        service._redis = AsyncMock()
        service._redis.setex = AsyncMock(side_effect=ConnectionError("redis down"))
        # Should not raise
        await service._save_to_redis("key", {"data": "value"})


class TestSaveVixToDb:
    async def test_none_pool(self, service):
        service._db_pool = None
        await service._save_vix_to_db(None)

    async def test_none_data(self, service, mock_db_pool):
        pool, conn = mock_db_pool
        service._db_pool = pool
        await service._save_vix_to_db(None)
        conn.execute.assert_not_awaited()

    async def test_success(self, service, mock_db_pool):
        pool, conn = mock_db_pool
        service._db_pool = pool

        vix_data = SimpleNamespace(
            time=datetime.now(timezone.utc),
            vix_spot=Decimal("18.5"),
            vix_1m=Decimal("19.0"),
            vix_2m=None,
            vix_3m=None,
        )

        await service._save_vix_to_db(vix_data)
        conn.execute.assert_awaited_once()

    async def test_db_error(self, service, mock_db_pool):
        pool, conn = mock_db_pool
        service._db_pool = pool
        conn.execute = AsyncMock(side_effect=Exception("db error"))

        vix_data = SimpleNamespace(
            time=datetime.now(timezone.utc),
            vix_spot=Decimal("18.5"),
            vix_1m=None,
            vix_2m=None,
            vix_3m=None,
        )

        # Should not raise
        await service._save_vix_to_db(vix_data)


class TestSaveYieldToDb:
    async def test_none_pool(self, service):
        service._db_pool = None
        await service._save_yield_to_db(None)

    async def test_success(self, service, mock_db_pool):
        pool, conn = mock_db_pool
        service._db_pool = pool

        yield_data = SimpleNamespace(
            time=datetime.now(timezone.utc),
            rate_2y=Decimal("4.0"),
            rate_5y=Decimal("4.2"),
            rate_10y=Decimal("4.5"),
            rate_30y=Decimal("4.8"),
        )

        await service._save_yield_to_db(yield_data)
        conn.execute.assert_awaited_once()


class TestSaveRealRatesToDb:
    async def test_none_pool(self, service):
        service._db_pool = None
        await service._save_real_rates_to_db(None)

    async def test_success(self, service, mock_db_pool):
        pool, conn = mock_db_pool
        service._db_pool = pool

        rates_data = SimpleNamespace(
            time=datetime.now(timezone.utc),
            nominal_10y=Decimal("4.25"),
            breakeven_10y=Decimal("2.30"),
            real_rate_10y=Decimal("1.95"),
            nominal_5y=None,
            breakeven_5y=None,
            real_rate_5y=None,
        )

        await service._save_real_rates_to_db(rates_data)
        conn.execute.assert_awaited_once()


class TestSaveCotToDb:
    async def test_none_pool(self, service):
        service._db_pool = None
        await service._save_cot_to_db(None)

    async def test_success(self, service, mock_db_pool):
        pool, conn = mock_db_pool
        service._db_pool = pool

        cot = SimpleNamespace(
            time=datetime.now(timezone.utc),
            market="GOLD",
            asset_mgr_long=100000,
            asset_mgr_short=50000,
            asset_mgr_net=50000,
            asset_mgr_pct_oi=Decimal("10.0"),
            lev_funds_long=80000,
            lev_funds_short=60000,
            lev_funds_net=20000,
            lev_funds_pct_oi=Decimal("4.0"),
            total_oi=500000,
            cot_sentiment=1,
            extreme_reading=False,
        )

        await service._save_cot_to_db(cot)
        conn.execute.assert_awaited_once()


class TestFetchVixJob:
    async def test_cboe_success(self, service):
        vix = SimpleNamespace(
            time=datetime.now(timezone.utc),
            vix_spot=Decimal("18.5"),
            regime=1,
            is_contango=True,
            vix_1m=None,
            vix_2m=None,
            vix_3m=None,
        )
        service.cboe.fetch_vix = AsyncMock(return_value=vix)
        service._save_to_redis = AsyncMock()
        service._save_vix_to_db = AsyncMock()

        await service._fetch_vix_job()

        service._save_to_redis.assert_awaited_once()
        service._save_vix_to_db.assert_awaited_once()

    async def test_cboe_fails_yahoo_succeeds(self, service):
        vix = SimpleNamespace(
            time=datetime.now(timezone.utc),
            vix_spot=Decimal("20.0"),
            regime=1,
            is_contango=None,
            vix_1m=None,
            vix_2m=None,
            vix_3m=None,
        )
        service.cboe.fetch_vix = AsyncMock(return_value=None)
        service.cboe_backup.fetch_vix = AsyncMock(return_value=vix)
        service._save_to_redis = AsyncMock()
        service._save_vix_to_db = AsyncMock()

        await service._fetch_vix_job()

        service.cboe_backup.fetch_vix.assert_awaited_once()
        service._save_to_redis.assert_awaited_once()

    async def test_both_fail(self, service):
        service.cboe.fetch_vix = AsyncMock(return_value=None)
        service.cboe_backup.fetch_vix = AsyncMock(return_value=None)
        service._save_to_redis = AsyncMock()
        service._save_vix_to_db = AsyncMock()

        await service._fetch_vix_job()

        service._save_to_redis.assert_not_awaited()
        service._save_vix_to_db.assert_not_awaited()


class TestFetchYieldCurveJob:
    async def test_all_succeed(self, service):
        now = datetime.now(timezone.utc)
        yield_data = SimpleNamespace(
            time=now,
            rate_2y=Decimal("4.0"),
            rate_10y=Decimal("4.5"),
            spread_2s10s=Decimal("0.5"),
            is_inverted=False,
        )
        rates_data = SimpleNamespace(
            time=now,
            nominal_10y=Decimal("4.5"),
            breakeven_10y=Decimal("2.3"),
            real_rate_10y=Decimal("2.2"),
        )
        recession_data = SimpleNamespace(
            time=now,
            probability_12m=Decimal("15.0"),
            signal_level=0,
        )

        service.fred.fetch_yield_curve = AsyncMock(return_value=yield_data)
        service.fred.fetch_real_rates = AsyncMock(return_value=rates_data)
        service.fred.fetch_recession_probability = AsyncMock(return_value=recession_data)
        service._save_to_redis = AsyncMock()
        service._save_yield_to_db = AsyncMock()
        service._save_real_rates_to_db = AsyncMock()

        await service._fetch_yield_curve_job()

        # 3 redis saves: yield, rates, recession
        assert service._save_to_redis.await_count == 3
        service._save_yield_to_db.assert_awaited_once()
        service._save_real_rates_to_db.assert_awaited_once()

    async def test_partial_failure(self, service):
        yield_data = SimpleNamespace(
            time=datetime.now(timezone.utc),
            rate_2y=Decimal("4.0"),
            rate_10y=Decimal("4.5"),
            spread_2s10s=Decimal("0.5"),
            is_inverted=False,
        )

        service.fred.fetch_yield_curve = AsyncMock(return_value=yield_data)
        service.fred.fetch_real_rates = AsyncMock(return_value=None)
        service.fred.fetch_recession_probability = AsyncMock(return_value=None)
        service._save_to_redis = AsyncMock()
        service._save_yield_to_db = AsyncMock()
        service._save_real_rates_to_db = AsyncMock()

        await service._fetch_yield_curve_job()

        # Only yield saved
        assert service._save_to_redis.await_count == 1
        service._save_yield_to_db.assert_awaited_once()
        service._save_real_rates_to_db.assert_not_awaited()


class TestFetchCotJob:
    async def test_success(self, service):
        report = SimpleNamespace(
            market="GOLD",
            cot_sentiment=1,
            asset_mgr_pct_oi=Decimal("10.0"),
            lev_funds_net=20000,
            extreme_reading=False,
            time=datetime.now(timezone.utc),
            asset_mgr_long=100000,
            asset_mgr_short=50000,
            asset_mgr_net=50000,
            lev_funds_long=80000,
            lev_funds_short=60000,
            lev_funds_pct_oi=Decimal("4.0"),
            total_oi=500000,
        )

        service.cftc.fetch_latest_cot = AsyncMock(return_value=[report])
        service._save_to_redis = AsyncMock()
        service._save_cot_to_db = AsyncMock()

        await service._fetch_cot_job()

        service._save_to_redis.assert_awaited_once()
        service._save_cot_to_db.assert_awaited_once()

    async def test_empty_reports(self, service):
        service.cftc.fetch_latest_cot = AsyncMock(return_value=[])
        service._save_to_redis = AsyncMock()
        service._save_cot_to_db = AsyncMock()

        await service._fetch_cot_job()

        service._save_to_redis.assert_not_awaited()
        service._save_cot_to_db.assert_not_awaited()


class TestTriggerShutdown:
    def test_sets_event(self, service):
        assert not service._shutdown_event.is_set()
        service.trigger_shutdown()
        assert service._shutdown_event.is_set()


class TestStopWhenNotRunning:
    async def test_no_op(self, service):
        assert service._running is False
        await service.stop()
        assert service._running is False
