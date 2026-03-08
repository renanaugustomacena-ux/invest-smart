# REPORT 04: ML Training e Path Verso un Modello Addestrato

> **Revisione**: 2026-03-05 — Verifica line-by-line su codice reale.
> Ogni finding include numero di riga esatto verificato nel sorgente.
> Cambiamenti rispetto alla versione precedente:
> - training_cycle.py LoC aggiornato da 400 a **1148** (fasi ora implementate, non placeholder)
> - Finding F03 declassato: fasi IMPLEMENTATE con vero data loading, model building, training loop
> - Aggiunto F16: `_create_weighted_loaders` ignora i pesi (linea 1130-1141)
> - Aggiunto F17: `_bars_to_features` produce solo 8 feature reali, zero-padded a 60
> - Confermati: F06 torch.load security, F07 numpy seed, F08 sample weights dead code
> - Confermato: _best_val_loss persistence bug cross-fase (training_orchestrator.py:107,212)

---

## Executive Summary

Il sistema ML training di MONEYMAKER è organizzato in **due service distinti** con una chiara separazione di responsabilità: il servizio **ml-training** (11 file Python, ~2,400 LoC) gestisce l'orchestrazione dell'epoch loop, il checkpoint, e l'inferenza gRPC; il lato **algo-engine** (nn/ directory) fornisce le architetture neurali, loss functions, dataset, optimizer, e un'interfaccia STUB che delega il training alla macchina ML. Il contratto gRPC (`ml_inference.proto`, 56 LoC) usa Decimal string-encoded per la precisione finanziaria.

**Stato reale**: L'infrastruttura architetturale è solida (~85% struttura). Il `TrainingCycle` a 5 fasi è ora **implementato** (1148 LoC) con vero data loading dal database, istanziazione modelli, chiamata all'orchestrator, e salvataggio checkpoint. Tuttavia il sistema **non è mai stato eseguito end-to-end**: il docker-compose ha ml-training commentato, il Dockerfile usa CUDA 12.1 NVIDIA (l'utente ha AMD RX 9070 XT), e nessun test copre il loop di training effettivo. I feature vector prodotti da `_bars_to_features()` contengono solo **8 dimensioni reali** su 60 (il resto è zero padding), rendendo il modello quasi cieco. I 20 MONEYMAKER_IMPLEMENTATION_DOCS dichiarano tutti "COMPLETATO" ma sono **specifiche di design** (blueprint dall'architettura CS2), non conferme di codice funzionante.

---

## Inventario Completo

### A. Servizio ml-training (Macchina ML Dedicata)

| # | File | Percorso | LoC | Stato |
|---|------|----------|-----|-------|
| 1 | main.py | services/ml-training/src/ml_training/main.py | 108 | COMPLETO |
| 2 | config.py | services/ml-training/src/ml_training/config.py | 69 | COMPLETO |
| 3 | server.py | services/ml-training/src/ml_training/server.py | 343 | COMPLETO |
| 4 | training_orchestrator.py | services/ml-training/src/ml_training/nn/training_orchestrator.py | 443 | COMPLETO (2 bug) |
| 5 | training_cycle.py | services/ml-training/src/ml_training/nn/training_cycle.py | **1148** | IMPLEMENTATO (was 400) |
| 6 | model_builder.py | services/ml-training/src/ml_training/nn/model_builder.py | 175 | COMPLETO |
| 7 | checkpoint_store.py | services/ml-training/src/ml_training/storage/checkpoint_store.py | 244 | COMPLETO (1 security bug) |
| 8 | __init__.py | services/ml-training/src/ml_training/__init__.py | ~5 | OK |
| 9 | __init__.py | services/ml-training/src/ml_training/nn/__init__.py | ~5 | OK |
| 10 | __init__.py | services/ml-training/src/ml_training/storage/__init__.py | ~5 | OK |
| 11 | conftest.py | services/ml-training/tests/conftest.py | 11 | SOLO PATH SETUP |
| 12 | test_training_cycle.py | services/ml-training/tests/test_training_cycle.py | 56 | SMOKE ONLY |
| 13 | Dockerfile | services/ml-training/Dockerfile | 47 | ERRORE GPU |
| 14 | pyproject.toml | services/ml-training/pyproject.toml | 55 | COMPLETO |
| 15 | README.md | services/ml-training/README.md | 123 | DISALLINEATO |
| **Totale** | | | **~2,837** | |

### B. Infrastruttura Training in algo-engine (nn/)

| # | File | Percorso | LoC | Stato |
|---|------|----------|-----|-------|
| 1 | training_orchestrator.py | algo-engine/src/algo_engine/nn/training_orchestrator.py | 158 | STUB |
| 2 | training_worker.py | algo-engine/src/algo_engine/nn/training_worker.py | 241 | COMPLETO |
| 3 | training_config.py | algo-engine/src/algo_engine/nn/training_config.py | 196 | COMPLETO |
| 4 | training_callbacks.py | algo-engine/src/algo_engine/nn/training_callbacks.py | 292 | COMPLETO |
| 5 | dataset.py | algo-engine/src/algo_engine/nn/dataset.py | 370 | COMPLETO (dead code) |
| 6 | losses.py | algo-engine/src/algo_engine/nn/losses.py | 316 | COMPLETO |
| 7 | optimizer_factory.py | algo-engine/src/algo_engine/nn/optimizer_factory.py | 199 | COMPLETO |
| 8 | model_evaluator.py | algo-engine/src/algo_engine/nn/model_evaluator.py | 529 | COMPLETO |
| 9 | retraining_trigger.py | algo-engine/src/algo_engine/nn/retraining_trigger.py | 149 | COMPLETO |
| 10 | early_stopping.py | algo-engine/src/algo_engine/nn/early_stopping.py | 83 | COMPLETO |
| 11 | ema.py | algo-engine/src/algo_engine/nn/ema.py | 129 | COMPLETO |
| **Totale** | | | **~2,662** | |

### C. Proto Contract

| # | File | Percorso | LoC | Stato |
|---|------|----------|-----|-------|
| 1 | ml_inference.proto | shared/proto/ml_inference.proto | 56 | COMPLETO |

### D. MONEYMAKER_IMPLEMENTATION_DOCS (21 file)

