"""Market Data API — OHLCV bars, tick stats, data quality."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.db.connection import get_pool
from backend.db.queries.market_data import (
    get_available_symbols,
    get_data_quality,
    get_ohlcv_bars,
    get_tick_stats,
)

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/bars")
async def get_bars(
    symbol: str = Query(...),
    timeframe: str = Query("M5"),
    limit: int = Query(500, ge=1, le=5000),
) -> dict:
    """Return OHLCV bars for charting."""
    pool = await get_pool()
    bars = await get_ohlcv_bars(pool, symbol, timeframe, limit)
    serialized = []
    for b in bars:
        serialized.append(
            {
                "time": b["time"].isoformat(),
                "open": str(b["open"]),
                "high": str(b["high"]),
                "low": str(b["low"]),
                "close": str(b["close"]),
                "volume": str(b["volume"]),
            }
        )
    return {"symbol": symbol, "timeframe": timeframe, "bars": serialized, "total": len(serialized)}


@router.get("/symbols")
async def get_symbols() -> dict:
    """Return available symbols."""
    pool = await get_pool()
    symbols = await get_available_symbols(pool)
    return {"symbols": symbols}


@router.get("/tick-stats")
async def get_tick_statistics(hours: int = Query(1, ge=1, le=24)) -> dict:
    """Return tick ingestion statistics."""
    pool = await get_pool()
    stats = await get_tick_stats(pool, hours)
    return {"stats": [{k: str(v) if v is not None else None for k, v in s.items()} for s in stats]}


@router.get("/quality")
async def get_quality() -> dict:
    """Return data quality overview."""
    pool = await get_pool()
    return await get_data_quality(pool)
