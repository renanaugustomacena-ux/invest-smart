# REPORT 02: Algo Engine — Core Pipeline e Decision Engine

**Data Audit Originale**: 2026-03-02
**Data Revisione**: 2026-03-05
**Auditor**: Claude Opus 4.6
**Scope**: Pipeline decisionale completa: main.py, orchestrator, strategie, generazione segnali, routing, adapter ZMQ, maturity gate, trading advisor, kill switch, portfolio, grpc_client, ml_feedback
**Severita Massima Trovata**: CRITICA
**Stato**: REVISIONATO — Tutti i finding verificati riga-per-riga contro il codice sorgente

---

## Executive Summary

L'Algo Engine e' il cuore del sistema MONEYMAKER con ~2,800+ LoC nei file core pipeline e 20+ moduli di intelligenza importati opzionalmente. L'architettura segue un pattern di **cascata con degradazione graziosa**: dati → features → regime → advisor (4 modi) → validazione → dispatch gRPC. Il sistema e' robusto con tutti i moduli opzionali (try/except), ma attualmente **solo il Mode 4 (Conservative/rule-based) e' operativo**.

**Cambiamenti dalla revisione originale**:
- Severita massima promossa a **CRITICA** (era ALTA)
- Aggiunti 4 bug CRITICI scoperti nella verifica riga-per-riga:
  - F01: Kill switch `is_active()` ritorna tuple, ma main.py lo usa come bool → trading SEMPRE bloccato
  - F02: gRPC direction enum `str(Direction.BUY)` = `"Direction.BUY"` → tutte le direzioni UNSPECIFIED
  - F03: ML feedback pool mai inizializzato → feedback loop completamente rotto
  - F04: PnL tracker registra dati fittizi (pnl=0, is_win=True) al fill
- Aggiunto finding: orchestrator.py e' codice morto (MAI importato da main.py)
- Aggiunto finding: BridgeClient channel mai chiuso (resource leak)
- Aggiunto finding: Portfolio state parzialmente persistito su Redis
- Totale: 4 CRITICI, 4 ALTI, 4 WARNING (era 0/2/4)

---

## 1. Inventario Completo dei File

### 1.1 Core Pipeline
| File | Path | LoC | Qualita | Stato |
|------|------|-----|---------|-------|
| main.py | `services/algo-engine/src/algo_engine/main.py` | 1,609 | 6.5/10 | **CRITICO** |
| orchestrator.py | `services/algo-engine/src/algo_engine/orchestrator.py` | 205 | 7/10 | MORTO (non usato) |
| portfolio.py | `services/algo-engine/src/algo_engine/portfolio.py` | 174 | 7.5/10 | ALTO |
| grpc_client.py | `services/algo-engine/src/algo_engine/grpc_client.py` | 206 | 6/10 | **CRITICO** |
| ml_feedback.py | `services/algo-engine/src/algo_engine/ml_feedback.py` | 98 | 5/10 | **CRITICO** |
| kill_switch.py | `services/algo-engine/src/algo_engine/kill_switch.py` | 145 | 7.5/10 | **CRITICO** |
| trading_types.py | `services/algo-engine/src/algo_engine/trading_types.py` | ~80 | OK | OK |
| zmq_adapter.py | `services/algo-engine/src/algo_engine/zmq_adapter.py` | ~150 | OK | OK |
| maturity_gate.py | `services/algo-engine/src/algo_engine/maturity_gate.py` | ~250 | OK | OK |
| signal_router.py | `services/algo-engine/src/algo_engine/signal_router.py` | ~120 | OK | OK |
| config.py | `services/algo-engine/src/algo_engine/config.py` | 103 | 7/10 | WARNING (vedi Report 01) |

### 1.2 Strategie
| File | Path | LoC | Stato |
|------|------|-----|-------|
| base.py | `strategies/base.py` | ~95 | OK |
| trend_following.py | `strategies/trend_following.py` | ~110 | WARNING |
| mean_reversion.py | `strategies/mean_reversion.py` | ~90 | OK |
| defensive.py | `strategies/defensive.py` | ~50 | OK |
| ml_proxy.py | `strategies/ml_proxy.py` | ~240 | WARNING |
| regime_router.py | `strategies/regime_router.py` | ~125 | OK |