| # | File | LoC | Tipo Reale |
|---|------|-----|------------|
| 0 | 00_INDICE_GENERALE.md | ~270 | Indice + Glossario |
| 1 | T1_01_TRAINING_ORCHESTRATOR.md | ~850 | SPECIFICA |
| 2 | T1_02_CICLO_TRAINING_5_FASI.md | ~830 | SPECIFICA |
| 3 | T1_03_DATALOADER_E_BATCH.md | ~580 | SPECIFICA |
| 4 | T1_04_FUNZIONI_DI_PERDITA.md | ~460 | SPECIFICA |
| 5 | T1_05_OTTIMIZZATORI_E_SCHEDULER.md | ~560 | SPECIFICA |
| 6 | T1_06_CALLBACK_E_TENSORBOARD.md | ~480 | SPECIFICA |
| 7 | T1_07_CHECKPOINT_MANAGEMENT.md | ~340 | SPECIFICA |
| 8 | T2_08_JEPA_ADATTAMENTO_MERCATO.md | ~580 | SPECIFICA |
| 9 | T2_09_VL_JEPA_CONCEPT_GROUNDING.md | ~900 | SPECIFICA |
| 10 | T2_10_EXPERIENCE_BANK_ENHANCEMENT.md | ~780 | SPECIFICA |
| 11 | T2_11_TEMPORAL_BASELINE_DECAY.md | ~790 | SPECIFICA |
| 12 | T2_12_MATURITY_GATING_5_TIER.md | ~720 | SPECIFICA |
| 13 | T3_13_MARKET_POV_CONSTRAINTS.md | ~960 | SPECIFICA |
| 14 | T3_14_TENSOR_FACTORY_MERCATO.md | ~430 | SPECIFICA |
| 15 | T3_15_SAFETY_SYSTEMS.md | ~460 | SPECIFICA |
| 16 | T3_16_METRICHE_DI_VALUTAZIONE.md | ~410 | SPECIFICA |
| 17 | T4_17_REGIME_CLASSIFICATION_HEAD.md | ~240 | SPECIFICA |
| 18 | T4_18_MODEL_FACTORY_ENHANCEMENT.md | ~240 | SPECIFICA |
| 19 | T4_19_STATE_RECONSTRUCTOR.md | ~720 | SPECIFICA |
| 20 | T4_20_SESSION_ENGINE_DAEMONS.md | ~940 | SPECIFICA |
| **Totale** | | **~12,540** | |

---

## Analisi Dettagliata

### A. Servizio ml-training

#### A.1 Entry Point — main.py (108 LoC)

**Cosa fa**: Avvia il server gRPC asincrono su porta 50056. Carica il modello `jepa_market` dal CheckpointStore all'avvio. Gestisce graceful shutdown su SIGTERM/SIGINT. Avvia un server HTTP Prometheus opzionale su porta 9096.

**Flusso**:
1. Crea `MLTrainingSettings` da env vars (prefisso `ML_`)
2. Inizializza `CheckpointStore` con directory e keep_last
3. Crea `MLInferenceServicer` e tenta `load_model("jepa_market")`
4. Registra il servicer su `grpc.aio.server()`
5. Attende `stop_event` → `server.stop(grace=5)`

**Stato**: COMPLETO — Nessun errore di logica. Pattern corretto per servizio gRPC Python asincrono.

**Problema SIGINT su Windows**: `loop.add_signal_handler()` non funziona su Windows (richiede Unix). Il servizio non potrà fare graceful shutdown su Windows. Funziona correttamente in Docker Linux.

#### A.2 Config — config.py (69 LoC)

**Cosa fa**: `MLTrainingSettings(MoneyMakerBaseSettings)` — tutte le impostazioni dal prefisso env `ML_`.

**Parametri chiave**:
- `ml_grpc_port=50056`, `ml_metrics_port=9096`
- `ml_seed=42`, `ml_batch_size=32`, `ml_max_epochs=100`
- `ml_learning_rate=1e-4`, `ml_weight_decay=1e-5`
- `ml_gradient_clip_norm=1.0`, `ml_early_stopping_patience=10`
- `ml_jepa_input_dim=60` (METADATA_DIM), `ml_jepa_latent_dim=128`
- `ml_min_val_sharpe=Decimal("1.0")`, `ml_min_val_win_rate=Decimal("0.55")`

**Stato**: COMPLETO — Decimal per soglie finanziarie, tutti i knob necessari presenti.

#### A.3 Server — server.py (343 LoC)

**Cosa fa**: `MLInferenceServicer` — implementa il contratto `MLInferenceService` dal proto. Gestisce `Predict()` e `GetModelInfo()`.

**Pattern Circuit Breaker**: Se il modello non è caricato → risponde HOLD con confidence="0.5" e reasoning="Modello non disponibile — fallback HOLD (circuit breaker)". Mai eccezioni non gestite verso il client.

**Flusso Predict**:
1. Estrae features dal request (string-encoded Decimal → float)
2. Costruisce tensor `(1, 1, feature_dim)` — batch=1, seq=1
3. Forward pass no_grad
4. Parse output: logits → softmax → direction + confidence
5. Confidence come `str(Decimal(str(round(conf, 4))))` — corretto, nessun double-encoding

**Verificato**: `_parse_output()` (linea 224-261) restituisce già una stringa Decimal. La `_do_predict()` (linea 218) chiama `str(confidence)` su una stringa → no-op, non è un bug.

**Problemi**:
- **Linea 199-202**: Input tensor shape `(1, 1, feature_dim)` con `unsqueeze(0)` — produce shape `(1, 1, 60)`. Funziona per _RAPStub (che fa `x[:, -1, :]`) ma non corrisponde a MarketRAPCoach che richiede `(batch, seq, 188)`.
- **Linea 311**: `_instantiate_model()` usa `model_builder.build_model()` locale — non supporta le architetture complesse di algo-engine.

**Stato**: COMPLETO per inferenza standalone. WARNING per compatibilità shape con modelli algo-engine completi.

#### A.4 Training Orchestrator — ml-training (443 LoC)

**Cosa fa**: Loop di training epoch-per-epoch completo. Questo è il **cuore del training** che avviene sulla macchina ML dedicata.

**Flusso**:
1. `run_training(model, optimizer, scheduler, train_loader, val_loader)` — async
2. Per ogni epoch: train pass → val pass → scheduler step → checkpoint se migliora → early stopping check
3. `_run_epoch()` — itera sui batch, gestisce mixed precision (AMP), gradient clipping (norm 1.0)
4. `_compute_loss()` — supporta sia JEPA (context/target → MSE) che supervised (features/direction → CrossEntropy)
5. Seed deterministico (42) con numpy, random, torch
6. Salva checkpoint tramite CheckpointStore con SHA-256

**Bug verificati**:

1. **_best_val_loss persistence cross-fase** (linee 107, 212-213):
   - `self._best_val_loss = float("inf")` inizializzato in `__init__` (linea 107)
   - Aggiornato durante training (linea 212-213) quando val_loss migliora
   - **BUG**: Se lo stesso orchestrator è riutilizzato per più fasi del TrainingCycle, il `_best_val_loss` dalla fase precedente persiste. La fase 2 potrebbe ereditare il best_val_loss della fase 1, causando early stopping prematuro se la fase 2 ha loss iniziale peggiore.
   - **Impatto**: Early stopping potrebbe scattare erroneamente nelle fasi 2-5 del ciclo.

2. **numpy seed non impostato** (linea 416):
   - `np.random.default_rng(seed)` crea un generatore RNG ma non lo assegna a nulla
   - Il generatore viene creato e immediatamente garbage-collected
   - **Fix**: Dovrebbe essere `np.random.seed(seed)` per il seed globale, o `rng = np.random.default_rng(seed)` con uso del generatore
   - **Impatto**: Riproducibilità non garantita per operazioni numpy

3. **AMP GradScaler**:
   - Linea 155-156: `torch.cuda.amp.GradScaler()` — deprecato in PyTorch ≥2.4
   - Linea 314: `torch.cuda.amp.autocast()` — stessa deprecation
   - **Fix**: `torch.amp.GradScaler("cuda")` e `torch.amp.autocast("cuda")`

**Stato**: COMPLETO — Loop funzionale, ma con bug nel seeding e nella persistenza cross-fase.

#### A.5 Training Cycle — 5 Fasi (1148 LoC) ⚠️ AGGIORNAMENTO IMPORTANTE

**NOTA**: La versione precedente di questo report dichiarava 400 LoC e fasi "placeholder". Dopo verifica line-by-line, il file è stato **significativamente espanso** a 1148 LoC con fasi reali implementate.

**Cosa fa**: `TrainingCycle` orchestra il pipeline a 5 fasi sequenziali:
1. **JEPA Pre-training** (linee 237-341): Carica barre dal DB → `_bars_to_features()` → `MarketJEPADataset` o fallback inline → `build_model("jepa_market")` → `orchestrator.run_training()` → save checkpoint
2. **Backtest Baseline** (linee 343-441): Carica trade vincenti da DB → fine-tune con checkpoint fase 1 → CrossEntropy su direzione
3. **Live Adaptation** (linee 443-539): Carica trade reali → temporal weighting 0.995 → LR ridotto (1/10) → fine-tune
4. **RAP Optimization** (linee 541-636): Mix backtest+live → `RAPTradingLoss` 4 componenti → `CosineAnnealing`
5. **Regime Head** (linee 638-727): Congela encoder → linear head 128→5 → supervised su regime labels

**Stato reale delle fasi**: Le fasi sono **implementate** con vero codice che:
- Chiama il database per caricare barre storiche e trade
- Istanzia modelli tramite `model_builder.build_model()`
- Chiama `self._orch.run_training()` sull'orchestrator reale
- Salva checkpoint tramite `self._store.save()`

**Problemi critici verificati**:

1. **Feature vector quasi vuoto** (linee 862-908):
   - `_bars_to_features()` produce solo **8 feature reali** per barra: open, high, low, close, volume, return, range_hl, body_ratio
   - Le rimanenti 52 dimensioni sono **zero-padded** (`while len(feature) < 60: feature.append(0.0)`)
   - Il modello JEPA ha `input_dim=60` ma riceve 87% zeri
   - **Impatto ALTO**: Il modello impara principalmente su 8 feature primitive. Gli indicatori tecnici (RSI, EMA, BB, ATR) configurati in `BrainSettings` non sono calcolati qui.

2. **_create_weighted_loaders ignora i pesi** (linee 1130-1141):
   - La fase 3 (Live Adaptation) chiama `_prepare_weighted_samples()` (linea 495) che calcola correttamente i pesi temporali
   - Ma `_create_weighted_loaders()` (linea 1130) **ignora completamente i pesi** e delega a `_create_supervised_loaders()` che non usa WeightedRandomSampler
   - Commento nel codice (linea 1139-1140): "Per semplicita', usa i loaders normali ma applica pesi nel loss" — ma i pesi non sono applicati nel loss dell'orchestrator
   - **Impatto**: Il temporal recency weighting della fase 3 è completamente non funzionale

3. **Prerequisites check non verifica dati sufficienti** (linee 129-158):
   - `check_prerequisites()` verifica solo che db, config, orchestrator e store non siano None
   - Non verifica se il DB contiene effettivamente ≥1000 barre (delegato alle singole fasi)
   - Questo è un design choice accettabile — ogni fase gestisce i propri requisiti minimi

**Stato**: IMPLEMENTATO — Significativo miglioramento rispetto alla versione placeholder. Le fasi fanno vero data loading e training. Bug critico: feature vector quasi vuoto e pesi temporali ignorati.

#### A.6 Model Builder (175 LoC)

**Cosa fa**: Factory locale che crea JEPA, RAP (stub MLP 60→64→3), e RegimeHead (5 classi) senza dipendere da algo-engine.

**Modelli supportati** (7 varianti, 3 builder):
- `jepa_market`, `jepa_pretrain` → `_build_jepa()` — TransformerEncoder
- `rap_coach`, `rap_optimized`, `backtest_baseline`, `live_adapted` → `_build_rap_stub()` — MLP 60→64→3
- `regime_head` → `_build_regime_head()` — encoder JEPA + linear 128→5

**Nota critica**: `_RAPStub` è un MLP semplice (60→64→3), **non** il MarketRAPCoach completo da algo-engine. Questo è intenzionale per inference leggera.

**Stato**: COMPLETO per i modelli supportati. Missing: supporto VL-JEPA, ensemble, modelli da algo-engine.

#### A.7 Checkpoint Store (244 LoC)

**Cosa fa**: Gestisce persistenza checkpoint con integrità SHA-256.

**Pattern**:
- `save()`: `torch.save()` → SHA-256 → sidecar JSON → latest copy → cleanup old
- `load()`: verifica SHA-256 → `torch.load()` con device auto-detection → metadata
- `_cleanup_old()`: mantiene gli ultimi `keep_last` checkpoint (default 5)
- `exists()`: controlla se `{model_name}_latest.pt` esiste
- `list_checkpoints()`: elenca tutti i sidecar per un modello

**Problema sicurezza**:
- **Linea 186**: `torch.load(pt_path, map_location=device)` senza `weights_only=True` — vulnerability arbitrary code execution tramite pickle deserialization in PyTorch ≥2.0.

**Stato**: COMPLETO — Robusto con SHA-256, cleanup automatico, latest symlink pattern. Security warning per torch.load.

