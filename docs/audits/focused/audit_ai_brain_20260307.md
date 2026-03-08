# MONEYMAKER AI-Brain Service - Comprehensive Audit Report

**Date:** 2026-03-07
**Scope:** Full exhaustive audit of `program/services/algo-engine/src/algo_engine/`
**Method:** Line-by-line read of every `.py` file via 6 parallel exploration agents
**Total Files Audited:** 141 Python files
**Total Lines of Code:** ~18,500+ lines
**Test Files Reviewed:** 45 test files across unit/integration/e2e/regression/brain_verification

---

## 1. EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| Total Python files | 141 |
| Total LOC (source) | ~18,500 |
| Total LOC (tests) | ~3,000+ |
| Test files | 45 |
| Critical issues | 11 |
| High-priority issues | 15 |
| Medium issues | 30+ |
| Low/suggestions | 20+ |
| Overall quality score | **7.2 / 10** |

**Verdict:** Well-architected, mathematically sound trading intelligence platform with strong financial precision (Decimal throughout) and good modular design. Critical issues exist in margin validation, buffer eviction, position sizing inference, and secrets management that must be fixed before production deployment.

---

## 2. ARCHITECTURE OVERVIEW

```
algo_engine/                          (~18,500 LOC)
├── __init__.py                    # Package root
├── config.py                      # BrainSettings (tunable params)
├── main.py                        # 1250+ line orchestrator (14-phase pipeline)
├── kill_switch.py                 # Redis-backed emergency stop
├── grpc_client.py                 # MT5 Bridge signal transmission
├── maturity_gate.py               # Signal gating + conviction index
├── ml_feedback.py                 # ML prediction persistence buffer
│
├── core/                          # Application lifecycle (493 LOC)
│   ├── lifecycle.py               # Singleton lock, shutdown hooks
│   ├── app_config.py              # Config + paths + feature flags
│   └── resource_monitor.py        # CPU/memory/disk/GPU monitoring
│
├── nn/                            # Neural network modules (~12,500 LOC)
│   ├── __init__.py                # MaturityState, MarketState, InferenceResult
│   ├── dataset.py                 # MarketTimeSeriesDataset, MarketJEPADataset
│   ├── concept_labeler.py         # Concept labeling for VL-JEPA
│   ├── embedding_projector.py     # Embedding visualization
│   ├── inference_engine.py        # Core inference orchestrator
│   ├── jepa_market.py             # VL-JEPA market model
│   ├── model_factory.py           # Model creation factory
│   ├── model_evaluator.py         # Walk-forward evaluation
│   ├── model_persistence.py       # 4-tier checkpoint search + SHA-256
│   ├── nn_config.py               # NN hyperparameter configuration
│   ├── trading_maturity.py        # Maturity state machine
│   ├── shadow_engine.py           # Shadow model A/B testing
│   ├── retraining_trigger.py      # Drift-based retrain signals
│   ├── training_callbacks.py      # Training lifecycle callbacks
│   ├── tensorboard_callback.py    # TensorBoard integration
│   ├── training_worker.py         # Thread-based retraining daemon
│   ├── training_metrics.py        # Prometheus metrics for ML
│   ├── training_config.py         # Hyperparameter dataclasses
│   ├── training_orchestrator.py   # STUB interface for ML machine
│   ├── early_stopping.py          # Patience-based termination
│   ├── ema.py                     # Exponential model weight averaging
│   ├── losses.py                  # 4 loss families (InfoNCE, VL-JEPA, RAP, Sharpe)
│   ├── optimizer_factory.py       # AdamW + LR schedulers
│   ├── layers/
│   │   ├── superposition.py       # Superposition attention layer
│   │   └── hflayers.py            # Hopfield layer integration
│   └── rap_coach/                 # RAP Coach architecture
│       ├── __init__.py            # RAPCoach ensemble
│       ├── market_model.py        # Market prediction head
│       ├── market_perception.py   # Feature perception encoder
│       ├── market_strategy.py     # Strategy selection head
│       ├── market_memory.py       # Experience replay memory
│       ├── market_pedagogy.py     # Training curriculum
│       ├── multi_scale_scanner.py # Multi-timeframe scanning
│       ├── trading_skill.py       # Skill assessment module
│       └── signal_explanation.py  # Explainable signal output
│
├── features/                      # Feature engineering (~4,200 LOC)
│   ├── pipeline.py                # OHLCV -> feature dict orchestrator
│   ├── technical.py               # 25+ indicator implementations
│   ├── regime.py                  # Rule-based regime classification
│   ├── regime_ensemble.py         # Multi-classifier ensemble (Rule+HMM+kMeans)
│   ├── regime_shift.py            # KL divergence shift detection
│   ├── market_vectorizer.py       # 60-dim feature vector builder
│   ├── macro_features.py          # Macro-economic features (Redis)
│   ├── sessions.py                # Trading session classification
│   ├── data_quality.py            # Data validation checks
│   ├── data_sanity.py             # Out-of-bounds clamping
│   ├── leakage_auditor.py         # Data leakage prevention
│   ├── feature_drift.py           # Feature distribution monitoring
│   ├── economic_calendar.py       # Event scheduling
│   ├── mtf_analyzer.py            # Multi-timeframe analysis
│   └── state_reconstructor.py     # Tensor state reconstruction
│
├── signals/                       # Signal generation (~700 LOC)
│   ├── generator.py               # Strategy -> TradingSignal conversion
│   ├── rate_limiter.py            # Sliding-window rate limiter
│   ├── spiral_protection.py       # Consecutive loss protection
│   ├── correlation.py             # Currency exposure tracking
│   ├── position_sizer.py          # Risk-based lot calculator
│   └── validator.py               # Last-line signal validation
│
├── strategies/                    # Trading strategies (~500 LOC)
│   ├── base.py                    # ABC + SignalSuggestion
│   ├── mean_reversion.py          # BB %B + RSI strategy
│   ├── trend_following.py         # Multi-indicator confirmation
│   ├── defensive.py               # Fail-safe HOLD strategy
│   ├── regime_router.py           # Regime -> strategy routing
│   └── __init__.py                # Factory functions + ML-aware router
│
├── analysis/                      # Market analysis (~4,000 LOC)
│   ├── capital_efficiency.py      # Position sizing tier selection
│   ├── manipulation_detector.py   # Spoofing/deception detection
│   ├── strategy_classifier.py     # Dual heuristic+NN classifier
│   ├── signal_quality.py          # Shannon entropy measurement
│   ├── price_level_analyzer.py    # S/R level proximity
│   ├── pnl_momentum.py            # Win/loss streak tracking
│   ├── trade_success.py           # P(TP before SL) predictor
│   ├── market_belief.py           # Bayesian regime updater
│   ├── scenario_analyzer.py       # Expectiminimax game tree
│   └── trading_weakness.py        # Recurring mistake detector
│
├── coaching/                      # Post-trade coaching (~1,200 LOC)
│   ├── explainability.py          # Signal narrative explanation (Italian)
│   ├── hybrid_coaching.py         # Rule+NN+KB fusion coaching
│   ├── longitudinal_engine.py     # 7/30/90-day trend analysis
│   ├── correction_engine.py       # Post-trade correction generation
│   ├── nn_refinement.py           # Correction weight fine-tuning
│   ├── pro_bridge.py              # Gap analysis vs pro benchmarks
│   └── progress/longitudinal.py   # Progress tracking
│
├── knowledge/                     # COPER knowledge base (~2,000 LOC)
│   ├── backtest_miner.py          # Pattern extraction from backtests
│   ├── market_graph.py            # Graph-based market relationships
│   ├── hybrid_signal_engine.py    # ML + KB signal fusion
│   ├── trade_history_bank.py      # Experience replay system
│   ├── v1_knowledge_importer.py   # Document importer
│   ├── init_knowledge.py          # Knowledge initialization
│   └── strategy_knowledge.py      # RAG knowledge retriever
│
├── services/                      # Service orchestrators (~4,700 LOC)
│   ├── trading_advisor.py         # 4-mode cascade (COPER/Hybrid/KB/Conservative)
│   ├── llm_service.py             # Ollama LLM integration
│   ├── trading_dialogue.py        # Intent-based chat engine
│   ├── coaching_orchestrator.py   # Post-trade coaching pipeline
│   ├── feedback_correlator.py     # Prediction vs outcome correlation
│   ├── history_bank_loader.py     # Trade history DB loader
│   ├── ml_lifecycle_controller.py # Model lifecycle + A/B testing
│   ├── economic_calendar_fetcher.py # Finnhub API integration
│   ├── performance_analysis.py    # Performance reporting
│   ├── trading_session_engine.py  # Async daemon loop
│   ├── trading_model_manager.py   # Checkpoint management
│   ├── trade_lesson_generator.py  # Lesson content generation
│   └── market_analysis_orchestrator.py # Analysis module router
│
├── processing/                    # Data processing (~3,500 LOC)
│   ├── data_pipeline.py           # Walk-forward normalization
│   ├── session_stats_builder.py   # Session-level stats
│   ├── tensor_factory.py          # Tensor assembly
│   ├── baselines/
│   │   ├── entity_resolver.py     # Symbol/session registry
│   │   ├── meta_drift.py          # Statistical drift detection
│   │   ├── strategy_thresholds.py # Threshold learning
│   │   └── pro_baseline.py        # Professional benchmarks
│   └── feature_engineering/
│       ├── base_features.py       # Returns, volatility, drawdown
│       ├── rating.py              # Composite trading rating
│       ├── trade_metrics.py       # WLBH classification
│       ├── vectorizer.py          # Batch feature extraction
│       └── strategy_features.py   # ADX, slope, momentum, RSI, BB
│
├── alerting/                      # Alert system (~180 LOC)
│   ├── dispatcher.py              # Rate-limited alert routing
│   └── telegram.py                # Telegram API client
│
├── analytics/                     # Attribution (~110 LOC)
│   └── attribution.py             # Per-strategy performance tracking
│
├── storage/                       # File management (~200 LOC)
│   └── storage_manager.py         # Checkpoint rotation + disk monitoring
│
├── observability/                 # Stub
│   └── __init__.py
│
└── reporting/                     # Stub
    └── __init__.py
```

