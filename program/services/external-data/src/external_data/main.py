# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""MONEYMAKER External Data Service - Main Entry Point.

Fetches quantitative macro data from external sources and persists to:
1. TimescaleDB for historical analysis
2. Redis for real-time feature engineering

Data sources:
- FRED: Yield curve, real rates, recession probability
- CBOE: VIX spot and term structure
- CFTC: COT reports (weekly)

Scheduling:
- VIX: Every 1-5 minutes (high frequency)
- Yield/Rates: Every hour (daily data)
- COT: Every 24 hours (weekly release)
"""

from __future__ import annotations

import asyncio
import json
import signal
import sys
from typing import Any

import asyncpg
import redis.asyncio as aioredis

from moneymaker_common.logging import get_logger, configure_logging

from .config import ExternalDataSettings
from .providers.fred import FREDProvider
from .providers.cboe import CBOEProvider, YahooVIXProvider
from .providers.cftc import CFTCProvider
from .scheduler import MacroDataScheduler

logger = get_logger(__name__)


class ExternalDataService:
    """Servizio principale per dati esterni macro."""

    def __init__(self, settings: ExternalDataSettings) -> None:
        self.settings = settings
        self.scheduler = MacroDataScheduler()

        # Providers
        self.fred = FREDProvider(
            api_key=settings.fred_api_key,
            base_url=settings.fred_base_url,
            timeout=settings.request_timeout_seconds,
        )
        self.cboe = CBOEProvider(timeout=settings.request_timeout_seconds)
        self.cboe_backup = YahooVIXProvider(timeout=settings.request_timeout_seconds)
        self.cftc = CFTCProvider(timeout=settings.request_timeout_seconds)

        # Storage
        self._db_pool: asyncpg.Pool | None = None
        self._redis: aioredis.Redis | None = None

        # State
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def _init_database(self) -> None:
        """Initialize database connection pool."""
        try:
            dsn = f"postgresql://{self.settings.db_user}:{self.settings.db_password}@{self.settings.db_host}:{self.settings.db_port}/{self.settings.db_name}"
            self._db_pool = await asyncpg.create_pool(
                dsn,
                min_size=2,
                max_size=10,
            )
            logger.info("Database pool initialized")
        except Exception as e:
            logger.error("Database connection failed", error=str(e))
            self._db_pool = None

    async def _init_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            self._redis = aioredis.from_url(
                self.settings.redis_url,
                decode_responses=True,
            )
            await self._redis.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.error("Redis connection failed", error=str(e))
            self._redis = None

    async def _save_to_redis(self, key: str, data: dict[str, Any]) -> None:
        """Save data to Redis with TTL."""
        if self._redis is None:
            return

        try:
            await self._redis.setex(
                key,
                self.settings.redis_cache_ttl_seconds,
                json.dumps(data, default=str),
            )
        except Exception as e:
            logger.error("Redis save error", key=key, error=str(e))

    async def _save_vix_to_db(self, vix_data: Any) -> None:
        """Save VIX data to TimescaleDB."""
        if self._db_pool is None or vix_data is None:
            return

        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO vix_data (time, vix_spot, vix_1m, vix_2m, vix_3m, source)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    vix_data.time,
                    float(vix_data.vix_spot),
                    float(vix_data.vix_1m) if vix_data.vix_1m else None,
                    float(vix_data.vix_2m) if vix_data.vix_2m else None,
                    float(vix_data.vix_3m) if vix_data.vix_3m else None,
                    "cboe",
                )
        except Exception as e:
            logger.error("VIX DB save error", error=str(e))

    async def _save_yield_to_db(self, yield_data: Any) -> None:
        """Save yield curve data to TimescaleDB."""
        if self._db_pool is None or yield_data is None:
            return

        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO yield_curve_data (time, rate_2y, rate_5y, rate_10y, rate_30y, source)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    yield_data.time,
                    float(yield_data.rate_2y) if yield_data.rate_2y else None,
                    float(yield_data.rate_5y) if yield_data.rate_5y else None,
                    float(yield_data.rate_10y),
                    float(yield_data.rate_30y) if yield_data.rate_30y else None,
                    "fred",
                )
        except Exception as e:
            logger.error("Yield DB save error", error=str(e))

    async def _save_real_rates_to_db(self, rates_data: Any) -> None:
        """Save real rates data to TimescaleDB."""
        if self._db_pool is None or rates_data is None:
            return

        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO real_rates_data (
                        time, nominal_10y, breakeven_10y, real_rate_10y,
                        nominal_5y, breakeven_5y, real_rate_5y, source
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    rates_data.time,
                    float(rates_data.nominal_10y),
                    float(rates_data.breakeven_10y),
                    float(rates_data.real_rate_10y),
                    float(rates_data.nominal_5y) if rates_data.nominal_5y else None,
                    float(rates_data.breakeven_5y) if rates_data.breakeven_5y else None,
                    float(rates_data.real_rate_5y) if rates_data.real_rate_5y else None,
                    "fred",
                )
        except Exception as e:
            logger.error("Real rates DB save error", error=str(e))

    async def _save_cot_to_db(self, cot_data: Any) -> None:
        """Save COT report to TimescaleDB."""
        if self._db_pool is None or cot_data is None:
            return

        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO cot_reports (
                        time, market, asset_mgr_long, asset_mgr_short, asset_mgr_net,
                        asset_mgr_pct_oi, lev_funds_long, lev_funds_short, lev_funds_net,
                        lev_funds_pct_oi, total_oi, cot_sentiment, extreme_reading, source
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT DO NOTHING
                    """,
                    cot_data.time,
                    cot_data.market,
                    cot_data.asset_mgr_long,
                    cot_data.asset_mgr_short,
                    cot_data.asset_mgr_net,
                    float(cot_data.asset_mgr_pct_oi),
                    cot_data.lev_funds_long,
                    cot_data.lev_funds_short,
                    cot_data.lev_funds_net,
                    float(cot_data.lev_funds_pct_oi),
                    cot_data.total_oi,
                    cot_data.cot_sentiment,
                    cot_data.extreme_reading,
                    "cftc",
                )
        except Exception as e:
            logger.error("COT DB save error", error=str(e))

    # ─── Job Functions ────────────────────────────────────────────────────

    async def _fetch_vix_job(self) -> None:
        """Job: Fetch VIX data."""
        logger.debug("Fetching VIX data")

        # Try CBOE first, fallback to Yahoo
        vix_data = await self.cboe.fetch_vix()
        if vix_data is None:
            logger.debug("CBOE failed, trying Yahoo backup")
            vix_data = await self.cboe_backup.fetch_vix()

        if vix_data is None:
            logger.warning("All VIX sources failed")
            return

        # Save to Redis for real-time access
        await self._save_to_redis(
            "macro:vix",
            {
                "spot": float(vix_data.vix_spot),
                "regime": vix_data.regime,
                "contango": vix_data.is_contango,
                "updated_at": vix_data.time.isoformat(),
            },
        )

        # Save to DB for history
        await self._save_vix_to_db(vix_data)

        logger.info(
            "VIX updated",
            spot=float(vix_data.vix_spot),
            regime=vix_data.regime,
        )

    async def _fetch_yield_curve_job(self) -> None:
        """Job: Fetch yield curve and real rates."""
        logger.debug("Fetching yield curve data")

        # Fetch both in parallel
        yield_data, rates_data, recession = await asyncio.gather(
            self.fred.fetch_yield_curve(),
            self.fred.fetch_real_rates(),
            self.fred.fetch_recession_probability(),
            return_exceptions=True,
        )

        # Handle yield curve
        if yield_data and not isinstance(yield_data, Exception):
            await self._save_to_redis(
                "macro:yield_curve",
                {
                    "rate_2y": float(yield_data.rate_2y) if yield_data.rate_2y else None,
                    "rate_10y": float(yield_data.rate_10y),
                    "spread_2s10s": (
                        float(yield_data.spread_2s10s) if yield_data.spread_2s10s else None
                    ),
                    "inverted": yield_data.is_inverted,
                    "updated_at": yield_data.time.isoformat(),
                },
            )
            await self._save_yield_to_db(yield_data)
            logger.info(
                "Yield curve updated",
                spread_2s10s=float(yield_data.spread_2s10s) if yield_data.spread_2s10s else None,
                inverted=yield_data.is_inverted,
            )

        # Handle real rates
        if rates_data and not isinstance(rates_data, Exception):
            await self._save_to_redis(
                "macro:real_rates",
                {
                    "real_rate_10y": float(rates_data.real_rate_10y),
                    "nominal_10y": float(rates_data.nominal_10y),
                    "breakeven_10y": float(rates_data.breakeven_10y),
                    "updated_at": rates_data.time.isoformat(),
                },
            )
            await self._save_real_rates_to_db(rates_data)
            logger.info(
                "Real rates updated",
                real_10y=float(rates_data.real_rate_10y),
            )

        # Handle recession probability
        if recession and not isinstance(recession, Exception):
            await self._save_to_redis(
                "macro:recession",
                {
                    "probability_12m": float(recession.probability_12m),
                    "signal_level": recession.signal_level,
                    "updated_at": recession.time.isoformat(),
                },
            )
            logger.info(
                "Recession probability updated",
                prob=float(recession.probability_12m),
            )

    async def _fetch_cot_job(self) -> None:
        """Job: Fetch COT reports."""
        logger.debug("Fetching COT data")

        reports = await self.cftc.fetch_latest_cot()

        if not reports:
            logger.warning("No COT reports fetched")
            return

        # Save each report
        for report in reports:
            await self._save_to_redis(
                f"macro:cot:{report.market.lower()}",
                {
                    "sentiment": report.cot_sentiment,
                    "asset_mgr_pct_oi": float(report.asset_mgr_pct_oi),
                    "lev_funds_net": report.lev_funds_net,
                    "extreme_reading": report.extreme_reading,
                    "report_date": report.time.isoformat(),
                },
            )
            await self._save_cot_to_db(report)

        logger.info("COT reports updated", count=len(reports))

    # ─── Service Lifecycle ────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the external data service."""
        logger.info("Starting External Data Service")

        # Initialize connections
        await self._init_database()
        await self._init_redis()

        # Register jobs
        self.scheduler.add_job(
            "vix",
            self._fetch_vix_job,
            interval_seconds=self.settings.vix_fetch_interval_minutes * 60,
            run_immediately=True,
        )

        self.scheduler.add_job(
            "yield_curve",
            self._fetch_yield_curve_job,
            interval_seconds=self.settings.yield_fetch_interval_minutes * 60,
            run_immediately=True,
        )

        self.scheduler.add_job(
            "cot",
            self._fetch_cot_job,
            interval_seconds=self.settings.cot_fetch_interval_hours * 3600,
            run_immediately=True,
        )

        # Start scheduler
        await self.scheduler.start()

        self._running = True
        logger.info("External Data Service started")

        # Wait for shutdown
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Stop the service gracefully."""
        if not self._running:
            return

        logger.info("Stopping External Data Service")
        self._running = False

        # Stop scheduler
        await self.scheduler.stop()

        # Close providers
        await self.fred.close()
        await self.cboe.close()
        await self.cboe_backup.close()
        await self.cftc.close()

        # Close connections
        if self._db_pool:
            await self._db_pool.close()
        if self._redis:
            await self._redis.close()

        self._shutdown_event.set()
        logger.info("External Data Service stopped")

    def trigger_shutdown(self) -> None:
        """Trigger graceful shutdown."""
        self._shutdown_event.set()


async def main() -> int:
    """Main entry point."""
    configure_logging("external-data")
    settings = ExternalDataSettings()

    service = ExternalDataService(settings)

    # Setup signal handlers
    loop = asyncio.get_running_loop()

    def signal_handler() -> None:
        logger.info("Shutdown signal received")
        service.trigger_shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    try:
        await service.start()
    except Exception as e:
        logger.error("Service error", error=str(e))
        return 1
    finally:
        await service.stop()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