### 1.3 Segnali
| File | Path | LoC | Stato |
|------|------|-----|-------|
| generator.py | `signals/generator.py` | ~120 | OK |
| correlation.py | `signals/correlation.py` | ~100 | WARNING |
| rate_limiter.py | `signals/rate_limiter.py` | ~60 | OK |

### 1.4 Servizi
| File | Path | LoC | Stato |
|------|------|-----|-------|
| trading_advisor.py | `services/trading_advisor.py` | ~506 | WARNING |

---

## 2. Analisi Dettagliata

### 2.1 main.py — Entry Point (1,609 LoC, Qualita 6.5/10)

**Cosa fa**: Punto di ingresso del servizio. Inizializza 20+ moduli, avvia loop ZMQ, processa barre OHLCV, genera e invia segnali.

**Architettura degli import (60+ moduli)**:

```python
# CORE (obbligatori — il servizio non parte senza)
from algo_engine.features.pipeline import FeaturePipeline, OHLCVBar
from algo_engine.features.regime import RegimeClassifier
from algo_engine.signals.generator import SignalGenerator
from algo_engine.signals.validator import SignalValidator
from algo_engine.kill_switch import KillSwitch
from algo_engine.portfolio import PortfolioStateManager

# INTELLIGENCE (opzionali — try/except con fallback None)
try:
    from algo_engine.services.trading_advisor import TradingAdvisor
except ImportError:
    TradingAdvisor = None  # Mode 4 Conservative usato come fallback
# ... 18+ altri moduli con lo stesso pattern
```

**Pattern di resilienza**: Ogni modulo opzionale e' importato in un blocco try/except. Se un modulo non e' disponibile, la variabile e' impostata a `None` e il sistema degrada graziosamente.

**Loop principale** (`run_brain()`, righe 600-1544 — **944 righe**):

```
1. Connetti ZMQ SUB a data-ingestion (tcp://data-ingestion:5555)
2. Sottoscrivi a topic "bar.*" per barre OHLCV
3. Per ogni messaggio ricevuto:
   a. Parse JSON → OHLCVBar (via zmq_adapter)
   b. Data sanity check (opzionale)
   c. FeaturePipeline.process(bar) → feature dict 60-dim
   d. RegimeClassifier.classify(features) → regime
   e. TradingAdvisor.advise() → signal suggestion (4-tier cascade)
      OPPURE RegimeRouter.route() se TradingAdvisor non disponibile
   f. SignalGenerator.generate_signal() → signal completo con SL/TP
   g. SignalValidator.validate() → 11 checks
   h. PositionSizer.calculate() → lots
   i. SpiralProtection.check() → permesso?
   j. KillSwitch.is_active() → bloccato? ← BUG: sempre True (F01)
   k. CorrelationChecker.check() → esposizione OK?
   l. RateLimiter.allow() → sotto il limite?
   m. Se tutto OK: gRPC SendSignal() → MT5 Bridge ← BUG: direzione UNSPECIFIED (F02)
   n. PnL Momentum record ← BUG: dati fittizi (F04)
4. Graceful shutdown su SIGINT/SIGTERM ← BUG: BridgeClient mai chiuso (F08)
```

#### BUG CRITICI IN main.py

**F01 — Kill Switch Return Type Mismatch** (righe 887, 1316):
```python
# kill_switch.py:104 — ritorna tuple
async def is_active(self) -> tuple[bool, str]:
    return self._cached_active, self._cached_reason

# main.py:887 — tratta il tuple come bool
if await kill_switch.is_active():  # tuple SEMPRE truthy!
    await asyncio.sleep(5)
    continue  # SKIP TUTTO — trading BLOCCATO
```
**Impatto**: Il kill switch risulta SEMPRE attivo perche' un tuple non-vuoto e' truthy. Nessun segnale viene mai generato.

**F02 — Direzione gRPC sempre UNSPECIFIED** (via grpc_client.py:60-61):
```python
# grpc_client.py
direction_str = str(signal.get("direction", "HOLD"))  # str(Direction.BUY) = "Direction.BUY"
direction_enum = _DIRECTION_MAP.get(direction_str, 0)  # "Direction.BUY" non in map → 0

_DIRECTION_MAP = {"BUY": 1, "SELL": 2, "HOLD": 3}  # aspetta "BUY", non "Direction.BUY"
```
**Impatto**: Tutti i segnali hanno direction=0 (UNSPECIFIED) nel protobuf → MT5 Bridge rifiuta o ha comportamento indefinito.

