# REPORT 09: Infrastructure, CI/CD, Monitoring e Security

## Executive Summary

L'infrastruttura MONEYMAKER è **enterprise-grade**: Docker Compose con 3 reti isolate (frontend/backend/monitoring), TLS/mTLS completo con script di generazione certificati, RBAC database per-service con least-privilege, 10 regole Prometheus di alerting (5 safety + 5 infra), 5 dashboard Grafana ricche (inclusa risk con VaR/CVaR/Sortino), alerting asincrono rate-limited via Telegram, struttura di logging JSON consistente tra Python e Go, RASP integrity verification con SHA-256.

**Problema critico**: Il file `program/infra/docker/.env` contenente password (`Trade.2026.Macena`) è **tracciato in git** nonostante le regole gitignore — il file è stato committato prima dell'aggiunta della regola. Inoltre, il Docker build context nel CI GitHub Actions è errato (punta alla directory del servizio invece che alla root del monorepo).

---

## Inventario Completo

### A. Docker e Orchestrazione

| # | File | Percorso | LoC | Stato |
|---|------|----------|-----|-------|
| 1 | docker-compose.yml | infra/docker/docker-compose.yml | 357 | OK |
| 2 | docker-compose.dev.yml | infra/docker/docker-compose.dev.yml | 16 | OK |
| 3 | Dockerfile algo-engine | services/algo-engine/Dockerfile | 44 | OK |
| 4 | Dockerfile data-ingestion | services/data-ingestion/Dockerfile | 66 | ECCELLENTE |
| 5 | Dockerfile mt5-bridge | services/mt5-bridge/Dockerfile | 44 | OK |
| 6 | Dockerfile ml-training | services/ml-training/Dockerfile | 47 | WARNING GPU |
| 7 | Dockerfile external-data | services/external-data/Dockerfile | 45 | OK |
| 8 | .env (dev) | infra/docker/.env | 6 | **CRITICO** |
| 9 | .env.example | program/.env.example | 152 | ECCELLENTE |
| 10 | .dockerignore | program/.dockerignore | ~15 | OK |

### B. CI/CD e Build

| # | File | Percorso | LoC | Stato |
|---|------|----------|-----|-------|
| 11 | ci.yml | .github/workflows/ci.yml | 142 | WARNING |
| 12 | security.yml | .github/workflows/security.yml | 86 | ECCELLENTE |
| 13 | Makefile | program/Makefile | 97 | ECCELLENTE |
| 14 | .pre-commit-config.yaml | program/.pre-commit-config.yaml | 44 | OK |
| 15 | Proto Makefile | shared/proto/Makefile | 44 | OK |

### C. Database Init (7 script)

| # | File | Percorso | LoC | Stato |
|---|------|----------|-----|-------|
| 16 | 001_init.sql | infra/docker/init-db/001_init.sql | 161 | ECCELLENTE |
| 17 | 002_ml_tables.sql | infra/docker/init-db/002_ml_tables.sql | 73 | OK |
| 18 | 003_strategy_tables.sql | infra/docker/init-db/003_strategy_tables.sql | 79 | OK |
| 19 | 004_economic_calendar.sql | infra/docker/init-db/004_economic_calendar.sql | 271 | ECCELLENTE |
| 20 | 005_macro_data.sql | infra/docker/init-db/005_macro_data.sql | 322 | ECCELLENTE |
| 21 | 006_rbac_roles.sql | infra/docker/init-db/006_rbac_roles.sql | 232 | ECCELLENTE |
| 22 | 007_rbac_passwords.sh | infra/docker/init-db/007_rbac_passwords.sh | 78 | OK |

### D. TLS/Certificati

| # | File | Percorso | LoC | Stato |
|---|------|----------|-----|-------|
| 23 | generate-certs.sh | infra/certs/generate-certs.sh | 275 | ECCELLENTE |
| 24 | .gitignore (certs) | infra/certs/.gitignore | ~25 | OK |
| 25 | .gitignore (docker certs) | infra/docker/certs/.gitignore | ~20 | OK |
| 26 | README.md (certs) | infra/docker/certs/README.md | ~10 | OK |

### E. Monitoring e Observability

