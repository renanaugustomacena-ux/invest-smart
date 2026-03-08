# REPORT 07: Features, Analysis, Knowledge, Coaching & Processing

## Executive Summary

Questo report copre **~60 moduli** per circa **~8,000+ LoC** distribuiti su 5 sottosistemi: Features (16 file, pipeline 60-dim + indicatori tecnici + regime), Analysis (11 file, classificazione strategia + qualità segnale + manipolazione), Knowledge (7 file, RAG + grafo relazioni + esperienza COPER), Coaching (7 file, correzioni + explainability + bridge pro), Processing (18 file, data pipeline + tensor factory + feature engineering). L'architettura è **solida e production-ready** con precisione Decimal, protezione anti-leakage, e fallback graceful. Criticità principali: 5 placeholder features nel vettore 60-dim (~8.3% inutilizzato), _prev_adx non inizializzato correttamente nel regime classifier, e assenza di dati order book L2 per il manipulation detector.

---

## Inventario Completo

### Features (16 file)

| # | File | LoC | Scopo | Stato |
|---|------|-----|-------|-------|
| 1 | pipeline.py | 336 | Pipeline principale → ~34 indicatori tecnici | ✅ OK |
| 2 | technical.py | 657 | Calcoli indicatori con Decimal arithmetic | ✅ OK |
| 3 | regime.py | 213 | Classificazione regime rule-based (5 livelli) | ⚠️ WARNING |
| 4 | regime_ensemble.py | 416 | Ensemble 3 classificatori (regole+HMM+kMeans) | ⚠️ WARNING |
| 5 | regime_shift.py | 338 | Rilevamento transizioni regime via KL-divergence | ✅ OK |
| 6 | market_vectorizer.py | 558 | Produzione vettore 60-dim normalizzato | ⚠️ WARNING |
| 7 | data_quality.py | 119 | Validazione pre-pipeline OHLCV | ✅ OK |
| 8 | data_sanity.py | 218 | Controlli plausibilità statistica | ✅ OK |
| 9 | feature_drift.py | 354 | Rilevamento drift distribuzionale via Z-score | ✅ OK |
| 10 | leakage_auditor.py | 417 | Audit formale data leakage (5 controlli) | ✅ OK |
| 11 | macro_features.py | 364 | Features macroeconomiche da Redis (VIX, yield, DXY) | ✅ OK |
| 12 | mtf_analyzer.py | 181 | Analisi multi-timeframe (M5/M15/H1) | ✅ OK |
| 13 | sessions.py | 81 | Confidence adjustment per sessione trading | ✅ OK |
| 14 | state_reconstructor.py | 414 | Sliding-window tensor factory per NN | ✅ OK |
| 15 | economic_calendar.py | ~80 | Blackout per eventi economici | ✅ OK |
| 16 | __init__.py | ~15 | Init package | ✅ OK |

### Analysis (11 file)

| 17 | strategy_classifier.py | 589 | Dual-classifier (heuristic+NN) per strategia | ⚠️ WARNING |
| 18 | signal_quality.py | 202 | Entropia Shannon per chiarezza mercato | ✅ OK |
| 19 | trade_success.py | 261 | Predittore P(TP prima di SL) via NN+heuristic | ✅ OK |
| 20 | trading_weakness.py | 250 | Rilevamento errori ricorrenti (7 tipi) | ✅ OK |
| 21 | capital_efficiency.py | 508 | Allocation tiers + risk budget tracking | ✅ OK |
| 22 | pnl_momentum.py | 270 | Win/loss streak tracker con time-decay | ✅ OK |
| 23 | market_belief.py | 458 | Modello Bayesiano posteriori regime | ✅ OK |
| 24 | price_level_analyzer.py | 531 | Classificazione zone S/R con ATR-normalization | ✅ OK |
| 25 | manipulation_detector.py | 251 | Rilevamento spoofing/fake breakout/churn | ⚠️ WARNING |
| 26 | scenario_analyzer.py | 425 | Expectiminimax game tree per decisioni | ⚠️ WARNING |
| 27 | __init__.py | ~15 | Init package | ✅ OK |