**F04 — PnL Tracker con Dati Fittizi** (riga ~1388):
```python
if pnl_momentum is not None:
    pnl_momentum.record_trade(
        pnl=Decimal("0"),   # PnL sconosciuto al momento del fill
        is_win=True,         # Placeholder SBAGLIATO
    )
```
**Impatto**: Momentum tracker, maturity observatory, e streak detection operano su dati falsi. Le decisioni di gating sono inaffidabili.

**Codice morto** (righe 269-301):
- `_parse_ohlcv_payload()` definita ma mai chiamata. La riga 914 usa `parse_bar_message()` da `zmq_adapter`.

### 2.2 orchestrator.py — CascadeOrchestrator (205 LoC, Qualita 7/10)

**Stato: CODICE MORTO** — Non importato ne' usato da main.py.

La classe `CascadeOrchestrator` implementa la logica di cascata 4-mode, ma:
- **Mai importato** in main.py (verificato con grep)
- **Mai istanziato** da nessun file nel progetto
- La cascata e' reimplementata inline in main.py (righe 1074-1131)
- 205 righe di codice con zero valore produttivo

**Probabile origine**: Refactoring incompleto. L'orchestrator doveva sostituire la logica inline in main.py, ma l'integrazione non e' mai stata completata.

**Raccomandazione**: Integrare orchestrator.py in main.py per ridurre run_brain() da 944 a ~700 righe, oppure eliminarlo.

### 2.3 kill_switch.py — Emergency Stop (145 LoC, Qualita 7.5/10)

**Cosa fa**: Kill switch di emergenza basato su Redis. Puo' essere attivato manualmente (Console) o automaticamente (limiti di rischio).

**API (3 metodi per controllare lo stato — confusionario)**:
1. `is_active() → tuple[bool, str]` — ritorna stato e motivo (ma usato come bool — BUG F01)
2. `check_or_raise() → None` — lancia eccezione se attivo (MAI USATO nel codice)
3. `auto_check()` — attiva automaticamente se limiti superati (usato a riga 1310)

**Redis Keys**:
- `moneymaker:kill_switch:active` → "1"/"0"
- `moneymaker:kill_switch:reason` → stringa motivo
- `moneymaker:kill_switch:activated_at` → ISO timestamp

**WARNING — Cache TTL di 1 secondo** (riga 43):
```python
self._cache_ttl: float = 1.0  # 1 secondo cache
```
Per un sistema safety-critical, 1 secondo di latenza significa che fino a 1 secondo di trading puo' continuare DOPO l'attivazione del kill switch. Per un sistema che processa barre M5 (una ogni 5 minuti), questo non e' problematico, ma per tick-level trading sarebbe critico.

**Punti positivi**: Fallback locale se Redis non disponibile, JSON serialization corretta, auto-check per limiti di rischio.

### 2.4 portfolio.py — State Management (174 LoC, Qualita 7.5/10)

**Cosa fa**: Gestisce lo stato del portafoglio: posizioni aperte, esposizione, drawdown, win/loss rate.

**BUG F07 — Mutable List Leak** (riga ~79):
```python
def get_state(self) -> dict[str, object]:
    return {
        "positions_detail": self._positions_detail,  # riferimento diretto!
    }
```
Un chiamante puo' mutare la lista interna, corrompendo lo stato del portafoglio.

**BUG F09 — Persistenza Redis incompleta** (righe 151-174):
- Solo `daily_loss_pct` e' sincronizzato con Redis
- `_open_position_count`, `_total_exposure`, `_symbols_exposed`, `_win_count`, `_loss_count` sono **persi al restart**
- Se il servizio si riavvia con trade aperti su MT5, il portfolio vede 0 posizioni → validatore permette nuove posizioni → rischio di over-exposure

### 2.5 grpc_client.py — BridgeClient (206 LoC, Qualita 6/10)