---

## 3. CRITICAL ISSUES (Fix Immediately)

### C1. Buffer Eviction Loses ML Predictions (DATA LOSS)
- **File:** `ml_feedback.py:44-46`
- **Description:** FIFO eviction when buffer full silently discards oldest prediction with no warning, retry, or metrics.
- **Impact:** ML predictions silently disappear, corrupting feedback loop.
- **Fix:** Log warning + Prometheus counter when dropping; or block until flush completes.

### C2. Position Sizer Broken for Unknown Symbols (100x SIZING ERROR)
- **File:** `signals/position_sizer.py:62-108`
- **Description:** `infer_pip_value("BTC")` returns 10 (forex default) but BTC pip_value is ~1000. Inference functions miss edge cases for non-forex instruments.
- **Impact:** 100x position sizing error on unknown symbols.
- **Fix:** Require explicit symbol in PIP_SIZES/PIP_VALUES registry, raise ValueError if missing.

### C3. Margin Calculation Ignores Account Leverage (OVERLEVERAGING)
- **File:** `signals/validator.py:237-244`
- **Description:** Hardcoded `Decimal("100000")` contract size and assumes 100:1 leverage. If account has 50:1, model overestimates available margin.
- **Impact:** Allows opening positions exceeding account limits.
- **Fix:** Read leverage from account context; add 20% safety margin buffer.