#### A.8 Test — conftest.py (11 LoC) + test_training_cycle.py (56 LoC)

**conftest.py**: Solo path manipulation per imports. **Nessun fixture pytest definito**.

**test_training_cycle.py**: 6 test di smoke che verificano solo `check_prerequisites()` e `CycleContext`.

**Test presenti**:
1. `test_db_none_returns_false` — db=None → False
2. `test_db_none_message_mentions_db` — messaggio contiene "db"
3. `test_no_config_returns_false` — config=None → False
4. `test_all_none_returns_false` — tutti None → False
5. `test_default_values` — CycleContext defaults corretti
6. `test_with_db_object` — CycleContext accetta qualsiasi db

**Test MANCANTI**:
- Nessun test per `execute_cycle()` (le 5 fasi)
- Nessun test per il TrainingOrchestrator (epoch loop)
- Nessun test per CheckpointStore (save/load roundtrip)
- Nessun test per ModelBuilder (istanziazione modelli)
- Nessun test per MLInferenceServicer (Predict/GetModelInfo)
- Nessun test per `_bars_to_features()` (verifica delle 8 feature)
- Nessun test per `_create_weighted_loaders()` (verifica pesi)

**Stato**: SMOKE ONLY — 6 test triviali su 15 file, 0% coverage del training loop.

---

### B. Infrastruttura Training in algo-engine

#### B.1 Training Orchestrator STUB (158 LoC)

**Cosa fa**: Definisce l'interfaccia `TrainingOrchestrator` lato algo-engine (inference machine). `run_training()` lancia `NotImplementedError` — by design.

**Classi**:
- `OrchestratorConfig`: model_type, epochs, batch_size, lr, weight_decay, patience, mixed_precision, gradient_clip
- `TrainingProgress`: epoch, losses, checkpoint_path, is_complete, early_stopped
- `TrainingResult`: final losses, best_val_loss, total_epochs, metrics dict
- `TrainingOrchestrator`: `.run_training()` → NotImplementedError, `.load_checkpoint()` → funziona, `.get_progress()` → funziona

**Design**: Corretto. Il brain-side definisce le interfacce e delega il training alla macchina ML via gRPC. Il `TrainingWorker` usa queste interfacce.

**Stato**: STUB — Per design. Interfacce ben definite.

#### B.2 Training Worker (241 LoC)

**Cosa fa**: Daemon thread che monitora il `RetrainingTrigger` e avvia il training quando le condizioni sono soddisfatte.

**Pattern**:
- `start()` → spawna daemon thread `_run_loop()`
- `_run_loop()` — sleep granulare 1s × N (reattivo allo shutdown)
- `request_training()` — **sincrono**, chiama `orchestrator.run_training()` → cattura NotImplementedError → logga "training_not_implemented"
- `stop(timeout=10)` — graceful con join

**Problema**: `request_training()` è sincrono. In produzione dovrebbe essere un gRPC call async alla macchina ML, non una chiamata locale che alza NotImplementedError.

**Stato**: COMPLETO per il pattern daemon, NON FUNZIONALE per training effettivo (by design sul brain).

#### B.3 Training Config (196 LoC)

**Stato**: COMPLETO — Dataclass importata da optimizer_factory e altri moduli.

#### B.4 Training Callbacks (292 LoC)

**Stato**: COMPLETO — Callback registry funzionante (TensorBoard, logging, checkpointing).

#### B.5 Dataset — dataset.py (370 LoC)

**Cosa fa**: Due dataset PyTorch + factory function.

**Classi**:
- `MarketTimeSeriesDataset`: Sliding window supervisionato. Features `(context_len, dim)` + target dict. `MONEYMAKER_FEATURE_DIM = 60`.
- `MarketJEPADataset`: Contrastive learning con context, target, negatives. `gap_min=120` barre tra positivi e negativi.
- `chronological_split()`: Split temporale puro (70/15/15). **No shuffling mai** (regola critica).
- `build_dataloaders()`: Factory per train/val/test DataLoader. `shuffle=False` sempre. `pin_memory=True` se CUDA.
- `compute_sample_weight()` (linee 294-326): Recency decay (0.995^distance) + penalità 10% pre-regime shift.
- `compute_batch_weights()` (linee 329-358): Normalizzazione per WeightedRandomSampler.

**Problema CONFERMATO**: `compute_sample_weight()` e `compute_batch_weights()` sono **definiti ed esportati** ma **mai chiamati** in `build_dataloaders()` (linee 264-271). Il DataLoader non usa WeightedRandomSampler, non passa weights. Queste sono **dead code functions**.

**Stato**: COMPLETO per dataset base. **DEAD CODE** per temporal weighting (linee 294-358).

#### B.6 Loss Functions — losses.py (316 LoC)

**Stato**: COMPLETO — 5 loss functions implementate e matematicamente corrette:
1. `jepa_contrastive_loss()`: InfoNCE
2. `vl_jepa_concept_loss()`: Multi-label BCE + VICReg diversity
3. `RAPTradingLoss(nn.Module)`: 4 componenti (direction, value, sparsity, position)
4. `sharpe_aware_loss()`: |mean_error| + std_error
5. `drawdown_penalty()`: Penalità quadratica se max drawdown > 5%

#### B.7 Optimizer Factory (199 LoC)

**Stato**: COMPLETO — AdamW, warmup + decay (cosine/linear/constant), clip_gradients, reset_scheduler_for_retraining.

#### B.8 Model Evaluator (529 LoC)

**Stato**: COMPLETO — Classificazione (accuracy, F1, confusion matrix), feature importance (permutation-based), trading simulato (Sharpe, win rate, profit factor con returns unitari ±1), conviction score composito. La simulazione usa returns unitari ±1.0 — proxy accettabile per training, non comparabile con metriche reali.

#### B.9 Retraining Trigger (149 LoC)

**Stato**: COMPLETO — 4 criteri (samples ≥500, cooldown 1000 barre, drift Z>2.5, growth ≥10%). Stato **in-memory** (non persistito a Redis/DB), si perde al riavvio.

#### B.10 Early Stopping (83 LoC) + EMA (129 LoC)

**Stato**: COMPLETO — Pattern standard, nessun problema.

---

### C. Proto Contract — ml_inference.proto (56 LoC)

**Servizio**: `MLInferenceService` con 2 RPC:
- `Predict(PredictionRequest) → PredictionResponse`
- `GetModelInfo(ModelInfoRequest) → ModelInfoResponse`

**PredictionRequest**: symbol, regime, features (map<string,string>), model_version, timestamp (int64 ns UTC)

