-- ============================================================
-- 002_ml_tables.sql — Model registry and ML tracking tables
--
-- These tables support the ML Training Lab integration.
-- They are safe to apply on top of 001_init.sql.
-- ============================================================

-- Model registry: tracks versioned model checkpoints.
CREATE TABLE IF NOT EXISTS model_registry (
    id              BIGSERIAL PRIMARY KEY,
    model_name      TEXT NOT NULL,
    version         TEXT NOT NULL,
    model_type      TEXT,          -- e.g. "jepa", "gnn", "mlp", "ensemble"
    checkpoint_path TEXT NOT NULL,
    is_active       BOOLEAN DEFAULT FALSE,
    training_samples INT,
    validation_accuracy NUMERIC(7, 6),  -- e.g. 0.847923
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB DEFAULT '{}',
    UNIQUE(model_name, version)
);

-- Index for fast lookup of active model.
CREATE INDEX IF NOT EXISTS idx_model_registry_active
    ON model_registry (model_name)
    WHERE is_active = TRUE;

-- Model performance metrics over time.
CREATE TABLE IF NOT EXISTS model_metrics (
    id          BIGSERIAL PRIMARY KEY,
    model_id    BIGINT NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metric_name TEXT NOT NULL,          -- e.g. "accuracy", "sharpe", "max_drawdown"
    metric_value NUMERIC(12, 6) NOT NULL,
    metadata    JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_model_metrics_model_time
    ON model_metrics (model_id, recorded_at DESC);

-- ML predictions log: raw predictions before strategy processing.
-- Useful for the feedback loop (compare predictions vs actual outcomes).
CREATE TABLE IF NOT EXISTS ml_predictions (
    id              BIGSERIAL,
    prediction_id   UUID NOT NULL DEFAULT gen_random_uuid(),
    symbol          TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    model_version   TEXT NOT NULL,
    direction       TEXT NOT NULL,      -- "BUY", "SELL", "HOLD"
    confidence      NUMERIC(5, 4) NOT NULL,
    regime          TEXT,
    features_hash   TEXT,               -- SHA-256 of the feature snapshot
    inference_time_us INT,              -- Inference latency in microseconds
    predicted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB DEFAULT '{}',
    PRIMARY KEY (id, predicted_at)
);

-- Convert to hypertable for time-series queries.
SELECT create_hypertable('ml_predictions', 'predicted_at',
    if_not_exists => TRUE
);

-- Compress old predictions after 7 days.
ALTER TABLE ml_predictions SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,model_name',
    timescaledb.compress_orderby = 'predicted_at DESC'
);

SELECT add_compression_policy('ml_predictions', INTERVAL '7 days',
    if_not_exists => TRUE
);