### C4. Telegram Bot Token in Plain Text (SECURITY)
- **File:** `alerting/telegram.py:27-29`
- **Description:** `bot_token` and `chat_id` stored as plain strings. No encryption, potentially logged on error.
- **CWE:** CWE-798 (Hard-coded Credentials)
- **Fix:** Use environment variables exclusively; never log token values.

### C5. SQLAlchemy Private API Coupling (FRAGILE)
- **File:** `services/feedback_correlator.py:228`, `services/history_bank_loader.py:228`
- **Description:** Accesses `row._mapping` internal SQLAlchemy API. Will break with SQLAlchemy updates.
- **Fix:** Use `dict(row)` or `row._asdict()` or proper `.keys()` iteration.

### C6. Encapsulation Violation in Model Lifecycle (DESIGN)
- **File:** `services/ml_lifecycle_controller.py:513-525`
- **Description:** `self._model_manager._model = shadow_model` directly mutates manager's private state. Also uses `getattr(self._shadow_engine, "_model", None)`.
- **Fix:** Add public methods `set_model()` / `get_model()` to manager classes.

### C7. Hardcoded Column Order Mismatch (DATA CORRUPTION)
- **File:** `services/feedback_correlator.py:369-371`
- **Description:** `_row_to_dict()` hardcoded column names don't match SQL query output column order (lines 98-139).
- **Fix:** Use column-name-based access instead of positional.

### C8. True Range Calculation Error (INCORRECT INDICATOR)
- **File:** `processing/feature_engineering/strategy_features.py:56-65`
- **Description:** True Range calculation omits `abs(low[i] - close[i-1])` term; uses subtraction directly without absolute value.
- **Fix:** Add `abs()` wrapper to close-to-close component.

### C9. Unsafe External API Deserialization
- **File:** `services/economic_calendar_fetcher.py:239`
- **Description:** No schema validation on Finnhub API JSON response. Malformed response silently propagates.
- **Fix:** Add pydantic schema validation for API responses.

### C10. Division by Zero in Sharpe-Aware Loss
- **File:** `nn/losses.py:274`
- **Description:** `errors.std()` can be 0 if all errors identical, causing division by zero.
- **Fix:** Add `max(errors.std(), 1e-8)` guard.

### C11. Zero-ATR Generates Signals Without Stop-Loss
- **File:** `signals/generator.py:84-95`
- **Description:** If ATR=0, SL and TP both remain 0. No validation or warning logged.
- **Impact:** Signals execute without protective stop-loss.
- **Fix:** Return None / reject signal when ATR <= 0.

---

## 4. HIGH-PRIORITY ISSUES (Fix This Sprint)

### H1. Dead Code in gRPC Client
- **File:** `grpc_client.py:192-196`
- `_start_trade_stream()` never called. Remove or implement.

### H2. Kill Switch Has No Persistent Audit Log
- **File:** `kill_switch.py`
- Activation/deactivation events only logged transiently. Should write to database for compliance.

### H3. Config Stores Telegram Tokens as Plain Strings
- **File:** `config.py`
- No masking in log output. API keys visible in debug logs.

### H4. Validator Silently Disables Correlation Check
- **File:** `signals/validator.py:255-268`
- If `correlation_checker` is None, all exposure checks bypassed without logging.

### H5. Hardcoded ML Priors in Regime Ensemble
- **File:** `features/regime_ensemble.py:113-125, 178-182`
- HMM means/stds and k-Means centroids are fixed in code, not learned or configurable.

### H6. Feature Schema Not Version-Controlled
- **File:** `processing/feature_engineering/vectorizer.py:31, 34-103`
- METADATA_DIM=60 must match NN exactly. Any feature change breaks all saved models. No version check.

### H7. Hardcoded Symbol/Session Registry
- **File:** `processing/baselines/entity_resolver.py:55-168`
- All symbols and sessions hardcoded in Python. No external config, no DST handling.

### H8. Trading Session Engine Race Conditions
- **File:** `services/trading_session_engine.py:102, 196`
- `asyncio.Event()` and `state.paused` accessed without synchronization primitives.

### H9. main.py Circular Reference Risk
- **File:** `main.py`
- 1250+ lines importing from services, features, nn, signals. Global singletons without explicit lifecycle.

### H10. gRPC Client Has No Retry/Circuit Breaker
- **File:** `grpc_client.py`
- Single attempt with 10s timeout. No exponential backoff, no circuit breaker.