| # | File | Percorso | LoC | Stato |
|---|------|----------|-----|-------|
| 27 | prometheus.yml | monitoring/prometheus/prometheus.yml | 33 | OK |
| 28 | alert_rules.yml | monitoring/prometheus/alert_rules.yml | 100 | OK |
| 29 | moneymaker-overview.json | monitoring/grafana/dashboards/ | 898 | OK |
| 30 | moneymaker-risk.json | monitoring/grafana/dashboards/ | 1154 | ECCELLENTE |
| 31 | moneymaker-data.json | monitoring/grafana/dashboards/ | 949 | OK |
| 32 | moneymaker-trading.json | monitoring/grafana/dashboards/ | 988 | OK |
| 33 | moneymaker-ml-training.json | monitoring/grafana/dashboards/ | 344 | OK |
| 34 | dashboards.yml | monitoring/grafana/provisioning/dashboards/ | 14 | OK |
| 35 | datasources.yml | monitoring/grafana/provisioning/datasources/ | 11 | OK |

### F. Codice Observability (algo-engine)

| # | File | Percorso | LoC | Stato |
|---|------|----------|-----|-------|
| 36 | health.py | algo-engine/src/algo_engine/observability/health.py | 181 | OK |
| 37 | logger_setup.py | algo-engine/src/algo_engine/observability/logger_setup.py | 138 | OK |
| 38 | rasp.py | algo-engine/src/algo_engine/observability/rasp.py | 195 | OK |
| 39 | sentry_setup.py | algo-engine/src/algo_engine/observability/sentry_setup.py | 164 | OK |
| 40 | dispatcher.py | algo-engine/src/algo_engine/alerting/dispatcher.py | 111 | ECCELLENTE |
| 41 | telegram.py | algo-engine/src/algo_engine/alerting/telegram.py | 73 | OK |

### G. Codice Observability (Go shared)

| # | File | Percorso | LoC | Stato |
|---|------|----------|-----|-------|
| 42 | health.go | shared/go-common/health/health.go | 127 | OK |
| 43 | logger.go | shared/go-common/logging/logger.go | 23 | OK |

**Totale file auditati**: 43 | **Totale LoC**: ~7,600+

---

## Analisi Dettagliata

### A. Docker Compose — docker-compose.yml (357 LoC)

**Architettura dei Servizi**:
```
┌──────────────────── frontend ─────────────────────┐
│  Grafana:3000    TensorBoard:6006                 │
└────────────────────────┬──────────────────────────┘
                         │
┌──────────────────── monitoring ───────────────────┐
│  Prometheus:9091                                   │
│  ↓ scrape                                         │
│  data-ingestion:9090  algo-engine:9093               │
│  mt5-bridge:9094                                  │
└────────────────────────┬──────────────────────────┘
                         │
┌──────────────────── backend ──────────────────────┐
│  PostgreSQL:5432      Redis:6379                  │
│  data-ingestion:5555  algo-engine:50054              │
│  mt5-bridge:50055                                 │
└───────────────────────────────────────────────────┘
```

**Sicurezza**:
- Password REQUIRED (operatore `?:` — compose fallisce se non impostate)
- RBAC per-service: `DI_DB_USER`, `BRAIN_DB_USER`, `MT5_DB_USER`, `ADMIN_DB_USER`
- TLS opzionale con toggle `MONEYMAKER_TLS_ENABLED`
- Certificati montati read-only
- Grafana: cookie secure, SameSite strict, HSTS, no anonymous, no signup
- Rate limiting su MT5 Bridge (10 req/min, burst 5)
- Health check su tutti i servizi con depends_on condition

**Port Mapping**:

| Servizio | Porte Esposte | Proto |
|----------|---------------|-------|
| PostgreSQL | 5432 | TCP |
| Redis | 6379 | TCP |
| data-ingestion | 5555 (ZMQ), 9090 (metrics), 8081 (health) | TCP |
| algo-engine | 50054 (gRPC), 8080 (REST), 9093 (metrics) | TCP |
| mt5-bridge | 50055 (gRPC), 9094 (metrics) | TCP |
| Prometheus | 9091 | HTTP |
| Grafana | 3000 | HTTP |
| TensorBoard | 6006 | HTTP |

