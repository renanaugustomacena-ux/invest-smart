"""Async PostgreSQL connection pool for the dashboard."""

from __future__ import annotations

import asyncpg

from backend.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the shared connection pool, creating it if needed."""
    global _pool
    if _pool is None:
        _pool = await create_pool()
    return _pool


async def create_pool() -> asyncpg.Pool:
    """Create a new asyncpg connection pool."""
    pool = await asyncpg.create_pool(
        host=settings.moneymaker_db_host,
        port=settings.moneymaker_db_port,
        database=settings.moneymaker_db_name,
        user=settings.moneymaker_db_user,
        password=settings.moneymaker_db_password,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
    )
    if pool is None:
        raise RuntimeError("Failed to create database pool")
    return pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
