# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Trading API — signals, executions, positions."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.db.connection import get_pool
from backend.db.queries.trading import get_recent_executions, get_recent_signals
from backend.models.schemas import TradingResponse
from backend.redis_client.client import get_json_key

router = APIRouter(prefix="/api/trading", tags=["trading"])


@router.get("", response_model=TradingResponse)
async def get_trading_data(
    symbol: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> TradingResponse:
    """Return trading signals, executions, and current positions."""
    pool = await get_pool()

    signals = await get_recent_signals(pool, limit=limit, symbol=symbol)
    executions = await get_recent_executions(pool, limit=limit, symbol=symbol)

    portfolio = await get_json_key("moneymaker:brain:state") or {}
    positions = portfolio.get("positions_detail", [])

    return TradingResponse(
        signals=[_serialize(s) for s in signals],
        executions=[_serialize(e) for e in executions],
        positions=positions,
        total_signals=len(signals),
        total_executions=len(executions),
    )


def _serialize(row: dict) -> dict:
    """Convert Decimal/datetime values to strings for JSON."""
    out = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif v is not None:
            out[k] = str(v)
        else:
            out[k] = None
    return out
