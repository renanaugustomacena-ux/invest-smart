-- MONEYMAKER V1 Economic Calendar Schema
-- Stores economic events for trading blackout management and event-driven analysis.
--
-- Primary use cases:
--   1. Automatic trading blackout during high-impact events (NFP, FOMC, etc.)
--   2. Event-driven feature engineering for ML models
--   3. Historical analysis of market reactions to economic releases

-- Enable TimescaleDB extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- Economic Events Table
-- ============================================================
-- Stores economic calendar events from providers like Finnhub.
-- Each event has impact level, expected/actual values, and timing.
CREATE TABLE IF NOT EXISTS economic_events (
    id              BIGSERIAL,
    event_id        TEXT            NOT NULL,         -- Provider's unique ID
    event_name      TEXT            NOT NULL,         -- e.g., "Nonfarm Payrolls"
    country         TEXT            NOT NULL,         -- ISO 3166-1 alpha-2, e.g., "US"
    currency        TEXT            NOT NULL,         -- e.g., "USD"
    event_time      TIMESTAMPTZ     NOT NULL,         -- Scheduled release time
    impact          TEXT            NOT NULL,         -- "low", "medium", "high"
    unit            TEXT,                             -- e.g., "K", "%", "B"
    previous_value  TEXT,                             -- Previous release value
    forecast_value  TEXT,                             -- Market consensus forecast
    actual_value    TEXT,                             -- Actual released value (NULL until release)
    surprise        NUMERIC(15,5),                    -- actual - forecast (calculated)
    source          TEXT            NOT NULL DEFAULT 'finnhub',
    fetched_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, event_time),
    UNIQUE (event_id, event_time)
);

-- Convert to TimescaleDB hypertable for efficient time-series queries
SELECT create_hypertable('economic_events', 'event_time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Indices for common query patterns
CREATE INDEX IF NOT EXISTS idx_econ_events_currency_time
    ON economic_events (currency, event_time DESC);

CREATE INDEX IF NOT EXISTS idx_econ_events_impact_time
    ON economic_events (impact, event_time DESC)
    WHERE impact = 'high';

CREATE INDEX IF NOT EXISTS idx_econ_events_country_time
    ON economic_events (country, event_time DESC);

-- ============================================================
-- Trading Blackout Windows
-- ============================================================
-- Pre-computed blackout windows for fast lookup during trading decisions.
-- Generated from economic_events based on impact level and event type.
CREATE TABLE IF NOT EXISTS trading_blackouts (
    id              BIGSERIAL,
    event_id        TEXT            NOT NULL, -- REFERENCES economic_events cannot verify easily across partitions, handled in logic
    symbol          TEXT            NOT NULL,         -- Affected trading symbol, e.g., "XAU/USD"
    blackout_start  TIMESTAMPTZ     NOT NULL,         -- When to stop trading
    blackout_end    TIMESTAMPTZ     NOT NULL,         -- When to resume trading
    reason          TEXT            NOT NULL,         -- e.g., "FOMC Rate Decision"
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, blackout_start)
);

