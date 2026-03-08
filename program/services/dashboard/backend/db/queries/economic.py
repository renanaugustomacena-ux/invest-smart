"""Economic calendar and blackout queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import asyncpg


async def get_upcoming_events(
    pool: asyncpg.Pool,
    days_ahead: int = 7,
    min_impact: str | None = "medium",
) -> list[dict]:
    """Fetch upcoming economic events."""
    now = datetime.now(timezone.utc)
    until = now + timedelta(days=days_ahead)

    if min_impact:
        rows = await pool.fetch(
            """
            SELECT event_time, event_name, country, currency,
                   impact, previous_value, forecast_value, actual_value
            FROM economic_events
            WHERE event_time BETWEEN $1 AND $2
              AND impact IN ('medium', 'high')
            ORDER BY event_time ASC
            """,
            now,
            until,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT event_time, event_name, country, currency,
                   impact, previous_value, forecast_value, actual_value
            FROM economic_events
            WHERE event_time BETWEEN $1 AND $2
            ORDER BY event_time ASC
            """,
            now,
            until,
        )
    return [dict(r) for r in rows]


async def get_active_blackouts(pool: asyncpg.Pool) -> list[dict]:
    """Fetch currently active trading blackouts."""
    rows = await pool.fetch(
        """
        SELECT symbol, blackout_start, blackout_end, reason, created_at
        FROM trading_blackouts
        WHERE blackout_start <= NOW() AND blackout_end >= NOW()
        ORDER BY blackout_start ASC
        """
    )
    return [dict(r) for r in rows]


async def get_recent_events(
    pool: asyncpg.Pool,
    limit: int = 20,
) -> list[dict]:
    """Fetch recent past economic events with actual values."""
    rows = await pool.fetch(
        """
        SELECT event_time, event_name, country, currency,
               impact, previous_value, forecast_value, actual_value
        FROM economic_events
        WHERE event_time <= NOW() AND actual_value IS NOT NULL
        ORDER BY event_time DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]