**Volumi**: postgres-data, redis-data, prometheus-data, grafana-data, tensorboard-logs

**Problemi**:
- Redis healthcheck incompatibile con TLS (usa `redis-cli` senza `--tls`)
- Backend network non ha `internal: true` (commento suggerisce di aggiungerlo in produzione)
- ml-training interamente commentato (vedi Report 04)

#### docker-compose.dev.yml (16 LoC)
Override minimale: aggiunge `MONEYMAKER_LOG_LEVEL=DEBUG` a tutti i servizi.

---

### B. Dockerfiles (5 servizi)

#### B.1 algo-engine (44 LoC) — `python:3.11-slim`
- Non-root user `moneymaker:1000`
- PYTHONDONTWRITEBYTECODE + PYTHONUNBUFFERED
- Porte: 50052, 8082, 9092 (⚠ diverse dal compose: 50054, 8080, 9093)
- Healthcheck: Python urllib su porta metriche

**ERRORE**: Port mismatch tra Dockerfile EXPOSE e docker-compose ports (già segnalato in Report 01).

#### B.2 data-ingestion (66 LoC) — Multi-stage build
- Stage 1: `golang:1.22-bookworm` → build statico CGO_ENABLED=0
- Stage 2: `alpine:3.21` (~5 MB)
- Flags: `-ldflags="-s -w" -trimpath` (binary compatto e riproducibile)
- Healthcheck: `curl /healthz`
- **ECCELLENTE** — build production-grade

#### B.3 mt5-bridge (44 LoC) — `python:3.11-slim`
- Commento documenta che MetaTrader5 è Windows-only
- ImportError gestito gracefully
- Porte: 50052, 8082, 9092 (⚠ stesso mismatch del brain)

#### B.4 ml-training (47 LoC) — `pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime`
- GPU NVIDIA CUDA 12.1 (⚠ utente ha AMD — vedi Report 04)
- gRPC healthcheck su porta 50056
- Non-root user `moneymaker:moneymaker`

#### B.5 external-data (45 LoC) — `python:3.11-slim`
- Servizio leggero per dati macro (FRED, CBOE, CFTC)
- Usa `requirements.txt` invece di `pyproject.toml` (inconsistenza minore)

---

### C. CI/CD

#### C.1 ci.yml (142 LoC)

**Job 1 — Python Lint & Test**:
- Python 3.11, pip cache per pyproject.toml hash
- ruff (lint) → black (format) → mypy (types) → pytest (test)
- Test su python-common + algo-engine
- Script custom: health check + brain verification

**Job 2 — Go Lint & Test**:
- Go 1.22, mod cache
- go vet → golangci-lint → `go test -v -race`
- Race detector attivo (critico per dati real-time)

**Job 3 — Docker Build**:
- `docker/build-push-action@v5` per 3 servizi

**ERRORE CRITICO nel Docker build** (righe 120-142):
```yaml
# SBAGLIATO:
context: services/data-ingestion

# CORRETTO:
context: .
dockerfile: ./services/data-ingestion/Dockerfile
```
Il Dockerfile fa `COPY shared/go-common/` che richiede la root come context. Il Makefile lo fa correttamente (`docker build -f services/data-ingestion/Dockerfile .`) ma il CI no.

#### C.2 security.yml (86 LoC)

**Schedule**: Ogni lunedì 06:00 UTC + su push se pyproject.toml cambia.

3 controlli di sicurezza:
1. **pip-audit** — vulnerabilità dipendenze Python (algo-engine, mt5-bridge)
2. **govulncheck** — CVE nei moduli Go (data-ingestion)
3. **trufflehog** — scanning segreti nel filesystem (con esclusioni)

**ECCELLENTE** — difesa in profondità su 3 assi ortogonali.

#### C.3 Makefile (97 LoC)

Target principali:
- `make proto` — compila protobuf
- `make build-go` — build data-ingestion
- `make test` — test Python + Go
- `make lint` — ruff + black + mypy + golangci-lint
- `make ci` — lint + typecheck + test + docker-build (validazione completa pre-push)
- `make docker-build` — 3 immagini
- `make docker-up/down` — gestione stack
- `make clean` — pulizia artefatti

Auto-detection venv: usa `.venv/bin/python` se presente, altrimenti `python` di sistema.

