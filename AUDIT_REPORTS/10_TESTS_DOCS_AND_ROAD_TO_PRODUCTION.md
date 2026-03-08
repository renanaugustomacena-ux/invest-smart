# REPORT 10: Test Suite, Documentazione e Road to Production

## Executive Summary

MONEYMAKER dispone di **353 test Python passing** (100% pass rate) concentrati nel servizio algo-engine,
**9 test Go** per data-ingestion e **5 test** per mt5-bridge. Il servizio ml-training ha **1 file test
con 6 casi ma NON runnabile** (ImportError per modulo non installabile). Console, external-data e
monitoring hanno **zero test**. La documentazione è vasta (10.646 LoC in 14 documenti principali,
175 concept docs, 12 skill analysis, 14 V1_Bot blueprint) ma contiene **discrepanze critiche** con
il codice reale — la GUIDE/03 sottostima safety (20% vs ~90% reale) e monitoring (dice "nessuna
dashboard" ma 5 JSON esistono). I 20 MONEYMAKER_IMPLEMENTATION_DOCS sono stati **rimossi dal repository**
(probabilmente nel force-push del 2026-03-02). Il sistema è pronto per paper trading rule-based ma
richiede 25+ azioni per raggiungere la produzione ML completa.

---

## 1. Inventario Test Completo

### 1.1 algo-engine — 353 test (100% pass, 4.257 LoC)

#### Unit Test (19 file, 245 test)

| File | Test | LoC | Moduli Coperti |
|------|------|-----|----------------|
| `test_technical.py` | 32 | ~200 | RSI, EMA, BB, ATR, MACD, Stochastic |
| `test_technical_extended.py` | 31 | ~200 | Indicatori estesi, edge case |
| `test_ml_proxy.py` | 29 | ~250 | MLProxy, fallback, timeout, retry |
| `test_zmq_adapter.py` | 17 | ~150 | ZMQ subscription, topic filtering |
| `test_signal_validator.py` | 15 | ~200 | 11 controlli di validazione |
| `test_portfolio.py` | 13 | ~150 | Equity tracking, margin, daily reset |
| `test_strategy_base.py` | 12 | ~120 | BaseStrategy interface |
| `test_regime.py` | 11 | ~120 | 5 regimi, classificazione |
| `test_pipeline.py` | 10 | ~120 | Feature engineering pipeline 60-dim |
| `test_mean_reversion.py` | 9 | ~100 | BB + RSI + Stochastic strategy |
| `test_trend_following.py` | 9 | ~100 | EMA cross + ADX strategy |
| `test_signal_generator.py` | 9 | ~120 | Signal generation, confidence |
| `test_spiral_protection.py` | 9 | ~100 | Spiral + DrawdownEnforcer |
| `test_grpc_client.py` | 8 | ~100 | gRPC client, connection, timeout |
| `test_position_sizer.py` | 8 | ~100 | Drawdown scaling, min/max lots |
| `test_build_router.py` | 6 | ~80 | Strategy routing logic |
| `test_defensive.py` | 6 | ~80 | DefensiveStrategy (HOLD) |
| `test_kill_switch.py` | 6 | ~80 | Redis kill switch, daily reset |
| `test_regime_router.py` | 5 | ~70 | Regime → Strategy mapping |

#### Brain Verification (12 file, 89 test)

| File | Test | Moduli Coperti |
|------|------|----------------|
| `test_e2e_cascade.py` | 18 | E2E cascade 4-mode pipeline |
| `test_coaching.py` | 11 | Pedagogy, correction engine |
| `test_integrity.py` | 11 | Cross-module contract integrity |
| `test_full_pipeline.py` | 10 | Feature → Signal pipeline |
| `test_cascade.py` | 7 | CascadeOrchestrator mode selection |
| `test_foundational.py` | 6 | Import, init, basic contracts |
| `test_storage.py` | 7 | Model persistence, checkpoints |
| `test_trading_skills.py` | 5 | Strategy-specific skills |
| `test_pedagogy.py` | 4 | MarketPedagogy layer |
| `test_strategy.py` | 4 | MarketStrategy MoE layer |
| `test_memory.py` | 3 | MarketMemory layer |
| `test_perception.py` | 3 | MarketPerception layer |

#### Integration Test (2 file, 8 test)

| File | Test | Moduli Coperti |
|------|------|----------------|
| `test_full_pipeline.py` | 5 | Pipeline completa tick → signal |
| `test_safety_e2e.py` | 3 | Kill switch + spiral + sizer E2E |

#### Architecture Test (1 file, 11 test)

| File | Test | Moduli Coperti |
|------|------|----------------|
| `test_architecture.py` | 11 | Forward pass shapes, METADATA_DIM=60, tutti i layer NN |

### 1.2 data-ingestion — 9 test Go (211 LoC)

| File | Test | Moduli Coperti |
|------|------|----------------|
| `aggregator_test.go` | 9 | Aggregazione OHLCV M1/M5/M15/H1 |

**Stato**: Solo l'aggregator è testato. Connettori (Polygon, Binance), normalizer, publisher, dbwriter: **zero test**.

### 1.3 mt5-bridge — 5 test Python (150 LoC)

| File | Test | Moduli Coperti |
|------|------|----------------|
| `test_grpc_servicer.py` | 5 | gRPC servicer, request handling |

**Stato**: Solo il gRPC servicer è testato. OrderManager, PositionTracker, MT5Connector: **zero test**.

### 1.4 ml-training — 6 test (55 LoC, NON ESEGUIBILI)

| File | Test | Stato |
|------|------|-------|
| `test_training_cycle.py` | 6 | **ERRORE**: `ModuleNotFoundError: No module named 'ml_training'` |

**Causa**: Il servizio ml-training non ha un `pyproject.toml` con `[tool.pytest.ini_options]` configurato per risolvere il pacchetto, oppure manca l'installazione in dev mode (`pip install -e .`).

### 1.5 Servizi SENZA Test

| Servizio | File Sorgente | Test | Note |
|----------|--------------|------|------|
| console | `moneymaker_console.py` (1 file) | 0 | TUI interattiva, 15 categorie di comandi |
| external-data | 3+ provider Python | 0 | CBOE, CFTC, FRED data providers |
| monitoring | Config/provisioning | 0 | Non applicabile (infra config) |

---

## 2. Copertura Test — Analisi dei Gap

### 2.1 Mappa di Copertura per Modulo

```
algo-engine/
├── main.py ................................ ❌ ZERO test (entry point)
├── config.py .............................. ✅ Indiretto via conftest
├── orchestrator/ .......................... ✅ test_cascade (7) + test_e2e_cascade (18)
├── features/
│   ├── pipeline.py ........................ ✅ test_pipeline (10)
│   ├── technical.py ....................... ✅ test_technical (32+31)
│   ├── regime*.py ......................... ✅ test_regime (11) + test_regime_router (5)
│   ├── data_quality.py .................... ❌ ZERO test
│   ├── data_sanity.py ..................... ❌ ZERO test
│   ├── feature_drift.py ................... ❌ ZERO test
│   ├── leakage_auditor.py ................. ❌ ZERO test
│   ├── regime_shift.py .................... ❌ ZERO test
│   ├── sessions.py ........................ ❌ ZERO test
│   ├── economic_calendar.py ............... ❌ ZERO test
│   ├── macro_features.py .................. ❌ ZERO test
│   ├── mtf_analyzer.py .................... ❌ ZERO test
│   └── state_reconstructor.py ............. ❌ ZERO test
├── strategies/
│   ├── trend_following.py ................. ✅ test_trend_following (9)
│   ├── mean_reversion.py .................. ✅ test_mean_reversion (9)
│   ├── defensive.py ....................... ✅ test_defensive (6)
│   ├── ml_proxy.py ........................ ✅ test_ml_proxy (29)
│   └── regime_router.py ................... ✅ test_regime_router (5)
├── signals/
│   ├── generator.py ....................... ✅ test_signal_generator (9)
│   ├── validator.py ....................... ✅ test_signal_validator (15)
│   ├── signal_router.py ................... ❌ ZERO test
│   ├── position_sizer.py .................. ✅ test_position_sizer (8)
│   ├── spiral_protection.py ............... ✅ test_spiral_protection (9)
│   └── kill_switch.py ..................... ✅ test_kill_switch (6)
├── nn/
│   ├── MarketPerception ................... ✅ test_perception (3) + test_architecture
│   ├── MarketMemory ....................... ✅ test_memory (3) + test_architecture
│   ├── MarketStrategy ..................... ✅ test_strategy (4) + test_architecture
│   ├── MarketPedagogy ..................... ✅ test_pedagogy (4) + test_architecture
│   ├── MarketRAPCoach ..................... ✅ test_architecture (11)
│   ├── InferenceEngine .................... ✅ test_architecture (indiretto)
│   ├── training_orchestrator.py ........... ❌ ZERO test (STUB)
│   ├── model_evaluator.py ................. ❌ ZERO test
│   ├── retraining_trigger.py .............. ❌ ZERO test
│   ├── jepa_market.py ..................... ❌ ZERO test
│   ├── concept_labeler.py ................. ❌ ZERO test
│   ├── losses.py .......................... ❌ ZERO test
│   ├── dataset.py ......................... ❌ ZERO test
│   ├── optimizer_factory.py ............... ❌ ZERO test
│   ├── hflayers.py ........................ ❌ ZERO test
│   └── superposition.py ................... ❌ ZERO test
├── analysis/ (10 file) .................... ❌ ZERO test per TUTTI
├── knowledge/ (7 file) .................... ❌ ZERO test per TUTTI
├── coaching/ (7 file) ..................... ✅ test_coaching (11, parziale)
├── processing/ (13 file) .................. ❌ ZERO test per TUTTI
├── services/ .............................. ❌ ZERO test
├── observability/ ......................... ❌ ZERO test
└── storage/ ............................... ✅ test_storage (7)

data-ingestion/
├── connectors/ (Polygon, Binance, Mock) ... ❌ ZERO test
├── normalizer/ ............................ ❌ ZERO test
├── aggregator/ ............................ ✅ aggregator_test (9)
├── publisher/ ............................. ❌ ZERO test
└── dbwriter/ .............................. ❌ ZERO test

mt5-bridge/
├── grpc_server.py ......................... ✅ test_grpc_servicer (5)
├── connector.py ........................... ❌ ZERO test
├── order_manager.py ....................... ❌ ZERO test
└── position_tracker.py .................... ❌ ZERO test

ml-training/
└── tutti i moduli ......................... ❌ test NON eseguibili (ImportError)
```

### 2.2 Riepilogo Copertura

| Categoria | File Testati | File Non Testati | Copertura |
|-----------|-------------|-----------------|-----------|
| Core pipeline (brain) | 15 | 3 | ~83% |
| Safety systems | 5/5 | 0 | **100%** |
| Strategie | 5/5 | 0 | **100%** |
| Neural network | 5/44 | 39 | ~11% |
| Features | 4/16 | 12 | ~25% |
| Analysis | 0/10 | 10 | **0%** |
| Knowledge | 0/7 | 7 | **0%** |
| Processing | 0/13 | 13 | **0%** |
| Data Ingestion (Go) | 1/5 | 4 | ~20% |
| MT5 Bridge | 1/4 | 3 | ~25% |
| ML Training | 0/11 | 11 | **0%** |
| Console | 0/1 | 1 | **0%** |
| External Data | 0/3 | 3 | **0%** |

**Copertura globale stimata**: ~30% dei moduli hanno almeno un test. Il core pipeline e safety
sono ben coperti; tutto il resto (ML, analysis, knowledge, processing) ha zero copertura.

---

## 3. Tool Diagnostici

### 3.1 Inventario (34 file, 12.285 LoC)

#### Tool Standalone (14 file)

| File | LoC | Scopo |
|------|-----|-------|
| `feature_audit.py` | ~200 | Audit feature vector 60-dim |
| `db_health_diagnostic.py` | ~200 | Controllo salute database |
| `dev_health.py` | ~150 | Health check ambiente sviluppo |
| `context_gatherer.py` | ~250 | Raccolta contesto sistema |
| `build_tools.py` | ~150 | Build e packaging |
| `ml_debugger.py` | ~200 | Debug modelli ML |
| `user_tools.py` | ~100 | Utility utente |
| `_infra.py` | ~100 | Infrastruttura comune tool |
| `integrity_manifest.py` | ~200 | Manifest integrità codice |
| `dead_code_detector.py` | ~200 | Detector codice morto |
| `backend_validator.py` | ~200 | Validatore backend |
| `moneymaker_hospital.py` | ~300 | Diagnostica completa sistema |
| `project_snapshot.py` | ~200 | Snapshot stato progetto |
| `headless_validator.py` | ~150 | Validazione senza UI |
| `portability_check.py` | ~150 | Check portabilità cross-platform |

#### Brain Verification Suite (16 file + 2 common)

| File | Sezione | Scopo |
|------|---------|-------|
| `brain_verify.py` | Runner | Orchestratore verifica completa |
| `_common.py` | Shared | Utility comuni |
| `sec01_foundational.py` | 01 | Test fondamentali |
| `sec02_learning.py` | 02 | Capacità apprendimento |
| `sec03_utility.py` | 03 | Funzioni utilità |
| `sec04_safety.py` | 04 | Sistemi safety |
| `sec05_architecture.py` | 05 | Architettura NN |
| `sec06_monitoring.py` | 06 | Monitoring/observability |
| `sec07_market_domain.py` | 07 | Dominio mercato |
| `sec08_human_interaction.py` | 08 | Interazione umana |
| `sec09_continuous_improvement.py` | 09 | Miglioramento continuo |
| `sec10_meta_level.py` | 10 | Meta-analisi |
| `sec11_ethical.py` | 11 | Considerazioni etiche |
| `sec12_specialized.py` | 12 | Specializzazioni |
| `sec13_deployment.py` | 13 | Deploy readiness |
| `sec14_benchmarking.py` | 14 | Benchmarking |
| `sec15_philosophical.py` | 15 | Aspetti filosofici |
| `sec16_decision_framework.py` | 16 | Framework decisionale |

**Stato**: Questi tool sono script di diagnostica/verifica, NON test pytest. Servono per
ispezione manuale del sistema in esecuzione. Nessuno è integrato nella CI.

---

## 4. Documentazione — Inventario e Accuratezza

### 4.1 Documenti Principali (14 file, 10.646 LoC)

#### GUIDE/ (3 file, 757 LoC)

| File | LoC | Scopo | Accuratezza |
|------|-----|-------|-------------|
| `01_GUIDA_PROXMOX_VM.md` | 215 | Setup Proxmox/VM | ✅ Accurata |
| `02_GUIDA_MONITORING_E_TRAINING.md` | 241 | Monitoring + training | ⚠️ Parziale |
| `03_STATO_ARCHITETTURA_ONESTO.md` | 301 | Stato onesto del sistema | ❌ **OBSOLETA** |

#### docs/ (8 file, 8.000 LoC)

| File | LoC | Scopo | Accuratezza |
|------|-----|-------|-------------|
| `01_ARCHITETTURA.md` | 651 | Architettura generale | ✅ Accurata |
| `02_INSTALLAZIONE_E_AVVIO.md` | 981 | Guida installazione | ⚠️ Da verificare |
| `03_PIPELINE_SEGNALI.md` | 717 | Pipeline segnali | ✅ Accurata |
| `04_TRAINING_E_APPRENDIMENTO.md` | 977 | Training ML | ⚠️ Descrive design, non stato attuale |
| `05_METATRADER5_ESECUZIONE.md` | 732 | MT5 Bridge | ✅ Accurata |
| `06_CONSOLE_OPERATIVA.md` | 1.713 | Console TUI | ✅ Accurata |
| `07_DATABASE_E_STORAGE.md` | 1.042 | Schema DB | ✅ Accurata |
| `08_MONITORAGGIO_E_STABILITA.md` | 1.187 | Monitoring stack | ⚠️ Parziale |

#### program/docs/ (3 file, 1.889 LoC)

| File | LoC | Scopo | Accuratezza |
|------|-----|-------|-------------|
| `MONEYMAKER-V1-part1-infrastruttura.md` | 568 | Infrastruttura completa | ✅ Accurata |
| `MONEYMAKER-V1-part2-algo-engine.md` | 678 | Algo Engine pipeline | ✅ Accurata |
| `MONEYMAKER-V1-part3-safety-execution.md` | 643 | Safety + execution | ✅ Accurata |

### 4.2 Documenti Supplementari (5.913 LoC)

| Directory | File | LoC | Scopo |
|-----------|------|-----|-------|
| `docs/plans/` | 2 | ~300 | Safety-first implementation plan |
| `audits/` | 2 | ~200 | Audit observability + console |
| `skills_analysis/` | 7+12 | ~5.400 | Analisi skill, gap analysis |

### 4.3 Knowledge Base (175 file)

| Directory | File | Scopo |
|-----------|------|-------|
| `AI_Trading_Brain_Concepts/` | 175 | Compendio strategie, indicatori, ML concepts |

**Stato**: Materiale educativo/reference. Non documentazione operativa. Include 50+ strategie
documentate, fondamenti matematici, architetture deep learning, etc.

### 4.4 V1_Bot Blueprint (15 file)

| Directory | File | Scopo |
|-----------|------|-------|
| `program/V1_Bot/` | 14 MD + 1 README | Blueprint architettura originale CS2 |

**Stato**: Documenti di design originale. Molti concetti sono stati implementati, altri no.
Da trattare come reference, non come specifica di stato attuale.

### 4.5 MONEYMAKER_IMPLEMENTATION_DOCS — RIMOSSI

I 20 documenti T1_01→T4_20 che documentavano i task di implementazione (tutti marcati
"COMPLETATO") **non sono più presenti nel repository**. Sono stati rimossi durante il
force-push con history squash del 2026-03-02.

**Impatto**: Nessun impatto funzionale (erano specifiche, non codice), ma la perdita
della tracciabilità dei task è un rischio documentale.

---

## 5. Discrepanze Documentazione vs Codice

### 5.1 GUIDE/03 — Discrepanze CRITICHE

La GUIDE/03 (`03_STATO_ARCHITETTURA_ONESTO.md`) datata 2026-02-28 contiene errori significativi
che devono essere corretti per evitare confusione:

| # | Affermazione GUIDE/03 | Realtà nel Codice | Severità |
|---|----------------------|-------------------|----------|
| 1 | "Kill switch / safety: 20%" | Safety ~90%: kill_switch.py (145 LoC), spiral_protection.py (188 LoC), position_sizer.py (146 LoC), validator.py (312 LoC, 11 checks), portfolio.py (174 LoC), 3 E2E test, 10 Prometheus rules | **CRITICA** |
| 2 | "Grafana: nessuna dashboard pre-costruita" | 5 dashboard JSON esistono (4.333 LoC): moneymaker-overview, moneymaker-trading, moneymaker-data, moneymaker-risk, moneymaker-ml-training | **ALTA** |
| 3 | "Alert rules: non configurate" | `alert_rules.yml` con 10 regole (5 safety + 5 infra) esiste in monitoring/ | **ALTA** |
| 4 | "ML Lab Service: NON ESISTE — nessun codice per VM 102" | ml-training/ ha 11 file Python (~1.900 LoC) con server gRPC, TrainingOrchestrator completo, 5-phase cycle, checkpoint store | **CRITICA** |
| 5 | "321 test" | 353 test (32 aggiunti dopo la data della GUIDE) | **BASSA** |
| 6 | "Non c'è nessun optimizer (SGD, Adam)" | `optimizer_factory.py` esiste in algo-engine/nn/ con Adam, AdamW, SGD, scheduler | **ALTA** |
| 7 | "Non c'è nessuna loss function" | `losses.py` con 5 loss functions (316 LoC) in algo-engine/nn/ | **ALTA** |
| 8 | "Non c'è nessun DataLoader" | `dataset.py` esiste in algo-engine/nn/ con MarketDataset + DataLoader | **ALTA** |
| 9 | "Validazione segnali: 7 controlli" | Ora sono 11 controlli (XAGUSD 5000oz, margin check, etc. aggiunti) | **BASSA** |

### 5.2 Discrepanze tra docs/ e Codice

| # | Documento | Affermazione | Realtà | Severità |
|---|-----------|-------------|--------|----------|
| 1 | `04_TRAINING.md` | Descrive 5-phase training come funzionante | Phases sono structural (ritornano dict, non trainano) | **ALTA** |
| 2 | `02_INSTALLAZIONE.md` | Docker setup standard | MT5 Bridge non può girare in Docker Linux | **ALTA** |
| 3 | `08_MONITORAGGIO.md` | Monitoring stack completo | Prometheus config OK, ma deployment non testato | **MEDIA** |

---

## 6. Findings Critici — Sintesi da Tutti i Report

Questa tabella consolida i findings più importanti da tutti i 9 report precedenti, ordinati per
severità e impatto sulla roadmap verso produzione.

### 6.1 CRITICI (Bloccanti per Produzione)

| # | Finding | Report | Dettaglio |
|---|---------|--------|-----------|
| C1 | **MT5 Bridge non può girare in Docker Linux** | R08 | MetaTrader5 Python package è Windows-only. Il Dockerfile è inutile. MT5 Bridge DEVE girare nativamente su Windows (VM 101) |
| C2 | **training_orchestrator.py in algo-engine è STUB** | R03, R04 | `raise NotImplementedError()` — by design, delega a ml-training |
| C3 | **TrainingCycle 5 fasi sono placeholder** | R04 | Ritornano `dict` con metadati, non eseguono training reale |
| C4 | **Nessun DataLoader wired** | R04 | `dataset.py` esiste ma non è collegato a TrainingCycle |
| C5 | **GPU mismatch: CUDA 12.1 nel Dockerfile, utente ha AMD RX 9070 XT** | R04, R09 | Serve ROCm, non CUDA |
| C6 | **`.env` con password trackato in git** | R09 | `program/infra/docker/.env` contiene `Trade.2026.Macena` — compromesso |
| C7 | **Zero test E2E tick-to-trade** | R10 | Nessun test che verifica il flusso completo dati → segnale → ordine |
| C8 | **GUIDE/03 obsoleta con errori critici** | R10 | 9 discrepanze documentate, rischio di decisioni basate su info errate |

### 6.2 ALTI (Richiedono Azione Prima del Deploy)

| # | Finding | Report | Dettaglio |
|---|---------|--------|-----------|
| A1 | Port mismatch Dockerfile vs docker-compose | R01 | EXPOSE (50052/8082/9092) vs compose (50054/8080/9093) |
| A2 | ml-training commentato in docker-compose | R01, R04 | Servizio definito ma disabilitato |
| A3 | Drawdown limit mismatch brain=5% vs mt5-bridge=10% | R01, R08 | Config incoerente tra servizi |
| A4 | Solo Mode 4 (Conservative) operativo | R02 | Modi 1-3 richiedono ML non ancora funzionante |
| A5 | VL-JEPA model file mancante | R03 | `vl_jepa.py` referenziato ma non esiste |
| A6 | Model factory non supporta JEPA/ensemble | R03 | Solo RAP Coach supportato |
| A7 | CI Docker build context errato | R09 | `services/X` invece di root con `-f` |
| A8 | ml-training test non eseguibili | R10 | ImportError per modulo non installato |
| A9 | Zero test per analysis/ (10 moduli) | R10 | Nessuna verifica su analysis pipeline |
| A10 | Zero test per knowledge/ (7 moduli) | R10 | Knowledge base non testata |
| A11 | Zero test per processing/ (13 moduli) | R10 | Data processing non testato |
| A12 | Zero test per connettori Go (Polygon/Binance) | R10 | Solo aggregator testato |
| A13 | numpy.random.seed deprecato | R04 | Usare `np.random.default_rng()` |

### 6.3 MEDI (Miglioramenti Pre-Produzione)

| # | Finding | Report | Dettaglio |
|---|---------|--------|-----------|
| M1 | Redis healthcheck TLS-incompatibile | R09 | `redis-cli ping` fallisce con TLS abilitato |
| M2 | Sentry DSN vuoto di default | R09 | Nessun error tracking in produzione |
| M3 | Console senza test | R10 | 15 categorie di comandi non testate |
| M4 | External-data senza test | R10 | Provider CBOE/CFTC/FRED non testati |
| M5 | Temporal weighting non wired | R04 | `regime_shift.py` ha il codice ma non è collegato |
| M6 | MONEYMAKER_IMPLEMENTATION_DOCS rimossi | R10 | Tracciabilità task persa |
| M7 | Brain verification tools non in CI | R10 | 16 sezioni di verifica, solo manuali |

### 6.4 BASSI (Nice-to-Have)

| # | Finding | Report | Dettaglio |
|---|---------|--------|-----------|
| B1 | TLS certificates self-signed | R09 | OK per dev, servono CA-signed per prod |
| B2 | Grafana admin password hardcoded | R09 | `admin/moneymaker` nel provisioning |
| B3 | 175 concept docs non cross-referenziati | R10 | Materiale educativo non collegato al codice |
| B4 | Skills analysis non aggiornata | R10 | Basata su stato precedente al safety update |

---

## 7. Interconnessioni — Mappa di Dipendenze per il Deploy

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    MONEYMAKER — DEPENDENCY MAP FOR PRODUCTION              ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐            ║
║  │ TimescaleDB  │◄────│ Data Ingest  │────►│   ZeroMQ     │            ║
║  │   (VM 100)   │     │   (Go)       │     │  PUB/SUB     │            ║
║  └──────┬───────┘     └──────────────┘     └──────┬───────┘            ║
║         │                                          │                    ║
║         │ SQL read                    bar.SYM.TF   │                    ║
║         ▼                                          ▼                    ║
║  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            ║
║  │    Redis     │◄────│   Algo Engine   │◄────│  ZMQ SUB     │            ║
║  │  Kill Switch │     │  (Python)    │     │  Adapter     │            ║
║  └──────────────┘     └──────┬───────┘     └──────────────┘            ║
║                              │                                          ║
║              ┌───────────────┼───────────────┐                          ║
║              │               │               │                          ║
║              ▼               ▼               ▼                          ║
║     ┌──────────────┐  ┌────────────┐  ┌──────────────┐                 ║
║     │  MT5 Bridge  │  │ ML Training│  │  Prometheus  │                 ║
║     │  (Windows!)  │  │ (GPU VM)   │  │  + Grafana   │                 ║
║     │   gRPC 50055 │  │ gRPC 50056 │  │  :9090/:3000 │                 ║
║     └──────┬───────┘  └────────────┘  └──────────────┘                 ║
║            │                                                            ║
║            ▼                                                            ║
║     ┌──────────────┐                                                    ║
║     │ MetaTrader 5 │                                                    ║
║     │   Broker     │                                                    ║
║     └──────────────┘                                                    ║
║                                                                        ║
║  LEGENDA:                                                              ║
║  ────► = Comunicazione attiva (funzionante)                            ║
║  - - ► = Comunicazione predisposta (non wired)                         ║
║  VM 100 = Linux Docker host                                            ║
║  VM 101 = Windows (MT5 nativo)                                         ║
║  VM 102 = Linux + GPU (ML training, da creare)                         ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 8. Road to Production — Master Checklist

### FASE 0: Correzioni Immediate (Pre-requisiti)

#### Segmento 0A: Sicurezza

- [ ] **Ruotare la password** `Trade.2026.Macena` compromessa nel `.env` trackato in git
- [ ] Rimuovere `program/infra/docker/.env` dal tracking git (`git rm --cached`)
- [ ] Aggiungere `program/infra/docker/.env` al `.gitignore` globale
- [ ] Verificare che nessun altro secret sia committato (`trufflehog` scan)
- [ ] Rigenerare certificati TLS se necessario

#### Segmento 0B: Documentazione Critica

- [ ] **Aggiornare GUIDE/03** con stato reale: safety ~90%, 5 dashboard, ml-training esiste
- [ ] Correggere count test: 321 → 353
- [ ] Aggiungere nota su optimizer_factory, losses.py, dataset.py che ESISTONO
- [ ] Correggere sezione ML Lab: da "NON ESISTE" a "~75% implementato"
- [ ] Documentare che MT5 Bridge NON può girare in Docker Linux

#### Segmento 0C: Fix Config

- [ ] Allineare drawdown limit: brain 5% e mt5-bridge 5% (o entrambi 10%)
- [ ] Allineare porte Dockerfile EXPOSE con docker-compose
- [ ] Scommentare ml-training in docker-compose.yml (quando pronto)
- [ ] Correggere CI Docker build context in `ci.yml`

---

### FASE 1: Paper Trading Rule-Based (Settimana 1-2)

#### Segmento 1A: Setup Ambiente

- [ ] Installare Proxmox su bare metal
- [ ] Creare VM 100 (Ubuntu Server + Docker)
- [ ] Creare VM 101 (Windows 11 per MT5)
- [ ] Configurare rete bridge tra VM (IP statici 10.0.x.x)
- [ ] Clonare repository su entrambe le VM

#### Segmento 1B: Deploy Servizi Core

- [ ] Creare `.env` reale con credenziali (DB, Redis, API keys)
- [ ] Avviare Docker stack su VM 100: `docker compose up -d` (senza ml-training)
- [ ] Verificare TimescaleDB avviato e schema inizializzato (7 script SQL)
- [ ] Verificare Redis avviato e raggiungibile
- [ ] Configurare API key Polygon.io nel `.env` di data-ingestion
- [ ] Verificare data-ingestion riceve tick e pubblica su ZMQ

#### Segmento 1C: MT5 Bridge (VM 101 Windows)

- [ ] Installare Python 3.11+ su VM 101
- [ ] Installare MetaTrader 5 e configurare account demo
- [ ] Installare dipendenze mt5-bridge (`pip install -r requirements.txt`)
- [ ] Configurare `.env` mt5-bridge con IP di VM 100 per gRPC
- [ ] Avviare mt5-bridge come servizio Windows
- [ ] Verificare che i segnali arrivano al MT5

#### Segmento 1D: Verifica Flusso Completo

- [ ] Inviare tick di test e verificare che brain genera segnale
- [ ] Verificare che il segnale passa la validazione (11 checks)
- [ ] Verificare che il segnale arriva al MT5 Bridge
- [ ] Verificare che l'ordine viene eseguito su demo MT5
- [ ] Monitorare per 48h in paper mode — annotare ogni trade
- [ ] Verificare kill switch funzionante: simulare max daily loss

---

### FASE 2: Monitoring e Safety Validation (Settimana 2-3)

#### Segmento 2A: Prometheus + Grafana

- [ ] Verificare Prometheus scraping attivo (`:9090/targets`)
- [ ] Importare le 5 dashboard Grafana pre-costruite
- [ ] Verificare che le metriche arrivano a ogni dashboard
- [ ] Configurare Grafana con password non-default
- [ ] Testare le 10 alert rules (simulare condizioni di trigger)

#### Segmento 2B: Safety System Validation

- [ ] Test kill switch: simulare drawdown ≥5% → verifica blocco totale
- [ ] Test spiral protection: simulare 3 loss consecutive → verifica riduzione size
- [ ] Test position sizer: verificare scaling corretto per ogni fascia di drawdown
- [ ] Test rate limiter: inviare burst di segnali → verifica throttling
- [ ] Test dedup: inviare segnale duplicato → verifica rifiuto (60s window)
- [ ] Documentare risultati di ogni test safety

#### Segmento 2C: Alerting

- [ ] Configurare Telegram bot per alerting (dispatcher.py + telegram.py)
- [ ] Testare alert Telegram per ogni regola critica
- [ ] Configurare Sentry DSN per error tracking
- [ ] Verificare che gli errori vengono catturati e notificati

---

### FASE 3: Stabilizzazione e Test Aggiuntivi (Settimana 3-4)

#### Segmento 3A: Test Coverage Critica

- [ ] Scrivere test per `signal_router.py` (attualmente zero test)
- [ ] Scrivere test per `data_quality.py` + `data_sanity.py`
- [ ] Scrivere test per `feature_drift.py` + `leakage_auditor.py`
- [ ] Scrivere test per `order_manager.py` (mt5-bridge)
- [ ] Scrivere test per `position_tracker.py` (mt5-bridge)
- [ ] Scrivere test per connettori Go (Polygon, Binance)
- [ ] Fix ml-training test: aggiungere `pyproject.toml` con pytest config + `pip install -e .`
- [ ] Scrivere almeno 1 test E2E tick-to-trade

#### Segmento 3B: Paper Trading Esteso

- [ ] 1 settimana continua di paper trading
- [ ] Raccogliere metriche: win rate, avg PnL, max drawdown, Sharpe stimato
- [ ] Analizzare distribuzione segnali per regime
- [ ] Identificare falsi segnali e migliorare soglie se necessario
- [ ] Documentare risultati in un report settimanale

---

### FASE 4: ML Training Setup (Settimana 5-8)

#### Segmento 4A: GPU VM Setup

- [ ] Creare VM 102 su Proxmox con GPU passthrough (AMD RX 9070 XT)
- [ ] Installare ROCm (NON CUDA) su VM 102
- [ ] Verificare `torch.cuda.is_available()` (ROCm si presenta come CUDA)
- [ ] Cambiare Dockerfile ml-training: da `nvidia/cuda:12.1` a `rocm/pytorch:latest`
- [ ] Clonare repository su VM 102

#### Segmento 4B: Wiring Training Pipeline

- [ ] Collegare `dataset.py` (MarketDataset) a `TrainingCycle` fasi
- [ ] Implementare DataLoader reale che legge da TimescaleDB
- [ ] Collegare `losses.py` alle fasi di training
- [ ] Collegare `optimizer_factory.py` al training loop
- [ ] Implementare le 5 fasi di `TrainingCycle` con training reale (non solo metadata dict)
- [ ] Verificare che `TrainingOrchestrator` (ml-training) esegue epoch complete

#### Segmento 4C: Primo Training

- [ ] Raccogliere almeno 1 mese di dati storici in TimescaleDB
- [ ] Eseguire Phase 1 JEPA pre-training (100+ epoch)
- [ ] Valutare metriche: loss convergence, validation Sharpe ≥ 1.0
- [ ] Salvare checkpoint con SHA-256 integrity
- [ ] Eseguire Phase 2 Pro Baseline con dati di backtest
- [ ] Documentare risultati training

#### Segmento 4D: ML Integration

- [ ] Abilitare gRPC ml_inference tra brain e ml-training
- [ ] Testare fallback: ML timeout → Conservative mode
- [ ] Attivare Mode 1 (COPER) in paper mode
- [ ] Monitorare per 1 settimana con ML attivo
- [ ] Confrontare performance ML vs rule-based

---

### FASE 5: Backtesting Framework (Settimana 8-10)

#### Segmento 5A: Implementazione

- [ ] Creare engine di backtesting walk-forward
- [ ] Implementare transaction cost model (spread + slippage)
- [ ] Implementare report generator (Sharpe, Calmar, max drawdown, win rate)
- [ ] Implementare CPCV (Combinatorial Purged Cross-Validation)
- [ ] Validare strategie su almeno 6 mesi di dati storici

#### Segmento 5B: Validazione

- [ ] Backtest TrendFollowing strategy: Sharpe target ≥ 1.0
- [ ] Backtest MeanReversion strategy: Sharpe target ≥ 0.8
- [ ] Backtest con ML: confronto vs baseline rule-based
- [ ] Stress test: performance durante eventi di mercato estremi
- [ ] Documentare risultati in report dettagliato

---

### FASE 6: Pre-Production Hardening (Settimana 10-12)

#### Segmento 6A: Security Hardening

- [ ] Implementare mTLS tra tutti i servizi gRPC
- [ ] Verificare RBAC database (ruoli per-servizio, no superuser)
- [ ] Abilitare Redis AUTH + TLS
- [ ] Configurare firewall su Proxmox (solo porte necessarie)
- [ ] Audit completo con `trufflehog`, `pip-audit`, `govulncheck`
- [ ] Implementare secret rotation automatica

#### Segmento 6B: Resilience

- [ ] Test failover: kill data-ingestion → brain degrada gracefully
- [ ] Test failover: kill Redis → kill switch fallisce safe (blocca trading)
- [ ] Test failover: kill ML training → brain torna a Conservative mode
- [ ] Test memory leak: monitorare per 72h continue
- [ ] Test CPU/RAM sotto carico (simulare 10 simboli in parallelo)

#### Segmento 6C: Observability Finale

- [ ] Verificare tutte le dashboard Grafana con dati reali
- [ ] Configurare retention Prometheus (almeno 30 giorni)
- [ ] Implementare log aggregation (Loki o ELK)
- [ ] Verificare che ogni errore genera alert Telegram
- [ ] Documentare runbook per ogni alert rule

---

### FASE 7: Go Live (Settimana 12+)

#### Segmento 7A: Transizione a Live

- [ ] Aprire account live MT5 con broker
- [ ] Configurare con size MINIMO (0.01 lotti)
- [ ] Abilitare kill switch con soglie conservative (2% daily, 5% drawdown)
- [ ] Monitorare 24/7 per prima settimana
- [ ] Review giornaliera di ogni trade eseguito
- [ ] Avere procedura di emergenza documentata (kill switch manuale)

#### Segmento 7B: Scaling Graduale

- [ ] Dopo 1 mese profittevole: aumentare a 0.02 lotti
- [ ] Dopo 3 mesi profittevoli: considerare 0.05 lotti
- [ ] Mai superare il 2% del capitale per trade
- [ ] Rivedere parametri ogni 2 settimane
- [ ] Mantenere log di ogni modifica parametri

---

## 9. Riepilogo Quantitativo Finale

### Codebase

| Metrica | Valore |
|---------|--------|
| Servizi | 6 (algo-engine, data-ingestion, mt5-bridge, ml-training, console, external-data) |
| File Python (algo-engine) | ~120+ |
| File Go (data-ingestion) | 13 |
| File Python (ml-training) | 11 |
| File Python (mt5-bridge) | 7 |
| Proto definitions | 5 |
| SQL init scripts | 7 |
| Grafana dashboards | 5 (4.333 LoC) |
| Prometheus alert rules | 10 |
| Diagnostic tools | 34 file (12.285 LoC) |

### Test

| Metrica | Valore |
|---------|--------|
| Test totali passing | **353** (algo-engine) + 9 (Go) + 5 (mt5-bridge) = **367** |
| Test non eseguibili | 6 (ml-training, ImportError) |
| Test LoC | 4.257 (Python) + 211 (Go) + 150 (mt5-bridge) + 55 (ml-training) = **4.673** |
| Copertura moduli | ~30% dei moduli ha almeno un test |
| Servizi con zero test | 3 (console, external-data, monitoring) |

### Documentazione

| Metrica | Valore |
|---------|--------|
| Documenti principali | 14 (10.646 LoC) |
| V1_Bot blueprints | 15 file |
| Concept docs | 175 file |
| Skills analysis | 19 file (5.913 LoC) |
| Plans/Audits | 4 file |
| README | 15+ |
| Discrepanze critiche GUIDE/03 | 9 errori documentati |

### Findings

| Severità | Conteggio | Più Critico |
|----------|-----------|-------------|
| CRITICO | 8 | MT5 Docker Linux, .env compromesso, training placeholder |
| ALTO | 13 | Port mismatch, zero test analysis/knowledge/processing |
| MEDIO | 7 | Redis TLS, Sentry, console test |
| BASSO | 4 | TLS self-signed, Grafana password, concept docs |
| **TOTALE** | **32** | |

### Stima Effort per Produzione

| Fase | Settimane | Effort |
|------|-----------|--------|
| Fase 0: Fix immediati | 0.5 | 1-2 giorni |
| Fase 1: Paper trading rule-based | 1-2 | 3-5 giorni attivi |
| Fase 2: Monitoring + Safety | 1 | 2-3 giorni |
| Fase 3: Stabilizzazione + Test | 1-2 | 5-7 giorni |
| Fase 4: ML Training | 3-4 | 10-15 giorni |
| Fase 5: Backtesting | 2 | 5-8 giorni |
| Fase 6: Hardening | 2 | 5-7 giorni |
| Fase 7: Go Live | 1+ | Ongoing |
| **TOTALE** | **~12 settimane** | **~40-50 giorni di lavoro attivo** |

---

## 10. Conclusione

MONEYMAKER è un sistema **architetturalmente solido e ben progettato** per il trading algoritmico.
Il core pipeline (data → features → regime → strategy → signal → execution) è **funzionante e testato**.
I safety systems sono **quasi completi** (~90%) e coprono kill switch, spiral protection,
position sizing e validazione a 11 controlli.

I principali blocchi verso la produzione sono:

1. **ML Training non wired**: L'infrastruttura esiste (~75%) ma le fasi di training sono
   placeholder. Il DataLoader, le loss functions e l'optimizer esistono come moduli isolati
   ma non sono collegati al ciclo di training.

2. **MT5 su Windows obbligatorio**: Il bridge non può girare in Docker Linux. Serve una VM
   Windows dedicata o esecuzione nativa.

3. **Sicurezza**: Password compromessa nel `.env` committato, necessaria rotazione immediata.

4. **Test coverage insufficiente**: 30% dei moduli testati. Analysis, knowledge, processing,
   ML e connettori hanno zero copertura.

5. **Documentazione obsoleta**: La GUIDE/03 contiene 9 errori che possono portare a decisioni
   errate.

Il percorso più veloce verso valore è: **Fix sicurezza → Paper trading rule-based → Monitoring →
ML training → Backtest → Live con size minimo**. Stima: ~12 settimane di lavoro attivo per
raggiungere il primo trade live con ML.
