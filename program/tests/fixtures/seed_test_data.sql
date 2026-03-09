-- MONEYMAKER Test Fixtures
-- Deterministic test data for integration and E2E tests.
-- All timestamps, prices, and values are fixed for reproducibility.

-- Sample OHLCV bars for XAUUSD (Gold), M1 timeframe
INSERT INTO ohlcv_bars (symbol, timeframe, time, open, high, low, close, volume, tick_count, complete, spread_avg)
VALUES
    ('XAUUSD', 'M1', '2025-01-15 12:00:00+00', 2650.50, 2651.80, 2649.20, 2651.00, 1500, 45, true, 0.30),
    ('XAUUSD', 'M1', '2025-01-15 12:01:00+00', 2651.00, 2652.30, 2650.50, 2652.10, 1200, 38, true, 0.28),
    ('XAUUSD', 'M1', '2025-01-15 12:02:00+00', 2652.10, 2653.00, 2651.80, 2652.80, 1350, 42, true, 0.32),
    ('XAUUSD', 'M1', '2025-01-15 12:03:00+00', 2652.80, 2653.50, 2652.00, 2652.30, 1100, 35, true, 0.29),
    ('XAUUSD', 'M1', '2025-01-15 12:04:00+00', 2652.30, 2653.20, 2651.50, 2653.00, 1400, 40, true, 0.31)
ON CONFLICT DO NOTHING;

-- Sample trading signals
INSERT INTO trading_signals (signal_id, symbol, direction, confidence, suggested_lots, stop_loss, take_profit, regime, source_tier, reasoning, created_at)
VALUES
    ('test-signal-001', 'XAUUSD', 'BUY', 0.72, 0.05, 2645.00, 2665.00, 'trending_up', 'TECHNICAL', 'RSI oversold bounce + EMA crossover', '2025-01-15 12:05:00+00'),
    ('test-signal-002', 'XAUUSD', 'SELL', 0.65, 0.03, 2660.00, 2640.00, 'trending_down', 'TECHNICAL', 'Bearish divergence + resistance rejection', '2025-01-15 13:00:00+00')
ON CONFLICT DO NOTHING;