**Build context corretto nel Makefile**: `docker build -f services/X/Dockerfile .` ← root come context.

#### C.4 pre-commit-config.yaml (44 LoC)

Hook configurati:
1. **pre-commit-hooks v4.6.0**: trailing-whitespace, end-of-file-fixer, yaml check, large file check (500KB), merge conflict check, **private key detection**
2. **ruff v0.4.4**: lint + format
3. **mypy v1.10.0**: type checking (⚠ file list hardcoded)
4. **golangci-lint v0.5.1**: go-fmt + go-vet

---

### D. Database Init Scripts (7 file, ~1,216 LoC)

#### 001_init.sql (161 LoC) — Schema Core
- **Hypertable**: `ohlcv_bars` (chunk 1 giorno, compress dopo 7g), `market_ticks` (chunk 1h, compress dopo 1g)
- **Tabelle**: trading_signals, trade_executions, audit_log
- **audit_log**: trigger PREVENT UPDATE e DELETE → immutabilità garantita a livello database
- Indici ottimizzati per query per simbolo+tempo

#### 002_ml_tables.sql (73 LoC) — ML
- model_registry (versioning), model_metrics, ml_predictions (hypertable, compress 7g)

#### 003_strategy_tables.sql (79 LoC) — Strategie
- strategy_performance (hypertable, compress 30g)
- Materialized view: strategy_daily_summary (refresh orario)

#### 004_economic_calendar.sql (271 LoC) — Calendario Economico
- economic_events, trading_blackouts, event_impact_rules
- Funzioni: `is_trading_blacked_out(symbol, time)`, `generate_blackouts_for_event(event_id)`
- Regole default: NFP (30 min pre/post), FOMC (30 min pre/60 post), Jobless Claims (10/15)
- Design database-driven (regole modificabili senza codice)

#### 005_macro_data.sql (322 LoC) — Dati Macro
- Tabelle: vix_data, yield_curve_data, real_rates_data, dxy_data, cot_reports, recession_probability
- Campi auto-calcolati: vix_regime, yield_inversion, dxy_trend
- Retention: tick 1 anno, daily 5-10 anni
- Materialized view: macro_snapshot (riga singola con ultimi valori)

#### 006_rbac_roles.sql (232 LoC) — RBAC
4 ruoli con least-privilege:
- `data_ingestion_svc`: WRITE market data, APPEND audit
- `algo_engine_svc`: READ market data, WRITE signals, APPEND audit
- `mt5_bridge_svc`: READ signals, UPDATE executed, WRITE executions, APPEND audit
- `moneymaker_admin`: ALL PRIVILEGES

#### 007_rbac_passwords.sh (78 LoC) — Password
- `ALTER ROLE` per ogni servizio con password da env var
- Skip se password non fornita
- Query di verifica finale

---

### E. TLS Infrastructure

#### generate-certs.sh (275 LoC)
Genera:
1. **Root CA** — 4096-bit RSA, 365 giorni, self-signed
2. **PostgreSQL cert** — server-auth, SANs: postgres/localhost/moneymaker-postgres/127.0.0.1
3. **Redis cert** — server-auth, stessi SAN pattern
4. **4 service certs** — server+client auth (mTLS bidirezionale)

Sicurezza:
- Private key `chmod 600`, cert `chmod 644`
- Cleanup di CSR e file OpenSSL temporanei
- Verifica con `openssl x509 -noout`
- Warning: mai committare chiavi private

**Certificati NON committati**: `.gitignore` in entrambe le directory certs esclude correttamente `*.key`, `*.crt`, `*.pem`, `*.csr`.

---

### F. Monitoring Stack

#### Prometheus — prometheus.yml (33 LoC)
- Scrape interval: 15s, evaluation interval: 15s
- 4 job: data-ingestion:9090, algo-engine:9093, mt5-bridge:9094, prometheus:9090
- Static discovery (no consul/etcd)
- Alert rules caricati da file separato

#### Alert Rules — alert_rules.yml (100 LoC)

**Safety (5 regole):**