**PredictionResponse**: direction ("BUY"/"SELL"/"HOLD"), confidence (string Decimal), reasoning, model_version, model_type, metadata map, inference_time_us

**Design corretto**: Tutti i numerici sono string-encoded Decimal → no precision loss.

**Mancante**: Non c'è un RPC `StartTraining()` o `GetTrainingProgress()` per avviare/monitorare il training da remoto. Il training cycle viene triggato solo internamente.

**Stato**: COMPLETO per inferenza. Mancano RPC per orchestrazione training remota.

---

### D. Docker Configuration

**Dockerfile** (47 LoC):
```
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime
```

**Problemi critici**:
1. **GPU NVIDIA → Utente ha AMD RX 9070 XT**: L'immagine base è CUDA-only. Non funzionerà con la GPU AMD dell'utente. Serve un'immagine ROCm-compatible.
2. **docker-compose.yml**: Servizio **interamente commentato** (linee 181-357). Include configurazione per GPU nvidia, TLS certs, volumi ml-models e tensorboard.
3. **Volume ml-models**: Anch'esso commentato (linea 357).
4. **Healthcheck**: Usa `grpc.insecure_channel` — non funzionerà con TLS abilitato.

**Stato**: ERRORE — Non utilizzabile nell'ambiente dell'utente senza modifiche.

---

### E. MONEYMAKER_IMPLEMENTATION_DOCS — Cross-Reference con Codice

L'`00_INDICE_GENERALE.md` è **esemplare nella sua onestà** (linee 12-24): dichiara chiaramente che "l'infrastruttura di training ML è allo 0% — il training_orchestrator.py è uno STUB". I 20 report sono definiti come blueprint per "adattare ogni singolo pezzo dell'architettura CS2 al dominio trading".

Tuttavia, nella tabella di stato (linee 30-52), **tutti e 20** i report sono marcati "COMPLETATO" — il che è tecnicamente corretto (i **report** sono completati come **documenti di specifica**), ma è fuorviante perché suggerisce che l'**implementazione** sia completata.

#### Cross-Reference Tier 1 (Infrastruttura Training)

| Doc | Titolo | Codice Referenziato | Esiste? | Implementato? |
|-----|--------|---------------------|---------|---------------|
| T1_01 | Training Orchestrator | `algo_engine/nn/training_orchestrator.py` | Sì (158 LoC STUB) | STUB su brain. COMPLETO su ml-training (443 LoC) |
| T1_02 | 5-Phase Cycle | `ml_training/nn/training_cycle.py` | Sì (**1148 LoC**) | **IMPLEMENTATO** — fasi reali con DB load e training |
| T1_03 | DataLoader e Batch | `algo_engine/nn/dataset.py` | Sì (370 LoC) | COMPLETO — MarketTimeSeriesDataset + MarketJEPADataset |
| T1_04 | Funzioni di Perdita | `algo_engine/nn/losses.py` | Sì (316 LoC) | COMPLETO — 5 loss functions implementate |
| T1_05 | Ottimizzatori e Scheduler | `algo_engine/nn/optimizer_factory.py` | Sì (199 LoC) | COMPLETO — AdamW + schedulers |
| T1_06 | Callback e TensorBoard | `algo_engine/nn/training_callbacks.py` | Sì (292 LoC) | COMPLETO |
| T1_07 | Checkpoint Management | `ml_training/storage/checkpoint_store.py` + `algo_engine/nn/model_persistence.py` | Sì | COMPLETO — SHA-256, sidecar, auto-cleanup |

**Tier 1 reale: ~85% implementato** (aggiornato da 75% — TrainingCycle ora implementato)

#### Cross-Reference Tier 2 (Sistemi di Apprendimento)

| Doc | Titolo | Codice Referenziato | Stato Implementazione |
|-----|--------|---------------------|-----------------------|
| T2_08 | JEPA Adaptation | `algo_engine/nn/jepa_market.py` | Architettura sì, training loop nel TrainingCycle |
| T2_09 | VL-JEPA Concepts | `algo_engine/nn/concept_labeler.py` | 5/16 concetti, labeler incompleto |
| T2_10 | Experience Bank | `algo_engine/knowledge/trade_history_bank.py` | ~90% completo |
| T2_11 | Temporal Baseline | `algo_engine/features/feature_drift.py` + `regime_shift.py` | ~85% codice, **NON WIRED** (pesi ignorati) |
| T2_12 | Maturity Gating | `algo_engine/nn/maturity_gate.py` | ~85% completo |

**Tier 2 reale: ~60% implementato** (T2_11 temporal weighting non funzionale)

#### Cross-Reference Tier 3 (Percezione e Sicurezza)

| Doc | Titolo | Codice Referenziato | Stato Implementazione |
|-----|--------|---------------------|-----------------------|
| T3_13 | Market-POV | `algo_engine/features/pipeline.py` | ~90% completo |
| T3_14 | Tensor Factory | `algo_engine/processing/tensor_factory.py` | ~90% completo |
| T3_15 | Safety Systems | `algo_engine/signals/` (kill_switch, spiral, sizer, validator) | ~90% completo |
| T3_16 | Eval Metrics | `algo_engine/nn/model_evaluator.py` | ~80% completo (Calmar, regime-conditional aggiunti) |

**Tier 3 reale: ~88% implementato**

#### Cross-Reference Tier 4 (Enhancement)

| Doc | Titolo | Codice Referenziato | Stato Implementazione |
|-----|--------|---------------------|-----------------------|
| T4_17 | Regime Head | MoE gating in MarketStrategy | Deviazione architetturale (implementato diversamente, OK) |
| T4_18 | Model Factory | `algo_engine/nn/model_factory.py` | ~40% (solo RAP, manca JEPA/ensemble) |
| T4_19 | State Reconstructor | `algo_engine/processing/tensor_factory.py` | ~70% completo |
| T4_20 | Session Engine | `algo_engine/services/trading_session_engine.py` | ~85% completo |

**Tier 4 reale: ~65% implementato**

---

## Findings Critici

