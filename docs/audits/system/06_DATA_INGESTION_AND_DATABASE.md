# REPORT 06: Data Ingestion, Database Schema e External Data

> **Revisione**: 2026-03-05 — Verifica line-by-line su codice reale.
> Cambiamenti rispetto alla versione precedente:
> - F01 data race confermato (polygon.go reconnectAttempts non atomico)
> - F02 nessuna reconnection Binance confermato (disabilitato in config, OK per V1)
> - Aggiunto F14 CRITICO: ohlcv_bars e market_ticks senza PRIMARY KEY/UNIQUE — duplicati possibili
> - Aggiunto F15: DSN password rischia di apparire nei log (main.go:61-67)
> - Aggiunto F16: SpreadAvg hardcoded a Zero nel DBWriter (writer.go:337)
> - Aggiunto F17: Sync flush fallback blocca main loop sotto backpressure (writer.go:305-314)
> - Aggiunto F18: Health port mismatch Dockerfile EXPOSE 9091 vs docker-compose 8081 (cross-ref Report 01)
> - Confermato: aggregator callback sotto mutex (F03), symbol map hardcoded (F04)

**Data Audit**: 2026-03-02 (rev. 2026-03-05)
**Auditor**: Claude Opus 4.6
**Scope**: Servizio Go data-ingestion (13 file), 7 script SQL init-db, servizio external-data, configurazione Prometheus/Grafana
**Severita Massima Trovata**: **CRITICO** (aggiornato da ALTA)

---

## Executive Summary

La pipeline di ingestione dati e' ben architettata con un servizio Go performante, schema TimescaleDB con hypertables e compressione, e un servizio external-data per macro-dati. Sono stati identificati **1 errore CRITICO** (tabelle DB senza PRIMARY KEY — duplicati possibili), **3 errori ALTI** (data race Polygon, assenza reconnection Binance, sync flush che blocca main loop), e **7 WARNING** (callback bloccante aggregatore, symbol map hardcoded, ZMQ senza HWM, Redis configurato ma non usato, SpreadAvg sempre Zero, DSN credential leak risk, health port mismatch).

---

## 1. Inventario Completo dei File

### 1.1 Servizio Data Ingestion (Go)
| File | Path | LoC | Stato |
|------|------|-----|-------|
| main.go | `services/data-ingestion/cmd/server/main.go` | 348 | WARNING |
| connector.go | `services/data-ingestion/internal/connectors/connector.go` | 103 | OK |
| polygon.go | `services/data-ingestion/internal/connectors/polygon.go` | 581 | ERRORE |
| binance.go | `services/data-ingestion/internal/connectors/binance.go` | 255 | ERRORE |
| mock.go | `services/data-ingestion/internal/connectors/mock.go` | 248 | OK |
| normalizer.go | `services/data-ingestion/internal/normalizer/normalizer.go` | 464 | OK |
| aggregator.go | `services/data-ingestion/internal/aggregator/aggregator.go` | 210 | WARNING |
| aggregator_test.go | `services/data-ingestion/internal/aggregator/aggregator_test.go` | 212 | OK |
| writer.go | `services/data-ingestion/internal/dbwriter/writer.go` | 444 | OK |
| batch.go | `services/data-ingestion/internal/dbwriter/batch.go` | 184 | OK |
| buffer.go | `services/data-ingestion/internal/dbwriter/buffer.go` | 125 | OK |
| metrics.go | `services/data-ingestion/internal/dbwriter/metrics.go` | 164 | OK |
| publisher.go | `services/data-ingestion/internal/publisher/publisher.go` | 196 | WARNING |
| go.mod | `services/data-ingestion/go.mod` | 27 | OK |
| config.yaml | `services/data-ingestion/config.yaml` | 227 | OK |

### 1.2 Database Init Scripts
| File | Path | LoC | Stato |
|------|------|-----|-------|
| 001_init.sql | `infra/docker/init-db/001_init.sql` | ~150 | OK |
| 002_ml_tables.sql | `infra/docker/init-db/002_ml_tables.sql` | ~80 | OK |
| 003_strategy_tables.sql | `infra/docker/init-db/003_strategy_tables.sql` | ~90 | OK |
| 004_economic_calendar.sql | `infra/docker/init-db/004_economic_calendar.sql` | ~200 | OK |
| 005_macro_data.sql | `infra/docker/init-db/005_macro_data.sql` | ~300 | OK |
| 006_rbac_roles.sql | `infra/docker/init-db/006_rbac_roles.sql` | ~100 | OK |
| 007_rbac_passwords.sh | `infra/docker/init-db/007_rbac_passwords.sh` | ~50 | WARNING |

