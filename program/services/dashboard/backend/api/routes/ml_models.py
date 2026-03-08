"""ML Models API — model registry, predictions, TensorBoard status."""

from __future__ import annotations

import httpx
from fastapi import APIRouter

from backend.config import settings
from backend.db.connection import get_pool
from backend.db.queries.ml import get_model_metrics, get_model_registry, get_recent_predictions

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.get("")
async def get_ml_data() -> dict:
    """Return ML models, predictions, and TensorBoard status."""
    pool = await get_pool()

    models = await get_model_registry(pool)
    predictions = await get_recent_predictions(pool, limit=30)
    metrics = await get_model_metrics(pool, limit=50)

    tb_online = await _check_tensorboard()

    return {
        "models": _serialize_list(models),
        "tensorboard_online": tb_online,
        "tensorboard_url": settings.tensorboard_public_url,
        "recent_predictions": _serialize_list(predictions),
        "training_metrics": _serialize_list(metrics),
    }


@router.get("/tensorboard/status")
async def tensorboard_status() -> dict:
    """Check if TensorBoard is reachable."""
    online = await _check_tensorboard()
    return {"online": online, "url": settings.tensorboard_public_url}


async def _check_tensorboard() -> bool:
    """Ping TensorBoard to check if it's running."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(settings.tensorboard_url)
            return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _serialize_list(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        out.append({k: v.isoformat() if hasattr(v, "isoformat") else str(v) if v is not None else None for k, v in row.items()})
    return out