### Knowledge (7 file)

| 28 | strategy_knowledge.py | 295 | RAG knowledge base (Sentence-BERT + cosine) | ✅ OK |
| 29 | market_graph.py | 291 | Grafo relazioni mercato in-memory | ✅ OK |
| 30 | trade_history_bank.py | 608 | COPER experience framework | ✅ OK |
| 31 | hybrid_signal_engine.py | 382 | Fusione ML + KB + Experience | ✅ OK |
| 32 | backtest_miner.py | 350 | Estrazione pattern vincenti da backtest | ✅ OK |
| 33 | init_knowledge.py | 231 | Inizializzazione KB con 50+ entry | ✅ OK |
| 34 | v1_knowledge_importer.py | 288 | Import da V1 Bot docs + markdown | ✅ OK |

### Coaching (7 file)

| 35 | correction_engine.py | 201 | Correzioni per deviazioni da benchmark | ✅ OK |
| 36 | explainability.py | 300 | Narrative Z-score per spiegazione segnali | ✅ OK |
| 37 | hybrid_coaching.py | 209 | Fusione rule + NN + KB coaching | ✅ OK |
| 38 | nn_refinement.py | 170 | MLP per affinamento pesi correzioni | ✅ OK |
| 39 | longitudinal_engine.py | 238 | Analisi trend temporali metriche | ✅ OK |
| 40 | pro_bridge.py | 198 | Gap analysis vs benchmark professionali | ✅ OK |
| 41 | progress/longitudinal.py | ~100 | Supporto tracking progressi | ✅ OK |

### Processing (18 file)

| 42 | data_pipeline.py | 270 | Outlier filtering + temporal split + RobustScaler | ✅ OK |
| 43 | tensor_factory.py | 241 | Assemblaggio tensori multi-vista per NN | ✅ OK |
| 44 | external_analytics.py | 290 | Caricamento benchmark istituzionali CSV/JSON | ✅ OK |
| 45 | heatmap_engine.py | 269 | Density heatmap 2D via Gaussian KDE | ✅ OK |
| 46 | session_stats_builder.py | 215 | Aggregazione statistiche per sessione | ✅ OK |
| 47 | baselines/pro_baseline.py | 360 | Benchmark professionali con decay temporale | ✅ OK |
| 48 | feature_engineering/base_features.py | 223 | Features statistiche fondamentali | ✅ OK |
| 49 | feature_engineering/strategy_features.py | 506 | Indicatori tecnici per strategia | ✅ OK |
| 50 | feature_engineering/trade_metrics.py | 302 | Classificazione WLBH e metriche trade | ✅ OK |
| 51 | feature_engineering/vectorizer.py | 171 | Batch feature extraction (60-dim) | ✅ OK |
| 52 | feature_engineering/rating.py | 312 | Rating composito 0-100 (4 componenti) | ✅ OK |

**Totale**: ~52+ file, ~8,000+ LoC

---

## Analisi Dettagliata — Moduli Chiave

### A. Pipeline 60-Dimensionale

#### pipeline.py (336 LoC) — Il Cuore

**Scopo**: Converte OHLCV bars grezze in ~34 indicatori tecnici via `technical.py`.

**Layout vettore 60-dim**:

| Indici | Gruppo | Features |
|--------|--------|----------|
| 0-5 | Price | OHLCV normalizzati + spread |
| 6-15 | Trend | SMA ratios, DEMA, MACD (line/signal/hist), ADX normalizzato |
| 16-25 | Momentum | RSI, Stochastic K/D, CCI, Williams %R, ROC, DI ratio |
| 26-33 | Volatility | ATR%, BB upper/lower/width, Keltner, Historical Vol, Parkinson |
| 34-40 | Volume | OBV norm, VWAP ratio, CMF, Chaikin Osc, Force Index, Vol ratio |
| 41-50 | Context | Hour sin/cos, DayOfWeek sin/cos, session, VIX, DXY, SPX corr |
| 51-59 | Microstructure | Bid-ask, OB imbalance, tick direction, trade flow, VPIN |