### 1.3 External Data Service
| File | Path | Stato |
|------|------|-------|
| __init__.py | `services/external-data/src/external_data/__init__.py` | OK |
| config.py | `services/external-data/src/external_data/config.py` | OK |
| main.py | `services/external-data/src/external_data/main.py` | OK |
| scheduler.py | `services/external-data/src/external_data/scheduler.py` | OK |
| fred.py | `services/external-data/src/external_data/providers/fred.py` | OK |
| cboe.py | `services/external-data/src/external_data/providers/cboe.py` | WARNING |
| cftc.py | `services/external-data/src/external_data/providers/cftc.py` | OK |

### 1.4 Monitoring Config
| File | Path | Stato |
|------|------|-------|
| prometheus.yml | `services/monitoring/prometheus/prometheus.yml` | OK |
| alert_rules.yml | `services/monitoring/prometheus/alert_rules.yml` | OK |

---

## 2. Analisi Dettagliata - Servizio Data Ingestion

### 2.1 Architettura del Flusso Dati

```
EXCHANGE (Polygon.io / Binance WebSocket)
    |
    | conn.ReadMessage() → RawMessage{Exchange, Symbol, Channel, Data, Timestamp}
    v
NORMALIZER
    |
    | NormalizeRawMessage() → NormalizedTick{Exchange, Symbol, Price(decimal), Extra map}
    v
+---+---+---+
|           |
v           v
ZMQ PUB     DB WRITER
|           |
| topic:    | COPY bulk insert
| "tick.*"  | BatchSize=1000
| "bar.*"   | FlushInterval=5s
|           | Workers=2
v           v
AI-BRAIN    TIMESCALEDB
(SUB)       (market_ticks, ohlcv_bars)
            |
            |
            v
         AGGREGATOR
            |
            | AddTick() → pendingBar → OnComplete callback
            v
         +---+---+
         |       |
         v       v
      ZMQ PUB   DB WRITER
      "bar.*"   ohlcv_bars
```

### 2.2 main.go - Entry Point (348 LoC)

**Cosa fa**: Orchestrazione dell'intero servizio. Inizializza logger, config, DBWriter, health checker, ZMQ publisher, normalizer, aggregator, connettore, e il main event loop.

**Symbol Mapping (hardcoded, linee 143-172)**:
30+ mapping da formato exchange a formato canonico MONEYMAKER:
- `"c:xauusd"` → `"XAU/USD"` (Polygon Forex)
- `"btcusdt"` → `"BTC/USDT"` (Binance)
- Copertura: XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCAD, USDCHF

**Timeframe configurati**: M1, M5, M15, H1 (attivi), H4 e D1 (definiti ma non attivati di default)

**Graceful Shutdown**:
1. SIGINT/SIGTERM catturato
2. `aggregator.FlushAll()` → emette tutte le bar pendenti
3. `dbWriter.FlushTicks()` + `dbWriter.FlushBars()` → drain database
4. Health = NotReady
5. HTTP server shutdown (15s timeout)
6. `connector.Close()` chiude WebSocket

**Problemi**:
- **WARNING**: Symbol map hardcoded in main.go. Richiede ricompilazione per aggiungere simboli. Dovrebbe essere in config.yaml.
- **WARNING**: Nessuna metrica Prometheus esportata dal servizio Go (solo health check). dbwriter.Metrics() esiste ma non e' esposto via HTTP.

### 2.3 connector.go - Interface (103 LoC)

**Cosa fa**: Definisce l'interfaccia `Connector` e il tipo `RawMessage`.

```go
type Connector interface {
    Name() string
    Connect() error
    Subscribe(symbols, channels []string) error
    ReadMessage() (RawMessage, error)
    Close() error
}

type RawMessage struct {
    Exchange  string   // "polygon", "binance"
    Symbol    string   // formato nativo
    Channel   string   // "trade", "kline"
    Data      []byte   // JSON payload
    Timestamp int64    // Unix nanoseconds
}
```

**Stato**: OK - Design pulito, interface-based. Permette mock, Polygon, Binance come implementazioni.

### 2.4 polygon.go - Connettore Polygon.io (581 LoC)

**Cosa fa**: WebSocket client per Polygon.io Forex con autenticazione, reconnection automatica, exponential backoff con jitter.

**Caratteristiche**:
- Connessione WebSocket con autenticazione API key
- Subscription a canali C (trade), CA (aggregate), CQ (quote)
- Message buffer di 256 messaggi (non-blocking)
- Reconnection automatica con exponential backoff (base 2s, max 60s, ±20% jitter)
- Circuit breaker dopo 50 tentativi falliti
- Ping loop a 30s per keepalive
- State machine atomica: disconnected→connecting→connected→reconnecting→closed

