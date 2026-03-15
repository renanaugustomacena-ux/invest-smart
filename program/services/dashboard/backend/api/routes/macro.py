"""Macro indicators API — VIX, yield curve, DXY, COT, recession."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.db.connection import get_pool
from backend.db.queries.macro import (
    get_cot_reports,
    get_dxy_history,
    get_macro_snapshot,
    get_recession_probability,
    get_vix_history,
    get_yield_curve_history,
)

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("/snapshot")
async def macro_snapshot() -> dict:
    """Return the latest macro snapshot (materialized view)."""
    pool = await get_pool()
    data = await get_macro_snapshot(pool)
    if not data:
        return {"snapshot": None}
    return {"snapshot": _serialize(data)}


@router.get("/vix")
async def vix_history(limit: int = Query(100, ge=1, le=1000)) -> dict:
    pool = await get_pool()
    rows = await get_vix_history(pool, limit)
    return {"data": _serialize_list(rows)}


@router.get("/yield-curve")
async def yield_curve(limit: int = Query(100, ge=1, le=1000)) -> dict:
    pool = await get_pool()
    rows = await get_yield_curve_history(pool, limit)
    return {"data": _serialize_list(rows)}


@router.get("/dxy")
async def dxy(limit: int = Query(100, ge=1, le=1000)) -> dict:
    pool = await get_pool()
    rows = await get_dxy_history(pool, limit)
    return {"data": _serialize_list(rows)}


@router.get("/cot")
async def cot(limit: int = Query(20, ge=1, le=100)) -> dict:
    pool = await get_pool()
    rows = await get_cot_reports(pool, limit)
    return {"data": _serialize_list(rows)}


@router.get("/recession")
async def recession() -> dict:
    pool = await get_pool()
    data = await get_recession_probability(pool)
    return {"data": _serialize(data) if data else None}


def _serialize(row: dict) -> dict:
    return {
        k: v.isoformat() if hasattr(v, "isoformat") else str(v) if v is not None else None
        for k, v in row.items()
    }


def _serialize_list(rows: list[dict]) -> list[dict]:
    return [_serialize(r) for r in rows]