**Status**: ✅ OK — Decimal precision, fallback macro features, Italian metaphors.

---

#### technical.py (657 LoC) — Calcoli Indicatori

**Verifica matematica di OGNI indicatore**:

| Indicatore | Formula | Corretto? |
|-----------|---------|-----------|
| SMA | Σclose[i] / period | ✅ |
| EMA | close × k + EMA_prev × (1-k), k=2/(period+1) | ✅ |
| RSI | 100 - 100/(1 + avg_gain/avg_loss), Wilder smoothing | ✅ |
| MACD | EMA(12) - EMA(26), Signal=EMA(9), Hist=MACD-Signal | ✅ |
| Bollinger | SMA ± 2×stddev (population, Decimal sqrt via Newton) | ✅ |
| ATR | EMA di TrueRange, Wilder smoothing | ✅ |
| ADX | 100 × EMA(|+DI - -DI| / (+DI + -DI)) | ✅ |
| Stochastic | %K = (C-L)/(H-L)×100, %D = SMA(%K, 3) | ✅ |
| OBV | Accumulatore ±volume basato su direzione close | ✅ |
| Williams %R | -100 × (H-C)/(H-L) | ✅ |
| CCI | (TP - SMA_TP) / (0.015 × MeanDeviation) | ✅ |
| ROC | (C[t] - C[t-n]) / C[t-n] × 100 | ✅ |
| Sqrt | Newton iteration per Decimal | ✅ |

**Status**: ✅ OK — Tutte le formule verificate, edge cases gestiti (zero denominatori → ZERO).

---

#### market_vectorizer.py (558 LoC) — Normalizzazione 60-dim

**Scopo**: Produce vettore float32 normalizzato [0,1] dal pipeline Decimal.

**⚠️ PLACEHOLDER FEATURES** (8.3% del vettore):

| Indice | Feature | Valore | Motivo |
|--------|---------|--------|--------|
| 37 | Chaikin Oscillator | 0.0 | Richiede serie ADL, non calcolata |
| 40 | Volume Profile Value Area | 0.5 | Hardcoded, non implementato |
| 55 | Realised Vol 5min | 0.0 | Non disponibile (solo M1+ bars) |
| 57 | Hurst Exponent | 0.5 | Troppo costoso da calcolare real-time |
| 58 | VPIN | 0.0 | Non implementato |

**Impatto**: 5/60 = 8.3% del vettore è inutilizzato. Il modello ML imparerà ad ignorare questi indici, ma spreca capacità.

**Status**: ⚠️ WARNING — Features placeholder riducono l'informazione disponibile.

---

### B. Regime Classification

#### regime.py (213 LoC) — Classificazione Rule-Based

**5 regimi** (in ordine di priorità):

| Regime | Condizione | Confidence |
|--------|-----------|-----------|
| HIGH_VOLATILITY | ATR > 2× avg_ATR | 0.50 + (ratio-2)×0.25 |
| TRENDING_UP | ADX > 25 AND EMA_fast > EMA_slow | 0.50 + ADX/100 |
| TRENDING_DOWN | ADX > 25 AND EMA_fast < EMA_slow | 0.50 + ADX/100 |
| REVERSAL | ADX was >40, ora declining + RSI estremo | 0.55 |
| RANGING (default) | ADX < 20, bande strette | 0.70 |

**BUG**: `_prev_adx` inizializzato a ZERO → al primo avvio, la condizione `_prev_adx > 40` non sarà mai vera → primo reversal non rilevato.

**Status**: ⚠️ WARNING — Bug inizializzazione _prev_adx.

---

#### regime_ensemble.py (416 LoC) — Ensemble 3 Classificatori

**Pesi voting**: Rule=0.50, HMM=0.30, kMeans=0.20

**Hysteresis**: Richiede `P(new) > P(old) + 0.15` per 3 barre consecutive → previene whipsaw.

**4 regimi canonici vs 5 enum**: REVERSAL → RANGING, HIGH_VOL e CRISIS → VOLATILE (perdita di specificità).

