# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Trading signals and executions queries."""

from __future__ import annotations

from datetime import datetime, timezone

import asyncpg


async def get_recent_signals(
    pool: asyncpg.Pool,
    limit: int = 50,
    symbol: str | None = None,
) -> list[dict]:
    """Fetch recent trading signals."""
    if symbol:
        rows = await pool.fetch(
            """
            SELECT signal_id, created_at, symbol, direction, confidence,
                   suggested_lots, stop_loss, take_profit, model_version,
                   regime, source_tier, reasoning, risk_reward
            FROM trading_signals
            WHERE symbol = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            symbol,
            limit,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT signal_id, created_at, symbol, direction, confidence,
                   suggested_lots, stop_loss, take_profit, model_version,
                   regime, source_tier, reasoning, risk_reward
            FROM trading_signals
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


async def get_signals_today_count(pool: asyncpg.Pool) -> int:
    """Count signals generated today."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    row = await pool.fetchrow(
        "SELECT COUNT(*) as cnt FROM trading_signals WHERE created_at >= $1",
        today,
    )
    return row["cnt"] if row else 0


async def get_recent_executions(
    pool: asyncpg.Pool,
    limit: int = 50,
    symbol: str | None = None,
) -> list[dict]:
    """Fetch recent trade executions."""
    if symbol:
        rows = await pool.fetch(
            """
            SELECT id, signal_id, executed_at, symbol, direction,
                   requested_price, executed_price, quantity, status,
                   slippage_pips, commission, swap, profit
            FROM trade_executions
            WHERE symbol = $1
            ORDER BY executed_at DESC
            LIMIT $2
            """,
            symbol,
            limit,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT id, signal_id, executed_at, symbol, direction,
                   requested_price, executed_price, quantity, status,
                   slippage_pips, commission, swap, profit
            FROM trade_executions
            ORDER BY executed_at DESC
            LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


async def get_daily_pnl(pool: asyncpg.Pool) -> dict:
    """Get today's P&L summary."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    row = await pool.fetchrow(
        """
        SELECT
            COALESCE(SUM(profit), 0) as total_pnl,
            COUNT(*) as total_trades,
            COUNT(*) FILTER (WHERE profit > 0) as wins,
            COUNT(*) FILTER (WHERE profit < 0) as losses
        FROM trade_executions
        WHERE executed_at >= $1 AND status = 'FILLED'
        """,
        today,
    )
    if not row:
        return {"total_pnl": "0.00", "total_trades": 0, "wins": 0, "losses": 0}
    return dict(row)
