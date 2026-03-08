-- MONEYMAKER V1 Macro Data Schema
-- Stores quantitative macro indicators for feature engineering and regime detection.
--
-- Data sources:
--   - FRED API: Yield curve, real rates, recession probability
--   - CBOE: VIX spot and term structure
--   - CFTC: Commitment of Traders (COT) reports
--   - Polygon/Other: DXY index changes
--
-- Design principles:
--   1. Only QUANTITATIVE data - no sentiment scores or news
--   2. Deterministic and verifiable - can be cross-checked
--   3. Mathematically precise - no subjective interpretation

-- Enable TimescaleDB extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- VIX Data (Fear/Volatility Index)
-- ============================================================
-- VIX is critical for Gold trading: panic = gold up
-- Term structure (contango/backwardation) signals regime
CREATE TABLE IF NOT EXISTS vix_data (
    time            TIMESTAMPTZ     NOT NULL,
    vix_spot        NUMERIC(10,4)   NOT NULL,     -- VIX spot price
    vix_1m          NUMERIC(10,4),                -- 1-month VIX future
    vix_2m          NUMERIC(10,4),                -- 2-month VIX future
    vix_3m          NUMERIC(10,4),                -- 3-month VIX future
    term_slope      NUMERIC(10,6),                -- (VIX_2m - VIX_spot) / VIX_spot
    is_contango     BOOLEAN,                      -- TRUE if term_slope > 0
    regime          SMALLINT        DEFAULT 0,    -- 0=calm, 1=elevated, 2=panic
    source          TEXT            NOT NULL DEFAULT 'cboe',
    fetched_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('vix_data', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_vix_time ON vix_data (time DESC);

-- VIX regime classification logic (calculated on insert/update)
-- calm: VIX < 15
-- elevated: 15 <= VIX < 25
-- panic: VIX >= 25
CREATE OR REPLACE FUNCTION calculate_vix_regime(vix_val NUMERIC)
RETURNS SMALLINT AS $$
BEGIN
    IF vix_val >= 25 THEN
        RETURN 2;  -- panic
    ELSIF vix_val >= 15 THEN
        RETURN 1;  -- elevated
    ELSE
        RETURN 0;  -- calm
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger to auto-calculate regime and term structure on insert
CREATE OR REPLACE FUNCTION vix_auto_calculate()
RETURNS TRIGGER AS $$
BEGIN
    NEW.regime := calculate_vix_regime(NEW.vix_spot);

    IF NEW.vix_2m IS NOT NULL AND NEW.vix_spot > 0 THEN
        NEW.term_slope := (NEW.vix_2m - NEW.vix_spot) / NEW.vix_spot;
        NEW.is_contango := NEW.term_slope > 0;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER vix_calc_trigger
    BEFORE INSERT OR UPDATE ON vix_data
    FOR EACH ROW
    EXECUTE FUNCTION vix_auto_calculate();

-- ============================================================
-- Yield Curve Data (Treasury Rates)
-- ============================================================
-- Yield curve inversion is a leading recession indicator
-- Affects Gold: recession fear = flight to safety = gold up
CREATE TABLE IF NOT EXISTS yield_curve_data (
    time            TIMESTAMPTZ     NOT NULL,
    rate_2y         NUMERIC(8,4),                 -- 2-year Treasury yield
    rate_5y         NUMERIC(8,4),                 -- 5-year Treasury yield
    rate_10y        NUMERIC(8,4)    NOT NULL,     -- 10-year Treasury yield
    rate_30y        NUMERIC(8,4),                 -- 30-year Treasury yield
    spread_2s10s    NUMERIC(8,4),                 -- 10Y - 2Y spread
    spread_5s30s    NUMERIC(8,4),                 -- 30Y - 5Y spread
    is_inverted     BOOLEAN,                      -- TRUE if 2s10s < 0
    inversion_depth NUMERIC(8,4),                 -- How deep (negative = inverted)
    source          TEXT            NOT NULL DEFAULT 'fred',
    fetched_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('yield_curve_data', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_yield_time ON yield_curve_data (time DESC);

-- Auto-calculate spreads on insert
CREATE OR REPLACE FUNCTION yield_auto_calculate()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.rate_2y IS NOT NULL AND NEW.rate_10y IS NOT NULL THEN
        NEW.spread_2s10s := NEW.rate_10y - NEW.rate_2y;
        NEW.is_inverted := NEW.spread_2s10s < 0;
        IF NEW.is_inverted THEN
            NEW.inversion_depth := NEW.spread_2s10s;
        END IF;
    END IF;

    IF NEW.rate_5y IS NOT NULL AND NEW.rate_30y IS NOT NULL THEN
        NEW.spread_5s30s := NEW.rate_30y - NEW.rate_5y;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER yield_calc_trigger
    BEFORE INSERT OR UPDATE ON yield_curve_data
    FOR EACH ROW
    EXECUTE FUNCTION yield_auto_calculate();

-- ============================================================
-- Real Rates (Inflation-Adjusted)
-- ============================================================
-- Real rates = Nominal yield - Inflation expectation
-- Negative real rates historically bullish for Gold
CREATE TABLE IF NOT EXISTS real_rates_data (
    time            TIMESTAMPTZ     NOT NULL,
    nominal_10y     NUMERIC(8,4)    NOT NULL,     -- Nominal 10Y yield
    breakeven_10y   NUMERIC(8,4)    NOT NULL,     -- 10Y inflation expectation (TIPS spread)
    real_rate_10y   NUMERIC(8,4)    NOT NULL,     -- nominal - breakeven
    nominal_5y      NUMERIC(8,4),
    breakeven_5y    NUMERIC(8,4),
    real_rate_5y    NUMERIC(8,4),
    source          TEXT            NOT NULL DEFAULT 'fred',
    fetched_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('real_rates_data', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_real_rates_time ON real_rates_data (time DESC);

-- ============================================================
-- Dollar Index (DXY) Changes
-- ============================================================
-- Gold has strong inverse correlation with USD
-- DXY strength = Gold weakness (typically)
CREATE TABLE IF NOT EXISTS dxy_data (
    time            TIMESTAMPTZ     NOT NULL,
    dxy_value       NUMERIC(10,4)   NOT NULL,     -- DXY index value
    change_1h_pct   NUMERIC(8,4),                 -- % change in last hour
    change_24h_pct  NUMERIC(8,4),                 -- % change in last 24h
    change_7d_pct   NUMERIC(8,4),                 -- % change in last 7 days
    sma_20          NUMERIC(10,4),                -- 20-period SMA
    trend_direction SMALLINT,                     -- -1=down, 0=neutral, 1=up
    source          TEXT            NOT NULL DEFAULT 'polygon',
    fetched_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('dxy_data', 'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_dxy_time ON dxy_data (time DESC);

-- ============================================================
-- COT Reports (Commitment of Traders)
-- ============================================================
-- Shows positioning of different trader categories
-- Large speculator positioning can signal sentiment extremes
CREATE TABLE IF NOT EXISTS cot_reports (
    time                    TIMESTAMPTZ     NOT NULL,     -- Report date
    market                  TEXT            NOT NULL,     -- e.g., "GOLD", "SILVER", "EUR"
    -- Asset Managers (the "smart money")
    asset_mgr_long          BIGINT,
    asset_mgr_short         BIGINT,
    asset_mgr_net           BIGINT,                       -- long - short
    asset_mgr_pct_oi        NUMERIC(8,4),                 -- % of total open interest
    -- Leveraged Funds (hedge funds)
    lev_funds_long          BIGINT,
    lev_funds_short         BIGINT,
    lev_funds_net           BIGINT,
    lev_funds_pct_oi        NUMERIC(8,4),
    -- Other Reportables
    other_long              BIGINT,
    other_short             BIGINT,
    -- Total Open Interest
    total_oi                BIGINT          NOT NULL,
    -- Computed sentiment
    cot_sentiment           SMALLINT,                     -- -1=bearish, 0=neutral, 1=bullish
    extreme_reading         BOOLEAN,                      -- TRUE if >90th or <10th percentile
    source                  TEXT            NOT NULL DEFAULT 'cftc',
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('cot_reports', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_cot_market_time ON cot_reports (market, time DESC);

-- ============================================================
-- Recession Probability (Fed Model)
-- ============================================================
-- NY Fed publishes recession probability model based on yield curve
CREATE TABLE IF NOT EXISTS recession_probability (
    time                TIMESTAMPTZ     NOT NULL,
    probability_12m     NUMERIC(8,4)    NOT NULL,     -- % probability in next 12 months
    probability_change  NUMERIC(8,4),                 -- Change from prior reading
    signal_level        SMALLINT,                     -- 0=low, 1=elevated, 2=high
    source              TEXT            NOT NULL DEFAULT 'fred',
    fetched_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('recession_probability', 'time',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_recession_time ON recession_probability (time DESC);

-- ============================================================
-- Macro Snapshots (Aggregated Latest Values)
-- ============================================================
-- Materialized view for quick lookup of current macro state
CREATE MATERIALIZED VIEW IF NOT EXISTS macro_snapshot AS
SELECT
    NOW() AS snapshot_time,
    -- VIX
    (SELECT vix_spot FROM vix_data ORDER BY time DESC LIMIT 1) AS vix_spot,
    (SELECT regime FROM vix_data ORDER BY time DESC LIMIT 1) AS vix_regime,
    (SELECT is_contango FROM vix_data ORDER BY time DESC LIMIT 1) AS vix_contango,
    -- Yield Curve
    (SELECT spread_2s10s FROM yield_curve_data ORDER BY time DESC LIMIT 1) AS yield_slope_2s10s,
    (SELECT is_inverted FROM yield_curve_data ORDER BY time DESC LIMIT 1) AS curve_inverted,
    -- Real Rates
    (SELECT real_rate_10y FROM real_rates_data ORDER BY time DESC LIMIT 1) AS real_rate_10y,
    -- DXY
    (SELECT change_1h_pct FROM dxy_data ORDER BY time DESC LIMIT 1) AS dxy_change_1h_pct,
    (SELECT trend_direction FROM dxy_data ORDER BY time DESC LIMIT 1) AS dxy_trend,
    -- COT Gold
    (SELECT asset_mgr_pct_oi FROM cot_reports WHERE market = 'GOLD' ORDER BY time DESC LIMIT 1) AS cot_gold_asset_mgr_pct,
    (SELECT cot_sentiment FROM cot_reports WHERE market = 'GOLD' ORDER BY time DESC LIMIT 1) AS cot_gold_sentiment,
    -- Recession
    (SELECT probability_12m FROM recession_probability ORDER BY time DESC LIMIT 1) AS recession_prob_12m
WITH NO DATA;

-- Create unique index for refresh concurrently
CREATE UNIQUE INDEX IF NOT EXISTS idx_macro_snapshot_time ON macro_snapshot (snapshot_time);

-- Function to refresh snapshot
CREATE OR REPLACE FUNCTION refresh_macro_snapshot()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY macro_snapshot;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Compression Policies
-- ============================================================
ALTER TABLE vix_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'source'
);
SELECT add_compression_policy('vix_data', INTERVAL '7 days', if_not_exists => TRUE);

ALTER TABLE yield_curve_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'source'
);
SELECT add_compression_policy('yield_curve_data', INTERVAL '30 days', if_not_exists => TRUE);

ALTER TABLE real_rates_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'source'
);
SELECT add_compression_policy('real_rates_data', INTERVAL '30 days', if_not_exists => TRUE);

ALTER TABLE dxy_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'source'
);
SELECT add_compression_policy('dxy_data', INTERVAL '7 days', if_not_exists => TRUE);

ALTER TABLE cot_reports SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'market'
);
SELECT add_compression_policy('cot_reports', INTERVAL '90 days', if_not_exists => TRUE);

ALTER TABLE recession_probability SET (
    timescaledb.compress
);
SELECT add_compression_policy('recession_probability', INTERVAL '365 days', if_not_exists => TRUE);

-- ============================================================
-- Data Retention Policies
-- ============================================================
-- Keep tick-level macro data for 1 year, summaries forever
SELECT add_retention_policy('vix_data', INTERVAL '365 days', if_not_exists => TRUE);
SELECT add_retention_policy('dxy_data', INTERVAL '365 days', if_not_exists => TRUE);
-- Keep daily summaries longer
SELECT add_retention_policy('yield_curve_data', INTERVAL '5 years', if_not_exists => TRUE);
SELECT add_retention_policy('real_rates_data', INTERVAL '5 years', if_not_exists => TRUE);
SELECT add_retention_policy('cot_reports', INTERVAL '10 years', if_not_exists => TRUE);
SELECT add_retention_policy('recession_probability', INTERVAL '10 years', if_not_exists => TRUE);