SELECT create_hypertable('trading_blackouts', 'blackout_start',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_blackouts_symbol_time
    ON trading_blackouts (symbol, blackout_start, blackout_end);

-- ============================================================
-- Event Impact Rules
-- ============================================================
-- Configurable rules for determining blackout windows per event type.
-- This allows fine-tuning without code changes.
CREATE TABLE IF NOT EXISTS event_impact_rules (
    id                  SERIAL          PRIMARY KEY,
    event_pattern       TEXT            NOT NULL,     -- Regex pattern, e.g., ".*Nonfarm.*"
    country             TEXT,                         -- NULL = all countries
    min_impact          TEXT            NOT NULL,     -- Minimum impact to apply rule
    pre_event_minutes   INTEGER         NOT NULL DEFAULT 30,
    post_event_minutes  INTEGER         NOT NULL DEFAULT 30,
    affected_symbols    TEXT[]          NOT NULL,     -- Array of symbols, e.g., {"XAU/USD", "EUR/USD"}
    enabled             BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Insert default rules for major economic events
INSERT INTO event_impact_rules (event_pattern, country, min_impact, pre_event_minutes, post_event_minutes, affected_symbols)
VALUES
    -- US Major Events
    ('.*Nonfarm Payrolls.*', 'US', 'high', 30, 30, ARRAY['XAU/USD', 'EUR/USD', 'GBP/USD', 'USD/JPY']),
    ('.*CPI.*', 'US', 'high', 30, 30, ARRAY['XAU/USD', 'EUR/USD', 'GBP/USD', 'USD/JPY']),
    ('.*GDP.*', 'US', 'high', 30, 30, ARRAY['XAU/USD', 'EUR/USD', 'GBP/USD']),
    ('.*FOMC.*', 'US', 'high', 30, 60, ARRAY['XAU/USD', 'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'NZD/USD', 'USD/CAD', 'USD/CHF']),
    ('.*Fed.*Chair.*', 'US', 'high', 15, 30, ARRAY['XAU/USD', 'EUR/USD', 'GBP/USD', 'USD/JPY']),
    ('.*Initial Jobless Claims.*', 'US', 'medium', 10, 15, ARRAY['XAU/USD', 'EUR/USD']),
    ('.*Retail Sales.*', 'US', 'high', 15, 15, ARRAY['XAU/USD', 'EUR/USD']),
    ('.*PPI.*', 'US', 'medium', 15, 15, ARRAY['XAU/USD']),

    -- ECB Events
    ('.*ECB.*Rate.*', 'EU', 'high', 30, 60, ARRAY['EUR/USD', 'XAU/USD', 'GBP/USD']),
    ('.*ECB.*President.*', 'EU', 'high', 15, 30, ARRAY['EUR/USD', 'XAU/USD']),

    -- Bank of England
    ('.*BoE.*Rate.*', 'GB', 'high', 30, 60, ARRAY['GBP/USD', 'XAU/USD', 'EUR/USD']),
    ('.*BoE.*Governor.*', 'GB', 'high', 15, 30, ARRAY['GBP/USD']),

    -- Bank of Japan
    ('.*BoJ.*Rate.*', 'JP', 'high', 30, 60, ARRAY['USD/JPY', 'XAU/USD']),

    -- Generic high-impact catch-all
    ('.*', NULL, 'high', 15, 15, ARRAY['XAU/USD'])
ON CONFLICT DO NOTHING;

-- ============================================================
-- Functions for Blackout Management
-- ============================================================

-- Function to check if trading is blacked out for a symbol
CREATE OR REPLACE FUNCTION is_trading_blacked_out(
    p_symbol TEXT,
    p_check_time TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    blacked_out BOOLEAN,
    reason TEXT,
    blackout_end TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        TRUE AS blacked_out,
        tb.reason,
        tb.blackout_end
    FROM trading_blackouts tb
    WHERE tb.symbol = p_symbol
      AND p_check_time >= tb.blackout_start
      AND p_check_time <= tb.blackout_end
    ORDER BY tb.blackout_end DESC
    LIMIT 1;

    -- If no rows returned, symbol is not blacked out
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::TEXT, NULL::TIMESTAMPTZ;
    END IF;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to generate blackout windows from events
CREATE OR REPLACE FUNCTION generate_blackouts_for_event(
    p_event_id TEXT
)
RETURNS INTEGER AS $$
DECLARE
    v_event RECORD;
    v_rule RECORD;
    v_count INTEGER := 0;
    v_symbol TEXT;
BEGIN
    -- Get the event
    SELECT * INTO v_event FROM economic_events WHERE event_id = p_event_id;
    IF NOT FOUND THEN
        RETURN 0;
    END IF;

    -- Find matching rules
    FOR v_rule IN
        SELECT * FROM event_impact_rules
        WHERE enabled = TRUE
          AND (country IS NULL OR country = v_event.country)
          AND v_event.event_name ~* event_pattern
          AND (
              (min_impact = 'high' AND v_event.impact = 'high') OR
              (min_impact = 'medium' AND v_event.impact IN ('high', 'medium')) OR
              (min_impact = 'low')
          )
        ORDER BY
            CASE WHEN country IS NOT NULL THEN 0 ELSE 1 END,  -- Prefer country-specific
            CASE min_impact WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END
    LOOP
        -- Insert blackout for each affected symbol
        FOREACH v_symbol IN ARRAY v_rule.affected_symbols
        LOOP
            INSERT INTO trading_blackouts (
                event_id, symbol, blackout_start, blackout_end, reason
            ) VALUES (
                p_event_id,
                v_symbol,
                v_event.event_time - (v_rule.pre_event_minutes || ' minutes')::INTERVAL,
                v_event.event_time + (v_rule.post_event_minutes || ' minutes')::INTERVAL,
                v_event.event_name || ' (' || v_event.country || ')'
            )
            ON CONFLICT DO NOTHING;

            v_count := v_count + 1;
        END LOOP;
    END LOOP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-generate blackouts when events are inserted
CREATE OR REPLACE FUNCTION trigger_generate_blackouts()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM generate_blackouts_for_event(NEW.event_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_generate_blackouts
    AFTER INSERT ON economic_events
    FOR EACH ROW
    EXECUTE FUNCTION trigger_generate_blackouts();

-- ============================================================
-- Views for Convenience
-- ============================================================

-- Upcoming high-impact events
CREATE OR REPLACE VIEW upcoming_high_impact_events AS
SELECT
    event_id,
    event_name,
    country,
    currency,
    event_time,
    forecast_value,
    previous_value,
    (event_time - NOW()) AS time_until
FROM economic_events
WHERE event_time > NOW()
  AND impact = 'high'
ORDER BY event_time
LIMIT 50;

-- Active blackouts right now
CREATE OR REPLACE VIEW active_blackouts AS
SELECT
    tb.symbol,
    tb.reason,
    tb.blackout_start,
    tb.blackout_end,
    (tb.blackout_end - NOW()) AS time_remaining
FROM trading_blackouts tb
WHERE NOW() BETWEEN tb.blackout_start AND tb.blackout_end
ORDER BY tb.blackout_end;

-- ============================================================
-- Compression Policy
-- ============================================================
ALTER TABLE economic_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'country,impact'
);

SELECT add_compression_policy('economic_events', INTERVAL '30 days', if_not_exists => TRUE);

ALTER TABLE trading_blackouts SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('trading_blackouts', INTERVAL '7 days', if_not_exists => TRUE);
