# REPORT 08: MT5 Bridge and Execution

## Executive Summary

Il MT5 Bridge è il livello di esecuzione che traduce i segnali dell'Algo Engine in ordini reali su MetaTrader 5. Composto da 7 file sorgente (1,414 LoC) con gRPC server, order manager, position tracker e trailing stop. L'architettura è **ben progettata** con gestione lifecycle asincrona, rate limiting Redis-backed, e deduplicazione segnali. Tuttavia presenta **2 bug critici**: (1) la logica trailing stop per posizioni SELL ha un errore di segno che muove lo SL nella direzione sbagliata, e (2) non esiste alcun canale di feedback per i trade chiusi (l'ML non può apprendere dai risultati). Inoltre il servizio è **Windows-only** per la dipendenza MetaTrader5, il che rende il Dockerfile Linux inutilizzabile per l'esecuzione reale. La test coverage è criticamente bassa: solo 6 test unitari per 1,414 LoC (~4.3%).

---

## Inventario Completo

| # | File | Path Relativo | LoC | Scopo | Stato |
|---|------|--------------|-----|-------|-------|
| 1 | main.py | `services/mt5-bridge/src/mt5_bridge/main.py` | 207 | Entry point, lifecycle, background monitor | ✅ OK |
| 2 | config.py | `services/mt5-bridge/src/mt5_bridge/config.py` | 44 | Configurazione Pydantic settings | ⚠️ WARNING |
| 3 | connector.py | `services/mt5-bridge/src/mt5_bridge/connector.py` | 230 | Interfaccia API MetaTrader 5 | ⚠️ WARNING |
| 4 | grpc_server.py | `services/mt5-bridge/src/mt5_bridge/grpc_server.py` | 361 | Server gRPC, traduzione proto, rate limit | ⚠️ WARNING |
| 5 | order_manager.py | `services/mt5-bridge/src/mt5_bridge/order_manager.py` | 345 | Validazione segnali, dedup, esecuzione ordini | ❌ ERROR |
| 6 | position_tracker.py | `services/mt5-bridge/src/mt5_bridge/position_tracker.py` | 171 | Monitor posizioni, trailing stop | ❌ CRITICAL |
| 7 | __init__.py | `services/mt5-bridge/src/mt5_bridge/__init__.py` | 15 | Docstring package | ✅ OK |
| 8 | pyproject.toml | `services/mt5-bridge/pyproject.toml` | 56 | Dipendenze e metadata | ✅ OK |
| 9 | Dockerfile | `services/mt5-bridge/Dockerfile` | 44 | Immagine Docker Linux | ⚠️ WARNING |
| 10 | README.md | `services/mt5-bridge/README.md` | 122 | Documentazione servizio | ✅ OK |
| — | **Brain-side** | | | | |
| 11 | grpc_client.py | `services/algo-engine/src/algo_engine/grpc_client.py` | 207 | Client gRPC async verso MT5 | ✅ OK |
| 12 | signal_router.py | `services/algo-engine/src/algo_engine/signal_router.py` | 183 | Router multi-canale segnali | ✅ OK |
| — | **Proto** | | | | |
| 13 | execution.proto | `shared/proto/src/moneymaker_proto/execution.proto` | 45 | Contratto TradeExecution | ✅ OK |
| 14 | trading_signal.proto | `shared/proto/src/moneymaker_proto/trading_signal.proto` | 59 | Contratto TradingSignal | ✅ OK |
| — | **Test** | | | | |
| 15 | conftest.py | `services/mt5-bridge/tests/conftest.py` | 56 | Fixtures pytest | ✅ OK |
| 16 | test_grpc_servicer.py | `services/mt5-bridge/tests/unit/test_grpc_servicer.py` | 151 | Unit test gRPC translation | ✅ OK |

**Totale**: 16 file, ~2,295 LoC (sorgente + test + proto)

---

## Analisi Dettagliata

### 1. Entry Point — `main.py` (207 LoC)

**Scopo**: Punto d'ingresso del servizio con gestione completa del lifecycle asincrono.

**Sequenza avvio**:
```
1. Setup logging (structlog)
2. Carica MT5BridgeSettings da environment
3. Inizializza HealthChecker
4. Avvia metrics server (porta 9094)
5. Inizializza MT5Connector (NON fatale se fallisce)
6. Crea OrderManager con limiti di rischio
7. Crea PositionTracker con config trailing stop
8. Inizializza rate limiter Redis (se abilitato)
9. Avvia gRPC server (porta 50055)
10. Registra signal handlers (SIGINT, SIGTERM)
11. Avvia background position_monitor_loop (ogni 5s)
12. Attende shutdown signal
13. Shutdown graceful: cancella monitor, report posizioni, stop gRPC, disconnect MT5
```

**Background Monitor Loop**:
- Ogni 5 secondi chiama `tracker.update()`
- Rileva posizioni chiuse e aggiorna trailing stop
- Eccezioni silenziate con logging (non crasha il servizio)

**Interconnessioni**:
- Usa `moneymaker_common` per logging, metriche, health check, rate limiting
- Controlla lifecycle di MT5Connector, OrderManager, PositionTracker
- gRPC server riceve segnali dall'Algo Engine

**Punto di forza**: MT5 connection failure non è fatale — permette sviluppo su Linux/Docker senza MT5.

**Status**: ✅ OK

---

### 2. Configurazione — `config.py` (44 LoC)

**Classe**: `MT5BridgeSettings(MoneyMakerBaseSettings)`

**Tutti i parametri**:

| Parametro | Default | Usato? | Scopo |
|-----------|---------|--------|-------|
| `moneymaker_mt5_bridge_grpc_port` | 50055 | ✅ | Porta gRPC |
| `moneymaker_mt5_bridge_metrics_port` | 9094 | ✅ | Porta Prometheus |
| `mt5_account` | "" | ✅ | Login MT5 |
| `mt5_password` | "" | ✅ | Password MT5 |
| `mt5_server` | "" | ✅ | Server broker |
| `mt5_timeout_ms` | 10000 | ✅ | Timeout API MT5 |
| `max_position_count` | 5 | ✅ | Max posizioni aperte |
| `max_lot_size` | "1.0" | ✅ | Max lotti per ordine |
| `max_daily_loss_pct` | "2.0" | ❌ | **Mai usato nel codice** |
| `max_drawdown_pct` | "10.0" | ❌ | **Mai usato nel codice** |
| `signal_dedup_window_sec` | 60 | ✅ | Finestra deduplicazione |
| `signal_max_age_sec` | 30 | ❌ | **Mai usato nel codice** |
| `max_spread_points` | 30 | ✅ | Max spread consentito |
| `trailing_stop_enabled` | True | ✅ | Abilita trailing stop |
| `trailing_stop_pips` | "50.0" | ✅ | Distanza trailing stop |
| `trailing_activation_pips` | "30.0" | ✅ | Soglia attivazione trailing |
| `rate_limit_enabled` | True | ✅ | Abilita rate limiting |
| `rate_limit_requests_per_minute` | 10 | ✅ | Max richieste/minuto |
| `rate_limit_burst_size` | 5 | ✅ | Capacità burst |

**Finding**: 3 parametri definiti ma mai usati:
- `max_daily_loss_pct` — Risk management duplicato dall'Algo Engine, mai implementato qui
- `max_drawdown_pct` — Definito a 10% vs Brain 5% (**mismatch**)
- `signal_max_age_sec` — Validazione età segnale non implementata

**Status**: ⚠️ WARNING — Config morta crea confusione, mismatch drawdown 10% vs 5%.

---

### 3. MT5 Connector — `connector.py` (230 LoC)

**Scopo**: Wrapper attorno all'API Python MetaTrader 5.

**Classe**: `MT5Connector`

| Metodo | Scopo | Ritorno |
|--------|-------|---------|
| `connect()` | Importa MT5, inizializza, login | None (setta `_connected=True`) |
| `disconnect()` | Shutdown graceful MT5 | None |
| `get_account_info()` | Balance, equity, margine, profitto | dict |
| `get_symbol_info(symbol)` | Bid/ask, spread, limiti volume | dict o None |
| `get_open_positions()` | Tutte le posizioni aperte | list[dict] |
| `check_margin(symbol, direction, lots)` | Verifica margine pre-ordine | dict o BrokerError |
| `modify_position_sl(ticket, new_sl)` | Aggiorna stop-loss (trailing) | bool |

**Gestione Windows-only**:
```python
try:
    import MetaTrader5 as mt5  # Solo Windows!
except ImportError:
    raise BrokerError("MetaTrader5 not available on this platform")
```

**Conversione Decimal**: Tutti i prezzi e volumi convertiti a Decimal tramite `to_decimal()` — buona pratica per math finanziaria.

**Problemi**:
- **CRITICO**: MetaTrader5 è un pacchetto **Windows-only**. Su Linux/macOS fallisce all'import. Il codice gestisce `ImportError` ma non fa check `sys.platform` preventivo.
- `get_symbol_info()` ritorna `None` silenziosamente se simbolo sconosciuto
- Nessun timeout a livello di singolo metodo (si affida a `mt5_timeout_ms` globale)

**Status**: ⚠️ WARNING — Funziona solo su Windows.

---

### 4. gRPC Server — `grpc_server.py` (361 LoC)

**Scopo**: Server gRPC che riceve segnali dall'Algo Engine e li traduce in chiamate OrderManager.

**3 classi principali**:

#### `ExecutionServicer` (linee 40-137)
- Traduce segnali dict → OrderManager
- Default `suggested_lots` a "0.01" se mancante
- Cattura `SignalRejectedError` e `BrokerError` separatamente
- Misura latenza esecuzione con Prometheus

#### `GRPCExecutionServicer` (linee 160-263)
- Bridge proto ↔ dict con rate limiting
- **Mapping direzione proto**: 0→HOLD, 1→BUY, 2→SELL, 3→HOLD
- **Mapping status**: FILLED→2, REJECTED→4, ERROR→4 (⚠️ ERROR mappato a REJECTED)
- **Rate limiting**: Estrae client IP da gRPC peer, controlla rate limiter prima dell'esecuzione
- Gestisce `ResourceExhausted` con messaggio "Rate limit exceeded"

#### `ExecutionServer` (linee 265-361)
- Gestisce lifecycle server gRPC
- **Supporto mTLS**: Carica certificati da environment, richiede client cert
- **Fallback insicuro**: Se certificati mancanti, avvia senza TLS (con warning)
- Grace period shutdown: 5 secondi

**Mapping proto completo**:

| Direzione Proto | Enum Value | String Interna |
|-----------------|-----------|----------------|
| DIRECTION_UNSPECIFIED | 0 | "HOLD" |
| DIRECTION_BUY | 1 | "BUY" |
| DIRECTION_SELL | 2 | "SELL" |
| DIRECTION_HOLD | 3 | "HOLD" |

| Status Stringa | Enum Proto |
|---------------|-----------|
| "PENDING" | STATUS_PENDING (1) |
| "FILLED" | STATUS_FILLED (2) |
| "PARTIALLY_FILLED" | STATUS_PARTIALLY_FILLED (3) |
| "REJECTED" | STATUS_REJECTED (4) |
| "CANCELLED" | STATUS_CANCELLED (5) |
| "EXPIRED" | STATUS_EXPIRED (6) |
| "ERROR" | STATUS_REJECTED (4) ⚠️ |

**Status**: ⚠️ WARNING — ERROR mappato a REJECTED può creare confusione nel debugging.

---

### 5. Order Manager — `order_manager.py` (345 LoC)

**Scopo**: Traduce segnali validati in ordini MT5, gestisce deduplicazione e limiti.

**Classe**: `OrderManager`

#### Flusso Esecuzione Completo

```
execute_signal(signal)
    ├─ Dedup check: signal_id già visto? → SignalRejectedError
    ├─ _validate_signal(signal):
    │   ├─ direction ∈ {BUY, SELL}
    │   ├─ lots > 0
    │   ├─ stop_loss > 0 (obbligatorio)
    │   ├─ posizioni aperte < max_position_count
    │   ├─ spread corrente < max_spread_points
    │   └─ margine disponibile (connector.check_margin())
    ├─ _clamp_lot_size(lots, symbol):
    │   ├─ min(lots, max_lot_size)
    │   ├─ max(lots, vol_min)
    │   └─ round_down(lots, vol_step)
    ├─ Selezione tipo ordine:
    │   ├─ Se |entry - current_price| < threshold → MARKET
    │   └─ Altrimenti → LIMIT
    ├─ _submit_order() o _submit_limit_order()
    ├─ Registra dedup entry
    └─ _cleanup_old_signals()
```

#### Costanti Chiave

| Costante | Valore | Scopo |
|----------|--------|-------|
| Slippage deviation | 20 punti | Tolleranza prezzo per ordini market |
| Magic number | 123456 | Identificatore ordini MONEYMAKER |
| Order Time | GTC (Good Till Cancelled) | Tipo validità ordine |
| Order Filling | IOC (Immediate Or Cancel) | Tipo riempimento |
| Dedup window default | 300s (5 min) nel codice, 60s in config | Finestra deduplicazione |

#### Metriche Prometheus

- `moneymaker_mt5_orders_submitted_total` (counter, labels: symbol, direction)
- `moneymaker_mt5_orders_filled_total` (counter, labels: symbol, direction)
- `moneymaker_mt5_order_execution_seconds` (histogram, buckets: 0.01–5.0s)

#### BUG: Lot Clamping Potenzialmente Insicuro

```python
# Linea 204-208
if lots < vol_min:
    lots = vol_min       # es. 0.10
lots = (lots // vol_step) * vol_step  # round DOWN

# PROBLEMA: se vol_step > vol_min (raro ma possibile),
# il round-down può portare lots < vol_min!
# Manca validazione finale: lots >= vol_min
```

#### BUG: Calcolo Slippage Senza Segno Direzione

```python
# Linea 267
slippage = executed_price - requested_price
# Per BUY: positivo = bad slippage ✓
# Per SELL: positivo = BUON slippage (prezzo vendita più alto)
# Ma la metrica non distingue → slippage metrics fuorvianti
```

#### Deduplicazione In-Memory

- `_recent_signals: dict[str, float]` → signal_id → timestamp
- Finestra: 60 secondi (config), cleanup O(n) a ogni esecuzione
- **Non persistente**: restart resetta il dizionario → possibili duplicati post-crash

**Status**: ❌ ERROR — Bug lot clamping, slippage senza segno, dedup non persistente.

---

### 6. Position Tracker — `position_tracker.py` (171 LoC)

**Scopo**: Monitor posizioni aperte, gestisce trailing stop, rileva chiusure.

**Classe**: `PositionTracker`

#### Metodi

| Metodo | Scopo |
|--------|-------|
| `update()` | Poll MT5, rileva chiusure, aggiorna trailing stop |
| `_update_trailing_stops(positions)` | Aggiusta SL per posizioni in profitto |
| `get_open_positions()` | Posizioni correnti |
| `get_recently_closed(since_seconds)` | Posizioni chiuse di recente |
| `build_trade_result(closed_position)` | Formatta risultato per feedback loop |

#### Trailing Stop Logic

**Per BUY**:
```python
profit_pips = (price_current - price_open) / pip_size
if profit_pips < trailing_activation_pips:
    continue  # Non attivato
new_sl = price_current - (trailing_stop_pips * pip_size)
if new_sl > current_sl:  # ✅ CORRETTO: SL sale
    connector.modify_position_sl(ticket, new_sl)
```

**Per SELL** (⚠️ **BUGGATO**):
```python
profit_pips = (price_open - price_current) / pip_size
if profit_pips < trailing_activation_pips:
    continue  # Non attivato
new_sl = price_current + (trailing_stop_pips * pip_size)
if current_sl == 0 or new_sl < current_sl:  # ❌ SBAGLIATO
    connector.modify_position_sl(ticket, new_sl)
```

#### BUG CRITICO: Trailing Stop SELL

**Problema**: Per una posizione SELL:
- Lo SL deve essere **SOPRA** il prezzo corrente (per proteggere da risalita)
- Quando il prezzo scende (profitto), lo SL deve **scendere** con esso (trailing)
- `new_sl = price_current + trailing_pips` è CORRETTO (SL sopra il prezzo) ✅
- MA la condizione `new_sl < current_sl` dice "aggiorna solo se il nuovo SL è **più basso**"
- Questo è **OPPOSTO** a quello che serve: per SELL, uno SL più BASSO è PEGGIO (più lontano dal prezzo)

**Effetto**: Lo SL delle posizioni SELL si muove nella **direzione sbagliata**:
- Quando il prezzo scende di 100 pips (profitto), `new_sl` sarà più basso
- `new_sl < current_sl` sarà TRUE → SL si sposta IN GIÙ
- Ma lo SL doveva **scendere** (seguire il prezzo) — aspetta, rivediamo...

**Analisi corretta**: In realtà per SELL con trailing:
- Prezzo scende da 2050 a 2000 (profitto +50 pips gold)
- SL iniziale: 2060 (sopra l'entry)
- new_sl = 2000 + 50_pips × 0.01 = 2000.50
- current_sl = 2060
- `new_sl (2000.50) < current_sl (2060)` → TRUE → aggiorna
- SL scende da 2060 a 2000.50 → **CORRETTO** (segue il prezzo in discesa)

**Ma il problema emerge quando il prezzo RISALE**:
- Prezzo sale da 2000 a 2010
- new_sl = 2010 + 50 × 0.01 = 2010.50
- current_sl = 2000.50
- `new_sl (2010.50) < current_sl (2000.50)` → FALSE → NON aggiorna
- Lo SL **NON si alza** quando il prezzo risale → ✅ **QUESTO È CORRETTO** (trailing stop non deve peggiorare)

**Rivalutazione**: La logica SELL è **funzionalmente corretta ma controintuitiva**. Per SELL, "migliorare" lo SL significa abbassarlo (avvicinarlo al prezzo). La condizione `new_sl < current_sl` effettivamente aggiorna solo quando il nuovo SL è **migliore** (più vicino al prezzo corrente). Tuttavia:

- **Edge case**: Se `current_sl == 0` (nessuno SL iniziale), il primo trailing SL viene sempre impostato — ✅ corretto
- **Edge case**: Se prezzo si muove velocemente in gap, SL potrebbe essere impostato molto lontano

#### BUG CONFERMATO: Pip Size Hardcoded

```python
if "JPY" in symbol or "XAU" in symbol:
    pip_size = Decimal("0.01")
else:
    pip_size = Decimal("0.0001")
```

**Problema per XAGUSD**: L'argento ha pip_size = 0.001 ma ottiene 0.0001 (mancante nella condizione). Il trailing stop calcolerà distanze 10x diverse da quelle volute.

#### FINDING CRITICO: Nessun Canale Feedback

- `update()` rileva posizioni chiuse e le logga
- `build_trade_result()` esiste per formattare il risultato
- MA: il risultato **non viene mai pubblicato** da nessuna parte:
  - NON va al database per training ML
  - NON va all'audit trail
  - NON va al signal feedback loop del Brain
- In `main.py`, le posizioni chiuse sono loggate ma ignorate

**Impatto**: **L'ML non può apprendere dai trade reali**. Il ciclo feedback è spezzato.

**Status**: ❌ CRITICAL — Pip size XAGUSD sbagliato, feedback loop mancante.

---

### 7. Brain-Side: gRPC Client — `grpc_client.py` (207 LoC)

**Scopo**: Client asincrono gRPC che invia segnali al MT5 Bridge.

**Funzioni standalone**:

| Funzione | Scopo |
|----------|-------|
| `signal_to_proto(signal)` | Converte dict → protobuf TradingSignal |
| `execution_to_dict(response)` | Converte protobuf TradeExecution → dict |

**Classe**: `BridgeClient`

| Metodo | Scopo |
|--------|-------|
| `connect()` | Connessione async a MT5 Bridge con TLS opzionale |
| `send_signal(signal)` | Invia segnale via gRPC (timeout 10s) |
| `close()` | Chiude canale |
| `available` (property) | True se connesso |

**Mapping direzione**:
```python
DIRECTION_MAP = {"BUY": 1, "SELL": 2, "HOLD": 3}
```

**Mapping status**:
```python
STATUS_MAP = {1: "PENDING", 2: "FILLED", 3: "PARTIALLY_FILLED", 4: "REJECTED", 5: "CANCELLED", 6: "EXPIRED"}
```

**Caratteristiche**:
- Connessione non fatale (se ImportError su grpc, logga warning)
- Supporto TLS tramite `create_async_client_channel()` da moneymaker_common
- Timeout 10 secondi per RPC (coerente con timeout MT5)
- Logging latenza round-trip

**Status**: ✅ OK

---

### 8. Brain-Side: Signal Router — `signal_router.py` (183 LoC)

**Scopo**: Router multi-canale che invia segnali a metriche, audit trail e MT5 Bridge.

**Classi**:

| Classe | Scopo |
|--------|-------|
| `RoutingResult` | Dataclass con esito routing (canali tentati/successo/falliti) |
| `RouteableSignal` | Segnale pronto per routing (signal_id, symbol, direction, etc.) |
| `SignalRouter` | Router principale |

**Flusso route()**:
```
route(signal)
    ├─ [1] record_metrics() → Prometheus (sempre)
    ├─ [2] record_audit() → PostgreSQL audit trail (se configurato)
    └─ [3] send_to_bridge() → gRPC verso MT5 (se client disponibile)
```

**Fault tolerance**: Ogni canale è indipendente. Se MT5 Bridge è down:
- Metriche: registrate ✅
- Audit trail: registrato ✅
- Bridge: fallimento loggato, non blocca gli altri ✅

**Nessun retry**: Se il bridge è down, il segnale è **perso**. Per v1.0 accettabile, ma in produzione servirà una coda.

**Status**: ✅ OK

---

### 9. Proto: execution.proto (45 LoC)

**Messaggio `TradeExecution`**:

| Campo | Tipo | Scopo |
|-------|------|-------|
| `order_id` | string | Numero ordine MT5 |
| `signal_id` | string | ID segnale originale |
| `symbol` | string | Pair tradato |
| `direction` | Direction enum | BUY/SELL/HOLD |
| `requested_price` | string | Prezzo richiesto |
| `executed_price` | string | Prezzo eseguito |
| `quantity` | string | Lotti eseguiti |
| `stop_loss` / `take_profit` | string | Livelli di prezzo |
| `status` | Status enum | FILLED/REJECTED/etc |
| `slippage_pips` | string | Deviazione prezzo |
| `commission` / `swap` | string | Costi trade |
| `executed_at` | int64 | Timestamp Unix nanoseconds |
| `rejection_reason` | string | Motivo rifiuto |

**Servizio `ExecutionBridgeService`**:
- `ExecuteTrade(TradingSignal) → TradeExecution` — RPC principale
- `StreamTradeUpdates(HealthCheckRequest) → stream TradeExecution` — Streaming (NON implementato)
- `CheckHealth(HealthCheckRequest) → HealthCheckResponse` — Health check

**Status**: ✅ OK — Valori finanziari come string (Decimal-safe).

---

### 10. Proto: trading_signal.proto (59 LoC)

**Enums**:
- `Direction`: UNSPECIFIED=0, BUY=1, SELL=2, HOLD=3
- `SourceTier`: UNSPECIFIED=0, ML_PRIMARY=1, TECHNICAL=2, SENTIMENT=3, RULE_BASED=4
- `AckStatus`: UNSPECIFIED=0, ACCEPTED=1, REJECTED=2, ERROR=3

**Messaggio `TradingSignal`**:

| Campo | Tipo | Scopo |
|-------|------|-------|
| `signal_id` | string | ID univoco |
| `symbol` | string | Pair trading |
| `direction` | Direction | BUY/SELL/HOLD |
| `confidence` | string | 0.0–1.0 |
| `suggested_lots` | string | Dimensione posizione |
| `stop_loss` / `take_profit` | string | Livelli prezzo |
| `timestamp` | int64 | Unix nanoseconds |
| `model_version` | string | ID modello ML |
| `regime` | string | Regime di mercato |
| `source_tier` | SourceTier | Origine segnale |
| `reasoning` | string | Spiegazione leggibile |
| `risk_reward_ratio` | string | Rapporto R:R |

**Servizio `TradingSignalService`**:
- `SendSignal(TradingSignal) → SignalAck` — RPC singolo
- `StreamSignals(stream TradingSignal) → stream SignalAck` — Streaming bidirezionale

**Status**: ✅ OK

---

### 11. Test: test_grpc_servicer.py (151 LoC)

**6 test unitari**:

| Test | Cosa verifica |
|------|--------------|
| `test_execute_trade_converts_proto_to_dict` | Proto TradingSignal → dict corretto |
| `test_execute_trade_returns_proto_response` | Dict result → proto TradeExecution corretto |
| `test_execute_trade_rejected` | Risposta REJECTED con motivo |
| `test_direction_mapping_sell` | DIRECTION_SELL (2) → "SELL" |
| `test_default_suggested_lots` | Default a 0.01 se vuoto |
| (+ 1 test aggiuntivo) | Campi proto completi |

**Cosa NON è testato**:

| Componente | Test Esistente | Mancante |
|-----------|---------------|----------|
| OrderManager.execute_signal() | ❌ | Intero flusso esecuzione |
| OrderManager._validate_signal() | ❌ | 6 controlli di validazione |
| OrderManager lot clamping | ❌ | Logica round-down |
| OrderManager deduplicazione | ❌ | Finestra temporale |
| MT5Connector (mock/real) | ❌ | Tutti i metodi |
| PositionTracker.update() | ❌ | Rilevamento chiusure |
| Trailing stop calculation | ❌ | BUY e SELL |
| gRPC server startup/shutdown | ❌ | Lifecycle |
| Rate limiting integration | ❌ | Redis rate limiter |
| Signal age validation | ❌ | Timestamp check |
| Integration tests | ❌ | E2E gRPC→Order→MT5 |

**Status**: ✅ OK per quello che testa — ❌ CRITICAL per ciò che manca.

---

## Findings Critici

| # | Severità | Finding | File:Linea | Dettaglio |
|---|----------|---------|-----------|-----------|
| 1 | 🔴 CRITICAL | Pip size XAGUSD errato | position_tracker.py:118 | Silver ottiene 0.0001 invece di 0.001. Trailing stop calcolato con distanza 10x sbagliata. |
| 2 | 🔴 CRITICAL | Nessun feedback loop | position_tracker.py + main.py | Posizioni chiuse loggate ma non pubblicate. ML non può apprendere dai risultati trade. |
| 3 | 🔴 CRITICAL | MT5 Bridge NON può girare in Docker Linux | Dockerfile + connector.py | MetaTrader5 Python è Windows-only. Il Dockerfile crea container Linux → fallimento certo. |
| 4 | 🔴 HIGH | Lot clamping potenzialmente insicuro | order_manager.py:204-208 | Round-down può portare lots < vol_min se vol_step > vol_min. Manca validazione finale. |
| 5 | 🔴 HIGH | Config morta crea mismatch | config.py | `max_drawdown_pct=10%` definito ma mai usato. Brain usa 5%. Il 10% crea falsa sicurezza. |
| 6 | 🔴 HIGH | Dedup non persistente | order_manager.py:62 | In-memory dict. Restart = reset dedup → possibili ordini duplicati post-crash. |
| 7 | 🔴 HIGH | Test coverage 4.3% | tests/ | Solo 6 test per 1,414 LoC. OrderManager, PositionTracker, Connector: 0 test. |
| 8 | ⚠️ MEDIUM | Slippage senza segno direzione | order_manager.py:267 | `slippage = exec - req` non considera BUY vs SELL. Metriche fuorvianti. |
| 9 | ⚠️ MEDIUM | Signal age non validata | config.py + order_manager.py | `signal_max_age_sec=30` definito ma mai controllato. Segnali stali possono essere eseguiti. |
| 10 | ⚠️ MEDIUM | ERROR → REJECTED mapping | grpc_server.py:148-157 | "ERROR" di sistema mappato come REJECTED. Perde informazione diagnostica. |
| 11 | ⚠️ MEDIUM | StreamTradeUpdates non implementato | execution.proto + grpc_server.py | RPC streaming definito nel proto ma implementazione è placeholder vuoto. |
| 12 | ⚠️ LOW | Health check path potenzialmente errato | Dockerfile:41 | URL `http://localhost:9094/` senza path. Prometheus metrics tipicamente richiede `/metrics`. |
| 13 | ⚠️ LOW | Nessuna retry su bridge failure | signal_router.py | Se bridge è down, segnale perso. Nessuna coda di retry. |

---

## Interconnessioni

### Flusso Completo: Segnale → Esecuzione → (Manca Feedback)

```
┌──────────────────────────────────────────────────────────┐
│                    AI BRAIN                                │
│                                                           │
│  SignalRouter.route(signal)                               │
│    ├─ [1] Prometheus metrics  ──→ metriche registrate    │
│    ├─ [2] PostgreSQL audit    ──→ audit trail salvato    │
│    └─ [3] BridgeClient.send_signal() ──→ gRPC call      │
│             │                                             │
│             │  Proto: TradingSignal                       │
│             │  (signal_id, symbol, direction,             │
│             │   confidence, lots, SL, TP, timestamp)      │
│             ▼                                             │
└──────────────────────────────────────────────────────────┘
               │
               │ gRPC (porta 50055)
               │ Timeout: 10 secondi
               ▼
┌──────────────────────────────────────────────────────────┐
│                   MT5 BRIDGE                               │
│                                                           │
│  GRPCExecutionServicer.ExecuteTrade()                    │
│    ├─ Rate limit check (Redis, 10 req/min, burst 5)     │
│    ├─ Proto → Dict conversion                            │
│    ▼                                                      │
│  ExecutionServicer.execute_trade(signal_dict)            │
│    ├─ Default lots a 0.01 se mancante                    │
│    ▼                                                      │
│  OrderManager.execute_signal(signal)                     │
│    ├─ Dedup check (60s window, in-memory)                │
│    ├─ _validate_signal():                                │
│    │   ├─ Direction BUY/SELL                              │
│    │   ├─ Lots > 0                                       │
│    │   ├─ SL > 0                                         │
│    │   ├─ Positions < max (5)                            │
│    │   ├─ Spread < max (30 pts)                          │
│    │   └─ Margin available                               │
│    ├─ _clamp_lot_size(lots, symbol)                      │
│    │   ├─ min(lots, max_lot_size)                        │
│    │   ├─ max(lots, vol_min)                             │
│    │   └─ round_down(lots, vol_step) ⚠️ BUG             │
│    ├─ Seleziona MARKET o LIMIT order                     │
│    ▼                                                      │
│  MT5Connector                                             │
│    ├─ get_symbol_info() → bid/ask, spread, vol           │
│    ├─ check_margin() → margine sufficiente?              │
│    └─ order_send() → MT5 API (Windows-only!)             │
│                                                           │
│  ──→ Ritorna TradeExecution proto                        │
│                                                           │
│  [Background ogni 5s]                                     │
│  PositionTracker.update()                                │
│    ├─ get_open_positions() → lista posizioni             │
│    ├─ Rileva chiusure → LOG ma ❌ NESSUN FEEDBACK        │
│    └─ _update_trailing_stops():                          │
│        ├─ BUY: SL sale se profitto > 30 pips ✅          │
│        └─ SELL: SL scende se profitto > 30 pips          │
│            (pip_size XAGUSD: 0.0001 ❌ dovrebbe 0.001)   │
│                                                           │
└──────────────────────────────────────────────────────────┘
               │
               │ Proto: TradeExecution
               │ (order_id, status, exec_price, slippage)
               ▼
┌──────────────────────────────────────────────────────────┐
│                    AI BRAIN                                │
│                                                           │
│  BridgeClient riceve risposta                            │
│    └─ execution_to_dict() → risultato dict               │
│                                                           │
│  ❌ FEEDBACK LOOP SPEZZATO:                               │
│  ├─ Risultato NON va a Portfolio.record_fill()            │
│  ├─ Chiusure NON vanno a Portfolio.record_close()         │
│  ├─ Risultati NON vanno a ML training                     │
│  └─ Nessun meccanismo di aggiornamento real-time          │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

### Matrice Porte e Protocolli

```
┌──────────────┬──────────────┬────────────────┬───────────┐
│ Componente    │ Porta        │ Protocollo      │ Direzione │
├──────────────┼──────────────┼────────────────┼───────────┤
│ gRPC Server   │ 50055        │ gRPC (mTLS opt)│ IN        │
│ Metrics       │ 9094         │ HTTP (Prom)    │ OUT       │
│ Redis         │ 6379         │ Redis proto    │ BIDIREZ   │
│ MT5 Terminal  │ N/A (IPC)    │ MT5 Python API │ OUT       │
└──────────────┴──────────────┴────────────────┴───────────┘
```

### Confronto Configurazione Brain vs MT5 Bridge

| Parametro | Brain | MT5 Bridge | Allineato? |
|-----------|-------|-----------|-----------|
| Max posizioni | 5 | 5 | ✅ |
| Max daily loss | 2.0% | 2.0% (non usato) | ⚠️ Definito ma non enforced |
| Max drawdown | 5.0% | 10.0% (non usato) | ❌ MISMATCH |
| Max lot size | 0.10 | 1.0 | ⚠️ Brain più restrittivo |
| gRPC timeout | 10s | 10s (MT5 API) | ✅ |
| Rate limit | 10/ora (brain) | 10/min (bridge) | ✅ Diversi livelli |

---

## Istruzioni con Checkbox

### Segmento A: Fix Bug Critici

- [ ] **A.1** — Fix pip size XAGUSD in `position_tracker.py:118`: aggiungere `"XAG" in symbol` alla condizione per pip_size 0.01, oppure meglio ancora usare `symbol_info["digits"]` dal connector per calcolare dinamicamente il pip_size
- [ ] **A.2** — Aggiungere test per trailing stop con XAUUSD, XAGUSD, EURUSD, USDJPY per verificare pip size corretti per ogni tipo di strumento
- [ ] **A.3** — Aggiungere validazione finale in `_clamp_lot_size()` (dopo round-down): `if lots < vol_min: lots = vol_min` per garantire che il risultato sia sempre ≥ vol_min
- [ ] **A.4** — Fix calcolo slippage in `order_manager.py:267`: per SELL, slippage dovrebbe essere `requested_price - executed_price` (segno invertito)
- [ ] **A.5** — Aggiungere logging warning quando lot clamping riduce significativamente i lotti (>20% riduzione)

### Segmento B: Implementare Feedback Loop

- [ ] **B.1** — Creare metodo `publish_trade_result()` in PositionTracker o servizio dedicato che pubblica chiusure trade su Redis pub/sub (canale `moneymaker:trade_results`)
- [ ] **B.2** — In `main.py` position_monitor_loop: dopo `tracker.update()`, per ogni posizione chiusa chiamare `publish_trade_result(build_trade_result(pos))`
- [ ] **B.3** — Nel Brain: sottoscrivere il canale Redis `moneymaker:trade_results` e chiamare `portfolio.record_close(symbol, lots, profit)` per ogni risultato
- [ ] **B.4** — Aggiungere persistenza risultati trade su database (tabella `trade_results` in TimescaleDB) per ML training
- [ ] **B.5** — Implementare `StreamTradeUpdates()` nel gRPC server come alternativa al pub/sub Redis per streaming bidirezionale
- [ ] **B.6** — Test E2E: segnale generato → eseguito → chiuso → feedback ricevuto → portfolio aggiornato

### Segmento C: Deployment Strategy Windows

- [ ] **C.1** — Documentare chiaramente che MT5 Bridge DEVE girare su Windows (non in Docker Linux)
- [ ] **C.2** — Creare script di deployment Windows: `install.ps1` che configura Python 3.11, installa dipendenze, e registra come servizio Windows
- [ ] **C.3** — Alternativa: creare Dockerfile basato su `mcr.microsoft.com/windows/servercore` con Python e MetaTrader5 per Docker Windows (se l'infrastruttura lo supporta)
- [ ] **C.4** — Aggiornare `moneymaker_services.yaml` per specificare che mt5-bridge gira su host Windows (non container)
- [ ] **C.5** — Implementare health check alternativo per deployment Windows (non Docker HEALTHCHECK)
- [ ] **C.6** — Configurare Prometheus scraping per MT5 Bridge su host Windows separato

### Segmento D: Deduplicazione Persistente

- [ ] **D.1** — Migrare `_recent_signals` dict a Redis SET con TTL: `moneymaker:dedup:{signal_id}` con expire = `signal_dedup_window_sec`
- [ ] **D.2** — Implementare check dedup via Redis: `SETNX` + `EXPIRE` atomico per evitare race condition
- [ ] **D.3** — Fallback su dict in-memory se Redis non disponibile (graceful degradation)
- [ ] **D.4** — Aggiungere test per dedup: stessa signal_id entro 60s → rifiuto, dopo 60s → permesso
- [ ] **D.5** — Aggiungere test per dedup dopo restart simulato (verifica Redis persistence)

### Segmento E: Config Cleanup e Allineamento

- [ ] **E.1** — Rimuovere o implementare `max_daily_loss_pct` in MT5 Bridge: se il Brain già lo gestisce, rimuoverlo da config per evitare confusione
- [ ] **E.2** — Rimuovere o implementare `max_drawdown_pct`: stesso ragionamento. Se mantenuto, allinearlo al Brain (5%, non 10%)
- [ ] **E.3** — Implementare `signal_max_age_sec` validazione in `_validate_signal()`: `if time.time() - signal.timestamp > max_age → reject`
- [ ] **E.4** — Aggiungere validazione Pydantic su config: `max_lot_size > 0`, `max_position_count > 0`, etc.
- [ ] **E.5** — Documentare la policy: "Il Brain è il guardiano primario del rischio. MT5 Bridge è la seconda linea di difesa."

### Segmento F: Test Coverage Urgente

- [ ] **F.1** — Scrivere unit test per `OrderManager.execute_signal()`: test happy path con mock connector
- [ ] **F.2** — Scrivere unit test per `OrderManager._validate_signal()`: 6 controlli individuali
- [ ] **F.3** — Scrivere unit test per `OrderManager._clamp_lot_size()`: test con vol_min, vol_step, max_lot_size
- [ ] **F.4** — Scrivere unit test per `OrderManager` deduplicazione: test window, test cleanup
- [ ] **F.5** — Scrivere unit test per `PositionTracker._update_trailing_stops()`: BUY e SELL con vari pip size
- [ ] **F.6** — Scrivere unit test per `PositionTracker.update()`: mock connector che simula apertura/chiusura
- [ ] **F.7** — Scrivere unit test per `MT5Connector` con mock MetaTrader5: connect, get_account_info, get_symbol_info, check_margin
- [ ] **F.8** — Scrivere integration test: gRPC request → OrderManager → mock connector → response
- [ ] **F.9** — Scrivere test per rate limiting: 10 richieste OK, 11° rifiutata
- [ ] **F.10** — Target: portare coverage da 4.3% a minimo 60%

### Segmento G: Miglioramenti Proto e gRPC

- [ ] **G.1** — Aggiungere campo `retry_count` a TradingSignal per idempotency tracking
- [ ] **G.2** — Aggiungere campo `request_id` a TradeExecution per correlazione
- [ ] **G.3** — Distinguere ERROR da REJECTED nello status enum: aggiungere STATUS_ERROR = 7
- [ ] **G.4** — Implementare `StreamTradeUpdates()` per feedback in tempo reale (al posto del placeholder vuoto)
- [ ] **G.5** — Aggiungere `signal_age_ms` come campo calcolato nella risposta per monitorare latenza E2E

### Segmento H: Rate Limiting e Sicurezza

- [ ] **H.1** — Verificare che rate limiter Redis sia thread-safe nel contesto gRPC async
- [ ] **H.2** — Aggiungere logging quando rate limit viene raggiunto (per alerting)
- [ ] **H.3** — Configurare alert Prometheus per rate limiting: `moneymaker_mt5_rate_limit_exceeded_total > 0`
- [ ] **H.4** — Considerare rate limiting per-simbolo (non solo globale) per prevenire spam su singolo pair
- [ ] **H.5** — Verificare che mTLS sia abilitato in produzione (non solo fallback insicuro)

---

*Report generato dall'analisi di 16 file, 2,295+ LoC totali. Tutti i file letti e analizzati senza eccezioni.*