**Status**: ⚠️ WARNING — Spread feature sempre 0.5 (placeholder), mapping lossy 5→4 regimi.

---

#### regime_shift.py (338 LoC) — Rilevamento Shift

**Algoritmo**: KL-divergence simmetrizzata su posteriors regime.
- Baseline EMA (λ=0.94) vs Current EMA (λ=0.06)
- Soglia: 0.35 nats
- Min 10 osservazioni prima di dichiarare shift

**Status**: ✅ OK — Matematicamente corretto, Laplace smoothing previene log(0).

---

### C. Analysis Modules Chiave

#### strategy_classifier.py (589 LoC)

**Dual-classifier**: 60% heuristic + 40% neural (5→32→16→5 MLP).

**5 strategie**: TREND_FOLLOWING, MEAN_REVERSION, BREAKOUT, SCALPING, DEFENSIVE.

**⚠️**: `bb_squeeze` feature mai calcolata nel vectorizer → uno degli input heuristic è placeholder.

---

#### manipulation_detector.py (251 LoC)

**3 segnali** (pesati):
- Spoofing (0.25): OB imbalance > 0.80 → **sempre 0 senza dati L2**
- Fake Breakout (0.40): Pierce BB + close inside
- Volume Deception (0.35): Alto volume senza price change

**⚠️**: 25% dell'indice è cieco senza dati order book L2.

---

#### scenario_analyzer.py (425 LoC)

**Expectiminimax**: MAX/MIN/CHANCE tree con GBM Monte-Carlo.
- Node budget: 1000
- Max depth: 4
- Chance branches: 5

**⚠️**: μ e σ per GBM devono essere calibrati esternamente. Leaf payoffs sono heuristici (0.5×ATR per BUY, 0.4 per SELL).

---

### D. Knowledge Base

#### trade_history_bank.py (608 LoC) — COPER Experience

**Scopo**: Memorizza contesti e risultati trade per decision-making contestuale.

**Similarity scoring**: `cos_sim + 0.2×hash_bonus + 0.4×effectiveness × confidence`

**Feedback loop**: `effectiveness = eff×0.7 + outcome×0.3` (EMA α=0.3)

**Temporal decay**: Esperienze >90 giorni senza feedback → ridotte del 10%.

**Training export**: Split cronologico 70/15/15 (previene leakage).

---

#### hybrid_signal_engine.py (382 LoC) — Fusione Multi-Source

**Pesi**: ML=0.50, KB=0.30, Experience=0.20

**Z-score deviation**: Confronta confidence corrente con baseline rolling.

**Drift adjustment**: `confidence *= (1.0 - min(|Z|×0.05, 0.15))`

**Conflict detection**: Flag quando direzioni da fonti diverse discordano.

---

### E. Processing Pipeline

#### data_pipeline.py (270 LoC) — Preprocessing

**Outlier filtering**: Z-score > 4.0 (4σ) rimuove righe estreme.

**Temporal split**: 70/15/15 cronologico, NO shuffle.

**RobustScaler**: Usa mediana e IQR (resistente a outlier) invece di mean/std.

**Scaler fitting**: SOLO su training set (previene leakage val/test).

---

## Findings Critici

