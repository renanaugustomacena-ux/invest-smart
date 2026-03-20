# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Market data queries (OHLCV bars, ticks)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import asyncpg


async def get_ohlcv_bars(
    pool: asyncpg.Pool,
    symbol: str,
    timeframe: str = "M5",
    limit: int = 500,
) -> list[dict]:
    """Fetch OHLCV bars for a symbol and timeframe."""
    rows = await pool.fetch(
        """
        SELECT time, open, high, low, close, volume
        FROM ohlcv_bars
        WHERE symbol = $1 AND timeframe = $2
        ORDER BY time DESC
        LIMIT $3
        """,
        symbol,
        timeframe,
        limit,
    )
    return [dict(r) for r in reversed(rows)]


async def get_available_symbols(pool: asyncpg.Pool) -> list[str]:
    """Get distinct symbols available in the database."""
    rows = await pool.fetch("SELECT DISTINCT symbol FROM ohlcv_bars ORDER BY symbol")
    return [r["symbol"] for r in rows]


async def get_tick_stats(pool: asyncpg.Pool, hours: int = 1) -> list[dict]:
    """Get tick ingestion statistics for the last N hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = await pool.fetch(
        """
        SELECT symbol, COUNT(*) as tick_count,
               AVG(spread) as avg_spread,
               MIN(time) as first_tick,
               MAX(time) as last_tick
        FROM market_ticks
        WHERE time >= $1
        GROUP BY symbol
        ORDER BY tick_count DESC
        """,
        since,
    )
    return [dict(r) for r in rows]


async def get_data_quality(pool: asyncpg.Pool) -> dict:
    """Get data quality overview."""
    bars_row = await pool.fetchrow("SELECT COUNT(*) as total_bars FROM ohlcv_bars")
    ticks_row = await pool.fetchrow("SELECT COUNT(*) as total_ticks FROM market_ticks")
    return {
        "total_bars": bars_row["total_bars"] if bars_row else 0,
        "total_ticks": ticks_row["total_ticks"] if ticks_row else 0,
    }