**ERRORE ALTO - Data Race su `reconnectAttempts`**:
- `reconnectAttempts` e' un campo `int` (non atomico) letto/scritto senza mutex in `reconnect()` (linea 280) e `dialAndAuth()` (linea 255)
- Puo' causare: backoff non corretto, circuit breaker che non scatta, o panic
- **Fix**: Convertire a `atomic.Int32` o proteggere con mutex

**WARNING - Drop silenzioso messaggi**:
- Se il buffer di 256 messaggi e' pieno, il messaggio piu' vecchio viene droppato senza log/metrica
- Perdita di osservabilita' sui messaggi persi
- **Fix**: Aggiungere contatore atomico `droppedMessages` e log periodico

### 2.5 binance.go - Connettore Binance (255 LoC)

**Cosa fa**: WebSocket client per Binance spot market. Piu' semplice di Polygon.

**ERRORE ALTO - Nessuna Reconnection Logic**:
- A differenza di Polygon, Binance connector NON ha reconnection automatica
- Su disconnessione WebSocket, `closed = true` e il servizio si ferma
- Richiede restart manuale
- **Mitigazione attuale**: Binance e' DISABILITATO in config.yaml (`enabled: false`)
- **Fix richiesto prima di attivare Binance**: Implementare reconnection con backoff (copiare da Polygon)

**WARNING - Stream parsing incompleta**:
- Commento TODO alla linea 159 indica parsing incompleto del stream envelope
- `parseStreamEnvelope()` funziona ma potrebbe non gestire tutti i formati Binance

**WARNING - Data race su `subscriptionID`**:
- `subscriptionID` incrementato senza atomics in `Subscribe()`
- Rischio se Subscribe() chiamato concorrentemente

### 2.6 mock.go - Mock Connector (248 LoC)

**Stato**: OK - Eccellente design con functional options pattern. Usato per test e development. Permette inject messaggi sintetici, callback personalizzati, e generazione automatica a intervallo configurabile.

### 2.7 normalizer.go - Normalizzatore (464 LoC)

**Cosa fa**: Converte messaggi raw exchange-specific in formato canonico `NormalizedTick`.

```go
type NormalizedTick struct {
    Exchange, Symbol, EventType string
    Price, Quantity             decimal.Decimal  // shopspring/decimal
    Side                       string           // "buy"/"sell"/""
    ExchangeTimestamp          int64            // ns UTC
    IngestTimestamp            int64            // ns UTC
    NormalizeTimestamp         int64            // ns UTC
    Extra                      map[string]interface{}  // bid, ask, spread, OHLCV
}
```

**Handler per exchange**:
- `normalizeBinance()`: Trade events con buyer/maker detection
- `normalizePolygon()`: Dispatch a Trade, Aggregate, Quote handlers
- `normalizeMock()`: Parsing semplificato per test

**Precisione finanziaria**:
- Usa `json.NewDecoder + UseNumber()` per evitare perdita precisione float64
- Tutti i prezzi calcolati con `shopspring/decimal`
- Mid-price: `(bid.Add(ask)).Div(decimal.NewFromInt(2))`

**TODO nel codice**:
- NormalizerPool per parallelismo (non necessario per V1)
- Event types aggiuntivi (depth, funding, liquidations)
- Exchange aggiuntivi (Bybit, OKX, Coinbase)

**Stato**: OK - Solido, preciso, ben documentato

### 2.8 aggregator.go - Aggregatore OHLCV (210 LoC)

**Cosa fa**: Accumula tick in barre OHLCV per ogni combinazione simbolo+timeframe.

**Timeframe supportati**: M1 (1min), M5, M15, H1, H4, D1

**Logica core** (`AddTick()`):
1. Per ogni timeframe configurato:
   - Calcola `openTime = floorTime(tickTime, timeframe)` (es. 12:34:56 → 12:30:00 per M5)
   - Se confine temporale superato → emetti bar completata via callback
   - Aggiorna pendingBar: close=price, high=max(high,price), low=min(low,price), volume+=vol, tickCount++

**WARNING - Callback chiamata dentro il lock**:
- `onComplete(completedBar)` e' chiamata con il mutex acquisito (linea 141)
- Se il callback e' lento (es. ZMQ publish o DB write bloccante), tutto il main loop si blocca
- **Fix**: Spostare la callback fuori dal lock, o eseguirla in goroutine separata

**Test**: `aggregator_test.go` (212 LoC) con 9 test che coprono:
- Inizializzazione, tick singolo/multipli, confine temporale
- Timeframe multipli, simboli multipli, flush shutdown
- Accesso concorrente (100 goroutine)
- Mapping timeframe→durata

### 2.9 dbwriter/ - Writer Database (917 LoC totali)

**writer.go (444 LoC)**: Worker pool pattern con buffer e batch insert.
- `Config`: BatchSize=1000, FlushInterval=5s, WorkerCount=2
- Pool pgx con MaxConns=WorkerCount*2, MinConns=WorkerCount
- Channel-based flush con fallback sincrono se canale pieno
- Graceful shutdown: flush finale, attendi worker, chiudi pool

