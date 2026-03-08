# Skill: Market Data Normalization & Quality

You are the Data Quality Engineer. You ensure that raw, chaotic exchange data is transformed into a pristine, unified format for the MONEYMAKER ecosystem.

---

## When This Skill Applies
Activate this skill whenever:
- Implementing data adapters (Binance, Bybit, MT5).
- Defining data structures (`MarketTick`, `OHLCV`).
- Debugging data anomalies (stale prices, spikes).
- Configuring symbol mappings.

---

## The Unified Data Model

### 1. MarketTick
- **Symbol**: Normalized (e.g., `BTCUSD`, `XAUUSD`). Uppercase, no separators.
- **Timestamp**: UTC Milliseconds (`int64`).
- **Price/Vol**: Decimal strings or types.
- **Source**: Lowercase identifier (`binance`, `mt5`).

### 2. Normalization Rules
- **Symbols**: Map `BTCUSDT` -> `BTCUSD`. Treat USDT as USD.
- **Time**: Convert all source timestamps (ISO8601, Unix Sec) to **Unix Milliseconds UTC**.
- **Clock Skew**: Reject ticks with timestamp delta > 30s vs local clock.

### 3. Data Quality Gates
- **Stale Data**: Alert if no tick for > 30s (Crypto) / 60s (Forex).
- **Negative Spread**: `Ask < Bid` -> **DISCARD** and log.
- **Zero Price**: `Price == 0` -> **DISCARD** and log.
- **Anomaly**: Price deviation > 10% from last tick -> Buffer and verify.

## Checklist
- [ ] Are symbols normalized (no 'USDT')?
- [ ] Are timestamps definitely UTC milliseconds?
- [ ] Is the negative spread check active?
- [ ] Are duplicates deduplicated?
