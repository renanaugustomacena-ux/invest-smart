-- ============================================================
-- 003_strategy_tables.sql — Strategy performance tracking tables
--
-- Tracks per-strategy signal history and P&L for attribution
-- analysis and strategy optimization.
-- Safe to apply on top of 001_init.sql and 002_ml_tables.sql.
-- ============================================================

-- Strategy performance: per-trade results attributed to specific strategies.
CREATE TABLE IF NOT EXISTS strategy_performance (
    id              BIGSERIAL,
    signal_id       UUID NOT NULL,
    strategy_name   TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    direction       TEXT NOT NULL,          -- "BUY" or "SELL"
    confidence      NUMERIC(5, 4) NOT NULL,
    regime          TEXT,                   -- Market regime at signal time
    source_tier     TEXT,                   -- "TECHNICAL", "STATISTICAL_PRIMARY", etc.
    entry_price     NUMERIC(20, 8),
    exit_price      NUMERIC(20, 8),
    stop_loss       NUMERIC(20, 8),
    take_profit     NUMERIC(20, 8),
    profit          NUMERIC(20, 8),         -- Realized P&L (NULL if still open)
    lots            NUMERIC(10, 4),
    status          TEXT NOT NULL DEFAULT 'OPEN',  -- OPEN, CLOSED, REJECTED
    opened_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at       TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}',
    PRIMARY KEY (id, opened_at)
);

-- Convert to hypertable for time-series queries.
SELECT create_hypertable('strategy_performance', 'opened_at',
    if_not_exists => TRUE
);

-- Index for strategy-level aggregations.
CREATE INDEX IF NOT EXISTS idx_strategy_perf_name
    ON strategy_performance (strategy_name, opened_at DESC);

-- Index for symbol-level analysis.
CREATE INDEX IF NOT EXISTS idx_strategy_perf_symbol
    ON strategy_performance (symbol, opened_at DESC);

-- Daily strategy summary: materialized view for fast dashboard queries.
CREATE MATERIALIZED VIEW IF NOT EXISTS strategy_daily_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', opened_at) AS day,
    strategy_name,
    symbol,
    COUNT(*) AS total_signals,
    COUNT(*) FILTER (WHERE profit > 0) AS wins,
    COUNT(*) FILTER (WHERE profit < 0) AS losses,
    COALESCE(SUM(profit), 0) AS total_profit,
    AVG(confidence) AS avg_confidence,
    MAX(opened_at) AS last_signal_at
FROM strategy_performance
WHERE status = 'CLOSED'
GROUP BY day, strategy_name, symbol
WITH NO DATA;

-- Refresh policy: update summary every hour.
SELECT add_continuous_aggregate_policy('strategy_daily_summary',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Compress old strategy performance data after 30 days.
ALTER TABLE strategy_performance SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'strategy_name,symbol',
    timescaledb.compress_orderby = 'opened_at DESC'
);

SELECT add_compression_policy('strategy_performance', INTERVAL '30 days',
    if_not_exists => TRUE
);