| # | Finding | Severità | Dove | Impatto |
|---|---------|----------|------|---------|
| F01 | **Dockerfile usa CUDA 12.1 NVIDIA, utente ha AMD RX 9070 XT** | CRITICO | `ml-training/Dockerfile:5` | GPU non utilizzata, training su CPU (10-100x più lento) |
| F02 | **docker-compose ml-training interamente commentato** | CRITICO | `docker-compose.yml:181-357` | Servizio non avviabile in container |
| F03 | ~~TrainingCycle fasi placeholder~~ → **CORRETTO**: fasi ora implementate con DB load reale, ma feature vector ha solo 8 dimensioni utili su 60 | **ALTO** | `training_cycle.py:862-908` | Modello riceve 87% zeri — feature vector quasi vuoto |
| F04 | **_best_val_loss persiste cross-fase** — early stopping potrebbe scattare erroneamente nelle fasi 2-5 | ALTO | `training_orchestrator.py:107,212-213` | Pipeline 5-fasi potrebbe abortire prematuramente |
| F05 | **TrainingWorker.request_training() sincrono** — chiama STUB che alza NotImplementedError | ALTO | `algo-engine/nn/training_worker.py` | No wiring gRPC tra brain e ml-training per il training |
| F06 | **torch.load() senza weights_only=True** — arbitrary code execution via pickle | **ALTO** | `checkpoint_store.py:186` | Security vulnerability in PyTorch ≥2.0 (CWE-502) |
| F07 | **np.random.default_rng(seed) non setta il seed globale** | MEDIO | `training_orchestrator.py:416` | Riproducibilità non garantita per numpy operations |
| F08 | **Sample weights definiti ma mai usati** (dead code) | MEDIO | `algo-engine/nn/dataset.py:264-271,294-358` | Temporal weighting T2_11 non applicato nei DataLoader |
| F09 | **Proto manca RPC per training remoto** | MEDIO | `ml_inference.proto` | Brain non può avviare/monitorare training sulla macchina ML |
| F10 | **RetrainingTrigger stato in-memory** | MEDIO | `algo-engine/nn/retraining_trigger.py` | Stato perso al riavvio servizio |
| F11 | **Model builder ml-training ≠ architetture algo-engine** | BASSO | `ml-training/nn/model_builder.py` vs `algo-engine/nn/` | _RAPStub è MLP semplice, non il MarketRAPCoach completo |
| F12 | **Input shape server (1,1,60) vs RAP Coach (batch,seq,188)** | BASSO | `server.py:199-202` | Incompatibile se si sostituisce _RAPStub con RAP Coach |
| F13 | **SIGINT handler non funziona su Windows** | BASSO | `ml-training/main.py:78` | Solo in sviluppo locale, OK in Docker Linux |
| F14 | **20 docs "COMPLETATO" ma sono specifiche** | INFO | `00_INDICE_GENERALE.md:30-52` | Fuorviante — l'indice stesso chiarisce (riga 14) che sono blueprint |
| F15 | **AMP GradScaler deprecated** | BASSO | `training_orchestrator.py:155-156,314` | `torch.cuda.amp.GradScaler()` → `torch.amp.GradScaler("cuda")` |
| F16 | **_create_weighted_loaders ignora i pesi** | ALTO | `training_cycle.py:1130-1141` | Fase 3 temporal weighting completamente non funzionale |
| F17 | **_bars_to_features solo 8 feature reali su 60** | ALTO | `training_cycle.py:862-908` | 52 dimensioni zero-padded — indicatori tecnici non calcolati |
| F18 | **conftest.py vuoto** — nessun fixture pytest | BASSO | `ml-training/tests/conftest.py` | Solo path setup, nessun fixture condiviso |
| F19 | **Nessun test per training loop effettivo** | ALTO | `ml-training/tests/` | 6 test smoke, 0% coverage epoch loop |

**Totale**: 2 CRITICO, 7 ALTO, 4 MEDIO, 4 BASSO, 2 INFO

---

## Interconnessioni

```
┌──────────────────────────────────────────────────────────────────────┐
│                    FLUSSO DI TRAINING END-TO-END                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────┐                                │
│  │  AI BRAIN (Inference Machine)   │                                │
│  │  ┌───────────────┐             │                                │
│  │  │ main.py       │─ ZMQ sub ──>│ Riceve barre OHLCV             │
│  │  │ (bar loop)    │             │                                │
│  │  └───────┬───────┘             │                                │
│  │          │ feature vector (60)  │                                │
│  │          ▼                      │                                │
│  │  ┌───────────────┐             │                                │
│  │  │ FeatureDrift  │             │                                │
│  │  │ (Z-score)     │─ drift ──>  │                                │
│  │  └───────┬───────┘             │                                │
│  │          │                      │                                │
│  │          ▼                      │                                │
│  │  ┌───────────────────┐         │                                │
│  │  │ RetrainingTrigger │         │                                │
│  │  │ 4 criteri:        │         │                                │
│  │  │ • initial ≥500    │         │                                │
│  │  │ • cooldown 1000bar│         │                                │
│  │  │ • drift Z>2.5     │         │                                │
│  │  │ • growth ≥10%     │         │                                │
│  │  └───────┬───────────┘         │                                │
│  │          │ should_retrain=True  │                                │
│  │          ▼                      │                                │
│  │  ┌───────────────────┐         │     ┌─────────────────────┐   │
│  │  │ TrainingWorker    │─ STUB ──┼──X──│  ML TRAINING LAB    │   │
│  │  │ (daemon thread)   │ raises  │     │  (Macchina ML GPU)  │   │
│  │  └───────────────────┘ NotImpl │     │                     │   │
│  │                                │     │  ┌───────────────┐  │   │
│  │  ┌───────────────────┐         │     │  │TrainingCycle  │  │   │
│  │  │ MLProxyStrategy   │◄─gRPC───┼─────┤  │ 5 fasi        │  │   │
│  │  │ (fallback HOLD)   │ 50056   │     │  │ (1148 LoC)    │  │   │
│  │  └───────────────────┘         │     │  │ IMPLEMENTATO  │  │   │
│  │                                │     │  └───────┬───────┘  │   │
│  └─────────────────────────────────┘     │          │          │   │
│                                          │          ▼          │   │
│  Contratto gRPC:                         │  ┌───────────────┐  │   │
│  ┌─────────────────────┐                 │  │Training       │  │   │
│  │ ml_inference.proto   │                 │  │Orchestrator   │  │   │
│  │ • Predict()          │                 │  │(443 LoC)      │  │   │
│  │ • GetModelInfo()     │                 │  │epoch loop     │  │   │
│  │ (manca: StartTrain)  │                 │  │gradient clip  │  │   │
│  └─────────────────────┘                 │  │early stopping │  │   │
│                                          │  │AMP optional   │  │   │
│  Componenti algo-engine condivisi:          │  └───────┬───────┘  │   │
│  ┌──────────────────────────────┐        │          │          │   │
│  │ dataset.py (370 LoC)         │        │          ▼          │   │
│  │ • MarketTimeSeriesDataset    │        │  ┌───────────────┐  │   │
│  │ • MarketJEPADataset          │        │  │Checkpoint     │  │   │
│  │ • chronological_split()      │        │  │Store (244 LoC)│  │   │
│  │ • build_dataloaders()        │        │  │SHA-256 + JSON │  │   │
│  │ ⚠ sample weights: DEAD CODE │        │  └───────┬───────┘  │   │
│  ├──────────────────────────────┤        │          │ .pt file │   │
│  │ losses.py (316 LoC)          │        │          ▼          │   │
│  │ • jepa_contrastive (InfoNCE) │        │  ┌───────────────┐  │   │
│  │ • vl_jepa_concept (BCE+VICReg│        │  │MLInference    │  │   │
│  │ • RAPTradingLoss (4-comp)    │        │  │Servicer       │  │   │
│  │ • sharpe_aware_loss          │        │  │(343 LoC)      │  │   │
│  │ • drawdown_penalty           │        │  │gRPC server    │  │   │
│  ├──────────────────────────────┤        │  └───────────────┘  │   │
│  │ optimizer_factory.py (199 LoC│        │                     │   │
│  │ model_evaluator.py (529 LoC) │        └─────────────────────┘   │
│  │ early_stopping.py (83 LoC)   │                                  │
│  │ ema.py (129 LoC)             │                                  │
│  └──────────────────────────────┘                                  │
│                                                                      │
│  CONNESSIONE MANCANTE: brain → ml-training per AVVIARE training      │
│  (nessun RPC StartTraining, nessun gRPC client nel brain per questo) │
│                                                                      │
│  BUG CRITICO: feature vector 8/60 dimensioni reali (87% zeri)       │
│  BUG CRITICO: temporal weighting calcolato ma MAI applicato          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Path Verso un Modello Addestrato

### Prerequisiti Hardware
- **GPU**: AMD RX 9070 XT con ROCm 6.x installato (RDNA4)
- **RAM**: ≥32 GB (training + database)
- **Storage**: SSD per checkpoint (ogni checkpoint ~50-200 MB)
- **Proxmox VM 102**: Dedicata al training con GPU passthrough

### 5-Phase Training Cycle (Stato Implementazione)

```
Fase 1: JEPA Pre-training          Fase 2: Backtest Baseline
┌─────────────────────┐            ┌─────────────────────┐
│ IMPLEMENTATO ✅      │            │ IMPLEMENTATO ✅      │
│ Input: ≥1000 barre  │            │ Input: ≥50 trade    │
│ OHLCV da DB         │            │ vincenti da backtest│
│                     │            │                     │
│ Modello: JEPA       │───cp───>   │ Modello: fine-tune  │
│ Loss: InfoNCE       │            │ Loss: CrossEntropy   │
│ ⚠ Solo 8 feature!  │            │                     │
└─────────────────────┘            └─────────┬───────────┘
                                             │
