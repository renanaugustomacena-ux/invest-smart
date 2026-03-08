# REPORT 01: Architettura di Sistema e Mappa dei Servizi

**Data Audit Originale**: 2026-03-02
**Data Revisione**: 2026-03-05
**Auditor**: Claude Opus 4.6
**Scope**: Topologia completa del sistema, protocolli di comunicazione, contratti proto, configurazione deployment, shared libraries
**Severita Massima Trovata**: CRITICA
**Stato**: REVISIONATO — Tutti i finding verificati riga-per-riga contro il codice sorgente

---

## Executive Summary

Il sistema MONEYMAKER e' un ecosistema di trading algoritmico basato su microservizi con 6 servizi applicativi + 3 infrastrutturali. L'architettura e' ben progettata con contratti proto-first, shared libraries consistenti, e network segmentation. Tuttavia, la revisione approfondita ha identificato **4 errori CRITICI**, **5 errori ALTI**, e **6 WARNING** che devono essere risolti prima del deployment.

**Cambiamenti dalla revisione originale**:
- Aggiunto F13 (ALTO): env var naming mismatch — il port override NON funziona
- Aggiunto F14 (WARNING): data-ingestion health port mapping errato nel docker-compose
- Aggiunto F15 (WARNING): config.yaml copiato nel container ma mai parsato dal codice Go
- F04 promosso da ALTO a CRITICO: confermato che le porte algo-engine sono irraggiungibili, env override non funziona
- Tutti i finding confermati con riferimenti esatti a file e riga

---

## 1. Inventario Completo dei File Analizzati

### 1.1 Protocol Buffers (Contratti)
| File | Path | LoC | Stato |
|------|------|-----|-------|
| health.proto | `shared/proto/health.proto` | 24 | OK |
| market_data.proto | `shared/proto/market_data.proto` | 43 | OK |
| trading_signal.proto | `shared/proto/trading_signal.proto` | 59 | OK |
| execution.proto | `shared/proto/execution.proto` | 45 | OK |
| ml_inference.proto | `shared/proto/ml_inference.proto` | 56 | OK |

**Generati**: 10 file Python (`*_pb2.py` + `*_pb2_grpc.py`) in `shared/proto/gen/moneymaker_proto/`

### 1.2 Configurazione Servizi
| File | Path | LoC | Stato |
|------|------|-----|-------|
| moneymaker_services.yaml | `program/configs/moneymaker_services.yaml` | 32 | WARNING |
| docker-compose.yml | `program/infra/docker/docker-compose.yml` | 358 | ERRORI |
| .env.example | `program/.env.example` | ~160 | ERRORI |

### 1.3 Dockerfiles
| File | Path | LoC | Stato |
|------|------|-----|-------|
| algo-engine/Dockerfile | `services/algo-engine/Dockerfile` | 44 | CRITICO |
| mt5-bridge/Dockerfile | `services/mt5-bridge/Dockerfile` | 44 | CRITICO |
| data-ingestion/Dockerfile | `services/data-ingestion/Dockerfile` | 66 | WARNING |
| ml-training/Dockerfile | `services/ml-training/Dockerfile` | 47 | CRITICO |

### 1.4 Shared Libraries - Python (`moneymaker_common`)
| File | Path | LoC | Stato |
|------|------|-----|-------|
| config.py | `shared/python-common/src/moneymaker_common/config.py` | 96 | OK |
| enums.py | `shared/python-common/src/moneymaker_common/enums.py` | 54 | OK |
| metrics.py | `shared/python-common/src/moneymaker_common/metrics.py` | 219 | OK |
| decimal_utils.py | `shared/python-common/src/moneymaker_common/decimal_utils.py` | ~80 | OK |
| logging.py | `shared/python-common/src/moneymaker_common/logging.py` | ~50 | OK |
| audit.py | `shared/python-common/src/moneymaker_common/audit.py` | ~100 | OK |
| audit_pg.py | `shared/python-common/src/moneymaker_common/audit_pg.py` | ~80 | OK |
| ratelimit.py | `shared/python-common/src/moneymaker_common/ratelimit.py` | ~120 | OK |
| health.py | `shared/python-common/src/moneymaker_common/health.py` | ~40 | OK |
| secrets.py | `shared/python-common/src/moneymaker_common/secrets.py` | ~60 | OK |
| grpc_credentials.py | `shared/python-common/src/moneymaker_common/grpc_credentials.py` | ~50 | OK |
| exceptions.py | `shared/python-common/src/moneymaker_common/exceptions.py` | ~30 | OK |
| pyproject.toml | `shared/python-common/pyproject.toml` | 22 | OK |

### 1.5 Shared Libraries - Go (`go-common`)
| File | Path | Stato |
|------|------|-------|
| config.go | `shared/go-common/config/config.go` | OK |
| health.go | `shared/go-common/health/health.go` | OK |
| logger.go | `shared/go-common/logging/logger.go` | OK |
| ratelimit.go | `shared/go-common/ratelimit/ratelimit.go` | OK |

### 1.6 Configurazioni per Servizio
| File | Path | Stato |
|------|------|-------|
| algo-engine config.py | `services/algo-engine/src/algo_engine/config.py` | CRITICO |
| mt5-bridge config.py | `services/mt5-bridge/src/mt5_bridge/config.py` | WARNING |
| data-ingestion config.yaml | `services/data-ingestion/config.yaml` | WARNING (orfano) |

---

## 2. Analisi Dettagliata

### 2.1 Contratti Protocol Buffers

I 5 file proto definiscono i contratti tra servizi. Sono ben strutturati e usano best practices (string-encoded Decimals per precisione finanziaria, timestamp in Unix nanoseconds).

#### health.proto
- **Package**: `moneymaker.v1`
- **Definisce**: `HealthCheckRequest`, `HealthCheckResponse` con enum Status (UNKNOWN, HEALTHY, DEGRADED, UNHEALTHY)
- **Campi**: service_name, status, message, details (map), timestamp, uptime_seconds
- **Usato da**: Embedded in execution.proto (import) e come standalone per tutti i servizi
- **Stato**: OK

