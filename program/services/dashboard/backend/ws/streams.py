"""WebSocket stream endpoints for real-time data."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.config import settings
from backend.db.connection import get_pool
from backend.db.queries.trading import get_daily_pnl, get_recent_signals, get_signals_today_count
from backend.redis_client.client import get_json_key, redis_health
from backend.ws.manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/overview")
async def ws_overview(websocket: WebSocket) -> None:
    """Stream overview KPIs at configured interval."""
    await manager.connect("overview", websocket)
    try:
        while True:
            try:
                pool = await get_pool()
                signals_today = await get_signals_today_count(pool)
                daily = await get_daily_pnl(pool)
                brain_state = await get_json_key("moneymaker:brain:state") or {}
                redis_status = await redis_health()

                total = daily.get("wins", 0) + daily.get("losses", 0)
                win_rate = f"{daily['wins'] / total * 100:.2f}" if total > 0 else "0.00"

                await websocket.send_json(
                    {
                        "type": "overview",
                        "data": {
                            "signals_today": signals_today,
                            "daily_pnl": str(daily.get("total_pnl", "0.00")),
                            "total_trades_today": daily.get("total_trades", 0),
                            "win_rate": win_rate,
                            "open_positions": brain_state.get("active_positions", 0),
                            "drawdown_pct": str(brain_state.get("drawdown_pct", "0.00")),
                            "kill_switch_active": brain_state.get("kill_switch_active", False),
                            "regime": brain_state.get("current_regime"),
                            "redis_status": redis_status.get("status", "disconnected"),
                        },
                    }
                )
            except Exception:
                await websocket.send_json(
                    {"type": "error", "data": {"message": "Data fetch failed"}}
                )

            await asyncio.sleep(settings.refresh_kpi)
    except WebSocketDisconnect:
        manager.disconnect("overview", websocket)


@router.websocket("/ws/trading")
async def ws_trading(websocket: WebSocket) -> None:
    """Stream recent signals and positions."""
    await manager.connect("trading", websocket)
    try:
        while True:
            try:
                pool = await get_pool()
                signals = await get_recent_signals(pool, limit=20)
                brain_state = await get_json_key("moneymaker:brain:state") or {}

                await websocket.send_json(
                    {
                        "type": "trading",
                        "data": {
                            "recent_signals": [
                                {
                                    k: (
                                        v.isoformat()
                                        if hasattr(v, "isoformat")
                                        else str(v) if v is not None else None
                                    )
                                    for k, v in s.items()
                                }
                                for s in signals
                            ],
                            "positions": brain_state.get("positions_detail", []),
                            "regime": brain_state.get("current_regime"),
                        },
                    }
                )
            except Exception:
                await websocket.send_json(
                    {"type": "error", "data": {"message": "Data fetch failed"}}
                )

            await asyncio.sleep(settings.refresh_kpi)
    except WebSocketDisconnect:
        manager.disconnect("trading", websocket)
