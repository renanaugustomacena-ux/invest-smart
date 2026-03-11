"""System health API — database, Redis, Prometheus, services."""

from __future__ import annotations

import time

from fastapi import APIRouter

from backend.db.connection import get_pool
from backend.models.schemas import ServiceHealth, SystemStatus
from backend.redis_client.client import redis_health

router = APIRouter(prefix="/api/system", tags=["system"])

_start_time = time.monotonic()


@router.get("/health", response_model=SystemStatus)
async def system_health() -> SystemStatus:
    """Return health status of all connected services."""
    db_status = await _check_database()
    redis_status = await _check_redis()

    return SystemStatus(
        database=db_status,
        redis=redis_status,
        services=[db_status, redis_status],
        uptime_seconds=time.monotonic() - _start_time,
    )


async def _check_database() -> ServiceHealth:
    try:
        pool = await get_pool()
        t0 = time.monotonic()
        await pool.fetchval("SELECT 1")
        latency = (time.monotonic() - t0) * 1000
        return ServiceHealth(name="PostgreSQL", status="connected", latency_ms=round(latency, 2))
    except Exception as e:
        return ServiceHealth(name="PostgreSQL", status="disconnected", error=str(e))


async def _check_redis() -> ServiceHealth:
    status = await redis_health()
    return ServiceHealth(
        name="Redis",
        status=status["status"],
        error=status.get("error"),
    )
