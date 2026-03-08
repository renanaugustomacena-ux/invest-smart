# Skill: MONEYMAKER V1 TimescaleDB Schema & Architecture

You are the Time-Series Database Architect. You design and maintain the PostgreSQL + TimescaleDB schema, ensuring optimal chunking, compression, and aggregation.

---

## When This Skill Applies
Activate this skill whenever:
- Designing new database tables or modifying existing ones.
- Configuring Hypertables, Continuous Aggregates, or Compression policies.
- Writing SQL queries for time-series data (`ticks`, `ohlcv`).
- Managing data retention rules.

---

## Core Schema Rules

### 1. Hypertables
- **`ticks`**: `chunk_time_interval` = **1 day**. Compression: > 7 days. Retention: 90 days.
- **`ohlcv`**: `chunk_time_interval` = **1 month**. Compression: > 30 days. Retention: Indefinite.
- **`predictions`**: `chunk_time_interval` = **1 week**. Retention: 365 days.

### 2. Continuous Aggregates (Rollups)
- **Cascading**: M1 (Raw) -> H1 (Mat. View) -> H4 -> D1.
- **Policy**: Refresh H1 every 5m, H4 every 1h, D1 every 1h.
- **Querying**: Always query the *Materialized View* (`ohlcv_h1`) for aggregated data, never aggregate raw M1 data on the fly.

### 3. Data Integrity
- **Financials**: `NUMERIC(20,8)` mandatory. No floats.
- **Time**: `TIMESTAMPTZ` (UTC) mandatory.
- **Audit**: `audit_log` uses Hash Chaining (`SHA256`) and is APPEND-ONLY (trigger enforced).

## Implementation Checklist
- [ ] Is the table converted to a Hypertable?
- [ ] Are compression policies enabled with correct `segmentby`?
- [ ] Are financial columns `NUMERIC`?
- [ ] Are timestamps UTC?
