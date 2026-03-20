# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Economic calendar API."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.db.connection import get_pool
from backend.db.queries.economic import get_active_blackouts, get_recent_events, get_upcoming_events

router = APIRouter(prefix="/api/economic", tags=["economic"])


@router.get("/upcoming")
async def upcoming_events(
    days: int = Query(7, ge=1, le=30),
) -> dict:
    """Return upcoming economic events."""
    pool = await get_pool()
    events = await get_upcoming_events(pool, days)
    return {"events": _serialize_list(events)}


@router.get("/blackouts")
async def active_blackouts() -> dict:
    """Return currently active trading blackouts."""
    pool = await get_pool()
    blackouts = await get_active_blackouts(pool)
    return {"blackouts": _serialize_list(blackouts)}


@router.get("/recent")
async def recent_events(limit: int = Query(20, ge=1, le=100)) -> dict:
    """Return recent past economic events."""
    pool = await get_pool()
    events = await get_recent_events(pool, limit)
    return {"events": _serialize_list(events)}


def _serialize_list(rows: list[dict]) -> list[dict]:
    return [
        {
            k: v.isoformat() if hasattr(v, "isoformat") else str(v) if v is not None else None
            for k, v in r.items()
        }
        for r in rows
    ]
