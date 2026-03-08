"""Strategy performance API."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.db.connection import get_pool
from backend.db.queries.strategy import (
    get_strategy_daily_summary,
    get_strategy_names,
    get_strategy_performance,
)

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


@router.get("/summary")
async def strategy_summary() -> dict:
    """Return daily strategy summary."""
    pool = await get_pool()
    data = await get_strategy_daily_summary(pool)
    return {"data": _serialize_list(data)}


@router.get("/performance")
async def strategy_performance(
    strategy: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """Return detailed strategy performance."""
    pool = await get_pool()
    data = await get_strategy_performance(pool, strategy, limit)
    return {"data": _serialize_list(data)}


@router.get("/names")
async def strategy_names() -> dict:
    """Return available strategy names."""
    pool = await get_pool()
    names = await get_strategy_names(pool)
    return {"strategies": names}


def _serialize_list(rows: list[dict]) -> list[dict]:
    return [
        {k: v.isoformat() if hasattr(v, "isoformat") else str(v) if v is not None else None for k, v in r.items()}
        for r in rows
    ]