**batch.go (184 LoC)**: Insert bulk con COPY protocol (piu' efficiente di INSERT).
- `insertTicks()`: COPY protocol per market_ticks
- `insertBars()`: COPY protocol per ohlcv_bars
- Fallback: `InsertTicksBatch()` con INSERT + ON CONFLICT DO NOTHING

**buffer.go (125 LoC)**: Buffer thread-safe con capacita' fissa.
- `TickBuffer` e `BarBuffer` con mutex per Add/Flush
- Auto-flush quando raggiunge capacita'

**metrics.go (164 LoC)**: Contatori atomici per osservabilita'.
- ticksReceived, ticksFlushed, barsReceived, barsFlushed, flushErrors
- AvgFlushDuration, Stats() per snapshot completo

**Stato**: OK - Production-grade con pattern worker pool ben implementato

### 2.10 publisher.go - ZMQ Publisher (196 LoC)

**Cosa fa**: Pubblica messaggi su ZeroMQ PUB socket con topic-based routing.

**Topic format**: `"event_type.exchange.symbol"` (es. `"bar.polygon.XAU/USD.M5"`)

**WARNING - Nessun High-Water Mark**:
- Socket ZMQ senza HWM puo' crescere in memoria se subscriber e' lento
- **Fix**: Impostare SO_HWM a valore ragionevole (es. 10000 messaggi)

**WARNING - 100ms sleep fisso su Close()**:
- Delay hardcoded per flush in-flight, potrebbe non bastare
- **Fix**: Rendere configurabile o usare SO_LINGER

### 2.11 config.yaml (227 LoC)

**Configurazione completa** del servizio:
- **Polygon**: Abilitato, 8 simboli Forex, canali trade+aggregate
- **Binance**: Disabilitato per V1
- **Database**: batch_size=1000, flush_interval=5s, workers=2
- **Redis**: Configurato (TTL=300s, prefix=moneymaker:tick:) ma **NON usato nel codice**
- **Aggregation**: M1, M5, M15, H1, H4, D1

**WARNING**: Sezione Redis in config.yaml ma nessuna integrazione Redis nel codice Go. O implementare o rimuovere.

---

## 3. Analisi Dettagliata - Schema Database

### 3.1 Tabelle Core (001_init.sql)

| Tabella | Tipo | Chunk | Compressione | Retention |
|---------|------|-------|-------------|-----------|
| ohlcv_bars | Hypertable | 1 giorno | dopo 7 giorni (by symbol,timeframe) | Nessuna |
| market_ticks | Hypertable | 1 ora | dopo 1 giorno (by symbol) | Nessuna |
| trading_signals | Regular | - | - | Nessuna |
| trade_executions | Regular | - | - | Nessuna |
| audit_log | Regular | - | - | Nessuna |

**audit_log**: Append-only con SHA-256 hash chain.
- Trigger `prevent_audit_modification()` blocca UPDATE e DELETE
- Campi: service, action, entity_type, entity_id, details (JSONB), prev_hash, hash
- **Eccellente**: Design tamper-proof per compliance

**CRITICO F14**: Le tabelle `ohlcv_bars` e `market_ticks` **non hanno PRIMARY KEY o UNIQUE constraint**. Questo significa che INSERT duplicati non vengono rilevati, e il `ON CONFLICT DO NOTHING` in `batch.go` non scatta mai. I backtest potrebbero restituire conteggi errati.

**Fix**: `ALTER TABLE ohlcv_bars ADD CONSTRAINT pk_ohlcv PRIMARY KEY (time, symbol, timeframe);` e `ALTER TABLE market_ticks ADD CONSTRAINT pk_ticks PRIMARY KEY (time, symbol);`

**WARNING**: Nessuna retention policy sulle tabelle. I dati cresceranno illimitatamente. Particolarmente critico per `market_ticks` (chunk 1 ora) e `audit_log`.

### 3.2 Tabelle ML (002_ml_tables.sql)

| Tabella | Tipo | Scopo |
|---------|------|-------|
| model_registry | Regular | Registro modelli con versioning |
| model_metrics | Regular | Metriche temporali per modello |
| ml_predictions | Hypertable | Log inferenze (compressione 7 giorni) |

**Nota**: Queste tabelle sono pronte ma il servizio ml-training non e' ancora operativo.

### 3.3 Tabelle Strategy (003_strategy_tables.sql)

| Tabella | Tipo | Scopo |
|---------|------|-------|
| strategy_performance | Hypertable | P&L per singolo trade (compressione 30 giorni) |
| strategy_daily_summary | Materialized View | Aggregazione giornaliera con continuous aggregate |

**strategy_daily_summary** e' una Continuous Aggregate con refresh ogni ora, lookback 7 giorni. Calcola: total_signals, wins, losses, total_profit, avg_confidence per strategia+simbolo+giorno.

### 3.4 Calendario Economico (004_economic_calendar.sql)

| Tabella | Tipo | Scopo |
|---------|------|-------|
| economic_events | Hypertable | Eventi economici (chunk 7 giorni) |
| trading_blackouts | Hypertable | Finestre di blackout trading |
| event_impact_rules | Regular | Regole configurabili per blackout |

**Sistema di Blackout Automatico**:
- Trigger `auto_generate_blackouts` su INSERT in economic_events
- Funzione `generate_blackouts_for_event()` genera blackout per ogni simbolo affetto
- Funzione `is_trading_blacked_out(symbol, time)` per query real-time
- **Regole pre-populate**: NFP, CPI, GDP, FOMC (US), ECB, BoE, BoJ con finestre 15-60 minuti
- **Simboli coperti**: XAU/USD, EUR/USD, GBP/USD, USD/JPY, AUD/USD, NZD/USD, USD/CAD, USD/CHF

**View utilita**:
- `upcoming_high_impact_events`: Prossimi 50 eventi high-impact
- `active_blackouts`: Blackout attualmente attivi

### 3.5 Macro Data (005_macro_data.sql)

| Tabella | Tipo | Retention | Scopo |
|---------|------|-----------|-------|
| vix_data | Hypertable | 1 anno | Indice di paura (regime 0/1/2) |
| yield_curve_data | Hypertable | 5 anni | Curva rendimenti Treasury |
| real_rates_data | Hypertable | 5 anni | Tassi reali (nominal - breakeven) |
| dxy_data | Hypertable | 1 anno | Dollar index |
| cot_reports | Hypertable | 10 anni | Positioning istituzionale |
| recession_probability | Hypertable | 10 anni | Probabilita' recessione Fed |

**macro_snapshot**: Materialized View con snapshot corrente di tutti i macro-dati per accesso veloce.

**Trigger auto-calcolo**:
- `vix_calc_trigger`: Calcola regime (calm/elevated/panic), term_slope, is_contango
- `yield_calc_trigger`: Calcola spread 2s10s, 5s30s, is_inverted

### 3.6 RBAC (006_rbac_roles.sql + 007_rbac_passwords.sh)

**4 ruoli definiti** con permessi minimi:

| Ruolo | Lettura | Scrittura | Scopo |
|-------|---------|-----------|-------|
| data_ingestion_svc | market data, macro | market data, macro, audit | Ingestione dati |
| algo_engine_svc | market, ml, macro, events, strategy | signals, predictions, strategy, audit | Generazione segnali |
| mt5_bridge_svc | signals | executions, strategy(update), audit | Esecuzione ordini |
| moneymaker_admin | ALL | ALL | Migrazione e manutenzione |

**007_rbac_passwords.sh**: Script bash che imposta password da variabili d'ambiente (`ALTER ROLE ... WITH PASSWORD`).

**WARNING**: Le password compaiono in plaintext nei log PostgreSQL quando esegue `ALTER ROLE`. Per produzione, considerare SCRAM-SHA-256 o meccanismo piu' sicuro.

---

## 4. Analisi Dettagliata - External Data Service

### 4.1 Architettura

```
MacroDataScheduler
    |
    +-> VIX Job (ogni 1 min)
    |   |-> CBOEProvider.fetch_vix()
    |   |-> fallback: YahooVIXProvider
    |   |-> save to Redis + TimescaleDB
    |
    +-> Yield/Rates Job (ogni 60 min)
    |   |-> FREDProvider.fetch_yield_curve()
    |   |-> FREDProvider.fetch_real_rates()
    |   |-> FREDProvider.fetch_recession_probability()
    |   |-> save to Redis + TimescaleDB
    |
    +-> COT Job (ogni 24h)
        |-> CFTCProvider.fetch_latest_cot()
        |-> save to Redis + TimescaleDB
```

### 4.2 Provider: CBOE (VIX)
- Fonte primaria: `cdn.cboe.com/api/global/delayed_quotes/`
- Fallback: Yahoo Finance API (`query1.finance.yahoo.com`)
- Regime: 0=calm (<15), 1=elevated (15-25), 2=panic (>=25)
- **TODO trovato**: `# TODO: Add VIX futures fetch for term structure` (cboe.py:179)

### 4.3 Provider: FRED (Yields, Rates, Recession)
- API: `api.stlouisfed.org/fred`
- Serie: DGS2, DGS5, DGS10, DGS30 (Treasury yields), T10YIE, T5YIE (breakeven), RECPROUSM156N (recession)
- Rate limit: 120 req/min (tier gratuito)

### 4.4 Provider: CFTC (COT)
- Fonte: `cftc.gov/dea/newcot/c_disagg.txt` (tab-separated)
- Mercati: GOLD, SILVER, EUR, JPY, GBP, CHF, CAD, AUD, DXY, WTI, NG
- Sentiment: bullish (net > 10% OI), bearish (net < -10% OI), neutral

### 4.5 Caching Redis
- Key pattern: `macro:vix`, `macro:yield_curve`, `macro:real_rates`, `macro:cot:{market}`
- TTL: 300 secondi

**Nota**: Il servizio external-data NON e' nel docker-compose.yml. Manca il Dockerfile e la configurazione di deployment. Attualmente funziona solo in esecuzione locale.

---

## 5. Analisi Monitoring

### 5.1 prometheus.yml
- Scrape interval: 15s
- Scrape targets: data-ingestion:9090, algo-engine:9093, mt5-bridge:9094, self:9090
- **OK**: Coerente con le porte definite nel docker-compose

### 5.2 alert_rules.yml (10 regole)

**Safety (5 regole, intervallo 15s)**:
1. `KillSwitchActivated` (CRITICAL, immediato) - kill switch attivo
2. `CriticalDrawdown` (CRITICAL, immediato) - drawdown > 5%
3. `HighDrawdown` (WARNING, 5 min) - drawdown > 3%
4. `DailyLossApproaching` (WARNING, 1 min) - loss > 1.5% (75% del limite)
5. `SpiralProtectionActive` (WARNING, immediato) - 3+ loss consecutive

**Infrastructure (5 regole, intervallo 30s)**:
1. `NoTicksReceived` (CRITICAL, 5 min) - nessun tick per 5 minuti
2. `HighPipelineLatency` (WARNING, 5 min) - P99 > 100ms
3. `ServiceDown` (CRITICAL, 1 min) - servizio non raggiungibile
4. `HighErrorRate` (WARNING, 5 min) - errori > 0.1/s
5. `BridgeUnavailable` (CRITICAL, 2 min) - MT5 Bridge non raggiungibile

**Nota su nome metriche**: Le regole usano `moneymaker_kill_switch_active`, `moneymaker_portfolio_drawdown_pct`, ma le metriche definite in `metrics.py` sono `moneymaker_brain_kill_switch_active`, `moneymaker_brain_drawdown_pct`. **POSSIBILE MISMATCH** nei nomi - verificare se le metriche emesse dal brain corrispondono a quelle referenziate nelle alert rules.

---

## 6. Findings Critici

| # | Severita | Componente | Problema | Fix |
|---|----------|-----------|----------|-----|
| F01 | **ALTO** | polygon.go | Data race su `reconnectAttempts` - campo int letto/scritto senza sync in goroutine diverse | Convertire a `atomic.Int32` |
| F02 | **ALTO** | binance.go | Nessuna reconnection logic - servizio muore su disconnessione | Implementare backoff+reconnect come Polygon |
| F03 | **WARNING** | aggregator.go | `onComplete` callback chiamata con mutex acquisito - blocca main loop se lenta | Spostare fuori dal lock o goroutine separata |
| F04 | **WARNING** | main.go | Symbol map hardcoded (30+ mapping) - richiede ricompilazione | Spostare in config.yaml |
| F05 | **WARNING** | publisher.go | Nessun HWM su socket ZMQ - memoria illimitata con subscriber lento | Impostare SO_HWM |
| F06 | **WARNING** | config.yaml | Sezione Redis configurata ma mai usata nel codice | Implementare o rimuovere |
| F07 | **WARNING** | 001_init.sql | Nessuna retention policy su ohlcv_bars e market_ticks | Aggiungere `add_retention_policy()` |
| F08 | **WARNING** | alert_rules.yml | Nome metriche nelle regole (`moneymaker_kill_switch_active`) potrebbe non corrispondere a quelle emesse (`moneymaker_brain_kill_switch_active`) | Verificare e allineare |
| F09 | **WARNING** | 007_rbac_passwords.sh | Password in plaintext nei log PostgreSQL | Usare SCRAM-SHA-256 |
| F10 | **WARNING** | external-data | Servizio non in docker-compose, manca Dockerfile per deployment | Creare Dockerfile e aggiungere a docker-compose |
| F11 | **BASSO** | binance.go | subscriptionID non atomico | Usare atomic.Int32 |
| F12 | **BASSO** | publisher.go | 100ms sleep hardcoded su Close() | Rendere configurabile |
| F13 | **BASSO** | cboe.py | TODO: VIX futures per term structure | Implementare quando necessario |
| F14 | **CRITICO** | 001_init.sql:10-53 | **ohlcv_bars e market_ticks senza PRIMARY KEY/UNIQUE constraint** — duplicati possibili, ON CONFLICT DO NOTHING in batch.go non scatta mai | Aggiungere `PRIMARY KEY (time, symbol, timeframe)` per ohlcv_bars e `PRIMARY KEY (time, symbol)` per market_ticks |
| F15 | **WARNING** | main.go:61-67 | DSN costruito con password in chiaro — se loggato, credential leak | Sanitizzare DSN prima di qualsiasi log |
| F16 | **WARNING** | writer.go:337 | `SpreadAvg: decimal.Zero` hardcoded — mai calcolato, dato sempre Zero nel DB | Calcolare media spread dai tick nel batch |
| F17 | **ALTO** | writer.go:305-314 | Sync flush fallback quando canale pieno blocca main loop — annulla design async sotto backpressure | Usare sliding window o drop old invece di block |
| F18 | **WARNING** | Dockerfile vs docker-compose | Health port EXPOSE 9091 nel Dockerfile ma docker-compose mappa 8081:8080 — cross-ref Report 01 F14 | Allineare porte |

---

## 7. Interconnessioni

### 7.1 Data Ingestion → Algo Engine

```
data-ingestion (Go)
    |
    | ZMQ PUB tcp://*:5555
    | Topic: "tick.polygon.XAU/USD" (tick data)
    | Topic: "bar.polygon.XAU/USD.M5" (aggregated bars)
    | Formato: JSON con decimal string
    v
algo-engine (Python)
    |
    | ZMQ SUB tcp://data-ingestion:5555
    | zmq_adapter.py: parsing JSON → OHLCVBar/Tick interno
    | Filtra per simboli e timeframe configurati
    v
FeaturePipeline (algo-engine)
```

### 7.2 Data Ingestion → Database

```
data-ingestion (Go)
    |
    | pgx COPY protocol (batch 1000 records)
    | Flush ogni 5 secondi O quando buffer pieno
    v
TimescaleDB
    |
    +→ market_ticks (hypertable, chunk 1h, compressione 1d)
    +→ ohlcv_bars (hypertable, chunk 1d, compressione 7d)
```

### 7.3 External Data → Database

```
external-data (Python)
    |
    | asyncpg INSERT statements
    | ON CONFLICT DO NOTHING per idempotenza
    v
TimescaleDB
    |
    +→ vix_data (regime classification automatica via trigger)
    +→ yield_curve_data (spread auto-calcolato via trigger)
    +→ real_rates_data
    +→ dxy_data
    +→ cot_reports
    +→ recession_probability
```

### 7.4 Economic Calendar → Trading Blackout

```
economic_events (INSERT)
    |
    | Trigger: auto_generate_blackouts
    v
generate_blackouts_for_event()
    |
    | Match event_impact_rules
    v
trading_blackouts (INSERT per ogni simbolo affetto)
    |
    | Query: is_trading_blacked_out(symbol, time)
    v
algo-engine → SignalValidator (controlla blackout prima di generare segnale)
```

---

## 8. Matrice Permessi RBAC

| Tabella | data_ingestion | algo_engine | mt5_bridge | admin |
|---------|:---:|:---:|:---:|:---:|
| ohlcv_bars | I,S | S | - | ALL |
| market_ticks | I,S | S | - | ALL |
| trading_signals | - | I,S | S,U | ALL |
| trade_executions | - | - | I,S | ALL |
| audit_log | I | I | I | ALL |
| model_registry | - | S | - | ALL |
| ml_predictions | - | I,S | - | ALL |
| strategy_performance | - | I,S,U | U | ALL |
| economic_events | I,S | S | - | ALL |
| trading_blackouts | I,S | S | - | ALL |
| vix_data | I,S | S | - | ALL |
| yield_curve_data | I,S | S | - | ALL |
| cot_reports | I,S | S | - | ALL |

*I=INSERT, S=SELECT, U=UPDATE, ALL=tutti i privilegi*

---

## 9. Istruzioni con Checkbox

### Segmento A: Fix Connettori (ALTO)
- [ ] **A1**: In `polygon.go`, convertire `reconnectAttempts` da `int` a `atomic.Int32`. Aggiornare tutti i punti di lettura/scrittura (linee 255, 280, 329)
- [ ] **A2**: In `polygon.go`, aggiungere contatore atomico `droppedMessages` incrementato quando il buffer di 256 messaggi e' pieno (linea 468)
- [ ] **A3**: In `polygon.go`, aggiungere log periodico (ogni 60s) del numero di messaggi droppati
- [ ] **A4**: In `binance.go`, implementare reconnection logic con exponential backoff. Copiare pattern da polygon.go: `state atomic.Int32`, `reconnect()`, `backoffDelay()`, max 50 tentativi
- [ ] **A5**: In `binance.go`, convertire `subscriptionID` a `atomic.Int32`
- [ ] **A6**: In `binance.go`, completare `parseStreamEnvelope()` per gestire tutti i formati Binance stream
- [ ] **A7**: Aggiungere test unitari per reconnection logic sia di Polygon che Binance

### Segmento B: Fix Aggregatore (WARNING)
- [ ] **B1**: In `aggregator.go`, spostare la callback `onComplete()` fuori dal mutex lock. Opzione raccomandata: raccogliere le bar completate in uno slice temporaneo, rilasciare il lock, poi chiamare le callback
- [ ] **B2**: Aggiungere test specifico: callback lenta (sleep 100ms) non deve bloccare AddTick() da goroutine diverse
- [ ] **B3**: Considerare aggiunta di max capacity per la mappa `bars` con warning se superata

### Segmento C: Osservabilita' (WARNING)
- [ ] **C1**: In `main.go`, esporre le metriche di dbwriter via HTTP endpoint Prometheus. Creare handler che esponga `dbwriter.Stats()` come metriche Prometheus
- [ ] **C2**: In `publisher.go`, impostare High Water Mark su ZMQ PUB socket (raccomandata: 10000 messaggi)
- [ ] **C3**: Verificare che i nomi metriche nelle alert rules (`moneymaker_kill_switch_active`) corrispondano a quelli emessi dal brain (`moneymaker_brain_kill_switch_active`). Se diversi, aggiornare alert_rules.yml
- [ ] **C4**: Aggiungere metrica Prometheus per messaggi ZMQ pubblicati al secondo
- [ ] **C5**: Aggiungere metrica per latenza tick-to-publish e tick-to-db

### Segmento D: Configurazione (WARNING)
- [ ] **D1**: Spostare la symbol map da `main.go` (linee 143-172) a `config.yaml` nella sezione `symbols.mapping` (gia' presente ma non usata dal codice)
- [ ] **D2**: Modificare `main.go` per leggere la symbol map da config.yaml invece che da codice hardcoded
- [ ] **D3**: Decidere se la sezione Redis in config.yaml deve essere implementata (caching tick per fast access) o rimossa
- [ ] **D4**: Rendere configurabili: WebSocket read deadline (attualmente 90s), auth timeout (10s), close flush delay (100ms)

### Segmento E: Database Schema (WARNING)
- [ ] **E1**: Aggiungere retention policy per `market_ticks`: `SELECT add_retention_policy('market_ticks', INTERVAL '90 days')` (90 giorni, i tick vecchi sono gia' aggregati in bar)
- [ ] **E2**: Aggiungere retention policy per `ohlcv_bars` M1: considerare `INTERVAL '1 year'` per barre M1 (le H1/D1 possono rimanere indefinitamente)
- [ ] **E3**: Aggiungere retention policy per `audit_log`: `INTERVAL '2 years'` o come richiesto da compliance
- [ ] **E4**: Verificare che le tabelle `trading_signals` e `trade_executions` non crescano illimitatamente - considerare conversione a hypertable o retention
- [ ] **E5**: Verificare che il trigger `prevent_audit_modification()` funziona correttamente tentando un UPDATE/DELETE su audit_log in ambiente di test
- [ ] **E6**: Testare l'idempotenza degli script init-db: eseguirli due volte e verificare che non producano errori (tutti i CREATE usano IF NOT EXISTS?)

### Segmento F: External Data Service (WARNING)
- [ ] **F1**: Creare `services/external-data/Dockerfile` seguendo il pattern degli altri servizi Python (base python:3.11-slim, COPY shared libs, pip install)
- [ ] **F2**: Aggiungere il servizio external-data al docker-compose.yml con le env vars necessarie (FRED_API_KEY, POLYGON_API_KEY)
- [ ] **F3**: Aggiungere external-data come target scrape in prometheus.yml (porta 9095)
- [ ] **F4**: Implementare il TODO in cboe.py: fetch VIX futures per calcolo term structure
- [ ] **F5**: Aggiungere test unitari per i provider (fred.py, cboe.py, cftc.py) con mock delle API esterne
- [ ] **F6**: Verificare che il CFTC parser gestisca cambiamenti nel formato del file tab-separated

### Segmento G: Sicurezza Database (BASSO)
- [ ] **G1**: In `007_rbac_passwords.sh`, valutare l'uso di SCRAM-SHA-256 per impostare password senza esposizione nei log
- [ ] **G2**: Verificare che `.gitignore` escluda qualsiasi file `.env` nella directory `infra/docker/`
- [ ] **G3**: Aggiungere commento nel script che avverte di non usare password di default in produzione
- [ ] **G4**: Verificare che il ruolo `data_ingestion_svc` NON abbia permessi UPDATE/DELETE su nessuna tabella (principio least privilege)

---

*Fine Report 06 - Prossimo: Report 02 (Algo Engine Core Pipeline)*
