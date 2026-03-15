# MONEYMAKER V1 — System Vision and Architecture Overview

> **Module 01** | System Architecture Reference

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Communication Patterns](#4-communication-patterns)
5. [Design Principles](#5-design-principles)
6. [Service Boundaries](#6-service-boundaries)
7. [Algo Engine Subsystem Map](#7-algo-engine-subsystem-map)
8. [End-to-End Signal Lifecycle](#8-end-to-end-signal-lifecycle)
9. [Configuration Architecture](#9-configuration-architecture)
10. [Port Reference](#10-port-reference)

---

## 1. Executive Summary

MONEYMAKER V1 is an autonomous algorithmic trading ecosystem built as a microservices architecture. It ingests real-time market data from Polygon.io (Forex/CFD), applies technical analysis with regime-aware strategy routing, generates validated trading signals, and executes trades through MetaTrader 5.

The system is designed around three pillars:

- **Data Intelligence** — High-throughput market data ingestion, normalization, and multi-timeframe OHLCV aggregation (Go)
- **Algo Engine** — Regime classification, 4-tier strategy cascade, signal generation with 10-point validation (Python)
- **Trade Execution** — Risk-enforced order management with position tracking and trailing stops (Python)

All financial calculations use Decimal arithmetic (never floating point). The system defaults to HOLD when uncertain — capital preservation is the top priority.

---

## 2. System Architecture

```
                    ┌──────────────────────────────────────────────────────┐
                    │                  MONEYMAKER V1 Stack                    │
                    ├──────────────────────────────────────────────────────┤
                    │                                                      │
  Polygon.io ──WS──>  Data Ingestion (Go)  ──ZMQ PUB/SUB──>  Algo Engine (Python)
                         port 5555                              port 50054
                            │                                       │
                            v                                       │ gRPC
                      TimescaleDB (PG16)                            v
                        port 5432                            MT5 Bridge (Python)
                            │                                  port 50055
                      Redis (cache)                                │
                        port 6379                                  v
                            │                                   Broker
                      Prometheus ──scrape──> all services          (MT5)
                        port 9091
                            │
                      Grafana (dashboards)
                        port 3000

```

Four core services plus monitoring infrastructure:

| Service | Language | Role |
|---|---|---|
| **Data Ingestion** | Go 1.22+ | Connects to Polygon.io via WebSocket, normalizes data, aggregates OHLCV bars, publishes via ZeroMQ |
| **Algo Engine** | Python 3.11+ | 17 subdirectories, 130+ Python files. Computes indicators, classifies regime, routes to strategies, validates and emits signals |
| **MT5 Bridge** | Python 3.11+ | Receives signals via gRPC, enforces risk limits, executes orders through MetaTrader 5 |
---

## 3. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Data Ingestion | Go | 1.22+ |
| Algo Engine | Python | 3.11+ |
| MT5 Bridge | Python | 3.11+ |
| Database | TimescaleDB (PostgreSQL) | 16 |
| Cache | Redis | 7 |
| IPC (data stream) | ZeroMQ PUB/SUB | latest |
| RPC (service calls) | gRPC + Protobuf | proto3 |
| Financial precision | shopspring/decimal (Go), decimal.Decimal (Python) | — |
| Monitoring | Prometheus | 2.50.1 |
| Dashboards | Grafana | 10.3.3 |
| Containers | Docker Compose | — |
| Logging | structlog (Python), zap (Go) | — |
| Config | Pydantic Settings (Python), env + YAML (Go) | — |
| Code quality | Black, Ruff, MyPy (Python); golangci-lint (Go) | — |
| CI/CD | GitHub Actions | — |

---

## 4. Communication Patterns

### ZeroMQ PUB/SUB — Market Data Distribution

- **Publisher**: Data Ingestion binds on `tcp://*:5555`
- **Subscriber**: Algo Engine connects via `BRAIN_ZMQ_DATA_FEED` env var
- **Tick topic format**: `{eventType}.{exchange}.{symbol}` (e.g., `trade.polygon.XAU/USD`)
- **Bar topic format**: `bar.{symbol}.{timeframe}` (e.g., `bar.XAU/USD.M1`)
- **Payload**: JSON with string-encoded Decimal values
- **Use case**: High-throughput, low-latency market data fan-out

### gRPC + Protobuf — Service-to-Service Calls

- **Algo Engine -> MT5 Bridge**: `TradingSignalService.SendSignal()` (signal dispatch)
- **All services**: `HealthCheckService` (standardized health protocol)
- **Contracts**: 5 `.proto` files in `shared/proto/`
- **Decimal encoding**: All financial values as strings in protobuf (never float/double)

### PostgreSQL + Redis — Shared State

- **TimescaleDB**: Historical OHLCV, ticks, signals, executions, audit log, strategy performance
- **Redis**: Real-time price cache (TTL 300s), portfolio state, signal deduplication, kill switch flag

---

## 5. Design Principles

### Decimal Everywhere

All financial values use `decimal.Decimal` (Python) or `shopspring/decimal` (Go). Protobuf encodes financial fields as strings. No floating-point arithmetic touches money.

### Fail-Safe HOLD

When the system is uncertain — ML unavailable, low confidence, unknown regime, high volatility — the default action is HOLD (do nothing). Capital preservation overrides profit seeking.

### Append-Only Audit

Every trading decision is logged to an immutable audit trail with SHA-256 hash chain. PostgreSQL triggers prevent UPDATE/DELETE on the `audit_log` table. Formula: `hash = SHA256(prev_hash | service | action | details | timestamp)`.

### ML-Optional Architecture

All ML features use graceful degradation via protected imports. If `import` fails or the ML service is down, the system falls back to rule-based strategies automatically. 11 optional modules can individually fail without affecting the core pipeline.

### Defense in Depth

Risk management operates at multiple layers:

1. Signal validation (10 checks in SignalValidator)
2. Kill switch (Redis-based, instant halt)
3. Circuit breakers (ML service, 5-failure threshold)
4. Position limits (`BRAIN_MAX_OPEN_POSITIONS`)
5. Drawdown caps (`BRAIN_MAX_DRAWDOWN_PCT`)
6. Rate limiting (`BRAIN_MAX_SIGNALS_PER_HOUR`)
7. Signal deduplication (60s window in MT5 Bridge)
8. Lot size clamping (min/max enforcement)
9. Signal age validation (reject stale signals)
10. Correlation checks (cross-pair exposure)

---

## 6. Service Boundaries

| Service | Owns | Does NOT Own |
|---|---|---|
| Data Ingestion | Exchange connections, normalization, OHLCV aggregation (M1/M5/M15/H1 runtime), tick persistence, Redis price cache | Feature computation, trading decisions |
| Algo Engine | Feature pipeline, regime classification, strategy routing (4-tier cascade), signal generation and validation, analysis, coaching, knowledge graph | Order execution, broker connectivity |
| MT5 Bridge | Order placement, position tracking, trailing stops, signal dedup, risk enforcement at execution | Market data, feature computation, strategy selection |
| Monitoring | Prometheus scraping, Grafana dashboards, alerting | Application logic |

---

## 7. Algo Engine Subsystem Map

The Algo Engine is the largest service (17 subdirectories, 130+ Python files). Its major subsystems:

```
algo_engine/
├── main.py                    # Entry point, protected imports (11 optional modules)
├── features/                  # Feature engineering pipeline
│   ├── regime_ensemble        # Market regime classification
│   ├── data_sanity            # Data quality validation
│   ├── feature_drift          # Feature distribution monitoring
│   └── market_vectorizer      # Market state vectorization
├── strategies/                # Trading strategy implementations
│   ├── coper_strategy         # Tier 1: COPER (primary)
│   ├── hybrid_strategy        # Tier 2: Hybrid ML + rules
│   ├── knowledge_strategy     # Tier 3: Knowledge-based
│   └── conservative_strategy  # Tier 4: Conservative fallback
├── signal/                    # Signal generation and validation
│   ├── signal_generator       # Creates TradingSignal with ATR-based SL/TP
│   └── signal_validator       # 10-point risk validation
├── regime/                    # Market regime classification and routing
│   ├── regime_classifier      # 5 regimes: TRENDING_UP/DOWN, RANGING, VOLATILE, UNKNOWN
│   └── regime_router          # Routes to best strategy per regime
├── analysis/                  # Post-trade and real-time analysis
├── coaching/                  # Trading improvement suggestions
├── knowledge/                 # Knowledge graph and pattern recognition
├── ml_lifecycle/              # ML model management (optional)
└── grpc_server/               # gRPC service interface
```

### 4-Tier Strategy Cascade

The Algo Engine uses a 4-tier fallback for signal generation:

1. **COPER** — Primary strategy (highest confidence signals)
2. **Hybrid** — ML + rule-based fusion (when ML service available)
3. **Knowledge** — Knowledge graph pattern matching
4. **Conservative** — Rule-based fallback (always available, lowest risk)

If a higher tier cannot produce a signal with sufficient confidence, the system falls through to the next tier. If all tiers produce HOLD, no signal is emitted.

---

## 8. End-to-End Signal Lifecycle

```
 1. Polygon.io sends tick via WebSocket
 2. Data Ingestion normalizes to canonical format (Decimal, BASE/QUOTE)
 3. Aggregator accumulates ticks into OHLCV bar (M1/M5/M15/H1)
 4. Completed bar published via ZMQ: topic "bar.XAU/USD.M15"
 5. Algo Engine receives bar, computes indicators (RSI, EMA, MACD, BB, ATR, ADX, ...)
 6. RegimeClassifier determines market state (e.g., TRENDING_UP)
 7. RegimeRouter selects strategy tier (e.g., COPER → TrendFollowingStrategy)
 8. Strategy generates SignalSuggestion (BUY, confidence 0.72)
 9. SignalGenerator creates full TradingSignal with ATR-based SL/TP
10. SignalValidator runs 10 risk checks (kill switch, drawdown, position limit, ...)
11. If all checks pass: gRPC SendSignal() to MT5 Bridge
12. MT5 Bridge validates signal age, deduplicates, clamps lot size
13. OrderManager sends MARKET order to MT5 terminal
14. PositionTracker monitors open position, manages trailing stop
15. On close: P&L recorded to trade_executions table
16. Audit log captures every step with SHA-256 hash chain
```

---

## 9. Configuration Architecture

Configuration flows through three layers (highest priority wins):

### Layer 1: Environment Variables (highest priority)

Set via `.env` file or Docker Compose `environment:` block. All prefixed with `MONEYMAKER_` or service-specific prefixes (`BRAIN_`, `MT5_`).

### Layer 2: YAML Config Files

- `services/data-ingestion/config.yaml` — exchange connections, aggregation, database batch settings
- `configs/development/` and `configs/production/` — environment-specific overrides

### Layer 3: Code Defaults (lowest priority)

Pydantic `BaseSettings` (Python) and `LoadBaseConfig()` (Go) define sensible defaults for all settings. The system runs with zero configuration in development mode (uses mock connector, local DB).

### Key Config Inheritance

```
Code defaults → YAML config → Environment variables → Docker Compose env
                                                        (highest priority)
```

---

## 10. Port Reference

| Service | Port | Protocol | Purpose |
|---|---|---|---|
| Data Ingestion | 5555 | ZMQ | Market data PUB socket |
| Data Ingestion | 9090 | HTTP | Prometheus metrics |
| Data Ingestion | 8081 (host) → 8080 (container) | HTTP | Health checks |
| Algo Engine | 50054 | gRPC | Signal service |
| Algo Engine | 8080 | HTTP | REST API + health checks |
| Algo Engine | 9093 | HTTP | Prometheus metrics |
| MT5 Bridge | 50055 | gRPC | Signal reception |
| MT5 Bridge | 9094 | HTTP | Prometheus metrics |
| PostgreSQL | 5432 | TCP | Database |
| Redis | 6379 | TCP | Cache |
| Prometheus | 9091 (host) → 9090 (container) | HTTP | Metrics collection |
| Grafana | 3000 | HTTP | Dashboards |

---

## Cross-References

| Topic | Module |
|---|---|
| Infrastructure and Docker Compose | [Module 02](02_Infrastructure_and_Proxmox_Server_Setup.md) |
| Microservices communication details | [Module 03](03_Microservices_Architecture_and_Communication.md) |
| Data ingestion pipeline | [Module 04](04_Data_Ingestion_and_Real_Time_Market_Data_Service.md) |
| Database schema | [Module 05](05_Database_Architecture_and_Time_Series_Storage.md) |
| Algo Engine intelligence layer | [Module 07](07_AI_Trading_Brain_Intelligence_Layer.md) |
| MT5 trade execution | [Module 08](08_MetaTrader5_Integration_and_Trade_Execution_Bridge.md) |
| Risk management | [Module 09](09_Risk_Management_and_Safety_Systems.md) |
| Monitoring stack | [Module 10](10_Monitoring_Observability_and_Dashboard.md) |
| Development workflow | [Module 11](11_Development_Workflow_Testing_and_Deployment.md) |
| Security and audit | [Module 12](12_Security_Compliance_and_Audit.md) |
| Current state and future work | [Module 13](13_Current_State_and_Future_Work.md) |
| Mathematical foundations | [Module 14](14_Mathematical_Foundations_and_Quantitative_Finance.md) |