#### market_data.proto
- **Package**: `moneymaker.v1.data` (DIVERSO dagli altri — `moneymaker.v1`)
- **MarketTick**: symbol, timestamp, bid/ask/last/volume (Decimal string), source, flags (bitmask: anomaly/stale/interpolated), spread
- **OHLCVBar**: symbol, timeframe (M1-D1), OHLCV (Decimal string), tick_count, complete flag, spread_avg
- **DataEvent**: oneof wrapper (tick | bar) per streaming unificato
- **Stato**: OK — Design pulito con flag per data quality
- **Nota**: Il package diverso e' intenzionale per separare il dominio dati, ma richiede attenzione nelle importazioni

#### trading_signal.proto
- **Package**: `moneymaker.v1`
- **Enum Direction**: DIRECTION_UNSPECIFIED, DIRECTION_BUY, DIRECTION_SELL, DIRECTION_HOLD
- **Enum SourceTier**: ML_PRIMARY, TECHNICAL, SENTIMENT, RULE_BASED
- **Enum AckStatus**: ACCEPTED, REJECTED, ERROR
- **TradingSignal**: 13 campi (signal_id, symbol, direction, confidence, suggested_lots, SL, TP, timestamp, model_version, regime, source_tier, reasoning, risk_reward_ratio)
- **Service**: `TradingSignalService` con SendSignal (unary) e StreamSignals (bidirectional)
- **Stato**: OK

#### execution.proto
- **Package**: `moneymaker.v1`
- **Importa**: trading_signal.proto (per Direction) e health.proto
- **TradeExecution**: order_id, signal_id, symbol, direction, requested/executed price, quantity, SL/TP, status, slippage, commission, swap, executed_at, rejection_reason
- **Enum Status**: PENDING, FILLED, PARTIALLY_FILLED, REJECTED, CANCELLED, EXPIRED
- **Service**: `ExecutionBridgeService` con ExecuteTrade, StreamTradeUpdates, CheckHealth
- **Stato**: OK come contratto — ma StreamTradeUpdates e' un **stub vuoto** nel codice mt5-bridge (vedi Report 08)

#### ml_inference.proto
- **Package**: `moneymaker.v1`
- **PredictionRequest**: symbol, regime, features (map<string,string>), model_version, timestamp
- **PredictionResponse**: direction, confidence, reasoning, model_version, model_type, metadata, inference_time_us
- **Service**: `MLInferenceService` con Predict e GetModelInfo
- **Stato**: OK come contratto — il server ml-training e' commentato in docker-compose

---

### 2.2 Topologia dei Servizi

```
                        +-----------+
                        |  Polygon  |
                        |  Binance  |
                        +-----+-----+
                              | WebSocket
                              v
+------------------------------------------------------------------+
|                    DOCKER COMPOSE STACK                            |
|                                                                   |
|  +------------------+     ZMQ PUB     +------------------+        |
|  | data-ingestion   | ==============> | algo-engine          |        |
|  | (Go)             |   :5555        | (Python)          |        |
|  | Expose: 5555,    |                | Expose: 50052,    |        |
|  |   9090, 9091     |                |   8082, 9092      |        |
|  +--------+---------+                +--------+----------+        |
|           |                                   |                   |
|           | SQL (batch writer)                | gRPC :50055       |
|           v                                   v                   |
|  +------------------+                +------------------+         |
|  | PostgreSQL 16    |                | mt5-bridge       |         |
|  | TimescaleDB      |<---------------| (Python)         |         |
|  | (:5432)          |     SQL        | Expose: 50055,   |         |
|  +--------+---------+                |   9094            |         |
|           ^                          +--------+---------+         |
|           |                                   |                   |
|  +------------------+                         | MT5 API           |
|  | Redis 7          |                         v                   |
|  | (:6379)          |                +------------------+         |
|  +------------------+                | MetaTrader 5     |         |
|                                      | (Windows VM)     |         |
|  +------------------+                +------------------+         |
|  | Prometheus       |  +------------------+  +---------------+    |
|  | (:9091->9090)    |  | Grafana          |  | TensorBoard   |    |
|  +------------------+  | (:3000)          |  | (:6006)       |    |
|                        +------------------+  +---------------+    |
|                                                                   |
|  [COMMENTATO] ml-training (Python, :50056) - NON ATTIVO          |
+------------------------------------------------------------------+
```

**ATTENZIONE CRITICA**: Le porte nel diagramma sopra mostrano i valori EXPOSE dal Dockerfile, NON le porte docker-compose. Il servizio algo-engine ascolta internamente su 50052/8082/9092 ma docker-compose mappa 50054:50054, 8080:8080, 9093:9093. Il servizio e' quindi **irraggiungibile** dalle porte docker-compose. Vedi sezione 2.5 per dettagli.

### 2.3 Protocolli di Comunicazione

| Origine | Destinazione | Protocollo | Porta Container | Stato | Note |
|---------|-------------|------------|----------------|-------|------|
| Polygon.io | data-ingestion | WebSocket/HTTPS | ext | OK | Reconnect con backoff+jitter, max 50 tentativi |
| Binance | data-ingestion | WebSocket | ext | OK | Via connettore dedicato |
| data-ingestion | PostgreSQL | TCP/SQL | 5432 | OK | Batch writer asincrono |
| data-ingestion | algo-engine | ZeroMQ PUB/SUB | 5555 | OK | Topic: `bar.{symbol}.{tf}` |
| algo-engine | PostgreSQL | TCP/SQL (asyncpg) | 5432 | OK | Via SQLAlchemy async |
| algo-engine | Redis | TCP | 6379 | OK | Kill switch, stato portfolio |
| algo-engine | mt5-bridge | gRPC (TradingSignalService) | 50055 | OK | SendSignal unary RPC |
| algo-engine | ml-training | gRPC (MLInferenceService) | 50056 | NON ATTIVO | Servizio commentato |
| mt5-bridge | PostgreSQL | TCP/SQL | 5432 | OK | Trade recording |
| mt5-bridge | Redis | TCP | 6379 | OK | Rate limiting |
| mt5-bridge | MetaTrader 5 | MT5 API (Windows) | locale | **CRITICO** | Windows-only, no dry-run |
| Prometheus | data-ingestion | HTTP scrape | 9090 | OK | |
| Prometheus | algo-engine | HTTP scrape | 9092* | **ALTO** | *Prometheus config potrebbe puntare a 9093 |
| Prometheus | mt5-bridge | HTTP scrape | 9094 | OK | |
| Grafana | Prometheus | HTTP | 9090 | OK | |