| Regola | Severità | Metrica | For | Threshold |
|--------|----------|---------|-----|-----------|
| KillSwitchActivated | CRITICAL | moneymaker_kill_switch_active | 0m | ==1 |
| CriticalDrawdown | CRITICAL | moneymaker_portfolio_drawdown_pct | 0m | >5% |
| HighDrawdown | WARNING | moneymaker_portfolio_drawdown_pct | 5m | >3% |
| DailyLossApproaching | WARNING | moneymaker_daily_loss_pct | 1m | >1.5% |
| SpiralProtectionActive | WARNING | moneymaker_spiral_consecutive_losses | 0m | >3 |

**Infrastruttura (5 regole):**

| Regola | Severità | Metrica | For | Threshold |
|--------|----------|---------|-----|-----------|
| NoTicksReceived | CRITICAL | rate(moneymaker_ticks_received_total[5m]) | 5m | ==0 |
| HighPipelineLatency | WARNING | histogram_quantile(0.99, ...) | 5m | >100ms |
| ServiceDown | CRITICAL | up | 1m | ==0 |
| HighErrorRate | WARNING | rate(moneymaker_errors_total[5m]) | 5m | >0.1/s |
| BridgeUnavailable | CRITICAL | moneymaker_bridge_available | 2m | ==0 |

Design pattern: 0m per kill switch (notifica immediata), 5m per performance (evita falsi positivi).

#### Grafana — 5 Dashboard (4,333 LoC totali)

1. **moneymaker-overview.json** (898 LoC) — Command Center: kill switch, status servizi, health score composito, error rate per servizio/tipo, latenza p50/p95/p99, heatmap errori
2. **moneymaker-risk.json** (1,154 LoC) — Risk Management: daily loss gauge, drawdown gauge, risk score composito, unrealized P&L, correlation blocks, VaR 95%, CVaR, portfolio beta, Sortino ratio, position concentration donut
3. **moneymaker-data.json** (949 LoC) — Data Pipeline: ticks/s, bars/s, pipeline health, throughput per exchange
4. **moneymaker-trading.json** (988 LoC) — Trading Performance: signal rates, win rate, P&L, execution latency
5. **moneymaker-ml-training.json** (344 LoC) — ML Training: training metrics (per quando ml-training sarà attivo)

Provisioning: auto-provisioning via `dashboards.yml` + `datasources.yml` → Prometheus come datasource default.

**Nota**: GUIDE/03 diceva "nessuna dashboard" — ERRATO. Ci sono 5 dashboard complete e professionali.

---

### G. Application Observability

#### health.py (181 LoC) — Health Check
- `BrainHealthChecker.check_all()` — async, verifica 5 componenti
- Database: query reale con latenza misurata
- Redis: solo import check (⚠ non testa connettività effettiva)
- NN Model: verifica METADATA_DIM
- Feature Pipeline: import check
- Output: JSON serializzabile per endpoint `/health`

#### logger_setup.py (138 LoC) — Structured Logging
- `JSONFormatter`: ELK/Loki-compatible (timestamp ISO8601, service tag, campi strutturati)
- `ConsoleFormatter`: ANSI colorato per sviluppo
- File rotation: 10MB max, 5 backup
- Auto-detection: `MONEYMAKER_ENV=production` → JSON, altrimenti console

#### rasp.py (195 LoC) — Integrity Verification
- `IntegrityGuard`: SHA-256 manifest di file critici
- Genera manifest → verifica all'avvio → rileva modifiche/mancanze
- Protegge: file nn/, pipeline, configurazioni
- Pattern: Runtime Application Self-Protection

#### sentry_setup.py (164 LoC) — Error Tracking
- Sentry opzionale (graceful se non installato)
- PII scrubbing: hostname → "moneymaker-node", path utente redacted
- 10% trace sampling per performance
- Breadcrumb categories: signal, trade, pipeline
- Skip in pytest (auto-detection)

#### dispatcher.py (111 LoC) — Alert Dispatcher
- Rate-limited per (level, title): 30s default, 5s per CRITICAL
- Multi-channel async: `asyncio.gather(*tasks, return_exceptions=True)`
- Cleanup entries vecchie ogni 3600s
- Emoji tagging: ℹ️ INFO, ⚠️ WARNING, 🚨 CRITICAL

