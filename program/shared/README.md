# Shared Libraries

Cross-service code shared by all MONEYMAKER microservices. Contains common utilities, Protobuf contracts, and language-specific helper packages.

## Contents

| Package | Language | Description |
|---|---|---|
| [python-common](python-common/) | Python | `moneymaker-common` — logging, config, metrics, health, enums, audit, decimal utils |
| [go-common](go-common/) | Go | Config loader, health checks, structured logging |
| [proto](proto/) | Protobuf | gRPC service contracts shared across all services |

## Python Common (`moneymaker-common`)

Installable as a local editable package. All Python services depend on it.

```bash
pip install -e shared/python-common/
```

### Modules

| Module | Purpose |
|---|---|
| `config.py` | Pydantic-based configuration loader |
| `logging.py` | Structured logging with `structlog` |
| `metrics.py` | Prometheus metric helpers (Brain pipeline + ML inference metrics) |
| `health.py` | Standardized health check endpoints |
| `enums.py` | Shared enumerations (`Side`, `SignalType`, `SourceTier`, etc.) |
| `exceptions.py` | Custom exception hierarchy |
| `audit.py` | Audit trail utilities (SHA-256 hash chain) |
| `audit_pg.py` | PostgreSQL audit persistence with bounded buffer (max 10,000 entries) |
| `decimal_utils.py` | Safe decimal arithmetic for financial data (`ZERO`, `to_decimal`) |

### ML Inference Metrics

The `metrics.py` module includes Prometheus metrics for monitoring ML integration:

| Metric | Type | Description |
|---|---|---|
| `moneymaker_brain_ml_predictions_total` | Counter | ML predictions by symbol, direction, model type |
| `moneymaker_brain_ml_prediction_latency_seconds` | Histogram | ML inference round-trip latency |
| `moneymaker_brain_ml_fallback_total` | Counter | Fallback events by reason (timeout, low confidence, etc.) |
| `moneymaker_brain_ml_confidence` | Histogram | ML confidence score distribution |

### Audit Buffer

The `audit_pg.py` module uses a bounded in-memory buffer (default 10,000 entries) to batch audit entries before flushing to PostgreSQL. If the buffer fills up, the oldest entry is dropped with a warning — this prevents memory exhaustion under heavy load while preserving the most recent audit trail.

## Go Common

Imported as a Go module by `data-ingestion`.

| Package | Purpose |
|---|---|
| `config/` | YAML + env config loader |
| `health/` | HTTP health check server |
| `logging/` | Structured JSON logging |

## Proto Definitions

gRPC + Protobuf contracts defining the communication interfaces between services:

| File | Defines |
|---|---|
| `market_data.proto` | Market data types (ticks, candles, order book) |
| `trading_signal.proto` | Trading signal format (BUY/SELL/HOLD with SL/TP) |
| `execution.proto` | Order execution request/response |
| `ml_inference.proto` | ML model inference service (`Predict`, `GetModelInfo`) |
| `health.proto` | Standardized health check protocol |

The `ml_inference.proto` contract supports all model types (`jepa`, `gnn`, `mlp`, `ensemble`) and uses string-encoded Decimals for all financial values.

### Recompile Protos

```bash
make proto                          # From project root
# or directly:
bash scripts/dev/generate-protos.sh
```
