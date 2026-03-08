# MONEYMAKER V1 — Data Ingestion and Real-Time Market Data Service

> **Module 04** | Data Pipeline Reference

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Connectors](#3-connectors)
4. [Normalizer](#4-normalizer)
5. [Aggregator](#5-aggregator)
6. [Publisher](#6-publisher)
7. [Database and Redis Persistence](#7-database-and-redis-persistence)
8. [Configuration](#8-configuration)
9. [Metrics and Monitoring](#9-metrics-and-monitoring)

---

## 1. Overview

The Data Ingestion service is a high-performance Go application that connects to market data sources via WebSocket, normalizes raw data into a canonical format, aggregates ticks into multi-timeframe OHLCV bars, and broadcasts everything via ZeroMQ PUB/SUB.

- **Language**: Go 1.22+
- **Location**: `services/data-ingestion/`
- **Primary data source**: Polygon.io (Forex/CFD)
- **Primary asset**: XAU/USD (Gold)
- **Secondary assets**: EUR/USD, GBP/USD, USD/JPY (hardcoded in main.go); AUD/USD, USD/CAD, NZD/USD, USD/CHF (configured in config.yaml)

---

## 2. Architecture

```
Exchange WebSocket  ──>  Connector  ──>  Normalizer  ──>  Aggregator  ──>  Publisher
                        (reconnect)     (canonical)      (M1→H1)         (ZMQ PUB)
                                            |                |               |
                                            v                v               v
                                      TimescaleDB       (flush on       Algo Engine (SUB)
                                      (market_ticks)     shutdown)
                                            |
                                            v
                                         Redis
                                       (tick cache, TTL 300s)
```

### Source Layout

```
cmd/server/main.go              # Entrypoint: initializes pipeline, signal handling
internal/
├── connectors/
│   ├── connector.go            # Connector interface, RawMessage struct, ConnectorConfig
│   ├── polygon.go              # Polygon.io Forex/CFD connector
│   ├── binance.go              # Binance spot connector
│   └── mock.go                 # Mock connector for dev/testing
├── normalizer/normalizer.go    # Symbol mapping, exchange-specific parsers
├── aggregator/aggregator.go    # OHLCV bar builder, multi-timeframe
└── publisher/publisher.go      # ZeroMQ PUB socket, topic routing, stats
config.yaml                     # Service configuration (225 lines)
```

---

## 3. Connectors

Each connector implements the `Connector` interface:

```go
type Connector interface {
    Connect() error
    Subscribe(symbols []string, channels []string) error
    ReadMessage() (RawMessage, error)
    Close() error
}
```

### Polygon.io (PRIMARY)

- **Data type**: Forex/CFD real-time tick and aggregate data
- **WebSocket URL**: `wss://socket.polygon.io/forex`
- **Authentication**: API key passed on connection (from `POLYGON_API_KEY` env var)
- **Auto-reconnect**: Exponential backoff with jitter (2s initial, 60s max, 50 max attempts)
- **Keep-alive**: Pong handler for connection health, ping every 30s
- **Auto-resubscribe**: Re-subscribes to all symbols after reconnection
- **Message types**:
  - `C` — Trade ticks (price, volume)
  - `CA` — Pre-aggregated bars
  - `CQ` — Quotes (bid/ask for mid-price calculation)
- **Symbols** (hardcoded in main.go): `C:XAUUSD`, `C:EURUSD`, `C:GBPUSD`, `C:USDJPY`
- **Symbols** (config.yaml, full set): adds `C:AUDUSD`, `C:USDCAD`, `C:NZDUSD`, `C:USDCHF`
- **Channels**: `trade`, `aggregate`

### Binance (Secondary)

- **Data type**: Crypto spot market data
- **WebSocket URL**: `wss://stream.binance.com:9443/ws`
- **Status**: Available but **disabled by default** in config.yaml (`enabled: false`)
- **Symbols**: btcusdt, ethusdt, bnbusdt, solusdt, xrpusdt, adausdt, dogeusdt, avaxusdt
- **Channels**: trade, depth, kline_1m, bookTicker
- **Rate limit**: 5 messages/second for subscriptions (Binance API limit)
- **Combined stream URL builder** and envelope-based message parsing

### Mock (Development)

- **Data type**: Synthetic tick data
- **Use case**: Development and testing without live exchange connections
- **Activation**: Automatic when `MONEYMAKER_ENV != production && != staging`
- **Features**: Injectable message factory for deterministic test data

---

## 4. Normalizer

Converts exchange-specific data formats to a canonical representation.

**Key responsibilities**:

- **Symbol mapping**: Exchange-native symbols to canonical `BASE/QUOTE` format (e.g., `C:XAUUSD` → `XAU/USD`, `c:xauusd` → `XAU/USD`, `xauusd` → `XAU/USD`)
- **Decimal precision**: Uses `shopspring/decimal` for all financial values — no float64 arithmetic
- **Multi-format parsing**: Handles Polygon trade ticks, aggregates, and quotes separately
- **Mid-price calculation**: Computes mid-price from bid/ask for Forex quotes

**Symbol map** (from main.go + config.yaml): 24 mappings for 8 Forex pairs (3 variants each: `c:xauusd`, `xau/usd`, `xauusd`) + 2 crypto pairs.

**Output**: `NormalizedTick` struct with three timestamps:

- `ExchangeTimestamp` — original exchange timestamp
- `ReceivedTimestamp` — when the connector received it
- `NormalizeTimestamp` — when normalization completed

---

## 5. Aggregator

Builds real-time OHLCV candles from tick streams at multiple timeframes.

### Runtime Timeframes (from main.go)

**M1, M5, M15, H1** — only 4 timeframes are instantiated at startup.

The `config.yaml` file lists 6 timeframes (`1m, 5m, 15m, 1h, 4h, 1d`), but the runtime code in `main.go` only creates aggregators for M1, M5, M15, and H1. H4 and D1 are configured but not active.

### Behavior

- Accumulates ticks per `symbol x timeframe` combination
- Emits a completed bar when the time boundary for that timeframe is crossed
- Thread-safe (protected by `sync.Mutex`)
- `FlushAll()` on graceful shutdown to prevent partial data loss — returns count of flushed bars
- Uses `floorTime()` to truncate timestamps to timeframe boundaries

### Bar Completion Callback

When a bar completes, the aggregator calls a callback that:
1. Marshals the bar to JSON
2. Publishes via ZMQ on topic `bar.{symbol}.{timeframe}` (e.g., `bar.XAU/USD.M1`)
3. Logs the publication at DEBUG level

---

## 6. Publisher

Fans out normalized data via ZeroMQ PUB socket.

### Configuration

- **Bind address**: `tcp://*:5555` (configurable via `MONEYMAKER_ZMQ_PUB_ADDR`)
- **Socket type**: zmq4.PUB (using `go-zeromq/zmq4` library)
- **HWM**: Not yet configured (TODO in publisher.go — defaults to library default)

### Topic Formats

Two distinct topic patterns are used:

| Data Type | Topic Format | Example |
|---|---|---|
| Ticks | `{eventType}.{exchange}.{symbol}` | `trade.polygon.XAU/USD` |
| Bars | `bar.{symbol}.{timeframe}` | `bar.XAU/USD.M15` |

ZeroMQ's prefix matching enables hierarchical subscription:

- `trade.polygon.XAU/USD` — only XAU/USD ticks from Polygon
- `trade.polygon` — all Polygon ticks
- `bar.XAU/USD` — all timeframe bars for XAU/USD
- `bar.` — all completed bars

### Publisher Stats

The publisher tracks internal metrics:

- `MessagesSent` — total messages published
- `BytesSent` — total bytes transmitted
- `Errors` — total publish failures
- `LastPublishAt` / `LastErrorAt` — timestamps for monitoring

### Health Check

`Ping()` verifies the publisher socket is still operational (used by health checker).

---

## 7. Database and Redis Persistence

### TimescaleDB (market_ticks)

Ticks are persisted to the `market_ticks` hypertable (1-hour chunks):

- **Batch size**: 1000 ticks per flush (config.yaml)
- **Flush interval**: 5000ms max hold time for partial batches
- **Writer workers**: 2 concurrent batch writer goroutines
- **Table**: `market_ticks` (configurable via `database.ticks_table`)

### Redis (tick cache)

Latest ticks cached for fast access by downstream services:

- **TTL**: 300 seconds (not 60 as some older docs stated)
- **Key prefix**: `moneymaker:tick:`
- **Purpose**: Real-time price lookups without DB queries

Both can be independently enabled/disabled via config.yaml (`database.enabled`, `redis.enabled`).

---

## 8. Configuration

### config.yaml (225 lines)

The full configuration file at `services/data-ingestion/config.yaml`:

```yaml
server:
  zmq_pub_addr: "tcp://*:5555"
  metrics_port: 9090
  health_port: 9091
  normalizer_workers: 4
  max_reconnect_attempts: 50

exchanges:
  polygon:
    enabled: true
    ws_url: "wss://socket.polygon.io/forex"
    symbols: ["C:XAUUSD", "C:EURUSD", "C:GBPUSD", "C:USDJPY",
              "C:AUDUSD", "C:USDCAD", "C:NZDUSD", "C:USDCHF"]
    channels: [trade, aggregate]
    reconnect_delay_ms: 2000
    max_reconnect_delay_ms: 60000
    ping_interval_ms: 30000

  binance:
    enabled: false    # Disabled for V1 (Forex focus)
    ws_url: "wss://stream.binance.com:9443/ws"
    symbols: [btcusdt, ethusdt, bnbusdt, solusdt, xrpusdt, adausdt, dogeusdt, avaxusdt]
    channels: [trade, depth, kline_1m, bookTicker]
    subscribe_rate_limit: 5

symbols:
  mapping:           # 24+ entries: exchange-native → canonical BASE/QUOTE
  ids:               # Numeric IDs: XAU/USD=1, EUR/USD=2, ..., BTC/USDT=101, ...

database:
  batch_size: 1000
  flush_interval_ms: 5000
  writer_workers: 2
  ticks_table: "market_ticks"
  enabled: true

redis:
  tick_ttl_seconds: 300
  key_prefix: "moneymaker:tick:"
  enabled: true

aggregation:
  enabled: true
  timeframes: ["1m", "5m", "15m", "1h", "4h", "1d"]
  zmq_topic_prefix: "candle"    # Note: actual runtime uses "bar" prefix (main.go)

logging:
  level: "info"
  format: "json"
  log_raw_messages: false
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MONEYMAKER_ENV` | `development` | Environment (development/staging/production) |
| `MONEYMAKER_DB_HOST` | `localhost` | TimescaleDB host |
| `MONEYMAKER_DB_PORT` | `5432` | TimescaleDB port |
| `MONEYMAKER_DB_NAME` | `moneymaker` | Database name |
| `MONEYMAKER_DB_USER` | `moneymaker` | Database user |
| `MONEYMAKER_DB_PASSWORD` | `moneymaker_dev` | Database password |
| `MONEYMAKER_REDIS_HOST` | `localhost` | Redis host |
| `MONEYMAKER_REDIS_PORT` | `6379` | Redis port |
| `MONEYMAKER_REDIS_PASSWORD` | `moneymaker_dev` | Redis password |
| `MONEYMAKER_ZMQ_PUB_ADDR` | `tcp://*:5555` | ZeroMQ PUB bind address |
| `POLYGON_API_KEY` | — | Polygon.io API key (required for production) |
| `MONEYMAKER_BINANCE_API_KEY` | — | Binance API key (optional, Binance disabled by default) |

### Config vs Runtime Discrepancies

| Setting | config.yaml | Runtime (main.go) | Notes |
|---|---|---|---|
| Aggregation timeframes | 1m, 5m, 15m, 1h, 4h, 1d | M1, M5, M15, H1 only | H4 and D1 not instantiated |
| ZMQ topic prefix | `candle` | `bar` | main.go uses `bar.{symbol}.{timeframe}` |
| Polygon symbols | 8 Forex pairs | 4 Forex pairs | main.go hardcodes subset |
| Health port | 9091 | 8081 (metrics_port + 1) | Dynamic calculation in main.go |

---

## 9. Metrics and Monitoring

Prometheus metrics exposed on port 9090:

| Metric | Type | Labels | Description |
|---|---|---|---|
| `moneymaker_ingestion_ticks_received_total` | Counter | symbol, exchange | Ticks received per symbol |
| `moneymaker_ingestion_bars_completed_total` | Counter | symbol, timeframe | OHLCV bars completed |
| `moneymaker_ingestion_latency_seconds` | Histogram | — | Tick processing latency |
| `moneymaker_risk_data_quality_rejected_total` | Counter | — | Data quality rejections |

Health check on port 8081 (host) → 8080 (container). Three-tier: `/healthz` (liveness), `/readyz` (readiness), `/health` (deep check including DB, Redis, ZMQ).

### Graceful Shutdown

On SIGTERM/SIGINT:
1. Sets health to not-ready (`checker.SetNotReady()`)
2. Flushes all partial OHLCV bars (`agg.FlushAll()`)
3. Shuts down health server (15s timeout)
4. Closes ZMQ publisher and connector

### Grafana Dashboard

The **Data Pipeline** dashboard (`moneymaker-data.json`) visualizes:

- Ticks/second and bars/second rates
- Data quality rejections and reasons
- Ingestion latency by exchange (p50/p95)
- Exchange reliability table
- Stale data detection
- Bar gap detection

---

## Cross-References

| Topic | Module |
|---|---|
| Architecture overview | [Module 01](01_System_Vision_and_Architecture_Overview.md) |
| Infrastructure and Docker | [Module 02](02_Infrastructure_and_Proxmox_Server_Setup.md) |
| Service communication | [Module 03](03_Microservices_Architecture_and_Communication.md) |
| Database schema (market_ticks, ohlcv_bars) | [Module 05](05_Database_Architecture_and_Time_Series_Storage.md) |
| Algo Engine (data consumer) | [Module 07](07_AI_Trading_Brain_Intelligence_Layer.md) |
| Monitoring dashboards | [Module 10](10_Monitoring_Observability_and_Dashboard.md) |