#### telegram.py (73 LoC) — Telegram Channel
- HTML formatting (bold title, plain body)
- Lazy httpx.AsyncClient init con timeout 10s
- Web preview disabilitato
- Graceful: restituisce False se httpx non disponibile

#### health.go (127 LoC) — Go Health Check
- Kubernetes-standard: `/healthz` (liveness), `/readyz` (readiness), `/health` (deep check)
- Thread-safe: `sync.RWMutex` per SetReady/SetNotReady
- Custom checks via `RegisterCheck()`
- JSON response con uptime e dettagli per componente

#### logger.go (23 LoC) — Go Logging
- `zap.NewProductionConfig()` → JSON su stdout
- ISO8601 timestamps, service tagging
- Consistente con Python JSONFormatter

---

## Findings Critici

| # | Finding | Severità | Dove | Impatto |
|---|---------|----------|------|---------|
| 1 | **`.env` con password tracciato in git** | **CRITICO** | `infra/docker/.env` | Password `Trade.2026.Macena` nel repo, accessibile a chiunque abbia accesso |
| 2 | **CI Docker build context errato** | ALTO | `.github/workflows/ci.yml:120-142` | Build Docker falliscono perché `COPY shared/` non trova i file |
| 3 | **Port mismatch Dockerfile vs compose** | ALTO | algo-engine Dockerfile (50052/8082/9092) vs compose (50054/8080/9093) | EXPOSE non ha effetto runtime ma documenta porte sbagliate |
| 4 | **Redis healthcheck incompatibile con TLS** | MEDIO | `docker-compose.yml:79` | Healthcheck fallirà quando TLS è abilitato |
| 5 | **MyPy pre-commit con file hardcoded** | MEDIO | `.pre-commit-config.yaml:33-36` | Path hardcoded nel hook non corrispondono a runtime |
| 6 | **Redis health check shallow** in health.py | MEDIO | `algo-engine/observability/health.py` | Solo import check, non testa connettività reale |
| 7 | **Rate limiting solo su MT5 Bridge** | MEDIO | `docker-compose.yml` | data-ingestion e algo-engine non hanno rate limiting |
| 8 | **Backend network non `internal: true`** | BASSO | `docker-compose.yml:343` | Servizi backend accessibili dall'host in dev |
| 9 | **external-data non nel CI** | BASSO | `ci.yml` | Nessun lint/test/build per external-data |
| 10 | **No Alertmanager** | BASSO | `prometheus.yml` | Alert push via dispatcher custom (accettabile, ma no persistence) |

---

## Interconnessioni

```
┌──────────────────────────────────────────────────────────┐
│                    INFRASTRUTTURA MONEYMAKER                  │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  RETE: frontend                     RETE: monitoring       │
│  ┌──────────┐  ┌──────────┐       ┌──────────────┐       │
│  │ Grafana  │  │TensorBoard│       │ Prometheus   │       │
│  │ :3000    │  │  :6006   │       │ :9091        │       │
│  └────┬─────┘  └──────────┘       └──────┬───────┘       │
│       │                                   │ scrape 15s    │
│       │ datasource                        │               │
│       └──────────────────>────────────────┘               │
│                                           │               │
│  RETE: backend                            │               │
│  ┌───────────────────────────────────────┐│               │
│  │ ┌──────────┐    ┌──────────────────┐ ││               │
│  │ │PostgreSQL│    │ Redis            │ ││               │
│  │ │ :5432    │    │ :6379 (+TLS opt) │ ││               │
│  │ │ RBAC 4   │    │ kill switch,     │ ││               │
│  │ │ ruoli    │    │ state, pub/sub   │ ││               │
│  │ └──────────┘    └──────────────────┘ ││               │
│  │                                       ││               │
│  │ ┌──────────┐ ┌────────┐ ┌──────────┐││               │
│  │ │data-ingest│ │algo-engine│ │mt5-bridge│││               │
│  │ │:5555 ZMQ  │ │:50054  │ │:50055    │├┤──metrics──>   │
│  │ │:9090 metr │ │:9093   │ │:9094     │││               │
│  │ │:8081 hlth │ │:8080   │ │          │││               │
│  │ └──────────┘ └────────┘ └──────────┘││               │
│  └───────────────────────────────────────┘│               │
│                                                            │
│  CI/CD (GitHub Actions)                                    │
│  ┌────────────────────────────────────────────────┐       │
│  │ Job 1: Python lint+test (ruff,black,mypy,pytest)│       │
│  │ Job 2: Go lint+test (vet, golangci-lint, race) │       │
│  │ Job 3: Docker build (3 servizi)                │       │
│  └────────────────────────────────────────────────┘       │
│                                                            │
│  Security Scanning (settimanale)                           │
│  ┌────────────────────────────────────────────────┐       │
│  │ pip-audit + govulncheck + trufflehog            │       │
│  └────────────────────────────────────────────────┘       │
│                                                            │
│  Alerting Pipeline                                         │
│  Prometheus → alert_rules (10) → algo-engine dispatcher      │
│                                  → Telegram (rate limited) │
│                                                            │
│  Logging Pipeline                                          │
│  Python (JSONFormatter) ─┐                                │
│  Go (zap production)    ─┤─> stdout → Docker → Loki (TBD)│
│  Sentry (opzionale)     ─┘                                │
└──────────────────────────────────────────────────────────┘
```

