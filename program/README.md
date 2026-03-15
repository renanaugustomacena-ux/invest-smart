# MONEYMAKER V1 — Trading Ecosystem

A microservices-based algorithmic trading system built for high-frequency data ingestion, rule-based signal generation, and automated trade execution on MetaTrader 5.

## Architecture

```
┌──────────────┐    ZeroMQ     ┌──────────────┐     gRPC      ┌──────────────┐
│    Data      │──────PUB/SUB──│   Algo Engine   │───────────────│  MT5 Bridge  │
│  Ingestion   │               │  (Signals)   │               │ (Execution)  │
│   (Go)       │               │  (Python)    │               │  (Python)    │
└──────┬───────┘               └──────┬───────┘               └──────┬───────┘
       │                              │                              │
       ▼                              ▼                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    TimescaleDB + Redis + Prometheus + Grafana               │
└──────────────────────────────────────────────────────────────────────────────┘
```

The Algo Engine operates with advanced rule-based strategies, routing signals based on market regime detection through a 4-tier cascade (COPER > Hybrid > Knowledge > Conservative).

## Tech Stack

| Component | Technology | Version |
|---|---|---|
| Data Ingestion | Go | 1.22+ |
| Algo Engine | Python | 3.11+ |
| MT5 Bridge | Python | 3.11+ |
| Database | TimescaleDB (PostgreSQL) | 16 |
| Cache | Redis | 7 |
| IPC | ZeroMQ (PUB/SUB) | — |
| RPC | gRPC + Protobuf | — |
| Monitoring | Prometheus + Grafana | — |
| Containers | Docker Compose | — |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Go 1.22+
- (Optional) `pre-commit` for git hooks

### Setup

```bash
# 1. Clone and configure
cp .env.example .env  # edit with your credentials

# 2. Automated setup (installs deps, starts DB & Redis)
bash scripts/dev/setup-local.sh

# 3. Start all services
make docker-up

# 4. Run tests
make test
```

### Key Make Targets

```bash
make test           # Run all Python + Go tests
make lint           # Lint Python (ruff/black) + Go (golangci-lint)
make fmt            # Auto-format all code
make typecheck      # Mypy type checking
make ci             # Full CI pipeline (lint + typecheck + test + build)
make docker-build   # Build all Docker images
make docker-up      # Start full stack
make docker-down    # Stop full stack
make proto          # Recompile Protobuf definitions
make clean          # Remove build artifacts and caches
```

## Project Structure

```
program/
├── configs/            # Per-environment YAML configuration
├── infrastructure/     # Docker Compose, DB init scripts
├── scripts/            # Dev setup and ops utilities
├── services/
│   ├── algo-engine/       # Signal generation engine (Python)
│   ├── data-ingestion/ # Market data pipeline (Go)
│   ├── external-data/  # Macro data from FRED, CBOE, CFTC (Python)
│   ├── console/        # MONEYMAKER Console — TUI/CLI (15 categories)
│   ├── monitoring/     # Grafana dashboards + Prometheus config
│   └── mt5-bridge/     # Trade execution via MetaTrader 5 (Python)
├── shared/
│   ├── go-common/      # Shared Go utilities
│   ├── proto/          # Protobuf service contracts
│   └── python-common/  # Shared Python library (moneymaker-common)
├── tests/              # E2E tests and fixtures
├── V1_Bot/             # System design documentation (14 modules)
├── Makefile            # Build, test, lint, deploy targets
├── .env.example        # Environment variable template
└── .pre-commit-config.yaml
```

## Configuration

Copy `.env.example` to `.env` and fill in:

- **Database**: `MONEYMAKER_DB_*` — TimescaleDB connection
- **Redis**: `MONEYMAKER_REDIS_*` — cache credentials
- **MT5**: `MT5_ACCOUNT`, `MT5_PASSWORD`, `MT5_SERVER`
- **Exchange APIs**: `MONEYMAKER_BINANCE_API_KEY`, etc.
Per-service YAML configs live in `configs/development/` and `configs/production/`.

## Ports Reference

| Service | Port | Protocol |
|---|---|---|
| Data Ingestion (ZMQ) | 5555 | TCP |
| Data Ingestion (Metrics) | 9090 | HTTP |
| Algo Engine (gRPC) | 50054 | HTTP/2 |
| Algo Engine (REST) | 8080 | HTTP |
| Algo Engine (Metrics) | 9093 | HTTP |
| External Data (Metrics) | 9095 | HTTP |
| MT5 Bridge (gRPC) | 50055 | HTTP/2 |
| Prometheus | 9091 | HTTP |
| Grafana | 3000 | HTTP |
| PostgreSQL | 5432 | TCP |
| Redis | 6379 | TCP |

## Design Principles

- **Decimal everywhere** — no `float` for financial values (`decimal.Decimal` in Python, `shopspring/decimal` in Go)
- **Fail-safe** — when in doubt, HOLD (do nothing)
- **Append-only audit** — SHA-256 hash chain for every decision
- **Credentials from env** — never hardcoded, always `os.environ`
- **Pure rule-based** — the system operates entirely with technical analysis and statistical models

## License

Proprietary — All rights reserved.