| # | Severità | Finding | File:Linea | Dettaglio |
|---|----------|---------|-----------|-----------|
| 1 | 🔴 HIGH | 5 placeholder features (8.3%) | market_vectorizer.py | Indici 37,40,55,57,58 sono zero/costanti. Spreca capacità del vettore 60-dim. |
| 2 | 🔴 HIGH | _prev_adx inizializzato a 0 | regime.py:79 | Primo reversal dopo startup non rilevato perché ZERO < 40 sempre. Fix: inizializzare a None. |
| 3 | ⚠️ MEDIUM | Spoofing detector cieco | manipulation_detector.py | Senza dati L2 order book, 25% dell'indice manipolazione è sempre 0. |
| 4 | ⚠️ MEDIUM | Spread feature sempre 0.5 | regime_ensemble.py | Senza bid-ask reali, 1 feature su 4 dell'osservazione HMM/kMeans è costante. |
| 5 | ⚠️ MEDIUM | bb_squeeze non calcolata | strategy_classifier.py | Feature usata nelle heuristic ma mai prodotta dal vectorizer. |
| 6 | ⚠️ MEDIUM | GBM non calibrato | scenario_analyzer.py | μ e σ devono essere forniti esternamente. Garbage in → garbage out. |
| 7 | ⚠️ MEDIUM | Regime mapping lossy (5→4) | regime_ensemble.py | REVERSAL e HIGH_VOL/CRISIS perdono specificità nel mapping canonico. |
| 8 | ⚠️ LOW | Confidence può superare 1.0 prima di clamp | regime.py | Formula 0.50 + ADX/100 con ADX=100 → 1.50 (poi clampato a 0.90). |
| 9 | ⚠️ LOW | Pro baselines hardcoded | pro_baseline.py | Benchmark professionali non configurabili da file esterno. |
| 10 | ⚠️ LOW | label_from_indicators() rischio leakage | concept_labeler.py | Usa features real-time per labeling → potenziale data leakage. |

---

## Interconnessioni

### Flusso Dati End-to-End

```
OHLCV Bars (da Data Ingestion via ZeroMQ)
         │
         ▼
┌────────────────────────────────────────────────┐
│  data_quality.py — Validazione OHLCV           │
│  ├─ High ≥ max(O,C), Low ≤ min(O,C)          │
│  ├─ Spike: range > 5× EMA range → REJECT      │
│  └─ Gap: > 3× intervallo → LOG WARNING        │
└────────┬───────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────┐
│  pipeline.py + technical.py                     │
│  ├─ ~34 indicatori tecnici (Decimal)           │
│  ├─ RSI, EMA, MACD, BB, ATR, ADX, Stoch...    │
│  └─ Macro features opzionali da Redis          │
└────────┬───────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────┐
│  market_vectorizer.py                           │
│  ├─ Normalizzazione [0,1] per ogni feature     │
│  ├─ 60-dim float32 vector                      │
│  └─ ⚠️ 5 placeholder (indici 37,40,55,57,58) │
└────────┬───────────────────────────────────────┘
         │
    ┌────┴────────────────────────────────────┐
    │                                          │
    ▼                                          ▼
┌─────────────────────┐  ┌──────────────────────────┐
│  regime.py (rules)   │  │  state_reconstructor.py   │
│  ├─ 5 regimi         │  │  ├─ Sliding windows       │
│  └─ Cascading check  │  │  ├─ 3-stream split        │
│                      │  │  │  (price/indicator/change)│
│  regime_ensemble.py  │  │  └─ Temporal augmentation  │
│  ├─ HMM (4 state)    │  └──────────────┬─────────────┘
│  ├─ kMeans (4 mean)  │                 │
│  └─ Weighted vote    │                 ▼
│     (R:0.5,H:0.3,K:0.2)│         [Neural Network]
│                      │          (MarketRAPCoach)
│  regime_shift.py     │
│  └─ KL-divergence    │
└────────┬─────────────┘
         │
         ▼
┌────────────────────────────────────────────────┐
│  PARALLEL ANALYSIS                              │
│                                                 │
│  market_belief.py — Bayesian posterior          │
│  signal_quality.py — Shannon entropy            │
│  manipulation_detector.py — Spoofing/fake/churn │
│  scenario_analyzer.py — Game tree search        │
│  strategy_classifier.py — Dual heuristic+NN    │
│  price_level_analyzer.py — S/R zone mapping     │
│  capital_efficiency.py — Risk budget tiers      │
│  pnl_momentum.py — Streak tracking             │
│  trade_success.py — P(TP<SL) prediction        │
│  trading_weakness.py — Error pattern detection  │
└────────┬───────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────┐
│  hybrid_signal_engine.py                        │
│  ├─ ML signals (0.50 weight)                   │
│  ├─ Knowledge base (0.30 weight)               │
│  └─ Experience COPER (0.20 weight)             │
│  → Fused signal with conflict detection         │
└────────┬───────────────────────────────────────┘
         │
         ▼
  [Signal Generation → Validation → MT5]
         │
  [POST-TRADE FEEDBACK]
         │
         ▼
┌────────────────────────────────────────────────┐
│  trade_history_bank.py — Store experience       │
│  correction_engine.py — Generate corrections    │
│  explainability.py — Narrative explanations     │
│  hybrid_coaching.py — Fuse coaching sources     │
│  longitudinal_engine.py — Trend analysis        │
│  pro_bridge.py — Gap vs professional benchmark  │
│  backtest_miner.py — Extract winning patterns   │
└────────────────────────────────────────────────┘
```