### H11. Stale Hardcoded Pro Benchmarks
- **File:** `processing/baselines/pro_baseline.py:66-127`
- Professional trader baselines with no versioning/dating. May be outdated.

### H12. Direction Enum Mismatch in Validator
- **File:** `signals/validator.py:112-113`
- Receives string "HOLD" but compares with `Direction.HOLD` enum. Works by coercion coincidence.

### H13. Trade Lesson Generator Logic Error
- **File:** `services/trade_lesson_generator.py:255`
- `worst < avg_pnl * 3` is wrong -- should be `abs(worst) > avg_pnl * 3` for drawdown check.

### H14. Correlation Checker Allows Unmapped Symbols
- **File:** `signals/correlation.py:95`
- Returns True (permissive) for symbols not in CURRENCY_PAIRS. Should log warning.

### H15. Model Manager No State Persistence
- **File:** `services/ml_lifecycle_controller.py`
- DailyMetrics, ABTestingState, PromotionState, DegradationState all lost on restart.

---

## 5. MEDIUM-PRIORITY ISSUES

| # | File | Issue |
|---|------|-------|
| M1 | `nn/model_persistence.py:75` | SHA-256 computed twice per load (inefficient) |
| M2 | `core/resource_monitor.py:137-138` | Threshold values hardcoded (should be constructor params) |
| M3 | `storage/storage_manager.py` | No atomic file operations (corruption risk during save) |
| M4 | `nn/optimizer_factory.py:86` | Potential division instability in warmup calculation |
| M5 | `core/app_config.py:110` | `enable_jepa_model` hardcoded to False |
| M6 | `nn/training_worker.py` | No timeout enforcement on training requests |
| M7 | `nn/training_config.py` | No validation that train+val+test ratios sum to 1.0 |
| M8 | `features/regime.py:137` | Confidence formula `0.50 + adx/100` not justified |
| M9 | `features/regime_shift.py:205-207` | Shift magnitude normalizer `3.0` is magic number |
| M10 | `features/market_vectorizer.py` | Placeholder ZEROs for indices 37,40,55,57,58 |
| M11 | `features/regime_ensemble.py:244` | Ensemble weights [0.5, 0.3, 0.2] not justified |
| M12 | `signals/spiral_protection.py:127` | Sets `_consecutive_losses = threshold` post-cooldown |
| M13 | `analysis/scenario_analyzer.py` | Leaf node evaluation trivial for game tree sophistication |
| M14 | `analysis/market_belief.py:195-209` | Normalization computed twice (redundant) |
| M15 | `coaching/explainability.py` | No validation that deviation keys match expected axes |
| M16 | `coaching/longitudinal_engine.py:112` | Only returns top 3 insights, discards rest |
| M17 | `knowledge/strategy_knowledge.py:148-152` | SHA-256 seeded RNG fallback embedding is weak |
| M18 | `knowledge/trade_history_bank.py:189` | No PnL bounds checking (NaN/Inf) |
| M19 | `services/coaching_orchestrator.py:206-211` | `except Exception` swallows all errors |
| M20 | `services/feedback_correlator.py:301-302` | No division-by-zero check for win_rate |
| M21 | `services/llm_service.py:83` | Side-effect: `self.model = model_names[0]` in is_available() |
| M22 | `services/performance_analysis.py:123` | Float boundary crossing from Decimal to numpy |
| M23 | `services/trading_model_manager.py:166` | `weights_only=True` requires recent torch (no version check) |
| M24 | `processing/data_pipeline.py:239` | Modifies scaler parameters in-place after fitting |
| M25 | `processing/tensor_factory.py:167-169` | Zero-padding changes statistical properties |
| M26 | `processing/baselines/meta_drift.py:31-32` | Hardcoded weights not exposed for tuning |
| M27 | `processing/feature_engineering/rating.py:45-55` | Hardcoded benchmarks undocumented |
| M28 | `processing/feature_engineering/strategy_features.py:193` | BB num_std=2.0 hardcoded |
| M29 | `alerting/dispatcher.py:75` | Rate-limit key format can cause unrelated alerts to collide |
| M30 | `analytics/attribution.py:45-46` | Division by zero returns magic 999.99 |

---

## 6. MATHEMATICAL CORRECTNESS AUDIT

### Technical Indicators (features/technical.py -- 657 lines)

| Indicator | Formula | Status |
|-----------|---------|--------|
| RSI | Wilder smoothing (alpha=1/period), RS=avg_gain/avg_loss | CORRECT |
| EMA | Seed with SMA, multiplier=2/(period+1) | CORRECT |
| MACD | Fast/Slow/Signal EMAs, histogram | CORRECT |
| Bollinger Bands | SMA +/- 2*stdev, Decimal sqrt via Newton's method | CORRECT |
| ATR | True Range + Wilder smoothing | CORRECT |
| ADX | +DM/-DM directional movement, Wilder smoothing, DX | CORRECT |
| Stochastic | %K=(C-L)/(H-L)*100, %D=SMA(%K) | CORRECT |
| CCI | (TP-SMA(TP))/(0.015*MD) | CORRECT |
| Donchian | Max/Min of period window | CORRECT |
| Williams %R | -100*(High-Close)/(High-Low) | CORRECT |

### Neural Network Losses (nn/losses.py -- 315 lines)

