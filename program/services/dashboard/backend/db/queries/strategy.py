# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Strategy performance queries."""

from __future__ import annotations

import asyncpg


async def get_strategy_daily_summary(pool: asyncpg.Pool) -> list[dict]:
    """Fetch strategy daily summary from materialized view."""
    try:
        rows = await pool.fetch("""
            SELECT strategy_name, symbol, day,
                   total_signals, wins, losses, total_profit,
                   avg_confidence, last_signal_at
            FROM strategy_daily_summary
            ORDER BY day DESC, total_profit DESC
            LIMIT 200
            """)
        return [dict(r) for r in rows]
    except Exception:
        return []


async def get_strategy_performance(
    pool: asyncpg.Pool,
    strategy_name: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Fetch detailed strategy performance records."""
    if strategy_name:
        rows = await pool.fetch(
            """
            SELECT strategy_name, symbol, direction, confidence,
                   regime, source_tier, entry_price, exit_price,
                   stop_loss, take_profit, profit, status,
                   opened_at, closed_at
            FROM strategy_performance
            WHERE strategy_name = $1
            ORDER BY opened_at DESC
            LIMIT $2
            """,
            strategy_name,
            limit,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT strategy_name, symbol, direction, confidence,
                   regime, source_tier, entry_price, exit_price,
                   profit, status, opened_at, closed_at
            FROM strategy_performance
            ORDER BY opened_at DESC
            LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


async def get_strategy_names(pool: asyncpg.Pool) -> list[str]:
    """Get distinct strategy names."""
    rows = await pool.fetch(
        "SELECT DISTINCT strategy_name FROM strategy_performance ORDER BY strategy_name"
    )
    return [r["strategy_name"] for r in rows]