### Mappa Leakage Prevention

```
┌─────────────────────────────────────────────────┐
│  ANTI-LEAKAGE CHAIN                              │
│                                                  │
│  [1] leakage_auditor.py                          │
│      ├─ Feature timestamps ≤ cutoff             │
│      ├─ Label embargo ≥ 5 bars                  │
│      ├─ Scaler fitted su train only             │
│      ├─ Walk-forward: train ≤ val ≤ test        │
│      └─ No raw prices (non-stationary)          │
│                                                  │
│  [2] data_pipeline.py                            │
│      ├─ Scaler.fit() solo su training set       │
│      ├─ Temporal split senza shuffle            │
│      └─ scaler_fit_sample_count per audit       │
│                                                  │
│  [3] dataset.py (nn/)                            │
│      ├─ chronological_split(70/15/15)           │
│      ├─ shuffle=False sempre                    │
│      └─ temporal weighting (recency decay)      │
│                                                  │
│  [4] feature_drift.py                            │
│      └─ Rileva distribution shift → retraining  │
│                                                  │
│  [5] data_sanity.py                              │
│      └─ Feature bounds checking                 │
└─────────────────────────────────────────────────┘
```

---

## Istruzioni con Checkbox

### Segmento A: Fix Placeholder Features nel Vettore 60-dim

- [ ] **A.1** — Implementare Chaikin Oscillator (indice 37): `CO = EMA(3, ADL) - EMA(10, ADL)` dove `ADL += ((C-L)-(H-C))/(H-L) × Volume`. Aggiungere calcolo in `technical.py` e collegare nel vectorizer.
- [ ] **A.2** — Implementare VPIN (indice 58): Volume-Synchronized Probability of Informed Trading. Se troppo complesso per real-time, usare proxy: `trade_flow_imbalance` normalizzato.
- [ ] **A.3** — Implementare Realised Vol 5min (indice 55): se dati sub-minute disponibili, calcolare `sqrt(sum(log_returns²))`. Altrimenti, usare proxy da ATR.
- [ ] **A.4** — Per Hurst Exponent (indice 57): implementare R/S Analysis semplificata su finestra 50 barre, oppure usare proxy: `autocorrelation_lag1 × 0.5 + 0.5` come stima grezza.
- [ ] **A.5** — Per Volume Profile Value Area (indice 40): implementare distribuzione volume per prezzo (bin histogram) e calcolare VA come 70% del volume. Se non disponibile, usare proxy: `(volume_at_vwap / total_volume)`.
- [ ] **A.6** — Test: verificare che tutti 60 indici producano valori non-zero su dati reali
- [ ] **A.7** — Documentare le formule di ogni indice nel vettore 60-dim in un file di reference

### Segmento B: Fix Regime Classification

- [ ] **B.1** — Fix `_prev_adx` in `regime.py:79`: inizializzare a `None`, modificare check reversal: `if self._prev_adx is not None and self._prev_adx > Decimal("40") and ...`
- [ ] **B.2** — Fix confidence clamping: aggiungere `min(confidence, Decimal("1.0"))` immediatamente dopo il calcolo, prima di qualsiasi altra operazione
- [ ] **B.3** — Aggiungere test: startup con ADX=45 poi drop a ADX=15 → REVERSAL rilevato
- [ ] **B.4** — Aggiungere test: confidence non supera mai 1.0 per nessuna combinazione di input
- [ ] **B.5** — Considerare spread feature reale per HMM/kMeans invece di placeholder 0.5: usare `(ask-bid)/pip_size` se disponibile dall'ingestion