Fase 3: Live Adaptation            Fase 4: RAP Optimization
┌─────────────────────┐            ┌─────────────────────┐
│ IMPLEMENTATO ⚠      │            │ IMPLEMENTATO ✅      │
│ Input: ≥20 trade    │            │ Input: mix trade    │
│ reali dell'utente   │◄───cp───   │ reali + backtest    │
│                     │            │                     │
│ Modello: fine-tune  │───cp───>   │ Modello: RAP stub   │
│ ⚠ Pesi temporali   │            │ Loss: RAP 4-comp    │
│   NON applicati!    │            │                     │
└─────────────────────┘            └─────────┬───────────┘
                                             │
                              Fase 5: Regime Head
                              ┌─────────────────────┐
                              │ IMPLEMENTATO ✅      │
                              │ Input: barre con     │
                              │ etichette regime     │◄───cp───
                              │                     │
                              │ Encoder: frozen JEPA│
                              │ Head: Linear→5 cls  │
                              │ Loss: CE sui 5 regimi│
                              └─────────────────────┘
```

### Cosa Funziona Già

| Componente | Stato | Note |
|-----------|-------|------|
| Training loop epoch-per-epoch | ✅ | ml-training/nn/training_orchestrator.py (443 LoC) |
| **5-Phase Training Cycle** | ✅ | **1148 LoC — fasi implementate con DB load reale** |
| Dataset + DataLoader | ✅ | Sliding window, JEPA contrastive, chronological split |
| Loss functions (5) | ✅ | InfoNCE, VL-JEPA concept, RAP multi-loss, Sharpe-aware, drawdown penalty |
| Optimizer + Scheduler | ✅ | AdamW + warmup/cosine/linear |
| Early stopping | ✅ | Patience-based |
| EMA weight averaging | ✅ | Decay 0.999 |
| Checkpoint persistence | ✅ | SHA-256, sidecar JSON, auto-cleanup |
| Model builder (7 varianti) | ✅ | JEPA, RAP stub ×4, Regime head |
| Retraining trigger | ✅ | 4 criteri (samples, cooldown, drift, growth) |
| gRPC inference server | ✅ | Predict() + GetModelInfo() con circuit breaker |
| Model evaluator | ✅ | Classification + trading metrics + conviction score |
| Proto contract | ✅ | Decimal string-encoded, latency tracking |

### Cosa Manca / Da Fixare

| Gap | Descrizione | Priorità | Effort |
|-----|-------------|----------|--------|
| **Feature vector 8/60** | `_bars_to_features()` produce solo 8 feature reali — aggiungere indicatori tecnici (RSI, EMA, BB, ATR) | CRITICO | 2 giorni |
| **Dockerfile ROCm** | Sostituire CUDA 12.1 con immagine ROCm-compatible | CRITICO | 2h |
| **Abilitare docker-compose** | Decommentare e adattare sezione ml-training | CRITICO | 1h |
| **torch.load security** | Aggiungere `weights_only=True` in checkpoint_store.py:186 | ALTO | 30 min |
| **_best_val_loss reset** | Reset `_best_val_loss = float("inf")` all'inizio di ogni `run_training()` | ALTO | 30 min |
| **Weighted loaders** | Implementare `_create_weighted_loaders()` con WeightedRandomSampler o peso nel loss | ALTO | 1 giorno |
| **Wire sample weights** | Usare `compute_batch_weights()` in `build_dataloaders()` di algo-engine | MEDIO | 4h |
| **Fix numpy seed** | `np.random.seed(seed)` in training_orchestrator.py:416 | MEDIO | 10 min |
| **gRPC StartTraining RPC** | Aggiungere al proto per orchestrazione remota | MEDIO | 1 giorno |
| **gRPC client nel brain** | Connettere TrainingWorker al ml-training via gRPC | MEDIO | 1 giorno |
| **Test training loop** | Test E2E: data → train → checkpoint → inference | ALTO | 2 giorni |
| **Persistere RetrainingTrigger** | Serializzare stato in Redis | BASSO | 4h |

---

## Istruzioni con Checkbox

### Segmento A: Fix GPU e Docker

- [ ] **Creare Dockerfile ROCm** — Sostituire `FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime` con un'immagine base ROCm-compatible per AMD RX 9070 XT
- [ ] **Decommentare ml-training in docker-compose.yml** — Abilitare le linee 181-357. Sostituire `nvidia` GPU driver con configurazione ROCm: `devices: ["/dev/kfd", "/dev/dri"]`
- [ ] **Decommentare volume ml-models** — Linea 357 di docker-compose.yml
- [ ] **Fix healthcheck per TLS** — Parametrizzare il check gRPC per supportare sia insecure che secure channel
- [ ] **Aggiungere `weights_only=True`** a `torch.load()` in checkpoint_store.py:186

### Segmento B: Fix Bug nel Codice

- [ ] **Fix _best_val_loss persistence** — In `training_orchestrator.py`, resettare `self._best_val_loss = float("inf")` all'inizio di `run_training()` per evitare contaminazione cross-fase
- [ ] **Fix numpy seed** — In `training_orchestrator.py:416`, cambiare `np.random.default_rng(seed)` in `np.random.seed(seed)`
- [ ] **Fix AMP deprecation** — In `training_orchestrator.py:155-156,314`, aggiornare a `torch.amp.GradScaler("cuda")` e `torch.amp.autocast("cuda")`
- [ ] **Implementare _create_weighted_loaders** — In `training_cycle.py:1130-1141`, implementare il sampling pesato o applicare i pesi nel loss della fase 3
- [ ] **Integrare sample weights in build_dataloaders** — In `algo_engine/nn/dataset.py:264-271`, usare `compute_batch_weights()` con WeightedRandomSampler (attenzione: preservare ordine cronologico)
- [ ] **Persistere RetrainingTrigger state** — Serializzare `RetrainingState` in Redis

### Segmento C: Feature Engineering (PRIORITÀ MASSIMA)

- [ ] **Espandere _bars_to_features()** — Aggiungere a `training_cycle.py:862-908`:
  - RSI (periodo 14)
  - EMA fast/slow (12/26)
  - Bollinger Bands (20,2σ)
  - ATR (14)
  - MACD + Signal line
  - Volume profile / OBV
  - Indicatori multi-timeframe
  - Target: ≥40 feature reali su 60 dimensioni
- [ ] **Allineare feature** — Garantire che i feature calcolati nel training cycle siano identici a quelli usati dal brain per l'inferenza (stessi indicatori, stesse formule, stessa normalizzazione)

### Segmento D: Connessione Brain ↔ ML Training

- [ ] **Aggiungere RPC `StartTraining`** al `ml_inference.proto` — Request: symbol, training_mode. Response: training_id, status
- [ ] **Aggiungere RPC `GetTrainingProgress`** — Request: training_id. Response: epoch, losses, progress%
- [ ] **Implementare gRPC client nel brain** — Modificare `TrainingWorker.request_training()` per gRPC
- [ ] **Feedback loop** — Meccanismo per far arrivare trade chiusi al ml-training per la Fase 3

### Segmento E: Test e Validazione

- [ ] **Test epoch loop** — `test_training_orchestrator.py`: modello piccolo, dati sintetici, verificare loss decresce
- [ ] **Test checkpoint roundtrip** — Save → load → SHA-256 match
- [ ] **Test _bars_to_features** — Verificare che produce ≥40 feature non-zero dopo il fix
- [ ] **Test _create_weighted_loaders** — Verificare che i pesi sono effettivamente applicati dopo il fix
- [ ] **Test dataset chronological split** — No data leakage
- [ ] **Test JEPA contrastive loss** — Loss diminuisce quando pred→target
- [ ] **Test model builder** — Forward pass per tutti e 7 i modelli
- [ ] **Test MLInferenceServicer Predict** — Mock model, direction ∈ {BUY,SELL,HOLD}
- [ ] **Test integration E2E** — Dati sintetici → 5 fasi → checkpoint → Predict() gRPC

### Segmento F: Documentazione

- [ ] **Aggiornare 00_INDICE_GENERALE.md** — Cambiare "COMPLETATO" in scala: SPEC_WRITTEN / IMPLEMENTED / PARTIAL
- [ ] **Aggiornare README ml-training** — Riflettere che TrainingCycle è ora implementato (1148 LoC)
- [ ] **Documentare path ROCm** — Aggiungere sezione su AMD RX 9070 XT con ROCm 6.x

---

## Riepilogo Completamento per Tier

```
Tier 1 — Infrastruttura Training:  █████████████████░░░  85%  (was 75%)
  T1_01 Orchestrator:              ████████████████████  100% (ml-training ha loop completo)
  T1_02 5-Phase Cycle:             █████████████████░░░  85%  (was 30% — fasi implementate)
  T1_03 DataLoader:                ████████████████████  100%
  T1_04 Loss Functions:            ████████████████████  100%
  T1_05 Optimizer/Scheduler:       ████████████████████  100%
  T1_06 Callbacks:                 ████████████████████  100%
  T1_07 Checkpoint:                ██████████████████░░  95%