| Loss | Status | Issue |
|------|--------|-------|
| InfoNCE contrastive | CORRECT | None |
| VL-JEPA concept | CORRECT | None |
| RAP multi-loss (direction+value+sparsity+positioning) | CORRECT | None |
| Sharpe-aware loss | BUG | `errors.std()` can be 0 -> division by zero |
| Drawdown penalty | CORRECT | None |

### Ensemble Math (features/regime_ensemble.py -- 416 lines)

| Component | Status |
|-----------|--------|
| KL Divergence (symmetric) | CORRECT -- (D(P||Q)+D(Q||P))/2 |
| HMM Gaussian emission | CORRECT -- posterior proportional to likelihood x prior |
| k-Means soft assignment (inverse-distance) | CORRECT |
| Weighted voting + normalization | CORRECT |
| Hysteresis anti-whipsaw | CORRECT |

### Financial Calculations

| Calculation | File | Status |
|-------------|------|--------|
| Decimal precision throughout | All | CORRECT |
| SL/TP via ATR multiplier | generator.py | CORRECT (but missing zero-ATR guard) |
| Risk/reward ratio | generator.py | CORRECT |
| Sharpe ratio | base_features.py | CORRECT (252 annualization) |
| Log returns | base_features.py | CORRECT |
| Max drawdown | base_features.py | CORRECT |
| Position sizing (Kelly-derived) | position_sizer.py | BUG (inference for unknown symbols) |

**Overall Mathematical Score: 9/10** -- All core indicators correct, 2 edge-case bugs found.

---

## 7. SECURITY AUDIT (OWASP-Aligned)

| Category | Status | Details |
|----------|--------|---------|
| Injection (SQL/Command) | SAFE | No SQL concatenation, parameterized queries via SQLAlchemy |
| Authentication | N/A | Internal service, no user auth |
| Sensitive Data Exposure | WARNING | Telegram token in plain text (C4); API keys may appear in logs |
| Deserialization | SAFE | `torch.load(weights_only=True)` prevents code execution |
| Access Control | N/A | Internal service |
| Security Misconfiguration | WARNING | 9 mypy modules with `ignore_errors=true` |
| XSS | N/A | No web interface |
| Dependencies | CHECK | `protobuf>=4.25` may be outdated; run `pip audit` |
| Logging | GOOD | Structured logging via moneymaker_common throughout |
| Input Validation | PARTIAL | Strategies don't validate feature dict keys; validator has gaps |

**Security Risk: LOW-MEDIUM** -- No external attack surface, but secrets management needs hardening.

---

## 8. CODE QUALITY SCORES BY MODULE

| Module | LOC | Files | Quality | Key Strengths | Key Weaknesses |
|--------|-----|-------|---------|---------------|----------------|
| core/ | 493 | 3 | 8.0/10 | Clean lifecycle, graceful degradation | Hardcoded thresholds |
| nn/ | ~12,500 | 26 | 7.2/10 | Strong model security, comprehensive losses | Stubs, EMA edge case |
| features/ | ~4,200 | 15 | 7.8/10 | Mathematical correctness, Decimal precision | Magic numbers, hardcoded ML priors |
| signals/ | ~700 | 6 | 6.5/10 | Good rate limiting, spiral protection | **Critical: position sizer, validator** |
| strategies/ | ~500 | 6 | 8.5/10 | Clean ABC, good factory pattern | Hardcoded thresholds |
| analysis/ | ~4,000 | 10 | 7.5/10 | Comprehensive analysis, Bayesian updates | Scenario analyzer trivial evaluation |
| coaching/ | ~1,200 | 7 | 7.0/10 | Good cascade, graceful degradation | Italian language inconsistency |
| knowledge/ | ~2,000 | 7 | 7.5/10 | Strong COPER pattern, experience replay | Weak fallback embedding, no dedup |
| services/ | ~4,700 | 14 | 6.4/10 | Good cascade patterns | **SQLAlchemy coupling, encapsulation violations** |
| processing/ | ~3,500 | 16 | 6.5/10 | Good statistical methods | **Hardcoded registries, True Range bug** |
| alerting/ | ~180 | 2 | 6.5/10 | Rate-limited dispatch | **Secrets in plain text** |
| analytics/ | ~110 | 1 | 7.5/10 | Clean tracking | Magic number for infinity |
| storage/ | ~200 | 1 | 7.0/10 | Safe deletion, disk monitoring | No atomicity |

---

## 9. TEST COVERAGE ANALYSIS

### Test Organization

| Category | Files | Purpose |
|----------|-------|---------|
| unit/ | 17 | Individual component tests |
| brain_verification/ | 12 | End-to-end pipeline verification |
| integration/ | 2 | Safety + full pipeline |
| e2e/ | 1 | Full pipeline |
| regression/ | 2 | Feature consistency + phase0 fixes |
| test_architecture.py | 1 | Service architecture validation |

### Coverage Assessment