---

## Postura di Sicurezza

### Punti di Forza

| Controllo | Implementato | Dettaglio |
|-----------|-------------|-----------|
| RBAC Database | ✅ | 4 ruoli, least-privilege, per-service |
| Audit Trail | ✅ | audit_log immutabile (trigger PREVENT UPDATE/DELETE) |
| TLS/mTLS | ✅ | Script generazione completo, opzionale via env |
| Password Non-Default | ✅ | `?:` operator nel compose, nessun default |
| Network Segmentation | ✅ | 3 reti isolate (frontend/backend/monitoring) |
| Secret Scanning | ✅ | trufflehog in CI |
| Vulnerability Scanning | ✅ | pip-audit + govulncheck |
| Rate Limiting | ⚠️ | Solo MT5 Bridge (manca su data-ingestion e algo-engine) |
| Non-Root Containers | ✅ | Tutti i servizi girano come user `moneymaker` |
| RASP Integrity | ✅ | SHA-256 manifest dei file critici |
| PII Scrubbing | ✅ | Sentry: hostname+path redacted |
| Cookie Security | ✅ | Grafana: Secure, SameSite, HSTS |
| Private Key Detection | ✅ | pre-commit hook |
| Code Linting + Types | ✅ | ruff + black + mypy + golangci-lint |
| Race Detection | ✅ | `go test -race` |

### Debolezze

| Debolezza | Severità | Mitigazione |
|-----------|----------|-------------|
| `.env` committato con password | CRITICO | `git rm --cached` + rotazione password |
| CI build context errato | ALTO | Fix paths nel workflow |
| Prometheus senza auth | MEDIO | Reverse proxy o basic auth |
| Redis health check shallow | MEDIO | Implementare PING reale |
| No container scanning (Trivy) | MEDIO | Aggiungere al CI |
| No SAST (Bandit) | MEDIO | Aggiungere al CI |
| No backup automatico DB | MEDIO | Aggiungere pg_dump periodico |

---

## Istruzioni con Checkbox

### Segmento A: Fix di Sicurezza Urgenti

- [ ] **Rimuovere `.env` dal tracking git** — `git rm --cached program/infra/docker/.env` e verificare che `.gitignore` copra il path. Il file `.env` è stato committato prima della regola gitignore. Dopo la rimozione, rotare le password (`Trade.2026.Macena` è ora nel git history)
- [ ] **Verificare che nessun altro segreto sia nel git history** — Usare `trufflehog filesystem --directory . --no-update` localmente per controllare
- [ ] **Generare password forti per produzione** — `openssl rand -base64 24` per ogni servizio (MONEYMAKER_DB_PASSWORD, MONEYMAKER_REDIS_PASSWORD, GRAFANA_PASSWORD, DI_DB_PASSWORD, BRAIN_DB_PASSWORD, MT5_DB_PASSWORD, ADMIN_DB_PASSWORD)

### Segmento B: Fix CI/CD

