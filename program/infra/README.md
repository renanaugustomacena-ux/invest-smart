# Infrastructure

Container orchestration and database initialization for the MONEYMAKER stack.

## Docker Compose

The full stack is defined in `docker/docker-compose.yml` and includes:

| Container | Image | Purpose |
|---|---|---|
| `moneymaker-postgres` | `timescale/timescaledb:latest-pg16` | TimescaleDB (time-series + relational) |
| `moneymaker-redis` | `redis:7-alpine` | In-memory cache and pub/sub |
| `moneymaker-data-ingestion` | Custom (Go) | Market data pipeline |
| `moneymaker-brain` | Custom (Python) | Signal generation |
| `moneymaker-mt5-bridge` | Custom (Python) | Trade execution |
| `moneymaker-prometheus` | `prom/prometheus:v2.50.1` | Metrics collection |
| `moneymaker-grafana` | `grafana/grafana:10.3.3` | Dashboards & alerting |

### Quick Start

```bash
# Start full stack
make docker-up

# Start only infrastructure (DB + Redis)
docker compose -f infrastructure/docker/docker-compose.yml up -d postgres redis

# Stop everything
make docker-down
```

### Dev Override

`docker-compose.dev.yml` provides development-specific overrides (e.g., volume mounts for hot-reload).

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

## Database Initialization

SQL scripts in `docker/init-db/` run automatically on first container start:

- Creates TimescaleDB hypertables for tick storage
- Sets up initial schema and indexes

## Volumes

| Volume | Purpose |
|---|---|
| `postgres-data` | Persistent database storage |
| `redis-data` | Redis AOF persistence |
| `prometheus-data` | Metrics history |
| `grafana-data` | Dashboard state and config |