| Component | Has Tests | Quality |
|-----------|-----------|---------|
| Kill switch | YES | Good |
| gRPC client | YES | Good |
| Technical indicators | YES | Excellent (2 test files) |
| Trend following | YES | Good |
| Mean reversion | YES | Good |
| Defensive strategy | YES | Good |
| Regime router | YES | Good |
| Strategy base | YES | Good |
| Signal generator | YES | Good |
| Signal validator | YES | Excellent (12/14 checks) |
| Spiral protection | YES | Good |
| Position sizer | YES | Excellent (edge cases) |
| ML proxy | YES | Excellent (341 lines) |
| Pipeline | YES | Good |
| Regime classifier | YES | Good |
| ZMQ adapter | YES | Good |
| Portfolio state | YES | Good |
| Feature vector consistency | YES | Excellent |
| Phase 0 regressions | YES | Excellent (10 fixes) |
| Architecture | YES | Good |
| Full pipeline | YES (3 files) | Good |
| Safety e2e | YES | Good |
| **Coaching module** | **NO** (verification only) | **GAP** |
| **Knowledge module** | **NO** (verification only) | **GAP** |
| **Analysis module** | **NO** | **GAP** |
| **Services module** | **NO** | **GAP** |
| **Processing module** | **NO** | **GAP** |
| **Alerting module** | **NO** | **GAP** |

**Test Ratio:** 45 test files / 141 source files = 32% coverage by file count. Core trading logic well-tested, but coaching/knowledge/analysis/services/processing modules lack dedicated unit tests.

---

## 10. CROSS-CUTTING CONCERNS

### A. Decimal vs Float Precision
- Pipeline, technical, vectorizer: Decimal throughout until tensor boundary. **CORRECT.**
- Conversion at numpy/torch boundary is explicit and intentional.
- **Risk areas:** `services/performance_analysis.py:123` crosses boundary without validation.

### B. Language Inconsistency
- Coaching module entirely in Italian (docstrings, messages, variable comments).
- Rest of codebase in English.
- **Impact:** Maintainability friction for non-Italian developers.

### C. Magic Numbers
- 50+ undocumented thresholds across the codebase.
- Examples: confidence baseline 0.50, ATR multiplier 2.0, ADX threshold 25, entropy caps, position thresholds.
- **Recommendation:** Extract to `constants.py` with calibration comments.

### D. Error Handling Pattern
- Prevalent `except Exception` blocks that swallow errors.
- Most log warnings but don't propagate or count failures.
- **Recommendation:** Use specific exception types; add Prometheus error counters.

### E. mypy Disabled for 9 Modules
```
algo_engine.storage.*
algo_engine.main
algo_engine.kill_switch
algo_engine.coaching.*
algo_engine.services.ml_lifecycle_controller
algo_engine.nn.embedding_projector
algo_engine.knowledge.*
algo_engine.features.macro_features
algo_engine.features.pipeline
algo_engine.features.regime_ensemble
moneymaker_common.ratelimit
```
**Risk:** Silent type errors in critical modules (coaching, knowledge, lifecycle controller).

---

## 11. STRENGTHS SUMMARY

1. **Decimal Precision** -- Entire pipeline uses `decimal.Decimal` for financial math. Float only at tensor boundary.
2. **Fail-Closed Kill Switch** -- Default blocks trading until Redis confirms safe.
3. **Model Security** -- `torch.load(weights_only=True)` prevents arbitrary code execution.
4. **4-Tier Cascade** -- TradingAdvisor gracefully degrades: COPER -> Hybrid -> KB -> Conservative.
5. **Multi-Layer Validation** -- Data quality + sanity + drift monitoring + leakage auditing.
6. **Regime-Based Routing** -- Strategy selection adapts to market conditions.
7. **Comprehensive Observability** -- Prometheus metrics, TensorBoard, structured logging.
8. **Modular Architecture** -- Clean separation of concerns across 11 modules.
9. **Graceful Degradation** -- All optional dependencies (psutil, pynvml, Ollama, Redis) handled.
10. **Good Test Foundation** -- 45 test files covering core trading logic.

---

## 12. COMPLETE FILE INVENTORY

