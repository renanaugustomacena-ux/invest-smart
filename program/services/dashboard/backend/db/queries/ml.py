"""ML model registry and predictions queries."""

from __future__ import annotations

import asyncpg


async def get_model_registry(pool: asyncpg.Pool) -> list[dict]:
    """Fetch all registered models."""
    rows = await pool.fetch(
        """
        SELECT id, model_name, model_type, version AS model_version, is_active,
               validation_accuracy, checkpoint_path, training_samples,
               created_at
        FROM model_registry
        ORDER BY created_at DESC
        """
    )
    return [dict(r) for r in rows]


async def get_active_model(pool: asyncpg.Pool) -> dict | None:
    """Get the currently active model."""
    row = await pool.fetchrow(
        """
        SELECT id, model_name, model_type, version AS model_version, is_active,
               validation_accuracy, checkpoint_path, created_at
        FROM model_registry
        WHERE is_active = true
        LIMIT 1
        """
    )
    return dict(row) if row else None


async def get_recent_predictions(
    pool: asyncpg.Pool,
    limit: int = 50,
) -> list[dict]:
    """Fetch recent ML predictions."""
    rows = await pool.fetch(
        """
        SELECT prediction_id, symbol, model_version, model_name,
               direction, confidence, regime, inference_time_us,
               predicted_at
        FROM ml_predictions
        ORDER BY predicted_at DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]


async def get_model_metrics(
    pool: asyncpg.Pool,
    model_id: int | None = None,
    limit: int = 100,
) -> list[dict]:
    """Fetch model performance metrics over time."""
    if model_id:
        rows = await pool.fetch(
            """
            SELECT model_id, metric_name, metric_value, recorded_at
            FROM model_metrics
            WHERE model_id = $1
            ORDER BY recorded_at DESC
            LIMIT $2
            """,
            model_id,
            limit,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT model_id, metric_name, metric_value, recorded_at
            FROM model_metrics
            ORDER BY recorded_at DESC
            LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]