**BUG CRITICO F02** (gia' descritto sopra) — Serializzazione direzione fallata.

**BUG F08 — Channel mai chiuso** (riga 201-206):
- `BridgeClient.close()` esiste come metodo
- Ma NON viene mai chiamato in main.py, nemmeno nel shutdown handler (riga ~1518)
- Il canale gRPC resta aperto indefinitamente
- Resource leak: connessioni non rilasciate, possibili problemi di porta al restart

**Nessun retry logic** (riga 189):
```python
response = await self._stub.ExecuteTrade(proto_signal, timeout=10)
# Nessun retry su timeout o errore transitorio → segnale perso
```

### 2.6 ml_feedback.py — ML Prediction Persistence (98 LoC, Qualita 5/10)

**BUG CRITICO F03** (riga 33-40):
```python
def __init__(self, pool: Any = None, max_buffer_size: int = 1000) -> None:
    self._pool = pool  # pool e' None

# main.py riga ~773
ml_feedback = MLPredictionWriter()  # pool=None di default, MAI impostato

# flush() riga ~55
async def flush(self) -> int:
    if not self._buffer or self._pool is None:  # SEMPRE True → return 0
        return 0
```
**Impatto**: Tutte le predizioni ML bufferizzate vengono scartate silenziosamente. Il feedback loop ML e' completamente rotto. La riga 1527 `flushed = await ml_feedback.flush()` non logga mai nulla.

### 2.7 Strategie (6 file)

#### base.py — Contratto Base
```python
@dataclass
class SignalSuggestion:
    direction: str | Direction  # Convertito a Direction in __post_init__
    confidence: Decimal         # [0.0, 1.0]
    reasoning: str
    metadata: dict | None = None

class TradingStrategy(ABC):
    @abstractmethod
    def analyze(self, features: dict[str, Any]) -> SignalSuggestion: ...
```
**Stato**: OK — Clean contract con validazione nel dataclass

#### trend_following.py
**Logica**: BUY se 3+ conferme su EMA fast>slow, Close>SMA200, MACD>0, ADX>25. Confidence = min(0.50 + ADX/100, 0.90).

**WARNING F05**: ADX non validato per range [0,100]. Se malformato, la formula produce valori errati mascherati dal min().

#### mean_reversion.py
**Logica**: BUY se BB%B < 0.10 AND RSI < 30. SELL se BB%B > 0.90 AND RSI > 70. Base confidence 0.65, max 0.85.
**Stato**: OK

#### defensive.py
**Logica**: Sempre HOLD con confidence 0.80. Usata per regimi alta volatilita'/inversione.
**Stato**: OK

#### ml_proxy.py (~240 LoC)
**Cosa fa**: Chiama ML service via gRPC con circuit breaker e fallback.

**WARNING F06**: Circuit breaker non distingue timeout (DEADLINE_EXCEEDED) da errori generici. Un network flaky causa oscillazione del circuito.

**Stato attuale**: ML service non attivo → sempre fallback HOLD.

#### regime_router.py
**Mapping**: trending_up/down → TrendFollowing, ranging → MeanReversion, high_volatility/reversal → Defensive.
**Stato**: OK

### 2.8 Trading Advisor — Cascata 4 Modi (506 LoC)

**4 Modi di Operazione**:

```
Mode 1 - COPER (Mature + model loaded):
    Usa experience bank per sintetizzare advice da trade storici simili.

Mode 2 - Hybrid (Learning + model loaded):
    Combina predizioni ML con regole tecniche.

Mode 3 - Knowledge (no model OR fallback):
    Usa knowledge base per trovare pattern simili.

Mode 4 - Conservative (sempre funziona):
    RegimeRouter → strategie rule-based (trend/mean_reversion/defensive).
```

**Stato attuale**:
- `has_model` = **False** (nessun modello addestrato)
- Mode 1, 2: **SEMPRE skippati**
- Mode 3: **Parziale** (knowledge base potrebbe essere vuota)
- Mode 4: **UNICO operativo**

**WARNING F10**: `_try_hybrid()` chiamata DUE VOLTE per maturity LEARNING (una volta specifica, una nel fallback generico). Inefficiente.

### 2.9 Signal Generator, Correlation Checker, Rate Limiter

**SignalGenerator** (120 LoC): SL = price ± ATR*1.5, TP = price ± ATR*2.5. Risk/Reward default 1.67:1. **Stato**: OK

**CorrelationChecker** (100 LoC): 12 coppie supportate (EUR/USD, GBP/USD, etc.). **WARNING F11**: Simboli sconosciuti passano silenziosamente senza log.

**RateLimiter** (60 LoC): Sliding window 1 ora, max 10 segnali. `time.monotonic()`. **Stato**: OK

### 2.10 Maturity Gate (250 LoC)

**5 livelli**: NOVICE → LEARNING → COMPETENT → MATURE → CONVICTION.
**Componenti**: ConvictionIndex, HysteresisGate (previene oscillazione), TradingModeGate.
**Stato**: OK — Design sofisticato. Attualmente bloccato a NOVICE/LEARNING (nessun modello per avanzare).

---

## 3. Flusso Completo Tick-to-Signal

```
ZMQ SUB (tcp://data-ingestion:5555)
    |
    | topic: "bar.{symbol}.{timeframe}"
    | payload: JSON con OHLCV + metadata
    v
zmq_adapter.py → OHLCVBar(symbol, timeframe, O, H, L, C, V, ticks, complete)
    |
    v
[DataSanityChecker] → Valida OHLCV plausibilita' (opzionale)
    |
    v
FeaturePipeline.process(bar) → dict 60 features
    | RSI, EMA fast/slow, SMA200, MACD, BB, ATR, ADX,
    | Stochastic, sessione, tick_count, spread, volume...
    v
RegimeClassifier.classify(features) → "trending_up"|"ranging"|"high_volatility"|...
    |
    v
+-- TradingAdvisor.advise() --+---- RegimeRouter.route() --+
|                              |                             |
| Mode 1: COPER (non attivo)  | (se TradingAdvisor = None) |
| Mode 2: Hybrid (non attivo) |                             |
| Mode 3: Knowledge (parziale)|  TrendFollowing             |
| Mode 4: Conservative ←------+  MeanReversion              |
|          RegimeRouter.route()|  Defensive                  |
+------------------------------+-----------------------------+
    |
    v
SignalSuggestion(direction, confidence, reasoning, metadata)
    |
    v
SignalGenerator.generate_signal(symbol, suggestion, price, atr)
    | UUID signal_id, SL = price ± ATR*1.5, TP = price ± ATR*2.5
    v
signal dict {signal_id, symbol, direction, confidence, SL, TP, regime, source_tier}
    |
    v
SignalValidator.validate(signal) → 11 checks fail-fast
    | 1. Confidence >= 0.65            7. Risk/reward >= 1.0
    | 2. Kill switch non attivo        8. Spread OK
    | 3. Max open positions (5)        9. Margin check
    | 4. Daily loss < 2%              10. Signal age < 30s
    | 5. Drawdown < 5%               11. Timeframe validation
    | 6. SL/TP presente e valido
    v
[CorrelationChecker] → esposizione valutaria < max (3 per currency)
    |
    v
[PositionSizer] → lots basati su equity, rischio, drawdown
    |
    v
[SpiralProtection] → riduce size dopo N loss consecutive
    |
    v
[RateLimiter] → max 10 segnali/ora
    |
    v
gRPC SendSignal(TradingSignal) → MT5 Bridge (:50055)
    | ← BUG F02: direction=UNSPECIFIED (0) per tutti i segnali
    v
SignalAck(status=ACCEPTED|REJECTED, reason)
```

---

## 4. Findings

| # | Severita | File:Riga | Problema | Impatto | Fix |
|---|----------|-----------|----------|---------|-----|
| F01 | **CRITICO** | `main.py:887,1316` + `kill_switch.py:104` | `is_active()` ritorna `tuple[bool, str]` ma main.py lo tratta come `bool`. Un tuple non-vuoto e' SEMPRE truthy. | **Trading completamente bloccato**: nessun segnale generato mai | `is_active, reason = await kill_switch.is_active()` + `if is_active:` |
| F02 | **CRITICO** | `grpc_client.py:60-61` | `str(Direction.BUY)` produce `"Direction.BUY"`, non `"BUY"`. `_DIRECTION_MAP` non lo trova → default 0 (UNSPECIFIED). | Tutti i segnali hanno direzione UNSPECIFIED → MT5 rifiuta | Estrarre `.value` o `.split(".")[-1]` dall'enum |
| F03 | **CRITICO** | `ml_feedback.py:33` + `main.py:~773` | `MLPredictionWriter(pool=None)` — pool MAI impostato via `set_pool()`. `flush()` ritorna sempre 0. | ML feedback loop completamente rotto, predizioni perse | Passare db_pool al costruttore o chiamare `set_pool()` dopo init |
| F04 | **CRITICO** | `main.py:~1388` | PnL momentum tracker registra `pnl=Decimal("0")` e `is_win=True` al momento del fill (PnL reale sconosciuto). | Maturity gating e streak detection basati su dati falsi | Registrare solo al close del trade (quando PnL e' noto) |
| F05 | **ALTO** | `trend_following.py` | ADX non validato per range [0,100]. Valori malformati mascherati dal `min()`. | Formula confidence produce valori errati senza segnalazione | Aggiungere: `if adx < 0 or adx > 100: return HOLD` |
| F06 | **ALTO** | `ml_proxy.py` | Circuit breaker non distingue timeout gRPC (DEADLINE_EXCEEDED) da errori generici. | Network flaky causa oscillazione del circuito | Pesare timeout +2, errori normali +1 |
| F07 | **ALTO** | `portfolio.py:~79` | `get_state()` ritorna riferimento diretto a `_positions_detail` (mutable list leak). | Chiamanti possono corrompere lo stato del portafoglio | `list(self._positions_detail)` |
| F08 | **ALTO** | `main.py:~1518` + `grpc_client.py:201-206` | `BridgeClient.close()` esiste ma MAI chiamato, nemmeno nel shutdown handler. | Resource leak, problemi di porta al restart | Aggiungere `await bridge_client.close()` nel shutdown |
| F09 | **WARNING** | `portfolio.py:151-174` | Solo `daily_loss_pct` persistito su Redis. `_open_position_count`, `_symbols_exposed` persi al restart. | Dopo restart: portfolio vede 0 posizioni → over-exposure possibile | Persistere tutti i campi critici su Redis |
| F10 | **WARNING** | `trading_advisor.py:~122-148` | `_try_hybrid()` chiamata 2 volte per maturity LEARNING (specifica + fallback). | Inefficiente (non pericoloso) | Refactoring cascata |
| F11 | **WARNING** | `correlation.py:~94` | Simboli sconosciuti passano silenziosamente (return True senza log). | Perdita osservabilita', esposizione non controllata per nuovi simboli | Aggiungere `logger.warning()` |
| F12 | **WARNING** | `main.py:269-301` | `_parse_ohlcv_payload()` definita ma mai chiamata. La riga 914 usa `parse_bar_message()`. | Codice morto, confusione | Eliminare o documentare come fallback |

---

## 5. Architettura: run_brain() — God Function

La funzione `run_brain()` in main.py e' una **god function** di **944 righe** (righe 600-1544) con 5+ livelli di nesting. Contiene:

- Inizializzazione di 20+ componenti
- Loop ZMQ principale
- Logica di cascata 4-mode (duplicata da orchestrator.py)
- Dispatch gRPC
- Error handling
- Shutdown handler
- Logging e metriche

**Problemi**:
1. **Testabilita'**: Impossibile fare unit test senza mockare 20+ dipendenze
2. **Leggibilita'**: Estremamente difficile seguire il flusso
3. **Manutenibilita'**: Ogni cambio rischia side-effects

**Nota**: `orchestrator.py` (205 LoC) implementa la stessa cascata in modo pulito ma NON e' usato. main.py reimplementa la logica inline.

**Raccomandazione**: Integrare orchestrator.py o estrarre funzioni helper:
```python
async def run_brain(settings: BrainSettings) -> None:
    components = await _initialize_components(settings)
    async for bar in _receive_market_data(components.zmq_sub):
        features = await _compute_features(bar, components)
        suggestion = await _generate_suggestion(features, components)
        signal = await _validate_and_size(suggestion, components)
        if signal:
            await _dispatch_signal(signal, components)
```

---

## 6. Stato Operativo Attuale

### Cosa FUNZIONA (operativo ora)

| Componente | Stato | Note |
|-----------|-------|------|
| ZMQ Subscription | OK | Riceve barre da data-ingestion |
| Feature Pipeline | OK | 60 features calcolate |
| Regime Classification | OK | 5 regimi riconosciuti |
| Mode 4 (Conservative) | OK | RegimeRouter + 3 strategie |
| TrendFollowing | OK (con WARNING) | 4 indicatori, soglia 3/4 |
| MeanReversion | OK | BB + RSI + Stoch opzionale |
| Defensive | OK | HOLD per volatilita' alta |
| Signal Generator | OK | SL/TP basati su ATR |
| Signal Validator | OK | 11 checks fail-fast |
| Spiral Protection | OK | Riduce lots dopo loss |
| Correlation Checker | OK (con WARNING) | 12 coppie |
| Rate Limiter | OK | 10/ora sliding window |
| Maturity Gate | OK | Hysteresis anti-oscillazione |

### Cosa NON FUNZIONA (bug critici)

| Componente | Bug | Impatto |
|-----------|-----|---------|
| Kill Switch check | F01: tuple trattato come bool | Trading SEMPRE bloccato |
| gRPC Direction | F02: enum serializzato male | Tutti i segnali UNSPECIFIED |
| ML Feedback | F03: pool mai inizializzato | Predizioni ML perse |
| PnL Tracking | F04: dati fittizi registrati | Gating decisions inaffidabili |
| BridgeClient | F08: channel mai chiuso | Resource leak |
| Portfolio Persistence | F09: stato parziale | Over-exposure dopo restart |

### Cosa NON ATTIVO (richiede lavoro futuro)

| Componente | Stato | Blocco |
|-----------|-------|--------|
| Mode 1 (COPER) | NON ATTIVO | Richiede modello addestrato + maturity MATURE |
| Mode 2 (Hybrid) | NON ATTIVO | Richiede modello addestrato + maturity LEARNING |
| Mode 3 (Knowledge) | PARZIALE | Knowledge base potrebbe essere vuota |
| ML Proxy Strategy | STUB | Servizio ML non deployato |
| Shadow Engine | NON TESTATO | Dipende da ML |
| Maturity Progression | BLOCCATA | Nessun modello per avanzare oltre NOVICE/LEARNING |

---

## 7. Interconnessioni

### 7.1 Dipendenze Interne del Brain

```
main.py (1,609 LoC — god function)
├── config.py (BrainSettings)
├── zmq_adapter.py (ZMQ SUB parsing)
├── features/pipeline.py (60-dim feature extraction)
├── features/regime.py (regime classification)
├── [orchestrator.py] ← NON USATO (codice morto)
├── services/trading_advisor.py (4-tier cascade)
│   ├── knowledge/trade_history_bank.py (Mode 1 COPER)
│   ├── knowledge/hybrid_signal_engine.py (Mode 2 Hybrid)
│   ├── knowledge/strategy_knowledge.py (Mode 3 Knowledge)
│   └── strategies/regime_router.py (Mode 4 Conservative)
│       ├── strategies/trend_following.py
│       ├── strategies/mean_reversion.py
│       └── strategies/defensive.py
├── signals/generator.py (signal creation)
├── signals/validator.py (11 checks)
├── signals/position_sizer.py (lot sizing)
├── signals/spiral_protection.py (consecutive loss protection)
├── signals/correlation.py (currency exposure)
├── signals/rate_limiter.py (10/hour cap)
├── kill_switch.py (Redis emergency stop) ← BUG F01
├── portfolio.py (equity tracking) ← BUG F07, F09
├── grpc_client.py (MT5 Bridge connection) ← BUG F02, F08
├── ml_feedback.py (ML prediction persistence) ← BUG F03
└── maturity_gate.py (mode determination)
```

### 7.2 Dipendenze Esterne

```
Algo Engine
├── ZMQ SUB → data-ingestion:5555 (market data input)
├── gRPC → mt5-bridge:50055 (signal output)
├── gRPC → ml-training:50056 (ML inference, NON ATTIVO)
├── PostgreSQL → :5432 (storage, audit)
├── Redis → :6379 (kill switch, caching, stato portfolio parziale)
└── Prometheus → :9092 (metrics export — ma irraggiungibile, vedi Report 01 F04)
```

---

## 8. Istruzioni con Checkbox

### Segmento A: Fix Kill Switch (CRITICO — F01)
- [ ] **A1**: `main.py:887` — Cambiare `if await kill_switch.is_active():` → `is_active, reason = await kill_switch.is_active()` + `if is_active:`
- [ ] **A2**: `main.py:1316` — Stesso fix della riga 887
- [ ] **A3**: Considerare refactoring di `is_active()` per ritornare solo `bool` (la reason e' raramente usata) e creare `get_status() → tuple[bool, str]` separato
- [ ] **A4**: Aggiungere test unitario: `assert isinstance(kill_switch.is_active(), tuple)` e verificare che main.py destruttura correttamente

### Segmento B: Fix Direzione gRPC (CRITICO — F02)
- [ ] **B1**: `grpc_client.py:60` — Cambiare serializzazione direzione:
  ```python
  raw_dir = signal.get("direction", "HOLD")
  if hasattr(raw_dir, "value"):
      direction_str = raw_dir.value  # Direction enum → "BUY"
  else:
      direction_str = str(raw_dir)
  direction_enum = _DIRECTION_MAP.get(direction_str, 0)
  ```
- [ ] **B2**: Aggiungere assert/log se `direction_enum == 0`: `logger.error("Direction UNSPECIFIED — bug di serializzazione")`
- [ ] **B3**: Aggiungere test: `assert _DIRECTION_MAP[Direction.BUY.value] == 1`

### Segmento C: Fix ML Feedback (CRITICO — F03)
- [ ] **C1**: `main.py:~773` — Passare il database pool al costruttore: `MLPredictionWriter(pool=db_pool)` oppure chiamare `ml_feedback.set_pool(db_pool)` dopo la creazione del pool
- [ ] **C2**: Aggiungere warning in `flush()` se pool e' None: `logger.warning("ML feedback pool non impostato — predizioni perse")`
- [ ] **C3**: Aggiungere test che verifica che `flush()` effettivamente scrive nel database

### Segmento D: Fix PnL Tracking (CRITICO — F04)
- [ ] **D1**: `main.py:~1388` — Rimuovere il record fittizio al fill. Aggiungere commento TODO: "Registrare PnL reale al close del trade"
- [ ] **D2**: Implementare meccanismo per tracciare trade aperti e registrare PnL al close (richiede feedback da MT5 Bridge via StreamTradeUpdates — attualmente stub vuoto)
- [ ] **D3**: Documentare che maturity progression e' inaffidabile finche' PnL tracking non e' implementato

### Segmento E: Fix Secondari (ALTO)
- [ ] **E1**: `trend_following.py` — Aggiungere validazione ADX range [0,100] (F05)
- [ ] **E2**: `ml_proxy.py` — Differenziare timeout da errori nel circuit breaker (F06)
- [ ] **E3**: `portfolio.py:~79` — `"positions_detail": list(self._positions_detail)` per evitare mutable leak (F07)
- [ ] **E4**: `main.py:~1518` — Aggiungere `await bridge_client.close()` nel shutdown handler (F08)

### Segmento F: Miglioramenti Osservabilita' (WARNING)
- [ ] **F1**: `main.py` startup — Aggiungere log con stato di ogni modulo caricato:
  ```python
  logger.info("Module status", trading_advisor=TradingAdvisor is not None, ...)
  ```
- [ ] **F2**: `correlation.py:~94` — Aggiungere `logger.warning()` per simboli non mappati (F11)
- [ ] **F3**: Aggiungere metrica `moneymaker_brain_active_mode` (gauge 1-4) per tracciare il mode operativo
- [ ] **F4**: Eliminare `_parse_ohlcv_payload()` da main.py (codice morto, F12)
- [ ] **F5**: Decidere se integrare orchestrator.py o eliminarlo

### Segmento G: Portfolio Persistence (WARNING)
- [ ] **G1**: `portfolio.py` — Aggiungere persistenza Redis per `_open_position_count`, `_total_exposure`, `_symbols_exposed` (F09)
- [ ] **G2**: Aggiungere meccanismo di riconciliazione portfolio ↔ MT5 al startup
- [ ] **G3**: Aggiungere test per verificare che stato portfolio sopravvive al restart

---

## 9. Riepilogo Severita'

| Severita | Count | Finding IDs |
|----------|-------|------------|
| CRITICO | 4 | F01, F02, F03, F04 |
| ALTO | 4 | F05, F06, F07, F08 |
| WARNING | 4 | F09, F10, F11, F12 |
| **Totale** | **12** | |

**Nota**: F01 e F02 sono **production-blocking** — il sistema non puo' generare ne' inviare segnali validi con questi bug. Devono essere risolti PRIMA di qualsiasi test end-to-end.

---

*Fine Report 02 — Prossimo: Report 03 (Neural Network Architecture)*