| # | File | LOC | Quality |
|---|------|-----|---------|
| 1 | `__init__.py` | ~5 | 8/10 |
| 2 | `config.py` | 102 | 7/10 |
| 3 | `main.py` | 1250+ | 6.5/10 |
| 4 | `kill_switch.py` | 157 | 7.5/10 |
| 5 | `grpc_client.py` | 235 | 6.5/10 |
| 6 | `maturity_gate.py` | 422 | 8.5/10 |
| 7 | `ml_feedback.py` | 99 | 6.5/10 |
| 8 | `core/__init__.py` | ~5 | 8/10 |
| 9 | `core/lifecycle.py` | 164 | 8/10 |
| 10 | `core/app_config.py` | 166 | 7.5/10 |
| 11 | `core/resource_monitor.py` | 163 | 7/10 |
| 12 | `nn/__init__.py` | 124 | 8/10 |
| 13 | `nn/dataset.py` | 370 | 7/10 |
| 14 | `nn/concept_labeler.py` | ~200 | 7/10 |
| 15 | `nn/embedding_projector.py` | ~250 | 7/10 |
| 16 | `nn/inference_engine.py` | ~400 | 7/10 |
| 17 | `nn/jepa_market.py` | ~350 | 7.5/10 |
| 18 | `nn/model_factory.py` | ~200 | 7/10 |
| 19 | `nn/model_evaluator.py` | ~300 | 7/10 |
| 20 | `nn/model_persistence.py` | 416 | 8.5/10 |
| 21 | `nn/nn_config.py` | ~150 | 7/10 |
| 22 | `nn/trading_maturity.py` | ~200 | 7/10 |
| 23 | `nn/shadow_engine.py` | ~250 | 7/10 |
| 24 | `nn/retraining_trigger.py` | ~200 | 7/10 |
| 25 | `nn/training_callbacks.py` | ~200 | 7/10 |
| 26 | `nn/tensorboard_callback.py` | ~180 | 7.5/10 |
| 27 | `nn/training_worker.py` | 240 | 6.5/10 |
| 28 | `nn/training_metrics.py` | 338 | 7.5/10 |
| 29 | `nn/training_config.py` | 196 | 7/10 |
| 30 | `nn/training_orchestrator.py` | 157 | 7/10 |
| 31 | `nn/early_stopping.py` | 82 | 8/10 |
| 32 | `nn/ema.py` | 128 | 8/10 |
| 33 | `nn/losses.py` | 315 | 7.5/10 |
| 34 | `nn/optimizer_factory.py` | 198 | 7/10 |
| 35 | `nn/layers/__init__.py` | ~10 | 8/10 |
| 36 | `nn/layers/superposition.py` | ~250 | 7/10 |
| 37 | `nn/layers/hflayers.py` | ~200 | 7/10 |
| 38 | `nn/rap_coach/__init__.py` | ~300 | 7/10 |
| 39 | `nn/rap_coach/market_model.py` | ~250 | 7/10 |
| 40 | `nn/rap_coach/market_perception.py` | ~250 | 7.5/10 |
| 41 | `nn/rap_coach/market_strategy.py` | ~200 | 7/10 |
| 42 | `nn/rap_coach/market_memory.py` | ~200 | 7/10 |
| 43 | `nn/rap_coach/market_pedagogy.py` | ~250 | 7/10 |
| 44 | `nn/rap_coach/multi_scale_scanner.py` | ~200 | 7/10 |
| 45 | `nn/rap_coach/trading_skill.py` | ~200 | 7/10 |
| 46 | `nn/rap_coach/signal_explanation.py` | ~200 | 7.5/10 |
| 47 | `features/__init__.py` | ~5 | 8/10 |
| 48 | `features/pipeline.py` | 336 | 8/10 |
| 49 | `features/technical.py` | 657 | 8/10 |
| 50 | `features/regime.py` | 213 | 7/10 |
| 51 | `features/regime_ensemble.py` | 416 | 7/10 |
| 52 | `features/regime_shift.py` | 338 | 7/10 |
| 53 | `features/market_vectorizer.py` | 559 | 8/10 |
| 54 | `features/macro_features.py` | 364 | 8/10 |
| 55 | `features/sessions.py` | 81 | 9/10 |
| 56 | `features/data_quality.py` | 119 | 7/10 |
| 57 | `features/data_sanity.py` | 218 | 7/10 |
| 58 | `features/leakage_auditor.py` | 417 | 9/10 |
| 59 | `features/feature_drift.py` | 354 | 8/10 |
| 60 | `features/economic_calendar.py` | 135 | 7/10 |
| 61 | `features/mtf_analyzer.py` | 181 | 8/10 |
| 62 | `features/state_reconstructor.py` | 414 | 8/10 |
| 63 | `signals/__init__.py` | ~2 | 8/10 |
| 64 | `signals/generator.py` | 138 | 7.5/10 |
| 65 | `signals/rate_limiter.py` | 53 | 9/10 |
| 66 | `signals/spiral_protection.py` | 192 | 8/10 |
| 67 | `signals/correlation.py` | 115 | 7.5/10 |
| 68 | `signals/position_sizer.py` | 199 | 7/10 |
| 69 | `signals/validator.py` | 315 | 6/10 |
| 70 | `strategies/__init__.py` | 81 | 9/10 |
| 71 | `strategies/base.py` | 95 | 9/10 |
| 72 | `strategies/mean_reversion.py` | ~80 | 8/10 |
| 73 | `strategies/trend_following.py` | ~80 | 8/10 |
| 74 | `strategies/defensive.py` | 57 | 10/10 |
| 75 | `strategies/regime_router.py` | 126 | 9/10 |
| 76 | `analysis/__init__.py` | ~5 | 8/10 |
| 77 | `analysis/capital_efficiency.py` | 507 | 7.5/10 |
| 78 | `analysis/manipulation_detector.py` | 251 | 7/10 |
| 79 | `analysis/strategy_classifier.py` | 589 | 7.5/10 |
| 80 | `analysis/signal_quality.py` | 202 | 7.5/10 |
| 81 | `analysis/price_level_analyzer.py` | 531 | 7.5/10 |
| 82 | `analysis/pnl_momentum.py` | 270 | 7/10 |
| 83 | `analysis/trade_success.py` | 261 | 7/10 |
| 84 | `analysis/market_belief.py` | 458 | 7.5/10 |
| 85 | `analysis/scenario_analyzer.py` | 425 | 7/10 |
| 86 | `analysis/trading_weakness.py` | 251 | 7/10 |
| 87 | `coaching/__init__.py` | ~5 | 8/10 |
| 88 | `coaching/explainability.py` | 300 | 7/10 |
| 89 | `coaching/hybrid_coaching.py` | 209 | 7/10 |
| 90 | `coaching/longitudinal_engine.py` | 238 | 7/10 |
| 91 | `coaching/correction_engine.py` | 201 | 7/10 |
| 92 | `coaching/nn_refinement.py` | 170 | 7/10 |
| 93 | `coaching/pro_bridge.py` | 198 | 7/10 |
| 94 | `coaching/progress/__init__.py` | ~5 | 8/10 |
| 95 | `coaching/progress/longitudinal.py` | ~150 | 7/10 |
| 96 | `knowledge/__init__.py` | 12 | 8/10 |
| 97 | `knowledge/backtest_miner.py` | ~400 | 7/10 |
| 98 | `knowledge/market_graph.py` | 291 | 7.5/10 |
| 99 | `knowledge/hybrid_signal_engine.py` | ~500 | 7/10 |
| 100 | `knowledge/trade_history_bank.py` | 608 | 8/10 |
| 101 | `knowledge/v1_knowledge_importer.py` | 288 | 7/10 |
| 102 | `knowledge/init_knowledge.py` | 231 | 7.5/10 |
| 103 | `knowledge/strategy_knowledge.py` | 295 | 8/10 |
| 104 | `services/__init__.py` | 9 | 8/10 |
| 105 | `services/trading_advisor.py` | 507 | 6.5/10 |
| 106 | `services/llm_service.py` | 252 | 6/10 |
| 107 | `services/trading_dialogue.py` | 318 | 7/10 |
| 108 | `services/coaching_orchestrator.py` | 396 | 7/10 |
| 109 | `services/feedback_correlator.py` | 475 | 6/10 |
| 110 | `services/history_bank_loader.py` | 331 | 6/10 |
| 111 | `services/ml_lifecycle_controller.py` | 752 | 5/10 |
| 112 | `services/economic_calendar_fetcher.py` | 529 | 6/10 |
| 113 | `services/performance_analysis.py` | 199 | 7/10 |
| 114 | `services/trading_session_engine.py` | 270 | 6/10 |
| 115 | `services/trading_model_manager.py` | 325 | 6/10 |
| 116 | `services/trade_lesson_generator.py` | 400 | 6/10 |
| 117 | `services/market_analysis_orchestrator.py` | 424 | 7/10 |
| 118 | `processing/__init__.py` | 20 | 8/10 |
| 119 | `processing/data_pipeline.py` | 270 | 6/10 |
| 120 | `processing/session_stats_builder.py` | 215 | 7/10 |
| 121 | `processing/tensor_factory.py` | 241 | 6/10 |
| 122 | `processing/baselines/__init__.py` | 16 | 8/10 |
| 123 | `processing/baselines/entity_resolver.py` | 274 | 5/10 |
| 124 | `processing/baselines/meta_drift.py` | 212 | 7/10 |
| 125 | `processing/baselines/strategy_thresholds.py` | 281 | 6/10 |
| 126 | `processing/baselines/pro_baseline.py` | 360 | 5/10 |
| 127 | `processing/feature_engineering/__init__.py` | 16 | 8/10 |
| 128 | `processing/feature_engineering/base_features.py` | 223 | 7/10 |
| 129 | `processing/feature_engineering/rating.py` | 312 | 6/10 |
| 130 | `processing/feature_engineering/trade_metrics.py` | 302 | 7/10 |
| 131 | `processing/feature_engineering/vectorizer.py` | 175 | 6/10 |
| 132 | `processing/feature_engineering/strategy_features.py` | 506 | 6/10 |
| 133 | `processing/validation/__init__.py` | 14 | 8/10 |
| 134 | `alerting/__init__.py` | ~3 | 8/10 |
| 135 | `alerting/dispatcher.py` | 111 | 7/10 |
| 136 | `alerting/telegram.py` | 73 | 6.5/10 |
| 137 | `analytics/__init__.py` | 4 | 8/10 |
| 138 | `analytics/attribution.py` | 109 | 7.5/10 |
| 139 | `storage/storage_manager.py` | 201 | 7/10 |
| 140 | `observability/__init__.py` | ~5 | N/A |
| 141 | `reporting/__init__.py` | ~5 | N/A |

