"""Macro indicators queries (VIX, yield curve, DXY, COT, recession)."""

from __future__ import annotations

import asyncpg


async def get_macro_snapshot(pool: asyncpg.Pool) -> dict | None:
    """Fetch the latest macro snapshot from the materialized view."""
    try:
        row = await pool.fetchrow("SELECT * FROM macro_snapshot LIMIT 1")
        return dict(row) if row else None
    except Exception:
        return None


async def get_vix_history(pool: asyncpg.Pool, limit: int = 100) -> list[dict]:
    """Fetch VIX history."""
    rows = await pool.fetch(
        """
        SELECT time, vix_spot, vix_1m, vix_2m, vix_3m,
               term_slope, is_contango, regime
        FROM vix_data
        ORDER BY time DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in reversed(rows)]


async def get_yield_curve_history(pool: asyncpg.Pool, limit: int = 100) -> list[dict]:
    """Fetch yield curve history."""
    rows = await pool.fetch(
        """
        SELECT time, rate_2y, rate_5y, rate_10y, rate_30y,
               spread_2s10s, is_inverted
        FROM yield_curve_data
        ORDER BY time DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in reversed(rows)]


async def get_dxy_history(pool: asyncpg.Pool, limit: int = 100) -> list[dict]:
    """Fetch DXY (Dollar Index) history."""
    rows = await pool.fetch(
        """
        SELECT time, dxy_value, change_1h_pct, change_24h_pct,
               change_7d_pct, sma_20, trend_direction
        FROM dxy_data
        ORDER BY time DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in reversed(rows)]


async def get_cot_reports(pool: asyncpg.Pool, limit: int = 20) -> list[dict]:
    """Fetch COT (Commitment of Traders) data."""
    rows = await pool.fetch(
        """
        SELECT time AS report_date, market, asset_mgr_net, asset_mgr_pct_oi,
               lev_funds_net, lev_funds_pct_oi, cot_sentiment, extreme_reading
        FROM cot_reports
        ORDER BY time DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]


async def get_recession_probability(pool: asyncpg.Pool) -> dict | None:
    """Fetch latest recession probability."""
    row = await pool.fetchrow("""
        SELECT time, probability_12m, probability_change, signal_level
        FROM recession_probability
        ORDER BY time DESC
        LIMIT 1
        """)
    return dict(row) if row else None