### 2.4 Network Segmentation (Docker)

```
networks:
  frontend:   Grafana (:3000), TensorBoard (:6006), Prometheus
  backend:    PostgreSQL, Redis, data-ingestion, algo-engine, mt5-bridge
  monitoring: Prometheus, Grafana, data-ingestion, algo-engine, mt5-bridge
```

- La segmentazione e' corretta concettualmente
- `frontend` espone solo le UI
- `backend` isola i servizi interni
- `monitoring` permette lo scraping Prometheus

**WARNING F09**: In configurazione attuale, backend NON ha `internal: true`, quindi tutti i servizi sono raggiungibili dall'host. Accettabile per development, da risolvere per produzione.

### 2.5 Analisi Porte — IL PROBLEMA CRITICO

Questo e' il finding piu' importante di questo report. La discrepanza tra porte e' stata verificata riga per riga.

#### Come funziona il sistema di configurazione porte

1. **MoneyMakerBaseSettings** (`shared/python-common/src/moneymaker_common/config.py:43`): `model_config = {"env_prefix": "", "case_sensitive": False}`
2. **BrainSettings** (`services/algo-engine/src/algo_engine/config.py:29-31`): definisce `brain_grpc_port`, `brain_rest_port`, `brain_metrics_port`
3. Con `env_prefix=""`, Pydantic cerca la env var con nome ESATTO del campo (case-insensitive): `BRAIN_GRPC_PORT`, `BRAIN_REST_PORT`, `BRAIN_METRICS_PORT`
4. Il docker-compose (`infra/docker/docker-compose.yml:142-160`) **NON passa** nessuna di queste env vars
5. Risultato: il servizio usa SEMPRE i default da `config.py`

#### Tabella Port Mapping Completa (VERIFICATA)

| Servizio | Dockerfile EXPOSE | docker-compose mapping | .env.example | config.py default | Pydantic env var attesa | Passata in docker-compose? |
|----------|------------------|----------------------|--------------|-------------------|------------------------|---------------------------|
| **algo-engine gRPC** | 50052 | 50054:50054 | MONEYMAKER_BRAIN_GRPC_PORT=50054 | 50052 | BRAIN_GRPC_PORT | **NO** |
| **algo-engine REST** | 8082 | 8080:8080 | BRAIN_REST_PORT=8082 | 8082 | BRAIN_REST_PORT | **NO** |
| **algo-engine metrics** | 9092 | 9093:9093 | BRAIN_METRICS_PORT=9092 | 9092 | BRAIN_METRICS_PORT | **NO** |
| **mt5-bridge gRPC** | 50055 | 50055:50055 | 50055 | 50055 | MONEYMAKER_MT5_BRIDGE_GRPC_PORT | OK (allineato) |
| **mt5-bridge metrics** | 9094 | 9094:9094 | 9094 | 9094 | MONEYMAKER_MT5_BRIDGE_METRICS_PORT | OK (allineato) |
| **data-ingestion ZMQ** | 5555 | 5555:5555 | 5555 | tcp://*:5555 | MONEYMAKER_ZMQ_PUB_ADDR | OK |
| **data-ingestion metrics** | 9090 | 9090:9090 | 9090 | 9090 | MONEYMAKER_METRICS_PORT | OK |
| **data-ingestion health** | 9091 | 8081:8080 | - | MetricsPort+1=9091 | - | **ERRATO** (8080≠9091) |
| **Prometheus** | - | 9091:9090 | - | - | - | OK |
| **Grafana** | - | 3000:3000 | - | - | - | OK |

#### Discrepanze Identificate