Tier 2 — Sistemi Apprendimento:    ████████████░░░░░░░░  60%
  T2_08 JEPA Market:               ████████░░░░░░░░░░░░  40% (architettura, training nel cycle)
  T2_09 VL-JEPA Concepts:          ██████░░░░░░░░░░░░░░  30% (5/16 concepts)
  T2_10 Experience Bank:           ██████████████████░░  90%
  T2_11 Temporal Baseline:         ████████░░░░░░░░░░░░  40% (codice ok, NON WIRED)
  T2_12 Maturity Gating:           █████████████████░░░  85%

Tier 3 — Percezione e Sicurezza:   █████████████████░░░  88%
  T3_13 Market-POV:                ██████████████████░░  90%
  T3_14 Tensor Factory:            ██████████████████░░  90%
  T3_15 Safety Systems:            ██████████████████░░  90%
  T3_16 Eval Metrics:              ████████████████░░░░  80%

Tier 4 — Enhancement:              █████████████░░░░░░░  65%
  T4_17 Regime Head:               ████████████████░░░░  80%
  T4_18 Model Factory:             ████████░░░░░░░░░░░░  40%
  T4_19 State Reconstructor:       ██████████████░░░░░░  70%
  T4_20 Session Engine:            █████████████████░░░  85%

OVERALL IMPLEMENTAZIONE:           █████████████░░░░░░░  74%  (was 72%)
```

---
