-- F-D1: Add UNIQUE constraints to prevent duplicate market data.
-- TimescaleDB requires the partitioning column (time) in any unique constraint.

ALTER TABLE ohlcv_bars
    ADD CONSTRAINT uq_ohlcv_bars UNIQUE (time, symbol, timeframe);

ALTER TABLE market_ticks
    ADD CONSTRAINT uq_market_ticks UNIQUE (time, symbol);