**CRITICO (F04) — algo-engine completamente irraggiungibile sulle porte docker-compose**:
- Il servizio ascolta su **50052/8082/9092** (default config.py, non sovrascritto)
- Docker-compose mappa **50054:50054, 8080:8080, 9093:9093** (porte container)
- Il servizio e' internamente su porte diverse → **traffico non arriva**
- La HEALTHCHECK nel Dockerfile (`localhost:9092`) funziona (la porta e' giusta internamente)
- Ma depends_on condition service_healthy passa per il motivo SBAGLIATO — il container e' "healthy" ma irraggiungibile dall'esterno
- Prometheus su `algo-engine:9093` → **FALLISCE** (servizio ascolta su 9092)
- Console su `algo-engine:50054` → **FALLISCE** (servizio ascolta su 50052)
- **NOTA IMPORTANTE**: Il flusso dati principale (ZMQ in, gRPC out a mt5-bridge) NON e' impattato perche' algo-engine e' client, non server, su quelle connessioni

**ALTO (F13) — .env.example usa nomi env var ERRATI**:
- `.env.example:69`: `MONEYMAKER_BRAIN_GRPC_PORT=50054` → Pydantic cerca `BRAIN_GRPC_PORT` (senza prefix `MONEYMAKER_`)
- `.env.example:73`: `BRAIN_REST_PORT=8082` → Valore corretto per config.py ma **ERRATO** per docker-compose (dovrebbe essere 8080)
- `.env.example:74`: `BRAIN_METRICS_PORT=9092` → Stesso problema (dovrebbe essere 9093)
- Anche se le env var vengono caricate, i valori sono quelli sbagliati

**WARNING (F14) — data-ingestion health port mapping errato**:
- Il servizio Go espone health su `MetricsPort + 1 = 9091` (`main.go`)
- Dockerfile HEALTHCHECK: `curl -f http://localhost:9091/healthz` → OK internamente
- Docker-compose: `8081:8080` → mappa host 8081 a container **8080**, ma servizio ascolta su **9091**
- Il health endpoint NON e' raggiungibile dall'host
- L'internal HEALTHCHECK passa (usa localhost:9091) → depends_on funziona
- Ma accesso esterno alla health page da host:8081 e' rotto

**WARNING — Prometheus port confusion**:
- `docker-compose: 9091:9090` (host 9091, container 9090)
- Questo si scontra nominalmente con data-ingestion health (che ascolta su 9091 nel container ma NON e' mappato correttamente)
- Funziona perche' sono container separati, ma crea confusione

### 2.6 Shared Libraries — Analisi

#### moneymaker_common (Python)
- **Dipendenze**: pydantic>=2.5, pydantic-settings>=2.1, structlog>=23.2, prometheus-client>=0.19, redis>=5.0
- **Python**: >=3.10 (target 3.11 nei Dockerfile)
- **Pattern chiave**: `MoneyMakerBaseSettings` con `env_prefix=""` + `case_sensitive=False` legge env var con nome identico al campo
- **Qualita'**: 8/10 — Solida, hash-chain audit trail, Decimal utils, RBAC support
- **Moduli**: config, enums, metrics (28 metriche), decimal_utils, logging (structlog), audit (hash chain), audit_pg (PostgreSQL audit trail), ratelimit, health, secrets, grpc_credentials, exceptions

**Findings specifici**:
1. `config.py:26` — `moneymaker_db_password: str = ""` — Password vuota come default. Il docker-compose forza password via `${MONEYMAKER_DB_PASSWORD:?required}`. Accettabile.
2. `config.py:43` — `env_prefix=""` significa che QUALSIASI env var con nome uguale a un campo puo' causare override inattesi. By design per flessibilita'.
3. `enums.py` — `Direction(str, Enum)` con valori "BUY"/"SELL"/"HOLD" vs proto `DIRECTION_BUY`/`DIRECTION_SELL`/`DIRECTION_HOLD`. La conversione avviene nel layer gRPC. Punto di attenzione (vedi F12).
4. `metrics.py` — 28 metriche Prometheus ben organizzate per dominio. No issue.

#### go-common (Go)
- **Moduli**: config (`LoadBaseConfig()` da env var), health, logging, ratelimit
- **Pattern**: `getEnv(key, fallback)` / `getEnvInt` / `getEnvBool`
- **Importazione**: via `replace` directive nel go.mod per monorepo
- **Qualita'**: 7/10 — Funzionale, nessun YAML parsing (tutto via env var)

### 2.7 Configurazione Brain (`config.py`) — Analisi Dettagliata

**File**: `services/algo-engine/src/algo_engine/config.py` (103 righe)

| Parametro | Default | Docker-compose env | .env.example | Coerente? |
|-----------|---------|-------------------|--------------|-----------|
| brain_grpc_port | 50052 | **NON PASSATO** | MONEYMAKER_BRAIN_GRPC_PORT=50054 (nome sbagliato) | **NO — CRITICO** |
| brain_rest_port | 8082 | **NON PASSATO** | BRAIN_REST_PORT=8082 (valore sbagliato) | **NO** |
| brain_metrics_port | 9092 | **NON PASSATO** | BRAIN_METRICS_PORT=9092 (valore sbagliato) | **NO** |
| brain_zmq_data_feed | tcp://localhost:5555 | BRAIN_ZMQ_DATA_FEED=tcp://data-ingestion:5555 | tcp://localhost:5555 | OK |
| brain_mt5_bridge_target | localhost:50055 | BRAIN_MT5_BRIDGE_TARGET=mt5-bridge:50055 | - | OK |
| brain_ml_enabled | False | **NON PASSATO** | - | OK (ML disabilitato) |
| brain_confidence_threshold | 0.65 | **NON PASSATO** | 0.65 | OK |
| brain_max_daily_loss_pct | 2.0 | **NON PASSATO** | 2.0 | OK |
| brain_max_drawdown_pct | **5.0** | **NON PASSATO** | 5.0 | OK (ma vedi F06 vs MT5) |
| brain_max_lots | **0.10** | **NON PASSATO** | - | OK (ma vedi F08 vs MT5) |
| brain_default_equity | 1000 | **NON PASSATO** | - | OK |
| brain_default_leverage | 100 | **NON PASSATO** | - | OK |

### 2.8 Configurazione MT5 Bridge (`config.py`) — Analisi

**File**: `services/mt5-bridge/src/mt5_bridge/config.py` (44 righe)

| Parametro | Default | .env.example | Brain equivalente | Coerente? |
|-----------|---------|-------------|-------------------|-----------|
| max_drawdown_pct | **"10.0"** | 10.0 | **5.0** | **NO — F06** |
| max_daily_loss_pct | "2.0" | 2.0 | 2.0 | OK |
| max_position_count | 5 | 5 | 5 | OK |
| max_lot_size | **"1.0"** | 1.0 | **0.10** | **DIVERSO — F08** |
| max_spread_points | 30 | - | - | OK |
| signal_dedup_window_sec | 60 | 60 | - | OK |
| signal_max_age_sec | 30 | 30 | - | OK (ma non implementato — vedi Report 08) |

**ALTO (F06) — Drawdown Mismatch**:
- Brain: `brain_max_drawdown_pct = Decimal("5.0")` (`config.py:53`)
- MT5 Bridge: `max_drawdown_pct = "10.0"` (`config.py:25`)
- Il brain smette di tradare al 5%, il bridge accetterebbe fino al 10%
- Non pericoloso in isolamento (brain e' piu' conservativo), ma indica mancanza di coerenza
- **AGGRAVANTE**: I limiti drawdown nel MT5 Bridge sono dichiarati ma **MAI ENFORCED nel codice** (vedi Report 08). order_manager.py non controlla il drawdown.

**WARNING (F08) — Max Lot Size Mismatch**:
- Brain: `brain_max_lots = Decimal("0.10")` — max 0.10 lotti
- MT5 Bridge: `max_lot_size = "1.0"` — max 1.0 lotto
- Brain e' il gatekeeper, quindi non pericoloso, ma confusionario

### 2.9 Docker Compose — Analisi Completa

**File**: `program/infra/docker/docker-compose.yml` (358 righe)

#### Servizi Infrastrutturali
1. **PostgreSQL 16 (TimescaleDB)**: `timescale/timescaledb:latest-pg16`. Health check con pg_isready. TLS condizionale. RBAC passwords (DI_DB_PASSWORD, BRAIN_DB_PASSWORD, MT5_DB_PASSWORD, ADMIN_DB_PASSWORD). Volume `postgres-data`. Init scripts in `./init-db`. **OK**.

2. **Redis 7-alpine**: Password obbligatoria (`${MONEYMAKER_REDIS_PASSWORD:?...}`). TLS condizionale. Volume `redis-data`. **OK**.

#### Servizi Applicativi
3. **data-ingestion** (Go): Build context `../..` (program root). Dockerfile `services/data-ingestion/Dockerfile`. Porte: 5555 (ZMQ), 9090 (metrics), 8081:8080 (health — **ERRATO**, vedi F14). Dipende da postgres+redis healthy. Multi-stage build (golang:1.22 → alpine:3.21). **WARNING** per health port.

4. **algo-engine** (Python): Build context `../..`. Dockerfile `services/algo-engine/Dockerfile`. Porte docker-compose: 50054:50054, 8080:8080, 9093:9093. Porte Dockerfile EXPOSE: 50052, 8082, 9092. **CRITICO** — porte non allineate e nessun env override nel docker-compose. Dipende da data-ingestion+postgres+redis healthy.

5. **mt5-bridge** (Python): Build context `../..`. Porte: 50055:50055, 9094:9094. Allineato con Dockerfile e config.py. Dipende da algo-engine healthy. **CRITICO** — MetaTrader5 package e' Windows-only, nessun dry-run mode per Docker/Linux.

6. **ml-training** (Python): **COMPLETAMENTE COMMENTATO** (righe 177-224). Ha 4 errori nel blocco commentato:
   - Build context errato: `../../services/ml-training` (dovrebbe essere `../..` + `dockerfile: services/ml-training/Dockerfile`)
   - GPU driver `nvidia` ma utente ha AMD RX 9070 XT
   - Mancano env var MONEYMAKER_REDIS_HOST/PASSWORD
   - Volume `ml-models:` commentato nella sezione volumes

#### Servizi Monitoring
7. **Prometheus**: `prom/prometheus:v2.50.1`, porta 9091:9090. Monta alert_rules.yml e prometheus.yml. **OK**.
8. **Grafana**: `grafana/grafana:10.3.3`, porta 3000:3000. Security headers. Monta dashboards e provisioning. **OK**.
9. **TensorBoard**: `tensorflow/tensorflow:2.15.0`, porta 6006:6006. Condivide volume `tensorboard-logs` con algo-engine. Health check wget. **OK**.

#### Volumi
```yaml
volumes:
  postgres-data:    # Persistenza PostgreSQL
  redis-data:       # Persistenza Redis
  prometheus-data:  # Dati Prometheus
  grafana-data:     # Dashboard Grafana
  tensorboard-logs: # Log TensorBoard (condiviso con algo-engine)
  # ml-models:      # COMMENTATO — scommentare con ml-training
```

---

## 3. Findings

| # | Severita | Componente | Problema | File:Riga | Fix |
|---|----------|-----------|----------|-----------|-----|
| F01 | **CRITICO** | mt5-bridge | MetaTrader5 Python package e' Windows-only. Il Dockerfile crea un container Linux che NON PUO' eseguire ordini reali. Non esiste un dry-run/simulation connector per Linux. | `services/mt5-bridge/Dockerfile:7` (comment) | Creare DryRunConnector per testing/dev; MT5 Bridge su Windows VM per prod |
| F02 | **CRITICO** | ml-training | Dockerfile usa `pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime` ma l'utente ha GPU AMD RX 9070 XT (RDNA 4). CUDA e' incompatibile con AMD. | `services/ml-training/Dockerfile:5` | Cambiare a `rocm/pytorch` con ROCm 6.x |
| F03 | **CRITICO** | ml-training | Build context nel docker-compose commentato e' `../../services/ml-training` ma Dockerfile COPY usa `shared/python-common` che non e' sotto quel context. Il build fallirebbe. | `infra/docker/docker-compose.yml:183` | Cambiare a `context: ../..` + `dockerfile: services/ml-training/Dockerfile` |
| F04 | **CRITICO** | algo-engine | Port mismatch TOTALE: Dockerfile EXPOSE 50052/8082/9092 e config.py usa questi default. Docker-compose mappa 50054/8080/9093. Le env var di port override NON sono passate nel docker-compose. Il servizio e' sano internamente ma **irraggiungibile** da Prometheus, Console, e qualsiasi client esterno. | `services/algo-engine/Dockerfile:38` + `config.py:29-31` + `docker-compose.yml:138-140` | Allineare Dockerfile EXPOSE e config.py default a 50054/8080/9093 |
| F05 | **ALTO** | algo-engine | Il HEALTHCHECK nel Dockerfile punta a `localhost:9092` — funziona perche' il default e' 9092. MA se il fix per F04 cambia il default a 9093, bisogna aggiornare anche il HEALTHCHECK. | `services/algo-engine/Dockerfile:41` | Aggiornare HEALTHCHECK a porta 9093 come parte del fix F04 |
| F06 | **ALTO** | risk config | max_drawdown_pct: Brain=5.0% vs MT5 Bridge=10.0%. Limiti incoerenti. **Aggravante**: i limiti drawdown nel MT5 Bridge sono dichiarati in config ma MAI enforced nel codice order_manager.py. | `algo-engine/config.py:53` + `mt5-bridge/config.py:25` | Allineare a 5.0% e implementare enforcement in order_manager.py |
| F07 | **ALTO** | ml-training | docker-compose commentato usa `driver: nvidia` per GPU. Utente ha AMD RX 9070 XT che richiede ROCm, non CUDA/NVIDIA. | `docker-compose.yml:222-224` | Rimuovere sezione nvidia; configurare per ROCm |
| F08 | **ALTO** | lot size | Brain max_lots=0.10 vs MT5 Bridge max_lot_size=1.0. Il bridge accetterebbe lotti 10x piu' grandi di quelli che il brain invierebbe. | config files | Allineare a 0.10 per paper trading; documentare se intenzionale |
| F09 | **WARNING** | network | backend network in docker-compose non ha `internal: true`. Tutti i servizi backend sono raggiungibili dall'host in configurazione attuale. | `docker-compose.yml:344` | Aggiungere `internal: true` per produzione |
| F10 | **WARNING** | proto | market_data.proto usa package `moneymaker.v1.data` diverso da tutti gli altri (`moneymaker.v1`). | `shared/proto/market_data.proto:3` | Documentare la scelta o allineare |
| F11 | **WARNING** | .env | .env.example definisce `MONEYMAKER_BRAIN_GRPC_PORT=50054` ma il nome corretto per Pydantic e' `BRAIN_GRPC_PORT` (senza prefix MONEYMAKER_). La env var non verrebbe mai letta. | `program/.env.example:69` | Rinominare a `BRAIN_GRPC_PORT=50054` |
| F12 | **WARNING** | enums | Direction enum Python ("BUY"/"SELL"/"HOLD") vs proto (DIRECTION_BUY/DIRECTION_SELL/DIRECTION_HOLD). La conversione e' implicita nel layer gRPC — un mapping sbagliato causerebbe ordini con direzione errata. | `enums.py` + `trading_signal.proto` | Aggiungere test esplicito per la mappatura |
| F13 | **ALTO** | env config | Le env var nel .env.example per le porte Brain usano naming convention inconsistente. `MONEYMAKER_BRAIN_GRPC_PORT` non matcha il campo Pydantic `brain_grpc_port`. `BRAIN_REST_PORT=8082` e `BRAIN_METRICS_PORT=9092` hanno valori che NON corrispondono al docker-compose. | `.env.example:69,73,74` | Fix naming a `BRAIN_GRPC_PORT`, `BRAIN_REST_PORT`, `BRAIN_METRICS_PORT` e valori a 50054, 8080, 9093 |
| F14 | **WARNING** | data-ingestion | Docker-compose mappa `8081:8080` per health, ma il servizio Go ascolta su porta 9091 (MetricsPort+1). L'health endpoint e' irraggiungibile dall'host. | `docker-compose.yml:96` + `main.go` | Cambiare mapping a `8081:9091` |
| F15 | **WARNING** | data-ingestion | `config.yaml` e' copiato nel container dal Dockerfile (`COPY services/data-ingestion/config.yaml /app/config/config.yaml`) ma il codice Go **non lo parsa**. Tutta la configurazione viene da env var. Il file e' documentazione orfana. | `services/data-ingestion/Dockerfile:52` | Rimuovere COPY dal Dockerfile o implementare parsing YAML |

---

## 4. Interconnessioni — Come Tutto e' Collegato

### 4.1 Flusso Dati Completo (Tick-to-Trade)

```
EXCHANGE (Polygon.io / Binance)
    |
    | 1. WebSocket connection (persistente, auto-reconnect con backoff)
    v
DATA-INGESTION (Go, ZMQ PUB su :5555)
    |
    | 2a. SQL INSERT tick/bar in TimescaleDB (batch writer asincrono)
    | 2b. ZMQ PUB su topic "bar.{symbol}.{timeframe}" (real-time)
    v
AI-BRAIN (Python, ZMQ SUB da data-ingestion:5555)
    |
    | 3. FeaturePipeline.process() -> vettore 60-dim
    | 4. RegimeClassifier.classify() -> regime (5 regimi)
    | 5. Cascade 4-tier: COPER -> Hybrid -> Knowledge -> Conservative
    | 6. SignalValidator.validate() -> 11 checks fail-fast
    | 7. PositionSizer.calculate() -> lots con Kelly criterion
    | 8. SpiralProtection.check() -> riduzione dopo loss consecutive
    | 9. KillSwitch.is_active() -> veto globale via Redis
    |
    | 10. gRPC SendSignal(TradingSignal) -> mt5-bridge:50055
    v
MT5-BRIDGE (Python, gRPC server su :50055)
    |
    | 11. OrderManager: dedup, spread check, (rate limiting via Redis)
    | 12. MT5Connector.execute() -> MT5 API (Windows only)
    v
METATRADER 5 (Windows VM, 10.0.4.11)
    |
    | 13. Ordine inviato al broker
    v
BROKER
```

### 4.2 Flusso di Stato e Monitoring

```
TUTTI I SERVIZI
    |
    | Prometheus metrics (scrape ogni 15s)
    v
PROMETHEUS (:9091 host, :9090 container)
    |
    | Alert rules evaluation (vedi Report 09 per metric name mismatch)
    v
GRAFANA (:3000) <-- 5 dashboard JSON preconfigurate
    |
    | Visual monitoring per l'operatore
    v
OPERATORE (via Console TUI/CLI — moneymaker_console.py)
    |
    | Console commands -> Redis (kill switch) / gRPC
    v
KILL SWITCH (Redis key: moneymaker:kill_switch:active)
    |
    | Blocca tutti i nuovi trade se attivo
    v
AI-BRAIN (controlla kill switch prima di ogni segnale)
```

### 4.3 Dipendenze di Avvio (docker-compose depends_on)

```
PostgreSQL (no deps)    Redis (no deps)
    |                       |
    +---+---+---+          +---+---+
    |   |   |   |          |   |   |
    v   v   v   v          v   v   v
    DI  BR  MT  ML         DI  BR  MT

DI = data-ingestion: depends_on postgres(healthy) + redis(healthy)
BR = algo-engine: depends_on DI(healthy) + postgres(healthy) + redis(healthy)
MT = mt5-bridge: depends_on BR(healthy)
ML = [commentato]: depends_on postgres(healthy) only
```

**Nota critica**: MT5 Bridge dipende da algo-engine healthy. Il HEALTHCHECK di algo-engine passa (usa localhost:9092, che corrisponde al default). Quindi la catena di avvio funziona, ma le porte esterne restano rotte.

### 4.4 Shared Library Dependency Graph

```
moneymaker_common (Python, 12 moduli)
    ^           ^           ^           ^
    |           |           |           |
algo-engine   mt5-bridge   ml-training   external-data (placeholder)
    ^
    |
moneymaker_proto (5 proto -> 10 file Python generati)
    ^           ^           ^
    |           |           |
algo-engine   mt5-bridge   ml-training

go-common (Go, 4 moduli: config, health, logging, ratelimit)
    ^
    |
data-ingestion
```

### 4.5 Database Access Pattern

| Servizio | Tabelle Lette | Tabelle Scritte | User RBAC |
|----------|--------------|----------------|-----------|
| data-ingestion | - | ohlcv_bars, market_ticks | data_ingestion_svc |
| algo-engine | ohlcv_bars, market_ticks, trading_signals | trading_signals, audit_log | algo_engine_svc |
| mt5-bridge | trading_signals | trade_executions, audit_log | mt5_bridge_svc |
| ml-training | ohlcv_bars, trading_signals | ml_models, training_runs, training_metrics | (non definito — F03 scope) |

### 4.6 Redis Key Pattern

| Servizio | Key Pattern | Tipo | Scopo |
|----------|------------|------|-------|
| algo-engine | `moneymaker:kill_switch:active` | String ("1"/"0") | Kill switch globale |
| algo-engine | `moneymaker:kill_switch:reason` | String | Motivo attivazione |
| algo-engine | `moneymaker:kill_switch:activated_at` | String (ISO timestamp) | Quando attivato |
| algo-engine | `moneymaker:daily_loss:*` | String (Decimal) | Perdita giornaliera |
| algo-engine | `moneymaker:portfolio:equity` | String (Decimal) | Equity corrente |
| mt5-bridge | `ratelimit:*` | Redis (token bucket) | Rate limiting |
| console | `moneymaker:kill_switch:*` | String | Lettura/scrittura stato kill |

### 4.7 moneymaker_services.yaml — Static Service Discovery

**File**: `program/configs/moneymaker_services.yaml` — Definisce IP statici per deployment Proxmox:

| Servizio | Host | Porte |
|----------|------|-------|
| data_ingestion | 10.0.1.10 | ZMQ:5555, metrics:9090, health:8080 |
| database | 10.0.2.10 | postgres:5432, redis:6379 |
| brain | 10.0.4.10 | gRPC:50054, REST:8080, metrics:9093 |
| mt5_bridge | 10.0.4.11 | gRPC:50055, metrics:9094 |
| monitoring | 10.0.5.10 | prometheus:9090, grafana:3000 |

**Nota**: I valori in questo file (brain gRPC:50054, REST:8080, metrics:9093) corrispondono al docker-compose ma NON al config.py default. Conferma che l'intento e' 50054/8080/9093 ma l'implementazione config.py ha i valori sbagliati.

---

## 5. Stato Rispetto a Distribuzione Finale

### Cosa FUNZIONA (pronto per deployment)
- Contratti proto completi e coerenti (5 servizi, 10 file generati)
- Shared libraries Python ben strutturate (moneymaker_common, 12 moduli, qualita' 8/10)
- Shared libraries Go funzionali (go-common, 4 moduli)
- Network segmentation Docker (3 reti: frontend, backend, monitoring)
- RBAC per database (4 utenti per-servizio configurabili)
- TLS condizionale per tutte le connessioni (PostgreSQL, Redis, gRPC)
- Password obbligatorie via shell parameter expansion `:?required`
- Health check per servizi infrastrutturali (PostgreSQL, Redis, TensorBoard)
- Flusso dati principale: data-ingestion → (ZMQ) → algo-engine → (gRPC) → mt5-bridge funzionale architetturalmente

### Cosa NON FUNZIONA (blocca deployment)
1. **Port mismatch algo-engine** — Porte completamente disallineate, servizio irraggiungibile per monitoring e console (F04)
2. **Env var naming** — .env.example usa nomi che Pydantic non riconosce, impedendo port override (F11, F13)
3. **MT5 Bridge in Docker** — Non puo' eseguire trading reale, nessun dry-run mode (F01)
4. **ML Training** — Non deployabile: CUDA per AMD, build context errato, env var mancanti (F02, F03, F07)
5. **Drawdown limits** — Incoerenti tra servizi e non enforced nel MT5 Bridge (F06)
6. **Health port data-ingestion** — Mapping errato nel docker-compose (F14)

---

## 6. Istruzioni con Checkbox

### Segmento A: Fix Porte algo-engine (CRITICO — F04, F05, F11, F13)

L'obiettivo e' allineare TUTTE le porte algo-engine a 50054/8080/9093 (i valori intesi da docker-compose e moneymaker_services.yaml).

- [ ] **A1**: `services/algo-engine/src/algo_engine/config.py:29` — Cambiare `brain_grpc_port: int = 50052` → `brain_grpc_port: int = 50054`
- [ ] **A2**: `services/algo-engine/src/algo_engine/config.py:30` — Cambiare `brain_rest_port: int = 8082` → `brain_rest_port: int = 8080`
- [ ] **A3**: `services/algo-engine/src/algo_engine/config.py:31` — Cambiare `brain_metrics_port: int = 9092` → `brain_metrics_port: int = 9093`
- [ ] **A4**: `services/algo-engine/Dockerfile:38` — Cambiare `EXPOSE 50052 8082 9092` → `EXPOSE 50054 8080 9093`
- [ ] **A5**: `services/algo-engine/Dockerfile:41` — Cambiare HEALTHCHECK da `localhost:9092` → `localhost:9093`
- [ ] **A6**: `program/.env.example:69` — Cambiare `MONEYMAKER_BRAIN_GRPC_PORT=50054` → `BRAIN_GRPC_PORT=50054`
- [ ] **A7**: `program/.env.example:73` — Cambiare `BRAIN_REST_PORT=8082` → `BRAIN_REST_PORT=8080`
- [ ] **A8**: `program/.env.example:74` — Cambiare `BRAIN_METRICS_PORT=9092` → `BRAIN_METRICS_PORT=9093`
- [ ] **A9**: Verificare coerenza con `moneymaker_services.yaml` — gia' corretto (50054/8080/9093)
- [ ] **A10**: Testare: `docker compose build algo-engine && docker compose up algo-engine` e verificare che le porte rispondano

### Segmento B: Strategia MT5 Bridge (CRITICO — F01)

- [ ] **B1**: Creare `DryRunConnector` in `services/mt5-bridge/src/mt5_bridge/connectors/` che simuli ordini senza MT5 per testing/development su Linux
- [ ] **B2**: Decidere strategia produzione: (a) eseguire mt5-bridge direttamente su Windows VM 10.0.4.11 senza Docker, oppure (b) usare gRPC reverse proxy
- [ ] **B3**: Se opzione (a): creare script di avvio Windows (`start_mt5_bridge.ps1`)
- [ ] **B4**: Se opzione (a): aggiornare `BRAIN_MT5_BRIDGE_TARGET` per puntare a 10.0.4.11:50055
- [ ] **B5**: Aggiornare commento nel Dockerfile mt5-bridge per chiarire che e' per CI/testing only
- [ ] **B6**: Documentare strategia di deployment nel README mt5-bridge

### Segmento C: Fix ML Training (CRITICO — F02, F03, F07)

- [ ] **C1**: `services/ml-training/Dockerfile:5` — Cambiare base image a `rocm/pytorch:rocm6.0_ubuntu22.04_py3.10_pytorch_2.1.2` o equivalente AMD
- [ ] **C2**: `docker-compose.yml:183` — Cambiare `context: ../../services/ml-training` → `context: ../..` e aggiungere `dockerfile: services/ml-training/Dockerfile`
- [ ] **C3**: `docker-compose.yml:222-224` — Rimuovere sezione `driver: nvidia` / `capabilities: [gpu]` e configurare per ROCm
- [ ] **C4**: Aggiungere nel docker-compose commentato: `MONEYMAKER_REDIS_HOST=redis` e `MONEYMAKER_REDIS_PASSWORD=${MONEYMAKER_REDIS_PASSWORD:?required}`
- [ ] **C5**: `docker-compose.yml:357` — Scommentare `ml-models:` nella sezione volumes
- [ ] **C6**: Aggiungere `ML_DB_USER` e `ML_DB_PASSWORD` al `.env.example`
- [ ] **C7**: Testare build: `docker build -f services/ml-training/Dockerfile .` dal context `program/`

### Segmento D: Allineamento Limiti di Rischio (ALTO — F06, F08)

- [ ] **D1**: Decidere valore unico per `max_drawdown_pct`: raccomandazione **5.0%**
- [ ] **D2**: `services/mt5-bridge/src/mt5_bridge/config.py:25` — Cambiare `max_drawdown_pct: str = "10.0"` → `"5.0"`
- [ ] **D3**: `program/.env.example` — Aggiornare `MAX_DRAWDOWN_PCT=5.0`
- [ ] **D4**: Decidere `max_lot_size`: raccomandazione **0.10** per paper trading, documentare se diverso per produzione
- [ ] **D5**: `services/mt5-bridge/src/mt5_bridge/config.py:23` — Cambiare `max_lot_size: str = "1.0"` → `"0.10"`
- [ ] **D6**: Documentare tabella limiti di rischio concordati in GUIDE o README

### Segmento E: Fix Health Port data-ingestion (WARNING — F14, F15)

- [ ] **E1**: `docker-compose.yml:96` — Cambiare `- "8081:8080"` → `- "8081:9091"` per allineare con la porta health reale
- [ ] **E2**: Decidere se mantenere `config.yaml` nel container data-ingestion (documentazione) o rimuovere `COPY` dal Dockerfile
- [ ] **E3**: Se mantenuto: aggiungere commento nel Dockerfile che chiarisce che config.yaml e' solo documentazione

### Segmento F: Hardening Docker per Produzione (WARNING — F09)

- [ ] **F1**: `docker-compose.yml:344` — Aggiungere `internal: true` al network `backend` per produzione
- [ ] **F2**: Valutare rimozione `ports:` mappings per PostgreSQL e Redis in produzione
- [ ] **F3**: Verificare che TLS certificates non siano committati nel repository (controllare `.gitignore` per `infra/docker/certs/`)
- [ ] **F4**: Aggiungere health check funzionale per mt5-bridge (attualmente dipende da urllib che potrebbe non funzionare senza MT5)

### Segmento G: Documentazione (WARNING — F10, F12)

- [ ] **G1**: Documentare la scelta del package `moneymaker.v1.data` vs `moneymaker.v1` nei proto
- [ ] **G2**: Aggiungere test esplicito per mappatura Direction enum Python ↔ proto
- [ ] **G3**: Aggiornare `moneymaker_services.yaml` per includere ml-training e monitoring dettagliato
- [ ] **G4**: Aggiornare `GUIDE/03_STATO_ARCHITETTURA_ONESTO.md` con lo stato reale dei port mapping

---

## 7. Riepilogo Severita'

| Severita | Count | Finding IDs |
|----------|-------|------------|
| CRITICO | 4 | F01, F02, F03, F04 |
| ALTO | 5 | F05, F06, F07, F08, F13 |
| WARNING | 6 | F09, F10, F11, F12, F14, F15 |
| **Totale** | **15** | |

---

*Fine Report 01 — Prossimo: Report 02 (Algo Engine Core Pipeline)*
