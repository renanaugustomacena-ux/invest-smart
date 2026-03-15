# MONEYMAKER V1 — Microservices Architecture and Communication

> **Module 03** | Service Communication Reference

---

## Table of Contents

1. [Service Overview](#1-service-overview)
2. [ZeroMQ PUB/SUB — Data Distribution](#2-zeromq-pubsub--data-distribution)
3. [gRPC Service Contracts](#3-grpc-service-contracts)
4. [Service Discovery](#4-service-discovery)
5. [Shared Libraries](#5-shared-libraries)
6. [Resilience Patterns](#6-resilience-patterns)
7. [Health Check Protocol](#7-health-check-protocol)
8. [Error Handling and Graceful Degradation](#8-error-handling-and-graceful-degradation)

---

## 1. Service Overview

| Service | Language | Communication | Role |
|---|---|---|---|
| Data Ingestion | Go 1.22+ | ZMQ PUB (outbound), HTTP (metrics/health) | Market data pipeline |
| Algo Engine | Python 3.11+ | ZMQ SUB (inbound), gRPC client (outbound), HTTP (metrics/health) | Signal generation |
| MT5 Bridge | Python 3.11+ | gRPC server (inbound), HTTP (metrics) | Trade execution |
| Monitoring | Prometheus + Grafana | HTTP scrape (inbound) | Observability |

**Data flow**: `Data Ingestion --(ZMQ)--> Algo Engine --(gRPC)--> MT5 Bridge --> Broker`

---

## 2. ZeroMQ PUB/SUB — Data Distribution

Used for high-throughput, low-latency market data streaming from Data Ingestion to Algo Engine.

### Publisher (Data Ingestion)

- **Binds** on `tcp://*:5555` (PUB socket)
- **Two topic formats** (from `cmd/server/main.go`):
  - **Ticks**: `{eventType}.{exchange}.{symbol}` — e.g., `trade.polygon.XAU/USD`
  - **Bars**: `bar.{symbol}.{timeframe}` — e.g., `bar.XAU/USD.M1`
- **Payload**: JSON with string-encoded Decimal values
- **HWM** (High Water Mark): Not yet configured (TODO in publisher.go) — defaults to ZeroMQ library default

### Subscriber (Algo Engine)

- **Connects** to publisher address (e.g., `tcp://data-ingestion:5555` in Docker, `tcp://10.0.1.10:5555` in production)
- **Address source**: `BRAIN_ZMQ_DATA_FEED` environment variable
- **Subscribes** to bar topics for configured symbols
- **Bar buffer**: Accumulates bars until processing cycle (every `ANALYSIS_INTERVAL=10` ticks)

### Topic Routing (from publisher.go)

The `PublishTick()` method constructs topics as `{eventType}.{exchange}.{symbol}`. ZeroMQ's prefix matching enables hierarchical filtering:

- Subscribe to `trade.polygon.XAU/USD` — only XAU/USD ticks from Polygon
- Subscribe to `trade.polygon` — all Polygon ticks
- Subscribe to `bar.` — all completed OHLCV bars

### Why ZeroMQ (Not gRPC)

- **No backpressure needed**: Market data is fire-and-forget; if the brain is slow, old data is correctly dropped
- **Lower latency**: No connection handshake per message
- **Fan-out ready**: Multiple subscribers can attach without code changes
- **Topic filtering**: Subscribers receive only the symbols they care about

---

## 3. gRPC Service Contracts

Five protobuf files in `shared/proto/` define all service interfaces:

### market_data.proto

| Message | Fields | Used By |
|---|---|---|
| `MarketTick` | symbol, timestamp (ms UTC), bid, ask, last, volume, source, flags, spread — all financial values as strings | Data Ingestion (produces), Algo Engine (consumes) |
| `OHLCVBar` | symbol, timeframe, timestamp, open, high, low, close, volume, tick_count, complete, spread_avg — all as strings | Data Ingestion (produces), Algo Engine (consumes) |
| `DataEvent` | oneof: tick or bar | Wrapper for streaming |

### trading_signal.proto

| Message | Fields | Used By |
|---|---|---|
| `TradingSignal` | signal_id, symbol, direction (BUY/SELL/HOLD), confidence, suggested_lots, stop_loss, take_profit, timestamp, model_version, regime, source_tier, reasoning, risk_reward | Algo Engine (produces), MT5 Bridge (consumes) |
| `SignalAck` | signal_id, status (ACCEPTED/REJECTED/ERROR), reason, timestamp | MT5 Bridge (produces), Algo Engine (consumes) |

**Service**: `TradingSignalService`
- `SendSignal(TradingSignal) returns (SignalAck)` — single signal dispatch
- `StreamSignals(stream TradingSignal) returns (stream SignalAck)` — bidirectional streaming

### execution.proto

| Message | Fields | Used By |
|---|---|---|
| `TradeExecution` | order_id, signal_id, symbol, direction, requested_price, executed_price, quantity, stop_loss, take_profit, status, slippage_pips, commission, swap, executed_at, rejection_reason | MT5 Bridge (produces) |

**Service**: `ExecutionBridgeService`
- `ExecuteTrade(TradingSignal) returns (TradeExecution)`
- `StreamTradeUpdates(Empty) returns (stream TradeExecution)`
- `CheckHealth(HealthCheckRequest) returns (HealthCheckResponse)`

### health.proto

| Message | Fields | Used By |
|---|---|---|
| `HealthCheckRequest` | service_name | All services |
| `HealthCheckResponse` | status (HEALTHY/DEGRADED/UNHEALTHY), message, details (map), timestamp, uptime_seconds | All services |

---

## 4. Service Discovery

### Docker Compose (Development)

Services reference each other by container name:
- `postgres:5432`, `redis:6379`
- `data-ingestion:5555`, `algo-engine:50054`, `mt5-bridge:50055`

### Static IP Map (Production)

`configs/moneymaker_services.yaml` defines IPs and ports for Proxmox deployment:

```yaml
data_ingestion:
  host: "10.0.1.10"
  zmq_pub_port: 5555
  metrics_port: 9090
brain:
  host: "10.0.4.10"
  grpc_port: 50054
  rest_port: 8080
  metrics_port: 9093
mt5_bridge:
  host: "10.0.4.11"
  grpc_port: 50055
  metrics_port: 9094
```

---

## 5. Shared Libraries

### Python Common (`moneymaker-common`)

Location: `shared/python-common/` — installable as editable package (`pip install -e .`).

| Module | Purpose | Key Details |
|---|---|---|
| `config.py` | Pydantic BaseSettings for `MONEYMAKER_*` env vars | Auto-loads from environment |
| `logging.py` | Structured JSON logging via structlog | Service-tagged output |
| `metrics.py` | Prometheus metric definitions | 29+ metrics across 6 domains (brain, ML, ingestion, MT5, risk, system) |
| `health.py` | Three-tier health check (liveness, readiness, deep) | HEALTHY/DEGRADED/UNHEALTHY states |
| `enums.py` | Direction (BUY/SELL/HOLD), MarketRegime (5 values), TrendDirection (4 values), SourceTier (4 tiers) | Used by all Python services |
| `exceptions.py` | MoneyMakerError hierarchy (6 subclasses) | See Section 8 |
| `audit.py` | SHA-256 hash chain audit trail | In-memory chain with hash verification |
| `audit_pg.py` | PostgreSQL audit persistence | Bounded buffer (10K entries), async flush |
| `decimal_utils.py` | Financial Decimal utilities | `to_decimal()`, `calculate_pips()`, `position_value()` |

### Go Common

Location: `shared/go-common/` — imported as Go module.

| Package | Purpose | Key Details |
|---|---|---|
| `config/` | BaseConfig struct, environment loading | `LoadBaseConfig()`, `DatabaseURL()` builder |
| `logging/` | Structured JSON logging via zap | `NewLogger(serviceName)` |
| `health/` | HTTP health handlers | `/healthz`, `/readyz`, `/health` endpoints, `RegisterHTTPHandlers()` |

### Protobuf Contracts

Location: `shared/proto/` — compiled via `make proto`.

4 `.proto` files defining all inter-service message formats. All financial values encoded as strings in protobuf (never float/double). Generated Python and Go stubs are used by their respective services.

---

## 6. Resilience Patterns

### Signal Deduplication (MT5 Bridge)

The Order Manager maintains a dedup window (default 60s):
- Rejects duplicate `signal_id + symbol + direction` combos
- Auto-cleans expired entries
- Prevents duplicate orders from rapid re-evaluation cycles

### Graceful Shutdown

All services handle SIGTERM/SIGINT:
- **Data Ingestion**: Flushes pending OHLCV bars via `agg.FlushAll()`, closes ZMQ socket, shuts down health server (15s timeout)
- **Algo Engine**: Completes current processing cycle, flushes audit buffer
- **MT5 Bridge**: Does NOT close open positions — they survive service restarts

### Rate Limiting

Algo Engine enforces a configurable max signals per hour (`BRAIN_MAX_SIGNALS_PER_HOUR`: 10 dev, 50 prod) to prevent over-trading.

---

## 7. Health Check Protocol

Three-tier health check implemented consistently across all services:

| Level | Go Endpoint | Python Endpoint | Checks |
|---|---|---|---|
| **Liveness** | `/healthz` | `/health` | Process is running |
| **Readiness** | `/readyz` | `/ready` | Service can accept requests |
| **Deep** | `/health` | — | Dependencies reachable (DB, Redis, ZMQ) |

Health checks include:
- **Status**: HEALTHY / DEGRADED / UNHEALTHY
- **Uptime**: Seconds since service start
- **Details**: Map of dependency statuses

Docker Compose uses `pg_isready` and `redis-cli ping` for infrastructure health gates. Application services depend on infrastructure services being healthy before starting.

### Health Registration (Go)

```go
checker := health.NewChecker(serviceName)
checker.RegisterCheck("zmq_publisher", func() error { return pub.Ping() })
checker.SetReady()  // Called after all subsystems initialized
```

---

## 8. Error Handling and Graceful Degradation

### Exception Hierarchy (Python)

```
MoneyMakerError (base)
├── ConfigurationError — invalid config, missing env var
├── ConnectionError — DB, Redis, ZMQ, gRPC unreachable
├── DataValidationError — invalid market data
├── SignalRejectedError — signal failed validation (carries signal_id, reason)
├── RiskLimitExceededError — position/drawdown limit hit
└── BrokerError — MT5 API failure
```

### ML-Optional Protected Import Pattern

All optional modules in the Algo Engine use try/except on import (from `algo_engine/main.py`):

```python
try:
    from .features.regime_ensemble import RegimeEnsemble
    HAS_ENSEMBLE = True
except ImportError:
    HAS_ENSEMBLE = False
```

If an import fails, the feature is silently disabled and the core pipeline continues with basic functionality. This pattern applies to 11 optional modules:
1. Regime Ensemble
2. Data Sanity Checker
3. Feature Drift Monitor
4. Market Vectorizer
5. Trading Maturity Tracker
6. Trading Advisor
7. ML Lifecycle Manager
8. Performance Analyzer
9. Coaching Module
10. Pattern Recognition
11. Market Microstructure

The system logs which modules loaded successfully at startup. The `DRIFT_CHECK_INTERVAL` (100 ticks) controls how often drift monitoring runs when available.

---

## Cross-References

| Topic | Module |
|---|---|
| Architecture overview | [Module 01](01_System_Vision_and_Architecture_Overview.md) |
| Infrastructure and Docker | [Module 02](02_Infrastructure_and_Proxmox_Server_Setup.md) |
| Data ingestion pipeline | [Module 04](04_Data_Ingestion_and_Real_Time_Market_Data_Service.md) |
| Database schema | [Module 05](05_Database_Architecture_and_Time_Series_Storage.md) |
| Algo Engine intelligence | [Module 07](07_AI_Trading_Brain_Intelligence_Layer.md) |
| MT5 execution bridge | [Module 08](08_MetaTrader5_Integration_and_Trade_Execution_Bridge.md) |
| Risk management | [Module 09](09_Risk_Management_and_Safety_Systems.md) |