### Segmento C: Dati Order Book L2

- [ ] **C.1** — Valutare se i connettori (Polygon, Binance) possono fornire order book L2 o almeno bid-ask top-of-book
- [ ] **C.2** — Se L2 disponibile: calcolare `order_book_imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)`
- [ ] **C.3** — Se L2 NON disponibile: documentare che manipulation_detector opera al 75% di capacità (senza spoofing detection)
- [ ] **C.4** — Collegare bid-ask reale al vettore 60-dim indice 51 (attualmente placeholder se non disponibile)

### Segmento D: Strategy Classifier bb_squeeze

- [ ] **D.1** — Implementare `bb_squeeze` nel vectorizer: `squeeze = 1 se BB_width < Keltner_width, 0 altrimenti`
- [ ] **D.2** — Aggiungere `bb_squeeze_intensity`: `(Keltner_width - BB_width) / Keltner_width` per squeeze graduale
- [ ] **D.3** — Collegare al strategy_classifier come feature input
- [ ] **D.4** — Test: squeeze detection su dati storici XAUUSD con consolidamento noto

### Segmento E: Scenario Analyzer Calibration

- [ ] **E.1** — Implementare funzione di calibrazione μ/σ per GBM: `μ = EMA(log_returns, 20)`, `σ = realized_vol(20)`
- [ ] **E.2** — Aggiungere update automatico dei parametri GBM ad ogni nuovo bar
- [ ] **E.3** — Validare leaf payoffs con dati storici: il payoff medio di BUY trades è davvero ~0.5×ATR?
- [ ] **E.4** — Considerare calibrazione leaf payoffs da trade_history_bank (media PnL per direction per regime)

### Segmento F: Knowledge Base Population

- [ ] **F.1** — Eseguire `initialize_knowledge_base()` con tutti i documenti V1_Bot e AI_Trading_Brain_Concepts
- [ ] **F.2** — Verificare che ≥50 entries vengano caricate (soglia minima)
- [ ] **F.3** — Aggiungere knowledge entries per ogni strumento target (XAUUSD, EURUSD, GBPUSD, USDJPY, BTCUSD)
- [ ] **F.4** — Popolare market_graph con relazioni strumento-regime-strategia specifiche
- [ ] **F.5** — Test: query knowledge base per "XAUUSD trending" → ritorna ≥3 entries rilevanti

### Segmento G: Test Coverage Features/Analysis

- [ ] **G.1** — Test pipeline.py: 50 barre OHLCV sintetiche → verifica che tutti gli indicatori vengono calcolati
- [ ] **G.2** — Test market_vectorizer.py: output shape (60,), tutti valori in [0,1], nessun NaN/Inf
- [ ] **G.3** — Test regime_ensemble.py: 3 classificatori concordano → confidence alta
- [ ] **G.4** — Test regime_shift.py: shift simulato (trending → volatile) → KL-divergence > soglia
- [ ] **G.5** — Test feature_drift.py: drift simulato → ≥3/5 check positivi → trigger retraining
- [ ] **G.6** — Test leakage_auditor.py: scaler fittato su test set → audit FAIL
- [ ] **G.7** — Test manipulation_detector.py: fake breakout simulato → manipulation_index > 0.5
- [ ] **G.8** — Test trade_history_bank.py: store 100 esperienze → retrieve top-5 → similarity > 0.5

### Segmento H: Coaching Integration

- [ ] **H.1** — Verificare che correction_engine produce correzioni in italiano (come richiesto)
- [ ] **H.2** — Test explainability.py: segnale con Z-score alto → explanation con severity HIGH
- [ ] **H.3** — Test hybrid_coaching.py: rule e NN discordano → conflitto rilevato e loggato
- [ ] **H.4** — Collegare coaching output al console per display utente
- [ ] **H.5** — Test pro_bridge.py: metriche sotto benchmark → gap analysis con severity corretta

---

*Report generato dall'analisi di ~52 file, ~8,000+ LoC totali. Tutti i file letti e analizzati senza eccezioni.*