- [ ] **Fix Docker build context in ci.yml** — Per tutti e 3 i servizi, cambiare `context: services/X` in `context: .` e aggiungere `dockerfile: ./services/X/Dockerfile`
- [ ] **Aggiungere external-data al CI** — Lint, test, e Docker build per il servizio external-data
- [ ] **Aggiungere ml-training al CI** — Almeno lint e test (build Docker opzionale finché commentato)
- [ ] **Fix MyPy pre-commit** — Rimuovere file list hardcoded e usare `pass_filenames: false` con `entry: mypy --ignore-missing-imports program/services/algo-engine/src/`

### Segmento C: Fix Docker

- [ ] **Allineare porte Dockerfile↔compose** — algo-engine: cambiare EXPOSE in Dockerfile da 50052/8082/9092 a 50054/8080/9093. Stesso per mt5-bridge
- [ ] **Fix Redis healthcheck per TLS** — Condizionare il comando healthcheck: se `MONEYMAKER_TLS_ENABLED`, aggiungere `--tls --cacert /etc/ssl/certs/ca.crt`
- [ ] **Aggiungere `internal: true` alla rete backend** in produzione — commento già presente, ma deve diventare effettivo

### Segmento D: Hardening Monitoring

- [ ] **Aggiungere container scanning** — Integrare Trivy nella pipeline CI per scansione vulnerabilità nelle immagini Docker
- [ ] **Aggiungere SAST** — Integrare Bandit (Python) per static analysis delle vulnerabilità di sicurezza nel codice
- [ ] **Proteggere endpoint Prometheus** — Aggiungere basic auth o reverse proxy per l'endpoint metriche (:9091)
- [ ] **Implementare Redis health check reale** in `health.py` — Sostituire l'import check con `await redis_client.ping()` usando connessione asincrona

### Segmento E: Miglioramenti Alerting

- [ ] **Aggiungere rate limiting a data-ingestion** — Configurare `RATE_LIMIT_ENABLED=true` con limiti adeguati (es. 100 req/min per il feed dati)
- [ ] **Aggiungere rate limiting a algo-engine** — Configurare limiti sul gRPC server (es. 50 req/min)
- [ ] **Aggiungere alert per data-ingestion** — Regola per errori elevati nel servizio Go (attualmente non coperto)
- [ ] **Configurare Sentry DSN** — Impostare `SENTRY_DSN` env var per error tracking in produzione
- [ ] **Configurare Telegram bot** — Creare bot Telegram, ottenere token e chat_id, impostare env vars `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`

### Segmento F: Backup e Disaster Recovery

- [ ] **Implementare backup automatico PostgreSQL** — pg_dump periodico su storage esterno (cron o job Docker)
- [ ] **Implementare backup Redis** — Abilitare AOF (Append Only File) per persistenza + backup periodico del dump RDB
- [ ] **Documentare procedura di recovery** — Passi per ripristino da backup di database, Redis, e checkpoint modelli
- [ ] **Aggiungere retention policy per Prometheus** — Configurare `--storage.tsdb.retention.time=30d` per evitare esaurimento disco

### Segmento G: Certificati e TLS

- [ ] **Generare certificati per ambiente Proxmox** — Eseguire `generate-certs.sh` sulla macchina target e copiare in `infra/docker/certs/`
- [ ] **Testare stack TLS completo** — Abilitare `MONEYMAKER_TLS_ENABLED=true`, verificare connessione PostgreSQL SSL, Redis TLS, gRPC mTLS
- [ ] **Documentare rotazione certificati** — Procedura e cadenza (365 giorni validità, rinnovare prima di 30 giorni dalla scadenza)

---

## Discrepanze con GUIDE/03

| Affermazione GUIDE/03 | Realtà nel Codice | Verdetto |
|------------------------|-------------------|----------|
| "Nessuna dashboard creata" | 5 dashboard Grafana JSON complete (4,333 LoC) | **ERRATO** |
| "Safety al 20%" | Safety ~90% implementata | **ERRATO** |
| "Nessun alert configurato" | 10 regole Prometheus + dispatcher Telegram | **ERRATO** |

---

*Report generato il 2026-03-02 — Audit completo di 43 file infrastrutturali: Docker (7 file), CI/CD (4 file), DB init (7 script SQL + 1 bash), TLS (4 file), Monitoring (9 file), Observability code (8 file), Go shared (2 file).*
