"""Risk API — drawdown, daily loss, kill switch, position limits."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.models.schemas import RiskMetrics
from backend.redis_client.client import get_json_key, set_json_key

router = APIRouter(prefix="/api/risk", tags=["risk"])


class KillSwitchRequest(BaseModel):
    active: bool
    reason: str = "Manual override from dashboard"


@router.post("/kill-switch")
async def toggle_kill_switch(body: KillSwitchRequest) -> dict:
    """Manually activate or deactivate the kill switch via Redis."""
    brain_state = await get_json_key("moneymaker:brain:state") or {}
    brain_state["kill_switch_active"] = body.active
    brain_state["kill_switch_reason"] = body.reason if body.active else None
    await set_json_key("moneymaker:brain:state", brain_state)
    return {
        "success": True,
        "kill_switch_active": body.active,
        "reason": body.reason if body.active else None,
    }


@router.get("", response_model=RiskMetrics)
async def get_risk_metrics() -> RiskMetrics:
    """Return current risk state from Redis."""
    brain_state = await get_json_key("moneymaker:brain:state") or {}

    return RiskMetrics(
        daily_loss_pct=str(brain_state.get("daily_loss_pct", "0.00")),
        drawdown_pct=str(brain_state.get("drawdown_pct", "0.00")),
        kill_switch_active=brain_state.get("kill_switch_active", False),
        kill_switch_reason=brain_state.get("kill_switch_reason"),
        open_positions=brain_state.get("active_positions", 0),
        symbols_exposed=brain_state.get("symbols_exposed", []),
        maturity_state=brain_state.get("maturity_state"),
        regime=brain_state.get("current_regime"),
    )
