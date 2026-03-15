# MONEYMAKER V1 — Infrastructure and Deployment Setup

> **Module 02** | Infrastructure Reference

---

## Table of Contents

1. [Overview](#1-overview)
2. [Docker Compose Stack](#2-docker-compose-stack)
3. [Database Initialization](#3-database-initialization)
4. [Network Configuration](#4-network-configuration)
5. [Environment Configuration](#5-environment-configuration)
6. [Volume Management](#6-volume-management)
7. [CI/CD Pipeline](#7-cicd-pipeline)
8. [Development Setup](#8-development-setup)
9. [Proxmox Deployment](#9-proxmox-deployment)

---

## 1. Overview

MONEYMAKER V1 runs as a Docker Compose stack with 7 containers. The target production deployment is on a Proxmox VE bare-metal server with dedicated VMs per service group, but the entire stack can run on a single machine for development.

**Infrastructure files**: `infra/docker/`

### Service Dependency Graph

```
postgres ──────────┬──> data-ingestion ──> algo-engine ──> mt5-bridge
redis ─────────────┘        │                  │
                            │                  │
prometheus ──scrape──> all services            │
    │                                          │
grafana <──────────────────────────────────────┘
```

All application services depend on `postgres` (healthy) and `redis` (healthy) before starting. `algo-engine` waits for `data-ingestion` to start. `mt5-bridge` waits for `algo-engine` to start.

---

## 2. Docker Compose Stack

Defined in `infra/docker/docker-compose.yml`:

| Container | Image | Ports (host:container) | Health Check |
|---|---|---|---|
| `moneymaker-postgres` | `timescale/timescaledb:latest-pg16` | 5432:5432 | `pg_isready -U moneymaker -d moneymaker` |
| `moneymaker-redis` | `redis:7-alpine` | 6379:6379 | `redis-cli -a $PASSWORD ping` |
| `moneymaker-data-ingestion` | Custom Go image | 5555:5555 (ZMQ), 9090:9090 (metrics), 8081:8080 (health) | — |
| `moneymaker-brain` | Custom Python image | 50054:50054 (gRPC), 8080:8080 (REST), 9093:9093 (metrics) | — |
| `moneymaker-mt5-bridge` | Custom Python image | 50055:50055 (gRPC), 9094:9094 (metrics) | — |
| `moneymaker-prometheus` | `prom/prometheus:v2.50.1` | 9091:9090 | — |
| `moneymaker-grafana` | `grafana/grafana:10.3.3` | 3000:3000 | — |

**Note**: Data Ingestion maps host port 8081 to container port 8080 for health checks (the container's health server listens on 8081 internally, calculated as `metrics_port + 1`).

### Dev Override

`docker-compose.dev.yml` applies development-specific overrides for all three application services:

- Sets `MONEYMAKER_ENV=development`
- Sets `MONEYMAKER_LOG_LEVEL=DEBUG`

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

### Quick Start

```bash
# Full stack
make docker-up

# Infrastructure only (DB + Redis)
docker compose -f infra/docker/docker-compose.yml up -d postgres redis

# Stop
make docker-down
```

---

## 3. Database Initialization

Three SQL scripts in `infra/docker/init-db/` execute on first container start (alphabetical order):

### 001_init.sql — Core Schema (161 lines)

| Table | Type | Key Columns |
|---|---|---|
| `ohlcv_bars` | Hypertable (1-day chunks) | time, symbol, timeframe, open/high/low/close/volume (NUMERIC), tick_count, spread_avg, source. Compression after 7 days (segmentby: symbol, timeframe; orderby: time DESC). |
| `market_ticks` | Hypertable (1-hour chunks) | time, symbol, bid, ask, last_price, volume, spread, source, flags (**INTEGER**, not TEXT). Compression after 1 day (segmentby: symbol; orderby: time DESC). |
| `trading_signals` | Regular table | **id BIGSERIAL PRIMARY KEY**, signal_id TEXT (UNIQUE), symbol, direction, confidence, suggested_lots, stop_loss, take_profit, model_version, regime, source_tier, reasoning, **risk_reward** (not risk_reward_ratio), created_at. |
| `trade_executions` | Regular table | id BIGSERIAL PK, order_id (UNIQUE), signal_id (FK to trading_signals.signal_id), symbol, direction, **requested_price**, executed_price, quantity, stop_loss, take_profit, status, **slippage_pips** (not slippage), commission, swap, profit, close_price, closed_at, **executed_at** (not created_at), **rejection_reason**. |
| `audit_log` | Append-only table | id BIGSERIAL PK, created_at, service, action, entity_type, entity_id, details (JSONB), prev_hash, hash. Triggers prevent UPDATE/DELETE. SHA-256 hash chain. |

### 002_strategy_tables.sql — Strategy Performance (79 lines)

| Table | Type | Key Columns |
|---|---|---|
| `strategy_performance` | Hypertable (1-day chunks) | id BIGSERIAL PK, **signal_id UUID**, **strategy_name** TEXT, symbol, direction, **confidence** NUMERIC, **regime** TEXT, **source_tier** TEXT, entry_price, exit_price, **lots** NUMERIC, pnl, pnl_pct, **opened_at** TIMESTAMPTZ (hypertable column), closed_at, duration_minutes, **status** TEXT, **metadata** JSONB. Compression after 30 days (segmentby: strategy_name; orderby: opened_at DESC). |
| `strategy_daily_summary` | Continuous Aggregate | strategy_name, day (time_bucket '1 day'), **total_signals** (count), **wins** (count where pnl > 0), **losses** (count where pnl < 0), **total_profit** (sum pnl), **avg_confidence** (avg confidence), **last_signal_at** (max opened_at). Auto-refreshed. |

> **Full schema reference**: See [Module 05 — Database Architecture](05_Database_Architecture_and_Time_Series_Storage.md).

---

## 4. Network Configuration

### Docker Compose Networking

All services join a default Docker bridge network. Services reference each other by container name:

| Role | Services |
|---|---|
| Infrastructure | `postgres`, `redis` |
| Application | `data-ingestion`, `algo-engine`, `mt5-bridge` |
| Monitoring | `prometheus`, `grafana` |

### Proxmox Static IPs

For production deployment on Proxmox VMs (defined in `configs/moneymaker_services.yaml`):

| Service | VM IP | VLAN |
|---|---|---|
| Data Ingestion | 10.0.1.10 | Data (VLAN 10) |
| Database | 10.0.2.10 | Storage (VLAN 20) |
| Algo Engine | 10.0.4.10 | Compute (VLAN 40) |
| MT5 Bridge | 10.0.4.11 | Compute (VLAN 40) |
| Monitoring | 10.0.5.10 | Monitoring (VLAN 50) |

---

## 5. Environment Configuration

All sensitive values are passed via environment variables. Template: `.env.example` (72 lines).

### Variable Reference

| Category | Variable | Default | Description |
|---|---|---|---|
| General | `MONEYMAKER_ENV` | `development` | Environment name |
| General | `MONEYMAKER_LOG_LEVEL` | `INFO` | Log verbosity |
| Database | `MONEYMAKER_DB_HOST` | `localhost` | TimescaleDB host |
| Database | `MONEYMAKER_DB_PORT` | `5432` | TimescaleDB port |
| Database | `MONEYMAKER_DB_NAME` | `moneymaker` | Database name |
| Database | `MONEYMAKER_DB_USER` | `moneymaker` | Database user |
| Database | `MONEYMAKER_DB_PASSWORD` | `moneymaker_dev` | Database password |
| Redis | `MONEYMAKER_REDIS_HOST` | `localhost` | Redis host |
| Redis | `MONEYMAKER_REDIS_PORT` | `6379` | Redis port |
| Redis | `MONEYMAKER_REDIS_PASSWORD` | `moneymaker_dev` | Redis password |
| ZeroMQ | `MONEYMAKER_ZMQ_PUB_ADDR` | `tcp://*:5555` | PUB bind address |
| Algo Engine | `BRAIN_CONFIDENCE_THRESHOLD` | — | Minimum confidence for signals |
| Algo Engine | `BRAIN_MAX_SIGNALS_PER_HOUR` | — | Rate limit (10 dev, 50 prod) |
| Algo Engine | `BRAIN_MAX_OPEN_POSITIONS` | — | Position limit |
| Algo Engine | `BRAIN_MAX_DAILY_LOSS_PCT` | — | Daily loss cap |
| Algo Engine | `BRAIN_MAX_DRAWDOWN_PCT` | — | Max drawdown limit |
| Algo Engine | `BRAIN_ZMQ_DATA_FEED` | — | ZMQ SUB address (e.g., `tcp://data-ingestion:5555`) |
| Algo Engine | `BRAIN_MT5_BRIDGE_TARGET` | — | gRPC target (e.g., `mt5-bridge:50055`) |
| MT5 | `MT5_ACCOUNT` | — | Broker account number |
| MT5 | `MT5_PASSWORD` | — | Broker password |
| MT5 | `MT5_SERVER` | — | Broker server name |
| Data | `POLYGON_API_KEY` | — | Polygon.io API key (required for prod) |
| Monitoring | `GRAFANA_PASSWORD` | `admin` | Grafana admin password |

### Port Discrepancy Note

`.env.example` defines `BRAIN_REST_PORT=8082` and `BRAIN_METRICS_PORT=9092`, but `docker-compose.yml` maps Algo Engine to 8080 and 9093. The docker-compose values are canonical — the .env.example defaults are overridden at container level.

### Per-Environment Overrides

YAML config files in `configs/development/` and `configs/production/` provide environment-specific values beyond what `.env` covers.

---

## 6. Volume Management

| Volume | Container Mount | Purpose |
|---|---|---|
| `postgres-data` | `/var/lib/postgresql/data` | Database storage (hypertables, indexes, WAL) |
| `redis-data` | `/data` | Redis AOF persistence |
| `prometheus-data` | `/prometheus` | Metrics history (15-day retention default) |
| `grafana-data` | `/var/lib/grafana` | Dashboard state, provisioned config |

Additional bind mounts (read-only):

| Source | Container | Purpose |
|---|---|---|
| `./init-db` | postgres → `/docker-entrypoint-initdb.d` | SQL init scripts |
| `services/monitoring/prometheus/prometheus.yml` | prometheus → `/etc/prometheus/prometheus.yml` | Scrape config |
| `services/monitoring/grafana/provisioning` | grafana → `/etc/grafana/provisioning` | Datasource + dashboard provisioning |
| `services/monitoring/grafana/dashboards` | grafana → `/var/lib/grafana/dashboards` | Dashboard JSON files |

Volumes persist across container restarts. To reset all data: `docker compose down -v`.

---

## 7. CI/CD Pipeline

GitHub Actions workflow in `.github/workflows/ci.yml` (135 lines). Three parallel jobs:

### Job 1: Python Lint & Test

| Step | Tool | Targets |
|---|---|---|
| Lint | `ruff check` | `shared/python-common/`, `services/algo-engine/` |
| Format | `black --check` | Same targets |
| Type check | `mypy` | Same targets |
| Test | `pytest` | `python-common/tests/`, `algo-engine/tests/` |

### Job 2: Go Lint & Test

| Step | Tool | Targets |
|---|---|---|
| Vet | `go vet ./...` | `services/data-ingestion/` |
| Lint | `golangci-lint run ./...` | Same |
| Test | `go test -race ./...` | Same |

### Job 3: Docker Build

Builds all three application images to verify Dockerfiles compile successfully (does not push).

### Makefile Targets

14 targets defined in `Makefile`:

| Target | Description |
|---|---|
| `proto` | Compile Protocol Buffers via `shared/proto/Makefile` |
| `build-go` | Build Go binary → `services/data-ingestion/bin/data-ingestion` |
| `test` | Run all tests (Python + Go) |
| `test-go` | Run Go tests only |
| `test-python` | Run pytest for python-common, algo-engine, mt5-bridge |
| `lint` | Run all linters (Python + Go) |
| `lint-python` | `ruff check` + `black --check` on all Python sources |
| `lint-go` | `golangci-lint run` on data-ingestion |
| `fmt` | Auto-format all code (Black + Ruff fix + gofmt) |
| `typecheck` | `mypy` on algo-engine + python-common |
| `ci` | Full CI check: lint → typecheck → test → docker-build |
| `docker-build` | Build all 3 application Docker images |
| `docker-up` | Start Docker Compose stack |
| `docker-down` | Stop Docker Compose stack |
| `clean` | Remove Go binaries and Python cache files |

**Note**: `docker-up` and `docker-down` reference `infrastructure/docker/docker-compose.yml` in the Makefile, but the actual path is `infra/docker/docker-compose.yml`. This may require a path fix.

---

## 8. Development Setup

One-shot setup from project root:

```bash
bash scripts/dev/setup-local.sh
```

This script:
1. Checks prerequisites (Docker, Python 3.11+, Go 1.22+)
2. Copies `.env.example` to `.env`
3. Installs `moneymaker-common` as editable Python package
4. Starts DB + Redis containers
5. Installs pre-commit hooks

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker + Docker Compose | Latest | Container orchestration |
| Python | 3.11+ | Algo Engine, MT5 Bridge, shared libs |
| Go | 1.22+ | Data Ingestion service |
| Make | Any | Build automation |
| pre-commit | Latest (optional) | Git hook management |

### Python Virtual Environment

The Makefile auto-detects a `.venv/` directory and uses its binaries for `ruff`, `black`, `mypy`, and `pytest`. Without a venv, it falls back to system PATH.

---

## 9. Proxmox Deployment

The target production environment is a Proxmox VE bare-metal server:

- **CPU**: AMD Ryzen 9 7950X (16 cores / 32 threads)
- **RAM**: 128 GB DDR5 ECC
- **Storage**: 2x 2TB NVMe (ZFS RAID1) + 4x 16TB HDD (RAID10)
- **Network**: VLAN segmentation per service group

Each service group runs in its own VM. Docker Compose orchestrates containers within each VM. The `configs/moneymaker_services.yaml` file provides static service discovery with IPs and ports for cross-VM communication.

---

## Cross-References

| Topic | Module |
|---|---|
| Full database schema details | [Module 05](05_Database_Architecture_and_Time_Series_Storage.md) |
| Service communication protocols | [Module 03](03_Microservices_Architecture_and_Communication.md) |
| Data ingestion pipeline | [Module 04](04_Data_Ingestion_and_Real_Time_Market_Data_Service.md) |
| Monitoring and dashboards | [Module 10](10_Monitoring_Observability_and_Dashboard.md) |
| Security and audit | [Module 12](12_Security_Compliance_and_Audit.md) |
