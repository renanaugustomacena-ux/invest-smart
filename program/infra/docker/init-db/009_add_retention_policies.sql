-- F-D9: Add retention policies to prevent unbounded data growth.
-- ohlcv_bars: retain 1 year of candle data (compressed after 7 days)
-- market_ticks: retain 90 days of tick data (compressed after 1 day)

SELECT add_retention_policy('ohlcv_bars', INTERVAL '365 days', if_not_exists => TRUE);
SELECT add_retention_policy('market_ticks', INTERVAL '90 days', if_not_exists => TRUE);