---

## 13. PRIORITIZED REMEDIATION ROADMAP

### Phase 1: Critical Safety (Immediate)
1. Fix position_sizer.py symbol inference (C2)
2. Fix validator.py margin calculation (C3)
3. Fix generator.py zero-ATR guard (C11)
4. Fix losses.py division by zero (C10)
5. Move Telegram token to env var (C4)
6. Fix feedback_correlator.py column order (C7)

### Phase 2: Data Integrity (This Week)
7. Fix ml_feedback.py buffer eviction (C1)
8. Fix SQLAlchemy private API usage (C5)
9. Fix strategy_features.py True Range bug (C8)
10. Add schema validation for Finnhub API (C9)
11. Fix ml_lifecycle_controller encapsulation (C6)

### Phase 3: Robustness (This Sprint)
12. Add gRPC retry + circuit breaker (H10)
13. Add kill switch audit logging (H2)
14. Log when correlation check bypassed (H4)
15. Fix trading_session_engine race conditions (H8)
16. Fix trade_lesson_generator logic error (H13)
17. Persist lifecycle controller state (H15)

### Phase 4: Configuration (Next Sprint)
18. Extract ML priors to config files (H5)
19. Externalize symbol/session registry (H7)
20. Add feature schema versioning (H6)
21. Document all magic numbers
22. Extract thresholds to constants.py

### Phase 5: Quality (Backlog)
23. Add unit tests for coaching, knowledge, analysis, services modules
24. Enable mypy for disabled modules
25. Standardize Italian coaching to English
26. Refactor main.py (1250+ lines) into smaller modules
27. Remove dead code (grpc_client._start_trade_stream)
28. Add ANN index to knowledge retriever (FAISS)
