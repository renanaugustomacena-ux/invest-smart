# MONEYMAKER V1 — Sistema di Trading Algoritmico

> **Argomenti:** Architettura del servizio Algo Engine, pipeline di calcolo indicatori tecnici (25+ indicatori), classificazione del regime di mercato (5 regimi), routing delle strategie di trading (trend-following, mean-reversion, difensiva), generazione segnali con stop-loss/take-profit ATR-based, architettura neurale JEPA per embedding di mercato, sistemi di knowledge e coaching.
>
> **Autore:** Renan Augusto Macena

---

## Indice

1. [Architettura Algo Engine](#1-architettura-algo-engine)
2. [Il Cartografo: Feature Engineering](#2-il-cartografo-feature-engineering)
3. [L'Ufficiale Meteorologo: Regime Classification](#3-lufficiale-meteorologo-regime-classification)
4. [Il Timoniere: Strategy Router](#4-il-timoniere-strategy-router)
5. [L'Artigiano: Signal Generator](#5-lartigiano-signal-generator)
6. [Le Reti Neurali: JEPA](#6-le-reti-neurali-jepa)
7. [L'Archivio di Bordo: Knowledge Systems](#7-larchivio-di-bordo-knowledge-systems)

---

## 1. Architettura Algo Engine

L'**Algo Engine** è la Plancia di Comando della nave MONEYMAKER — il centro decisionale dove convergono tutte le informazioni sensoriali (dati di mercato), vengono analizzate attraverso modelli matematici e di machine learning, e si generano gli ordini di trading.

Scritto in Python 3.11+ con oltre 165 file sorgente, il Brain implementa:

- **Feature Pipeline**: calcolo di 25+ indicatori tecnici con aritmetica Decimal
- **Regime Classifier**: classificazione delle condizioni di mercato in 5 regimi
- **Strategy Router**: instradamento verso la strategia appropriata per ogni regime
- **Signal Generator**: costruzione di segnali completi con SL/TP e metadati
- **Signal Validator**: validazione contro 11 controlli di rischio
- **ML Integration**: integrazione opzionale con modelli neurali (JEPA, GNN)

| Componente | Cartella | File principali | Responsabilità |
| --- | --- | --- | --- |
| **Features** | `features/` | `pipeline.py`, `technical.py`, `regime.py` | Calcolo indicatori, classificazione regime |
| **Strategies** | `strategies/` | `regime_router.py`, `trend_following.py`, `mean_reversion.py` | Logica decisionale per direzione trade |
| **Signals** | `signals/` | `generator.py`, `validator.py`, `position_sizer.py` | Costruzione e validazione segnali |
| **Neural Networks** | `nn/` | `jepa_market.py`, `model_factory.py` | Embedding e predizione ML |
| **Knowledge** | `knowledge/` | `market_graph.py`, `strategy_knowledge.py` | Memoria e apprendimento |

> **Analogia:** La Plancia di Comando di una nave moderna. Il **Cartografo** (Feature Pipeline) trasforma le letture grezze del sonar in mappe navigabili. L'**Ufficiale Meteorologo** (Regime Classifier) analizza vento, onde e pressione per classificare le condizioni meteo. Il **Timoniere** (Strategy Router) riceve gli ordini e manovra la nave nella direzione giusta. L'**Artigiano** (Signal Generator) costruisce gli ordini di manovra con tutti i dettagli. Il **Controllore Qualità** (Validator) verifica che ogni ordine sia sicuro prima dell'esecuzione. E il **Sistema di Intelligenza** (JEPA) impara dai pattern storici per anticipare le condizioni future.

```mermaid
flowchart TB
    subgraph INPUT["DATI IN INGRESSO"]
        ZMQ["ZeroMQ SUB<br/>bar.SYMBOL.TF"]
        REDIS["Redis<br/>Latest prices"]
    end

    subgraph FEATURES["IL CARTOGRAFO<br/>(Feature Pipeline)"]
        TECH["Indicatori Tecnici<br/>25+ indicatori"]
        QUALITY["Data Quality<br/>Sanity checks"]
    end

    subgraph REGIME["L'UFFICIALE METEOROLOGO<br/>(Regime Classifier)"]
        CLASS["Classificatore<br/>5 regimi"]
        CONF["Confidence<br/>Score"]
    end

    subgraph ROUTER["IL TIMONIERE<br/>(Strategy Router)"]
        MAP["Mappa Regime→Strategia"]
        STRAT["Strategie:<br/>Trend, Mean-Rev, Difensiva"]
    end

    subgraph SIGNAL["L'ARTIGIANO<br/>(Signal Generator)"]
        BUILD["Costruzione Segnale<br/>UUID, timestamps"]
        SLTP["Calcolo SL/TP<br/>ATR-based"]
    end

    subgraph VALIDATE["IL CONTROLLORE<br/>(Signal Validator)"]
        CHECKS["11 Controlli Rischio"]
        PASS["Passa/Rifiuta"]
    end

    subgraph OUTPUT["OUTPUT"]
        GRPC["gRPC → MT5 Bridge"]
        LOG["Audit Trail"]
    end

    ZMQ --> TECH
    REDIS --> TECH
    TECH --> QUALITY
    QUALITY --> CLASS

    CLASS --> MAP
    CONF --> MAP
    MAP --> STRAT

    STRAT -->|"SignalSuggestion"| BUILD
    BUILD --> SLTP
    SLTP --> CHECKS

    CHECKS -->|"Valido"| GRPC
    CHECKS -->|"Rifiutato"| LOG
    GRPC --> LOG

    style ZMQ fill:#15aabf,color:#fff
    style TECH fill:#4a9eff,color:#fff
    style CLASS fill:#9775fa,color:#fff
    style STRAT fill:#228be6,color:#fff
    style BUILD fill:#51cf66,color:#fff
    style CHECKS fill:#ff922b,color:#fff
    style GRPC fill:#51cf66,color:#fff
```

> **Spiegazione Diagramma:** I dati arrivano via ZeroMQ (ciano). Il Cartografo (blu) calcola gli indicatori. Il Meteorologo (viola) classifica il regime. Il Timoniere (blu scuro) seleziona la strategia. L'Artigiano (verde) costruisce il segnale. Il Controllore (arancione) valida. Se passa, il segnale va al MT5 Bridge (verde). Tutto viene registrato nell'audit trail.

### 1.1 Flusso di Elaborazione

```mermaid
sequenceDiagram
    participant ZMQ as ZeroMQ
    participant FP as Feature Pipeline
    participant RC as Regime Classifier
    participant RR as Regime Router
    participant ST as Strategy
    participant SG as Signal Generator
    participant SV as Signal Validator
    participant GRPC as gRPC Client

    ZMQ->>FP: OHLCVBar(XAU/USD, M5)
    FP->>FP: Calcola 25+ indicatori
    FP->>RC: features dict

    RC->>RC: Classifica regime
    RC->>RR: RegimeClassification(TRENDING_UP, 0.78)

    RR->>RR: Lookup strategia per regime
    RR->>ST: features dict
    ST->>ST: Analizza e genera suggerimento
    ST->>SG: SignalSuggestion(BUY, 0.72, "3 conferme trend")

    SG->>SG: Calcola SL/TP da ATR
    SG->>SG: Genera UUID, timestamps
    SG->>SV: TradingSignal completo

    SV->>SV: Esegue 11 controlli
    alt Tutti i controlli passano
        SV->>GRPC: SendSignal(TradingSignal)
        GRPC-->>SV: SignalAck(ACCEPTED)
    else Almeno un controllo fallisce
        SV->>SV: Log rejection reason
    end
```

---

## 2. Il Cartografo: Feature Engineering

Il **Cartografo** trasforma i dati grezzi di mercato in una "mappa" di indicatori tecnici navigabili. Come un cartografo che dalle foto satellitari crea mappe con contorni, strade e punti di interesse, questo componente calcola **25+ indicatori** che descrivono lo stato del mercato.

**VINCOLO ARCHITETTURALE:** Tutti i calcoli usano `decimal.Decimal` per evitare errori di precisione floating-point. Come un farmacista che pesa i grammi con la bilancia di precisione invece di "a occhio".

| Categoria | Indicatori | Funzione |
| --- | --- | --- |
| **Trend** | SMA(200), EMA(12), EMA(26), EMA Fast/Slow | Direzione generale del mercato |
| **Momentum** | RSI(14), MACD, Stochastic, ROC, CCI, Williams %R | Forza e velocità del movimento |
| **Volatilità** | ATR(14), Bollinger Bands, Donchian Channels | Ampiezza delle oscillazioni |
| **Forza Trend** | ADX(14), +DI, -DI | Quanto è forte il trend |
| **Volume** | OBV, Volume MA | Partecipazione al movimento |

> **Analogia:** Ogni indicatore è uno **strumento diverso** nella borsa del cartografo:
> - **SMA/EMA** sono come le curve di livello — mostrano l'altitudine media del terreno (prezzo).
> - **RSI** è il termometro — misura la "febbre" del mercato (sopra 70 = surriscaldato, sotto 30 = ipotermia).
> - **MACD** è il radar della velocità — due auto (EMA veloce e lenta) su una strada: quando la veloce supera la lenta, il mercato accelera.
> - **ATR** è il sismografo — misura l'ampiezza delle scosse (volatilità).
> - **ADX** è l'anemometro — misura la forza del vento (trend), non la direzione.
> - **Bollinger Bands** sono i margini della strada — il 95% del traffico (prezzo) resta all'interno.

```mermaid
flowchart LR
    subgraph INPUT["Dati Grezzi"]
        OHLCV["OHLCVBar<br/>O, H, L, C, V"]
    end

    subgraph TREND["Indicatori Trend"]
        SMA["SMA(200)<br/>Media semplice"]
        EMA["EMA(12, 26)<br/>Media esponenziale"]
    end

    subgraph MOM["Indicatori Momentum"]
        RSI["RSI(14)<br/>0-100"]
        MACD["MACD<br/>line, signal, hist"]
        STOCH["Stochastic<br/>%K, %D"]
    end

    subgraph VOL["Indicatori Volatilità"]
        ATR["ATR(14)<br/>Average True Range"]
        BB["Bollinger Bands<br/>upper, mid, lower"]
    end

    subgraph STRENGTH["Forza Trend"]
        ADX["ADX(14)<br/>0-100"]
        DI["+DI / -DI<br/>Direzione"]
    end

    subgraph OUTPUT["Features Dict"]
        DICT["25+ chiavi<br/>tutti Decimal"]
    end

    OHLCV --> SMA
    OHLCV --> EMA
    OHLCV --> RSI
    OHLCV --> MACD
    OHLCV --> STOCH
    OHLCV --> ATR
    OHLCV --> BB
    OHLCV --> ADX
    OHLCV --> DI

    SMA --> DICT
    EMA --> DICT
    RSI --> DICT
    MACD --> DICT
    STOCH --> DICT
    ATR --> DICT
    BB --> DICT
    ADX --> DICT
    DI --> DICT

    style OHLCV fill:#4a9eff,color:#fff
    style RSI fill:#9775fa,color:#fff
    style ATR fill:#ff922b,color:#fff
    style ADX fill:#51cf66,color:#fff
    style DICT fill:#ffd43b,color:#000
```

> **Spiegazione Diagramma:** I dati OHLCV (blu) alimentano tutti gli indicatori in parallelo. Ogni categoria (trend, momentum, volatilità, forza) produce valori che confluiscono nel dizionario finale (giallo) usato dalle fasi successive.

### 2.1 Formule Chiave

**RSI (Relative Strength Index):**
```
RSI = 100 - (100 / (1 + RS))
RS  = Guadagno_medio / Perdita_media (su 14 periodi)
```

**MACD (Moving Average Convergence/Divergence):**
```
Linea MACD    = EMA(12) - EMA(26)
Linea Segnale = EMA(Linea MACD, 9)
Istogramma    = Linea MACD - Linea Segnale
```

**ATR (Average True Range):**
```
TR  = max(H-L, |H-C_prev|, |L-C_prev|)
ATR = EMA(TR, 14)
```

**ADX (Average Directional Index):**
```
+DM = H - H_prev (se positivo e > |L-L_prev|)
-DM = L_prev - L (se positivo e > +DM)
DX  = 100 * |+DI - -DI| / (+DI + -DI)
ADX = EMA(DX, 14)
```

---

## 3. L'Ufficiale Meteorologo: Regime Classification

L'**Ufficiale Meteorologo** analizza gli strumenti (indicatori) e dichiara le condizioni meteo (regime di mercato). Come un meteorologo che guarda barometro, anemometro e igrometro per dire "oggi c'è tempesta" o "oggi c'è calma piatta".

MONEYMAKER classifica il mercato in **5 regimi**, ordinati per priorità di rilevamento:

| Regime | Condizione | Analogia Meteo |
| --- | --- | --- |
| **ALTA_VOLATILITÀ** | ATR > 2× ATR_medio | Tempesta in arrivo |
| **TREND_RIALZISTA** | ADX > 25, EMA veloce > EMA lenta | Vento forte da sud |
| **TREND_RIBASSISTA** | ADX > 25, EMA veloce < EMA lenta | Vento forte da nord |
| **INVERSIONE** | ADX in calo da >40, RSI estremo | Cambio di stagione |
| **LATERALE** | ADX < 20, bande strette | Calma piatta |

> **Analogia:** Il meteorologo ha una **checklist** che segue in ordine. Prima controlla se c'è tempesta (alta volatilità) — se sì, tutti gli altri controlli diventano irrilevanti. Poi controlla la direzione del vento forte (trend). Se il vento era forte e ora sta calando con temperature estreme (RSI), è un cambio di stagione (inversione). Se nessuna condizione speciale è rilevata, è calma piatta (laterale). L'etichetta del regime guida la scelta della strategia: non usi la stessa attrezzatura per navigare nella tempesta e nella bonaccia.

```mermaid
stateDiagram-v2
    [*] --> CHECK_VOL: Features ricevute

    CHECK_VOL --> VOLATILE: ATR > 2× media
    CHECK_VOL --> CHECK_TREND: ATR normale

    CHECK_TREND --> TREND_UP: ADX > 25 AND<br/>EMA_fast > EMA_slow
    CHECK_TREND --> TREND_DOWN: ADX > 25 AND<br/>EMA_fast < EMA_slow
    CHECK_TREND --> CHECK_REV: ADX ≤ 25

    CHECK_REV --> REVERSAL: ADX↓ da >40 AND<br/>RSI estremo
    CHECK_REV --> RANGING: Nessuna condizione

    VOLATILE --> [*]: regime="volatile"
    TREND_UP --> [*]: regime="trending_up"
    TREND_DOWN --> [*]: regime="trending_down"
    REVERSAL --> [*]: regime="reversal"
    RANGING --> [*]: regime="ranging"
```

> **Spiegazione Diagramma:** La macchina a stati mostra l'ordine di priorità dei controlli. Prima si verifica la volatilità (tempesta batte tutto). Poi il trend (vento forte). Poi l'inversione (cambio stagione). Il default è laterale (calma).

### 3.1 Soglie di Classificazione

| Parametro | Valore | Significato |
| --- | --- | --- |
| `ADX_TRENDING_THRESHOLD` | 25 | Sopra = trend presente |
| `ADX_STRONG_TREND` | 40 | Trend molto forte |
| `ADX_RANGING_THRESHOLD` | 20 | Sotto = mercato laterale |
| `ATR_VOLATILITY_MULTIPLIER` | 2.0 | ATR > 2× media = alta volatilità |
| `RSI_OVERBOUGHT` | 70 | Ipercomprato |
| `RSI_OVERSOLD` | 30 | Ipervenduto |

```mermaid
flowchart TB
    subgraph SOGLIE["Soglie del Meteorologo"]
        ADX["ADX<br/><20: Laterale<br/>20-25: Debole<br/>25-40: Forte<br/>>40: Molto forte"]
        RSI["RSI<br/><30: Ipervenduto<br/>30-70: Neutro<br/>>70: Ipercomprato"]
        ATR["ATR Ratio<br/><1: Bassa vol<br/>1-2: Normale<br/>>2: Alta vol"]
    end

    subgraph REGIME["Regime Output"]
        R1["VOLATILE<br/>confidence: 0.85"]
        R2["TRENDING_UP<br/>confidence: 0.78"]
        R3["TRENDING_DOWN<br/>confidence: 0.75"]
        R4["REVERSAL<br/>confidence: 0.65"]
        R5["RANGING<br/>confidence: 0.60"]
    end

    ADX --> R2
    ADX --> R3
    ADX --> R4
    ADX --> R5
    RSI --> R4
    ATR --> R1

    style R1 fill:#ff6b6b,color:#fff
    style R2 fill:#51cf66,color:#fff
    style R3 fill:#ff922b,color:#fff
    style R4 fill:#9775fa,color:#fff
    style R5 fill:#ffd43b,color:#000
```

---

## 4. Il Timoniere: Strategy Router

Il **Timoniere** riceve gli ordini dalla plancia (regime classificato) e manovra la nave sul binario giusto (strategia appropriata). Come uno scambio ferroviario che indirizza i treni sui binari corretti in base alla destinazione.

| Regime | Strategia Attivata | Logica |
| --- | --- | --- |
| `trending_up` | TrendFollowingStrategy | Segui la corrente, cerca conferme BUY |
| `trending_down` | TrendFollowingStrategy | Segui la corrente, cerca conferme SELL |
| `ranging` | MeanReversionStrategy | Compra ai minimi, vendi ai massimi |
| `volatile` | DefensiveStrategy | HOLD sempre — non entrare nella tempesta |
| `default` | DefensiveStrategy | Nel dubbio, fermati |

> **Analogia:** Il capostazione della ferrovia ha una mappa che associa ogni destinazione (regime) a un binario (strategia). Quando arriva un treno (features), guarda l'etichetta della destinazione e aziona lo scambio corretto. Se l'etichetta è sconosciuta o illeggibile, manda il treno sul binario di sicurezza (difensivo) dove resta fermo finché non si chiarisce la situazione.

```mermaid
flowchart TB
    subgraph REGIME_IN["Regime Rilevato"]
        R1["TRENDING_UP"]
        R2["TRENDING_DOWN"]
        R3["RANGING"]
        R4["VOLATILE"]
        R5["Sconosciuto"]
    end

    subgraph ROUTER["Scambio Ferroviario<br/>(RegimeRouter)"]
        MAP["Mappa<br/>Regime → Strategia"]
    end

    subgraph STRATEGIES["Binari (Strategie)"]
        TF["TrendFollowingStrategy<br/>'segui la corrente'"]
        MR["MeanReversionStrategy<br/>'compra basso, vendi alto'"]
        DEF["DefensiveStrategy<br/>'HOLD sempre'"]
    end

    R1 --> MAP
    R2 --> MAP
    R3 --> MAP
    R4 --> MAP
    R5 --> MAP

    MAP -->|"trending_*"| TF
    MAP -->|"ranging"| MR
    MAP -->|"volatile/default"| DEF

    TF -->|"BUY/SELL"| OUT["SignalSuggestion"]
    MR -->|"BUY/SELL"| OUT
    DEF -->|"HOLD"| OUT

    style TF fill:#51cf66,color:#fff
    style MR fill:#4a9eff,color:#fff
    style DEF fill:#ff922b,color:#fff
    style OUT fill:#ffd43b,color:#000
```

> **Spiegazione Diagramma:** I regimi (input) passano attraverso il Router (scambio). TrendFollowing (verde) gestisce i trend. MeanReversion (blu) gestisce i mercati laterali. Defensive (arancione) è il binario di sicurezza. Tutti producono un SignalSuggestion (giallo).

### 4.1 TrendFollowingStrategy — "Il Surfista"

Come un surfista che cavalca l'onda, questa strategia richiede **almeno 3 conferme** che il trend sia reale prima di salirci sopra.

**Indicatori di conferma:**
1. **Incrocio EMA**: EMA veloce > lenta (BUY) o < (SELL)
2. **Prezzo vs SMA(200)**: sopra (BUY) o sotto (SELL) la linea di galleggiamento
3. **Istogramma MACD**: positivo (BUY) o negativo (SELL)
4. **ADX > 25**: la forza del vento è sufficiente

**Calcolo confidenza:** `0.50 + ADX/100` (max 0.90)

```mermaid
flowchart LR
    subgraph CONFIRM["Conferme (min 3)"]
        C1["EMA veloce > lenta?"]
        C2["Prezzo > SMA 200?"]
        C3["MACD hist > 0?"]
        C4["ADX > 25?"]
    end

    subgraph COUNT["Conteggio"]
        BUY_N["BUY: N conferme"]
        SELL_N["SELL: N conferme"]
    end

    subgraph DECISION["Decisione"]
        BUY["BUY<br/>conf = 0.50 + ADX/100"]
        SELL["SELL<br/>conf = 0.50 + ADX/100"]
        HOLD["HOLD<br/>conf = 0.30"]
    end

    C1 --> BUY_N
    C1 --> SELL_N
    C2 --> BUY_N
    C2 --> SELL_N
    C3 --> BUY_N
    C3 --> SELL_N
    C4 --> BUY_N
    C4 --> SELL_N

    BUY_N -->|"≥ 3 e > SELL"| BUY
    SELL_N -->|"≥ 3 e > BUY"| SELL
    BUY_N -->|"< 3"| HOLD
    SELL_N -->|"< 3"| HOLD

    style BUY fill:#51cf66,color:#fff
    style SELL fill:#ff6b6b,color:#fff
    style HOLD fill:#ffd43b,color:#000
```

---

## 5. L'Artigiano: Signal Generator

L'**Artigiano** prende il progetto dell'ingegnere (SignalSuggestion dalla strategia) e costruisce il pezzo finito (TradingSignal) con tutti i dettagli: ID univoco, timestamps, stop-loss, take-profit e metadati per l'audit trail.

| Campo | Origine | Descrizione |
| --- | --- | --- |
| `signal_id` | UUID4 | Identificatore univoco del segnale |
| `symbol` | Input | Strumento (es. "XAU/USD") |
| `direction` | Strategia | BUY, SELL, HOLD |
| `confidence` | Strategia | Decimal [0, 1] |
| `entry_price` | Mercato | Prezzo corrente al momento della generazione |
| `stop_loss` | ATR-based | entry ± ATR × 1.5 |
| `take_profit` | ATR-based | entry ± ATR × 2.5 |
| `risk_reward_ratio` | Calcolato | TP_distance / SL_distance |
| `reasoning` | Strategia | Spiegazione leggibile |
| `timestamp_ms` | Sistema | Quando è stato generato |

> **Analogia:** L'artigiano riceve uno schizzo dal progettista che dice solo "costruisci una sedia" (direzione BUY). L'artigiano aggiunge: numero di serie (UUID), data di fabbricazione (timestamp), altezza dello schienale (stop-loss basato sull'ATR — quanto volatile è il legno), profondità del sedile (take-profit), e un'etichetta che spiega perché questa sedia è stata costruita così (reasoning).

```mermaid
sequenceDiagram
    participant ST as Strategia
    participant SG as Signal Generator
    participant MKT as Mercato
    participant OUT as Output

    ST->>SG: SignalSuggestion<br/>(BUY, 0.72, "3 conferme")

    SG->>MKT: Richiedi prezzo corrente
    MKT-->>SG: 2045.67

    SG->>SG: Genera UUID
    SG->>SG: Calcola SL = 2045.67 - (ATR × 1.5)
    SG->>SG: Calcola TP = 2045.67 + (ATR × 2.5)
    SG->>SG: Calcola R:R = TP_dist / SL_dist

    SG->>OUT: TradingSignal<br/>{<br/>  signal_id: "abc-123",<br/>  direction: BUY,<br/>  confidence: 0.72,<br/>  entry: 2045.67,<br/>  stop_loss: 2041.42,<br/>  take_profit: 2052.75,<br/>  risk_reward: 1.67<br/>}
```

### 5.1 Calcolo Stop-Loss e Take-Profit

I livelli di protezione sono calcolati come multipli dell'ATR (Average True Range):

```
Per BUY:
  Stop-Loss  = entry_price - (ATR × SL_multiplier)  // default 1.5
  Take-Profit = entry_price + (ATR × TP_multiplier) // default 2.5

Per SELL:
  Stop-Loss  = entry_price + (ATR × SL_multiplier)
  Take-Profit = entry_price - (ATR × TP_multiplier)
```

**Esempio con XAU/USD:**
```
entry_price = 2045.67
ATR(14) = 2.83

SL_distance = 2.83 × 1.5 = 4.245
TP_distance = 2.83 × 2.5 = 7.075

Per BUY:
  stop_loss = 2045.67 - 4.245 = 2041.425
  take_profit = 2045.67 + 7.075 = 2052.745
  risk_reward = 7.075 / 4.245 = 1.67
```

---

## 6. Le Reti Neurali: JEPA

**JEPA** (Joint Embedding Predictive Architecture) è il sistema di intelligenza artificiale della nave che impara dai pattern storici per anticipare le condizioni future. A differenza dei modelli generativi che ricostruiscono i dati, JEPA predice lo **stato futuro nello spazio latente** — come un operaio esperto che prevede il prossimo stato della macchina dal suo funzionamento corrente, senza dover smontare ogni pezzo.

| Componente | Input | Output | Architettura |
| --- | --- | --- | --- |
| **JEPAEncoder** | (B, seq, 60) | (B, 128) | Linear → Transformer(2L, 4H) → Pool → Linear |
| **JEPAPredictor** | (B, 128) | (B, 128) | Linear(128→64) → ReLU → Linear(64→128) |
| **JEPAMarketModel** | Sequenza stati | Predizione stato futuro | Encoder + Target Encoder (EMA) + Predictor |

> **Analogia:** JEPA è come un **navigatore esperto** che ha visto migliaia di traversate. Non ha bisogno di analizzare ogni onda singolarmente (ricostruzione). Invece, guarda la "sensazione" generale del mare (embedding latente) e prevede come sarà tra un'ora. Ha un "gemello mentale" (target encoder) che si aggiorna lentamente per non saltare a conclusioni affrettate (EMA momentum). La loss VICReg assicura che le sue previsioni siano **variate** (non tutte uguali), **invarianti** (consistenti), e **decorrelate** (ogni dimensione cattura informazioni diverse).

```mermaid
flowchart TB
    subgraph INPUT["Input Sequenza"]
        SEQ["Market States<br/>(B, seq_len, 60)"]
    end

    subgraph ENCODER["JEPAEncoder"]
        PROJ1["Linear<br/>60 → 128"]
        TRANS["TransformerEncoder<br/>2 layers, 4 heads"]
        POOL["Mean Pooling<br/>temporale"]
        PROJ2["LayerNorm + Linear<br/>128 → 128"]
    end

    subgraph PREDICTOR["JEPAPredictor"]
        P1["Linear 128→64"]
        RELU["ReLU"]
        P2["Linear 64→64"]
        RELU2["ReLU"]
        P3["Linear 64→128"]
    end

    subgraph TARGET["Target Encoder (EMA)"]
        TENC["Encoder clone<br/>momentum update"]
    end

    subgraph LOSS["VICReg Loss"]
        VAR["Variance"]
        INV["Invariance"]
        COV["Covariance"]
    end

    SEQ --> PROJ1
    PROJ1 --> TRANS
    TRANS --> POOL
    POOL --> PROJ2
    PROJ2 --> P1
    P1 --> RELU
    RELU --> P2
    P2 --> RELU2
    RELU2 --> P3

    SEQ --> TENC
    TENC -->|"target embedding"| LOSS
    P3 -->|"predicted embedding"| LOSS

    style SEQ fill:#4a9eff,color:#fff
    style TRANS fill:#9775fa,color:#fff
    style P3 fill:#51cf66,color:#fff
    style TENC fill:#ffd43b,color:#000
    style LOSS fill:#ff922b,color:#fff
```

> **Spiegazione Diagramma:** La sequenza di stati di mercato (blu) passa attraverso l'Encoder con Transformer (viola). Il Predictor (verde) genera l'embedding predetto. Il Target Encoder (giallo) genera l'embedding target con update EMA. La loss VICReg (arancione) confronta le due predizioni.

### 6.1 Dimensioni Architettura

| Parametro | Valore | Descrizione |
| --- | --- | --- |
| `MARKET_DIM` | 60 | Dimensione input (features di mercato) |
| `LATENT_DIM` | 128 | Dimensione spazio latente |
| `PREDICTOR_DIM` | 64 | Dimensione nascosta predictor |
| `N_HEADS` | 4 | Attention heads nel Transformer |
| `N_LAYERS` | 2 | Layer del TransformerEncoder |
| `DROPOUT` | 0.1 | Dropout per regolarizzazione |

---

## 7. L'Archivio di Bordo: Knowledge Systems

L'**Archivio di Bordo** conserva le lezioni apprese dalle battaglie passate. MONEYMAKER mantiene diversi sistemi di knowledge:

| Sistema | Scopo | Storage |
| --- | --- | --- |
| **MarketGraph** | Relazioni tra asset (correlazioni) | In-memory graph |
| **StrategyKnowledge** | Pattern che funzionano per ogni regime | SQLite |
| **BacktestMiner** | Insight estratti da trade storici | PostgreSQL |
| **CorrectionEngine** | Feedback da trade falliti | Redis |

> **Analogia:** Come l'archivio della nave che contiene:
> - **Carte nautiche** (MarketGraph): mostrano dove sono le secche (correlazioni pericolose), i canali navigabili (asset decorrelati), e le correnti (relazioni di lead/lag).
> - **Manuali di manovra** (StrategyKnowledge): "In tempesta, usa questa procedura. In bonaccia, usa quest'altra."
> - **Rapporti di missione** (BacktestMiner): cosa ha funzionato e cosa no nelle traversate passate.
> - **Note del capitano** (CorrectionEngine): errori commessi e come evitarli in futuro.

```mermaid
graph TB
    subgraph KNOWLEDGE["Sistemi di Knowledge"]
        MG["MarketGraph<br/>Correlazioni<br/>Lead/Lag<br/>Clustering"]
        SK["StrategyKnowledge<br/>Pattern per regime<br/>Success rates"]
        BM["BacktestMiner<br/>Trade history<br/>Win/Loss analysis"]
        CE["CorrectionEngine<br/>Feedback loop<br/>Error patterns"]
    end

    subgraph CONSUMERS["Consumatori"]
        ROUTER["Regime Router"]
        VALIDATOR["Signal Validator"]
        SIZER["Position Sizer"]
        COACH["Coaching System"]
    end

    MG -->|"asset relationships"| VALIDATOR
    MG -->|"correlation risk"| SIZER
    SK -->|"optimal params"| ROUTER
    BM -->|"historical context"| ROUTER
    CE -->|"avoid patterns"| VALIDATOR
    CE -->|"learning"| COACH

    style MG fill:#9775fa,color:#fff
    style SK fill:#4a9eff,color:#fff
    style BM fill:#ffd43b,color:#000
    style CE fill:#ff922b,color:#fff
```

> **Spiegazione Diagramma:** I quattro sistemi di knowledge (viola, blu, giallo, arancione) alimentano diversi consumatori. Il MarketGraph informa Validator e Sizer sulle correlazioni. StrategyKnowledge guida il Router sui parametri ottimali. BacktestMiner fornisce contesto storico. CorrectionEngine chiude il loop di apprendimento.

### 7.1 MarketGraph — Relazioni tra Asset

Il MarketGraph mantiene un grafo di relazioni tra asset:

```
Nodi: Asset (XAU/USD, EUR/USD, BTC/USDT, ...)
Archi: Correlazione, Lead/Lag, Cluster membership

Esempio:
  XAU/USD --[corr: -0.65]--> USD Index
  EUR/USD --[leads: 2 bars]--> GBP/USD
  BTC/USDT --[cluster: crypto]--> ETH/USDT
```

**Uso:** Prima di aprire una posizione su EUR/USD, il validator controlla se ci sono già posizioni aperte su asset altamente correlati (GBP/USD, AUD/USD) per evitare sovraesposizione.

### 7.2 Cascade Fallback

Quando il sistema deve prendere una decisione, segue una cascata di fallback:

```
1. ML Model (JEPA/GNN)     → Se disponibile e confidence > 0.7
2. Technical Strategy      → Regime-based strategies
3. Knowledge Base          → Pattern storici
4. Conservative Default    → HOLD
```

---

*Continua nella Parte 3: Sicurezza ed Esecuzione (Safety & Execution)*
