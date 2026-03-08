"""Overview API — aggregated KPIs and service health."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from backend.db.connection import get_pool
from backend.db.queries.trading import get_daily_pnl, get_recent_signals, get_signals_today_count
from backend.models.schemas import OverviewKPIs, OverviewResponse, ServiceHealth
from backend.redis_client.client import get_json_key, redis_health

router = APIRouter(prefix="/api/overview", tags=["overview"])


@router.get("", response_model=OverviewResponse)
async def get_overview() -> OverviewResponse:
    """Return aggregated dashboard overview."""
    pool = await get_pool()

    signals_today = await get_signals_today_count(pool)
    daily = await get_daily_pnl(pool)
    recent = await get_recent_signals(pool, limit=10)

    brain_state = await get_json_key("moneymaker:brain:state") or {}

    win_rate = "0.00"
    total = daily.get("wins", 0) + daily.get("losses", 0)
    if total > 0:
        win_rate = f"{daily['wins'] / total * 100:.2f}"

    kpis = OverviewKPIs(
        signals_today=signals_today,
        daily_pnl=str(daily.get("total_pnl", "0.00")),
        open_positions=brain_state.get("active_positions", 0),
        drawdown_pct=str(brain_state.get("drawdown_pct", "0.00")),
        kill_switch_active=brain_state.get("kill_switch_active", False),
        win_rate=win_rate,
        total_trades_today=daily.get("total_trades", 0),
    )

    # Service health checks
    redis_status = await redis_health()
    services = [
        ServiceHealth(name="PostgreSQL", status="connected"),
        ServiceHealth(
            name="Redis",
            status=redis_status.get("status", "disconnected"),
            error=redis_status.get("error"),
        ),
    ]

    return OverviewResponse(
        kpis=kpis,
        services=services,
        recent_signals=recent,
        timestamp=datetime.now(timezone.utc),
    )
