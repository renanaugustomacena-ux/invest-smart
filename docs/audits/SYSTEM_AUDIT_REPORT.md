# MONEYMAKER V1 — System Audit Report v2.0

> **Version**: 2.0 | **Date**: 2026-03-09
> **Scope**: 7 services, ~12,961 LoC algo-engine, pure algorithmic/mathematical architecture
> **Standards**: ISO/IEC 25010, ISO 27001, OWASP Top 10, IEEE 730, STRIDE
> **Previous**: v1.0 (11 consolidated audits, 45 findings)
> **Classification**: Internal — Confidential

---

## Table of Contents

1. [Executive Dashboard](#1-executive-dashboard)
2. [Architecture & Service Map](#2-architecture--service-map)
3. [Algo-Engine Core Pipeline](#3-algo-engine-core-pipeline)
4. [Feature Pipeline & Regime Classification](#4-feature-pipeline--regime-classification)
5. [Mathematical Modules](#5-mathematical-modules)
6. [Strategy Suite](#6-strategy-suite)
7. [Safety Systems & Risk Management](#7-safety-systems--risk-management)
8. [Backtesting Infrastructure](#8-backtesting-infrastructure)
9. [Optimization Suite](#9-optimization-suite)
10. [Data Ingestion & Database](#10-data-ingestion--database)
11. [MT5 Bridge & Execution](#11-mt5-bridge--execution)
12. [Infrastructure, CI/CD & Security](#12-infrastructure-cicd--security)
13. [Test Coverage & Quality](#13-test-coverage--quality)
14. [Dependency Audit](#14-dependency-audit)
15. [Performance Analysis](#15-performance-analysis)
16. [Consolidated Findings](#16-consolidated-findings)
17. [Risk Heat Map](#17-risk-heat-map)
18. [Production Readiness Matrix](#18-production-readiness-matrix)
19. [Remediation Roadmap](#19-remediation-roadmap)
20. [Appendices](#20-appendices)

---

## 1. Executive Dashboard

### 1.1 Overall Quality Score

**Quality Score: 8.2 / 10** (up from 7.5 in v1.0)

| ISO/IEC 25010 Dimension | Score | Trend | Notes |
|--------------------------|-------|-------|-------|
| Functional Suitability | 8.5 | UP | Core pipeline bugs F01, F02 fixed; 7 strategies operational |
| Performance Efficiency | 7.5 | STABLE | 5s timeout, Decimal overhead acceptable for financial precision |
| Compatibility | 7.0 | UP | Port alignment fixed; proto contracts stable |
| Usability | 7.0 | STABLE | 80+ console commands; TUI functional but 0 tests |
| Reliability | 8.0 | UP | Kill switch fixed; spiral Redis persistence added |
| Security | 7.5 | UP | Backend network internal; TLS conditional; .env history remains |
| Maintainability | 9.0 | UP | main.py refactored 1,609→530 LoC; clean AlgoEngine class |
| Portability | 6.5 | STABLE | MT5 Bridge Windows-only remains architectural constraint |

### 1.2 Findings Summary

| Severity | v1.0 | Fixed | Still Open | New | v2.0 Total |
|----------|------|-------|------------|-----|------------|
| CRITICAL | 9 | 7 | 2 | 1 | 3 |
| HIGH | 14 | 9 | 5 | 3 | 8 |
| MEDIUM | 0 | 0 | 0 | 8 | 8 |
| WARNING | 22 | 7 | 15 | 5 | 20 |
| **Total** | **45** | **23** | **22** | **17** | **39** |

**51% of v1.0 findings resolved.** Net reduction from 45 to 39 findings, with 17 new findings identified in expanded scope (math modules, backtesting, optimization, CI/CD, Grafana security).

### 1.3 Production Readiness Traffic Lights

```
Service             Code  Tests  Safety  Deploy  Overall
─────────────────────────────────────────────────────────
data-ingestion      [G]   [A]    [G]     [G]     [G] GREEN
algo-engine         [G]   [A]    [G]     [G]     [G] GREEN
mt5-bridge          [A]   [A]    [A]     [R]     [R] RED
console             [G]   [R]    [G]     [A]     [A] AMBER
dashboard           [A]   [R]    [A]     [A]     [A] AMBER
external-data       [A]   [R]    [A]     [R]     [R] RED
monitoring          [G]   [G]    [G]     [G]     [G] GREEN

Legend: [G]=Green (ready) [A]=Amber (needs work) [R]=Red (blocked)
```

### 1.4 Top 5 Risks

| # | Risk | Impact | Section |
|---|------|--------|---------|
| 1 | MT5 Bridge cannot run in Docker Linux (Windows-only) | Cannot deploy unified stack | 11 |
| 2 | `.env` password remains in git history | Credential compromise | 12 |
| 3 | Feedback loop incomplete (closed trades not streamed) | Stale portfolio state | 11 |
| 4 | CI references removed ml-training service | CI pipeline fails | 12 |
| 5 | Grafana anonymous admin access in docker-compose | Dashboard takeover | 12 |

### 1.5 Key Metrics

| Metric | Value |
|--------|-------|
| Total Source Files | ~120+ |
| Total Lines of Code | ~35,000+ |
| Algo-Engine LoC | 12,961 |
| Test Files | ~35 |
| Test Count | ~380+ |
| Test Pass Rate | 100% |
| Strategies | 9 (7 active + 2 base/router) |
| Math Modules | 8 (3,386 LoC) |
| Prometheus Metrics | 28 defined |
| Alert Rules | 10 |
| Grafana Dashboards | 5 |
| Docker Services | 7 |
| Proto Definitions | 4 |
| Safety Layers | 7 |

---

## 2. Architecture & Service Map

### 2.1 Service Topology

```
                        +-----------+
                        |  Polygon  |
                        |  (Forex)  |
                        +-----+-----+
                              | WebSocket/HTTPS
                              v
+------------------------------------------------------------------+
|                    DOCKER COMPOSE STACK                            |
|                                                                   |
|  +------------------+     ZMQ PUB     +------------------+        |
|  | data-ingestion   | ==============> | algo-engine      |        |
|  | (Go)             |   :5555         | (Python)         |        |
|  | :9090 metrics    |                 | :50057 gRPC      |        |
|  | :9091 health     |                 | :8087 REST       |        |
|  +--------+---------+                 | :9097 metrics    |        |
|           |                           +--------+---------+        |
|           | SQL (batch COPY)                   |                  |
|           v                                    | gRPC :50055      |
|  +------------------+                          v                  |
|  | PostgreSQL 16    |                 +------------------+        |
|  | TimescaleDB      |<---------------| mt5-bridge       |        |
|  | (:5432)          |     SQL        | (Python)         |        |
|  +--------+---------+                | :50055 gRPC      |        |
|           ^                          | :9094 metrics    |        |
|           |                          +--------+---------+        |
|  +------------------+                         |                  |
|  | Redis 7          |                         | MT5 API          |
|  | (:6379)          |                         v                  |
|  +------------------+                +------------------+        |
|                                      | MetaTrader 5     |        |
|  +------------------+                | (Windows VM)     |        |
|  | dashboard        |                +------------------+        |
|  | (:8888)          |                                            |
|  +------------------+  +------------------+  +------------------+|
|                        | Prometheus       |  | Grafana          ||
|                        | (:9091→9090)     |  | (:3000)          ||
|                        +------------------+  +------------------+|
+------------------------------------------------------------------+
```

### 2.2 Communication Protocol Matrix

| Source | Destination | Protocol | Port | TLS | Status |
|--------|------------|----------|------|-----|--------|
| Polygon.io | data-ingestion | WebSocket/HTTPS | ext | YES | OK |
| data-ingestion | PostgreSQL | TCP/SQL | 5432 | Opt | OK |
| data-ingestion | algo-engine | ZeroMQ PUB/SUB | 5555 | NO | OK |
| data-ingestion | Redis | TCP | 6379 | Opt | OK |
| algo-engine | PostgreSQL | TCP/SQL (asyncpg) | 5432 | Opt | OK |
| algo-engine | Redis | TCP | 6379 | Opt | OK |
| algo-engine | mt5-bridge | gRPC | 50055 | mTLS Opt | OK |
| mt5-bridge | PostgreSQL | TCP/SQL | 5432 | Opt | OK |
| mt5-bridge | Redis | TCP | 6379 | Opt | OK |
| mt5-bridge | MetaTrader 5 | MT5 API | local | N/A | **Windows-only** |
| Prometheus | services | HTTP scrape | varies | NO | OK |
| dashboard | PostgreSQL | TCP/SQL | 5432 | Opt | OK |
| dashboard | Redis | TCP | 6379 | Opt | OK |

### 2.3 Network Segmentation

3 Docker networks with proper isolation:

| Network | Type | Services | Purpose |
|---------|------|----------|---------|
| `backend` | **internal: true** | PostgreSQL, Redis, data-ingestion, algo-engine, mt5-bridge, dashboard | Internal only — no host access |
| `frontend` | bridge | Grafana, Prometheus, dashboard | External-facing UI |
| `monitoring` | bridge | Prometheus, data-ingestion, algo-engine, mt5-bridge | Metrics collection |

**Status**: Backend network correctly marked `internal: true` (fixed since v1.0).

### 2.4 Port Mapping Verification

| Service | Config Default | docker-compose | Dockerfile EXPOSE | Aligned? |
|---------|---------------|----------------|-------------------|----------|
| algo-engine gRPC | 50057 | 50057:50057 | 50057 | **YES** |
| algo-engine REST | 8087 | 8087:8087 | 8087 | **YES** |
| algo-engine metrics | 9097 | 9097:9097 | 9097 | **YES** |
| data-ingestion ZMQ | 5555 | 5555:5555 | 5555 | **YES** |
| data-ingestion metrics | 9090 | 9090:9090 | 9090 | **YES** |
| data-ingestion health | 9091 | 8081:9091 | 9091 | Remapped (OK) |
| mt5-bridge gRPC | 50055 | 50055:50055 | 50055 | **YES** |
| mt5-bridge metrics | 9094 | 9094:9094 | 9094 | **YES** |
| dashboard | 8888 | 8888:8888 | 8888 | **YES** |

**Status**: All ports aligned (fixed since v1.0). The data-ingestion health port remap (8081→9091) is intentional to avoid host conflicts.

### 2.5 Shared Libraries

**moneymaker_common (Python)** — 12 modules, quality 8.5/10:

| Module | LoC | Purpose | Tests |
|--------|-----|---------|-------|
| config.py | ~80 | Pydantic base settings | YES |
| enums.py | ~40 | Direction, Status, Regime enums | YES |
| metrics.py | ~120 | 28 Prometheus metric definitions | YES |
| decimal_utils.py | ~60 | High-precision Decimal helpers | YES |
| logging.py | ~50 | Structured logging (structlog) | YES |
| audit.py | ~90 | SHA-256 hash chain audit trail | YES |
| audit_pg.py | ~80 | PostgreSQL audit integration | YES |
| ratelimit.py | ~40 | Rate limiting utilities | YES |
| health.py | ~50 | Health check utilities | YES |
| secrets.py | ~60 | Secret management from env vars | YES |
| grpc_credentials.py | ~70 | TLS/mTLS channel creation | Partial |
| exceptions.py | ~30 | Custom exception hierarchy | YES |

**go-common (Go)** — 4 modules:

| Module | LoC | Purpose |
|--------|-----|---------|
| config/ | ~131 | Config from YAML/env, DSN building, TLS |
| health/ | ~60 | HTTP health checks (/healthz) |
| logging/ | ~40 | Structured logging (zap) |
| ratelimit/ | ~616 | Redis token bucket + Lua, gRPC/HTTP middleware |

**Proto Definitions** — 4 files:

| Proto | Messages | Services | Key Fields |
|-------|----------|----------|-----------|
| market_data.proto | MarketTick, OHLCVBar, DataEvent | - | Decimal strings for prices |
| trading_signal.proto | TradingSignal, SignalAck | SendSignal, StreamSignals | signal_id UUID, confidence, SL/TP |
| execution.proto | TradeExecution | ExecuteTrade, StreamTradeUpdates | 7-state status enum |
| health.proto | HealthCheckRequest/Response | Health | Standard gRPC health |

### 2.6 Data Flow — Tick to Trade

```
Exchange WebSocket → data-ingestion (normalize, aggregate)
    ├── ZMQ PUB → algo-engine (features, regime, strategy, signal)
    │     ├── Kill Switch check (Redis)
    │     ├── Data Quality → MTF → Features (60-dim) → Regime (5 states)
    │     ├── Strategy Router → Signal Generator → Position Sizer
    │     ├── Validator (11 checks) → Spiral → Rate Limiter
    │     └── gRPC → mt5-bridge (order execution)
    │           ├── Dedup → Validate → Lot Clamp → MT5 API
    │           └── Position Tracker (trailing stops, closed trade detection)
    └── SQL COPY → PostgreSQL (ohlcv_bars, market_ticks)

Latency Budget: <100ms P99 target (ZMQ ~1ms + pipeline ~50ms + gRPC ~10ms)
```

### 2.7 Architecture Findings

| ID | Severity | Finding | Status |
|---|----------|---------|--------|
| F04 | ~~CRITICAL~~ | Port mismatch Dockerfile/compose/config | **FIXED** — All aligned to 50057/8087/9097 |
| F13 | ~~HIGH~~ | .env.example wrong env var names | **FIXED** — env_prefix="" reads ALGO_* correctly |
| F-I7 | ~~WARNING~~ | Backend network not internal | **FIXED** — `internal: true` set |

---

## 3. Algo-Engine Core Pipeline

### 3.1 Architecture Overview

The algo-engine has been **significantly refactored** since v1.0:

| Metric | v1.0 | v2.0 | Change |
|--------|------|------|--------|
| main.py LoC | 1,609 | 530 | **-67%** |
| God function `run_brain()` | 944 lines | Eliminated | Replaced by `AlgoEngine.process_bar()` |
| engine.py | N/A | 404 LoC | New clean class |
| Dead code `_parse_ohlcv_payload()` | Present | Removed | **FIXED** |
| Dead code `orchestrator.py` | Present | Removed | **FIXED** |
| Total source files | 60 | 60 | Stable |
| Total LoC | 12,877 | 12,961 | +0.7% |

### 3.2 Pipeline Architecture

```
main.py:run_engine()          engine.py:AlgoEngine.process_bar()
┌─────────────────────┐       ┌─────────────────────────────────────┐
│ 1. Config loading   │       │ Step 1: DataQualityChecker          │
│ 2. Redis connect    │       │ Step 2: MTF accumulation + BarBuffer│
│ 3. Component init   │       │ Step 3: FeaturePipeline (60-dim)    │
│ 4. ZMQ subscribe    │       │   3a: Advanced feature enrichment   │
│ 5. Main loop:       │──────>│   3b: Adaptive parameter tuning     │
│    - Kill switch    │       │ Step 4: RegimeClassifier + Bayesian │
│    - ZMQ recv       │       │ Step 5: SessionClassifier           │
│    - process_bar()  │       │ Step 6: RegimeRouter (strategy)     │
│    - gRPC dispatch  │       │ Step 7: SignalGenerator             │
│    - Trade polling  │       │ Step 8: PositionSizer + Spiral      │
│ 6. Graceful shutdown│       │ Step 9: SignalValidator (11 checks) │
└─────────────────────┘       │ Step 10: RateLimiter               │
                              └─────────────────────────────────────┘
```

### 3.3 Signal Flow (Updated)

```
ZMQ SUB (tcp://data-ingestion:5555)
    │ topic: "bar.{symbol}.{timeframe}"
    v
zmq_adapter.py → parse_bar_message() → OHLCVBar
    │
    v
engine.py:process_bar() [5-second timeout]
    ├── DataQualityChecker.validate_bar() ─[FAIL]─> None
    ├── MTF accumulation + BarBuffer ─[insufficient]─> None
    ├── FeaturePipeline.compute_features() → 60-dim dict
    │   ├── [opt] Fractal → Hurst exponent
    │   ├── [opt] Spectral → dominant cycle, entropy
    │   ├── [opt] OU → s-score, half-life
    │   └── [opt] Shift detector → distribution change
    ├── RegimeClassifier.classify() → regime + confidence
    │   └── [opt] Bayesian → posteriors overlay
    ├── SessionClassifier.classify() → session name
    ├── RegimeRouter.route() or .route_probabilistic()
    │   └── Strategy.generate() → SignalSuggestion
    ├── [HOLD?] → None
    ├── SignalGenerator.generate_signal() → signal dict
    ├── PositionSizer.calculate() or AdvancedSizer.calculate()
    ├── SpiralProtection.is_in_cooldown() ─[YES]─> None
    ├── SpiralProtection.get_sizing_multiplier() → adjust lots
    ├── SignalValidator.validate() ─[FAIL]─> None
    └── RateLimiter.allow() ─[NO]─> None
    │
    v
main.py: gRPC dispatch
    ├── Kill switch auto-check (daily_loss, drawdown)
    ├── signal_to_proto() → TradingSignal protobuf
    ├── BridgeClient.send_signal() → SignalAck
    ├── PortfolioManager.record_open()
    └── Audit trail (PostgreSQL)
    │
    v (every 10 bars)
    └── Closed trade polling → portfolio.record_close() + spiral.record_trade_result()
```

### 3.4 Bug Verification Matrix

| ID | Description | v1.0 Severity | Status | Evidence |
|---|-------------|---------------|--------|----------|
| F01 | Kill switch tuple treated as bool | CRITICAL | **FIXED** | `main.py:305`: `_ks_active, _ks_reason = await kill_switch.is_active()` |
| F02 | gRPC direction enum serialization | CRITICAL | **FIXED** | `grpc_client.py:62`: `raw_dir.value if hasattr(raw_dir, "value")` |
| F04-PnL | PnL tracker records fake data | CRITICAL | **FIXED** | `main.py:454-468`: Real PnL from `bridge_client.get_closed_trades()` |
| F05 | ADX not validated [0,100] | HIGH | **Open** | `trend_following.py`: ADX passed through `min()` but source data unclamped |
| F07 | Portfolio mutable list leak | HIGH | **FIXED** | `portfolio.py:78`: Returns `list(self._positions_detail)` copy |
| F08 | BridgeClient.close() never called | HIGH | **FIXED** | `main.py:500`: `await bridge_client.close()` in shutdown |
| F09 | Portfolio partially persisted | WARNING | **Improved** | `portfolio.py`: `persist_to_redis()` / `sync_from_redis()` with expanded fields |
| F10 | Unknown symbols pass silently | WARNING | **Open** | `correlation.py`: No validation against known symbol list |
| F12 | Dead code `_parse_ohlcv_payload()` | WARNING | **FIXED** | Entire main.py rewritten; dead code removed |
| God fn | `run_brain()` 944 lines | WARNING | **FIXED** | Replaced by `run_engine()` (210 lines) + `AlgoEngine` class (404 lines) |

### 3.5 Code Complexity Analysis

| File | LoC | Max Nesting | Cyclomatic | Assessment |
|------|-----|-------------|------------|------------|
| main.py | 530 | 3 | 12 | **Good** — clean async loop |
| engine.py | 404 | 4 | 18 | **Good** — linear pipeline, each step isolated |
| config.py | 152 | 2 | 8 | **Excellent** — pure validators |
| grpc_client.py | 298 | 3 | 10 | **Good** — proto conversion + error handling |
| zmq_adapter.py | 132 | 2 | 6 | **Excellent** — minimal parsing |
| kill_switch.py | ~260 | 3 | 14 | **Good** — Redis state machine |
| portfolio.py | ~175 | 2 | 8 | **Good** — state tracking |

### 3.6 Error Handling Audit

| Location | Error Type | Handling | Assessment |
|----------|-----------|----------|------------|
| `main.py:302` | Main loop outer | `try/except Exception → log + sleep(1)` | OK — resilient |
| `main.py:485` | CancelledError | `break` → graceful shutdown | OK |
| `main.py:454` | Closed trade poll | `try/except → log debug` | OK — non-critical |
| `main.py:474` | Drawdown enforcer | `try/except → log debug` | OK — defensive |
| `engine.py:144` | Pipeline timeout | `asyncio.TimeoutError → metric + None` | OK — prevents stalls |
| `engine.py:219` | Bayesian update | `try/except → log debug` | OK — optional module |
| `engine.py:370-403` | Advanced enrichment | Per-module try/except | **Good** — isolation |
| `grpc_client.py` | gRPC calls | Exception → log warning | OK — fail-open on dispatch |

**Assessment**: Error handling is comprehensive. All I/O operations wrapped. Advanced modules isolated — one failure cannot block the core pipeline.

### 3.7 Configuration Management

| Parameter | Env Var | Default | Valid Range | Validator |
|-----------|---------|---------|-------------|-----------|
| Confidence threshold | `ALGO_CONFIDENCE_THRESHOLD` | 0.65 | (0.0, 1.0] | `_validate_confidence_threshold` |
| Risk per trade | `ALGO_RISK_PER_TRADE_PCT` | 1.0% | [0.1, 5.0] | `_validate_risk_per_trade` |
| Max daily loss | `ALGO_MAX_DAILY_LOSS_PCT` | 2.0% | [0.5, 10.0] | `_validate_max_daily_loss` |
| Max drawdown | `ALGO_MAX_DRAWDOWN_PCT` | 5.0% | [1.0, 25.0] | `_validate_max_drawdown` |
| Max positions | `ALGO_MAX_OPEN_POSITIONS` | 5 | >0 | None (implicit) |
| Max lots | `ALGO_MAX_LOTS` | 0.10 | >0 | `_validate_max_lots` |
| Max signals/hour | `ALGO_MAX_SIGNALS_PER_HOUR` | 10 | >0 | `_validate_max_signals` |
| EMA fast/slow | `ALGO_DEFAULT_EMA_FAST/SLOW` | 12/26 | >0, fast<slow | `_validate_ema_ordering` |
| RSI period | `ALGO_DEFAULT_RSI_PERIOD` | 14 | >0 | `_validate_periods_positive` |
| Spiral threshold | `ALGO_SPIRAL_LOSS_THRESHOLD` | 3 | - | None |
| Spiral cooldown | `ALGO_SPIRAL_COOLDOWN_MINUTES` | 60 | - | None |
| Telegram token | `ALGO_TELEGRAM_BOT_TOKEN` | "" | - | Masked in `safe_dump()` |

**env_prefix**: Set to `""` with `case_sensitive=False` (`config.py:78`). All env vars are read as-is without prefix stripping.

### 3.8 Findings

| ID | Severity | Finding | Location |
|---|----------|---------|----------|
| F05 | HIGH | ADX not validated for range [0,100] | `trend_following.py` |
| F10 | MEDIUM | Unknown symbols pass silently through CorrelationChecker | `correlation.py:~94` |
| NEW-AE1 | MEDIUM | `algo_max_lots` is float but used as Decimal at runtime | `config.py:56`, `engine.py:293` |
| NEW-AE2 | MEDIUM | Pipeline timeout (5s) is hardcoded, not configurable | `engine.py:106` |
| NEW-AE3 | WARNING | No circuit breaker for gRPC bridge retries | `main.py:415-445` |
| NEW-AE4 | WARNING | `parse_bar_message()` KeyError not caught in main loop | `main.py:331` |

---

## 4. Feature Pipeline & Regime Classification

### 4.1 60-Dimensional Feature Vector

The pipeline (`pipeline.py` + `technical.py`) produces ~34 technical indicators via Decimal arithmetic:

| Indices | Group | Features | Mathematical Verification |
|---------|-------|----------|--------------------------|
| 0-5 | Price | OHLCV normalized + spread | Correct: close/open ratio, HL range |
| 6-15 | Trend | SMA ratios, DEMA, MACD (line/signal/hist), ADX | Correct: Wilder smoothing, MACD 12/26/9 |
| 16-25 | Momentum | RSI, Stochastic K/D, CCI, Williams %R, ROC, DI ratio | Correct: RSI Wilder formula verified |
| 26-33 | Volatility | ATR%, BB upper/lower/width, Keltner, Hist Vol, Parkinson | Correct: BB 2σ, ATR Wilder |
| 34-40 | Volume | OBV norm, VWAP ratio, CMF, Chaikin Osc, Force Index, Vol ratio | Partial: Chaikin = placeholder |
| 41-50 | Context | Hour sin/cos, DayOfWeek sin/cos, session, VIX, DXY, SPX corr | Correct: cyclical encoding |
| 51-59 | Microstructure | Bid-ask, OB imbalance, tick direction, trade flow, VPIN | Partial: 3 placeholders |

**All core indicator formulas verified mathematically correct**: RSI (Wilder smoothing), MACD (12/26/9 EMA), Bollinger (2σ), ATR (Wilder), ADX (DI+/DI- smoothed), Stochastic (%K/%D), OBV, CCI.

**Decimal precision**: All calculations use `Decimal` with 28-digit precision and `ROUND_HALF_EVEN`. The `@validate_decimal_inputs` decorator validates NaN/Inf on all technical calculations.

### 4.2 Placeholder Features (8.3%)

5 of 60 features are zero/constant placeholders:

| Index | Feature | Value | Reason | Impact |
|-------|---------|-------|--------|--------|
| 37 | Chaikin Oscillator | 0.0 | Requires ADL series accumulation | Low — volume analysis partial |
| 40 | Volume Profile Value Area | 0.5 | Not implemented | Low — volume profile unused |
| 55 | Realised Vol 5min | 0.0 | Sub-minute tick data unavailable | Low — Parkinson vol substitutes |
| 57 | Hurst Exponent | 0.5 | Too costly for real-time (moved to optional fractal module) | None — available via advanced module |
| 58 | VPIN | 0.0 | Requires tick-level volume imbalance | Low — CMF substitutes partially |

**Assessment**: Placeholders are LOW impact. Hurst is now available via the optional fractal module. Remaining 4 can be implemented incrementally.

### 4.3 Regime Classification

**5 regimes** with priority-ordered classification:

| Priority | Regime | Condition | Confidence Formula |
|----------|--------|-----------|-------------------|
| 1 | HIGH_VOLATILITY | ATR > 2x avg_ATR | 0.50 + (ratio-2)×0.25 |
| 2 | TRENDING_UP | ADX > 25 AND EMA_fast > EMA_slow | 0.50 + ADX/100 |
| 3 | TRENDING_DOWN | ADX > 25 AND EMA_fast < EMA_slow | 0.50 + ADX/100 |
| 4 | REVERSAL | ADX was >40, now declining + extreme RSI | 0.55 |
| 5 | RANGING (default) | ADX < 20, narrow bands | 0.70 |

**Hysteresis**: Requires `P(new) > P(old) + 0.15` for 3 consecutive bars before switching regime. This prevents whipsaw regime changes.

**Ensemble Classifier** (416 LoC): Rule-based (weight=0.50) + HMM (0.30) + kMeans (0.20) weighted voting.

**`_prev_adx` fix verified**: Now initialized to `None` instead of `0`, so first reversal detection works correctly (`regime.py:97`).

### 4.4 Additional Feature Modules

| Module | LoC | Purpose | Tests |
|--------|-----|---------|-------|
| data_quality.py | ~60 | OHLCV validation (H≥max(O,C), spike detection) | 0 |
| data_sanity.py | ~80 | Statistical plausibility checks | 0 |
| feature_drift.py | ~70 | Z-score distributional drift detection | 0 |
| leakage_auditor.py | ~90 | 5-check formal data leakage audit | 0 |
| macro_features.py | ~363 | VIX, yield, DXY from Redis | 0 |
| regime_shift.py | ~60 | KL-divergence regime transitions | 0 |
| sessions.py | ~80 | NY/London/Tokyo/Sydney session detection | 0 |
| mtf_analyzer.py | ~180 | Multi-timeframe (M1/M5/M15/H1) aggregation | YES |

### 4.5 Analysis Modules

| Module | LoC | Purpose | Tests |
|--------|-----|---------|-------|
| manipulation_detector.py | ~150 | Spoofing/fake breakout/churn detection | 0 |
| signal_quality.py | ~80 | Shannon entropy market clarity | 0 |
| price_level_analyzer.py | ~120 | Support/resistance classification | 0 |
| pnl_momentum.py | ~90 | Win/loss streak tracker (time-decay) | 0 |
| market_belief.py | ~100 | Bayesian posterior regime model | 0 |

### 4.6 Findings

| ID | Severity | Finding | Status |
|---|----------|---------|--------|
| F-FP1 | HIGH | 5 placeholder features (8.3% of vector) | **Open** — Low impact, incremental fix |
| F-FP2 | ~~HIGH~~ | `_prev_adx` initialized to 0 | **FIXED** — `None` initialization |
| F-FP3 | WARNING | Spoofing detector blind without L2 data | **Open** — 25% always 0 |
| F-FP4 | WARNING | Spread feature always 0.5 in ensemble | **Open** |
| F-FP5 | WARNING | `bb_squeeze` not calculated | **Open** |
| F-FP6 | WARNING | GBM parameters not calibrated | **Open** |
| NEW-FP1 | MEDIUM | 10 feature/analysis modules have 0 tests | feature_drift, leakage, macro, etc. |

---

## 5. Mathematical Modules

### 5.1 Overview

8 advanced mathematical modules providing optional analytical capabilities. All are injected into `AlgoEngine` via constructor parameters and wrapped in try/except for fault isolation.

| Module | LoC | Purpose | Test LoC | Tests |
|--------|-----|---------|----------|-------|
| stochastic.py | 742 | Brownian motion, GBM, Merton jump-diffusion, Heston | ~250 | YES |
| bayesian.py | 425 | Bayesian regime posteriors, Markov chain, Thompson sampling | ~260 | YES |
| copula.py | 462 | Bivariate/multivariate copula, tail dependence | ~280 | YES |
| extreme_value.py | 380 | GPD fitting, VaR/CVaR, Peaks-over-Threshold | ~250 | YES |
| ou_process.py | 378 | OU solver, mean-reversion s-score, half-life | ~250 | YES |
| fractal.py | 406 | Hurst exponent, R/S analysis, fractal dimension | ~230 | YES |
| spectral.py | 336 | FFT cycle detection, spectral entropy | ~250 | YES |
| information_theory.py | 245 | Shannon entropy, KL divergence, mutual info | ~250 | YES |
| **Total** | **3,374** | | **~2,020** | **100%** |

### 5.2 Bayesian Regime Detector

**Algorithm**: Adams & MacKay online changepoint detection with Normal-Inverse-Gamma (NIG) conjugate prior.

| Component | Implementation | Correctness |
|-----------|---------------|-------------|
| Posterior update | Welford's online mean/variance | Correct — numerically stable |
| Prior | NIG: μ₀=0, κ₀=1, α₀=1, β₀=1 | Standard conjugate prior |
| Hazard function | Constant rate λ=1/250 | Reasonable for daily data |
| Thompson Sampling | Beta(α, β) for strategy selection | Correct — exploration/exploitation |

**Integration**: `engine.py:213-220` — Updates on RSI values, provides posteriors to `RegimeRouter.route_probabilistic()`.

### 5.3 Stochastic Processes

| Process | Formula | Verification |
|---------|---------|-------------|
| GBM | dS = μS dt + σS dW | Correct — log-normal increments |
| Merton Jump-Diffusion | GBM + Poisson(λ) × N(μ_j, σ_j) | Correct — compound Poisson process |
| Heston | dv = κ(θ-v)dt + ξ√v dW_v, ρ correlation | Correct — CIR variance process |

**Numerical precision**: Uses `Decimal` for core parameters but `float` for simulation paths (acceptable — simulation is inherently approximate).

### 5.4 Extreme Value Theory

| Component | Method | Correctness |
|-----------|--------|-------------|
| GPD fitting | Probability-Weighted Moments (PWM) | Correct — ξ̂, σ̂ from PWM estimators |
| Threshold selection | Mean Residual Life plot heuristic | Correct — 90th percentile default |
| VaR | u + (σ̂/ξ̂)[(n/N_u × (1-p))^(-ξ̂) - 1] | Correct — GPD quantile formula |
| CVaR (ES) | VaR/(1-ξ̂) + (σ̂ - ξ̂×u)/(1-ξ̂) | Correct — Expected Shortfall |

### 5.5 Fractal Analysis

| Component | Method | Correctness |
|-----------|--------|-------------|
| Hurst exponent | Rescaled Range (R/S) analysis | Correct — log-log regression |
| R/S statistic | max(cumdev)/min(cumdev) / std | Correct — classical Hurst |
| Interpretation | H>0.5: trending, H<0.5: mean-reverting, H=0.5: random walk | Correct |

### 5.6 Spectral Analysis

| Component | Method | Correctness |
|-----------|--------|-------------|
| FFT | numpy.fft.fft with Hann window | Correct — windowed FFT |
| Dominant cycle | argmax of power spectral density | Correct |
| Spectral entropy | -Σ p_i log(p_i) on normalized PSD | Correct — Shannon on spectrum |

### 5.7 OU Process

| Component | Formula | Correctness |
|-----------|---------|-------------|
| MLE estimation | θ, μ, σ from OLS regression | Correct — Euler discretization |
| Half-life | ln(2)/θ | Correct |
| S-score | (x - μ) / σ_eq | Correct — standardized deviation |
| Signal | s > 1.25 → SELL, s < -1.25 → BUY | Reasonable thresholds |

### 5.8 Remaining Modules

| Module | Key Algorithm | Correctness |
|--------|--------------|-------------|
| Copula | Gaussian/Clayton/Gumbel | Correct — CDF transforms, copula density |
| Information Theory | KL(P‖Q) = Σ P log(P/Q) | Correct — with ε smoothing for zeros |

### 5.9 Numerical Precision Audit

| Module | Price/Financial | Simulation | Assessment |
|--------|----------------|------------|------------|
| Bayesian | Decimal for posteriors | - | Good |
| Stochastic | - | float64 for paths | Acceptable |
| EVT | Decimal for VaR/CVaR | float64 for fitting | Good |
| Fractal | - | float64 for R/S | Acceptable |
| Spectral | - | float64 for FFT | Required (FFT) |
| OU | Decimal for s-score | float64 for estimation | Good |
| Copula | - | float64 for density | Acceptable |
| Info Theory | - | float64 for entropy | Acceptable |

### 5.10 Findings

| ID | Severity | Finding | Detail |
|---|----------|---------|--------|
| NEW-MATH1 | MEDIUM | Stochastic simulation uses float, not Decimal | Acceptable for Monte Carlo but inconsistent with financial math policy |
| NEW-MATH2 | WARNING | OU half-life estimation can produce negative values for non-stationary data | Edge case — `max(0, half_life)` guard recommended |
| NEW-MATH3 | WARNING | GPD fitting may fail for small sample sizes (<30 data points) | PWM estimators require sufficient tail data |
| NEW-MATH4 | WARNING | Spectral FFT assumes equally-spaced data | Market data may have gaps (weekends, holidays) |

---

## 6. Strategy Suite

### 6.1 Strategy Architecture

```
TradingStrategy (ABC)
    │
    ├── TrendFollowing     — ADX + EMA crossover
    ├── MeanReversion      — Bollinger + RSI extremes
    ├── Defensive          — Conservative in high volatility
    ├── Breakout           — Range expansion detection
    ├── VolMomentum        — Volatility-based momentum (Phase 3)
    ├── OUMeanReversion    — OU s-score driven (Phase 3)
    ├── AdaptiveTrend      — Cycle-adjusted parameters (Phase 3)
    └── MultiFactor        — Composite multi-indicator (Phase 3)

RegimeRouter
    ├── route(regime, features)              — Deterministic dispatch
    └── route_probabilistic(posteriors, features) — Bayesian weighted
```

### 6.2 Strategy Deep Dive

| Strategy | LoC | Entry Conditions | SL/TP Method | Tests |
|----------|-----|-----------------|--------------|-------|
| TrendFollowing | 128 | ADX>25, EMA_fast>EMA_slow (BUY) | ATR-based (2x SL, 3x TP) | 9 |
| MeanReversion | 115 | RSI<30+price<BB_lower (BUY), RSI>70+price>BB_upper (SELL) | BB band distance | 9 |
| Defensive | 56 | RSI extremes in high vol | Tight stops (1x ATR) | 6 |
| Breakout | 121 | Price breaks N-period high/low with volume confirmation | Breakout range-based | 0 |
| VolMomentum | 180 | ATR expansion + momentum alignment | Dynamic ATR multiple | 0 |
| OUMeanReversion | 212 | OU s-score > threshold | Mean-reversion band | 0 |
| AdaptiveTrend | 221 | Dominant cycle-adjusted crossover | Cycle-proportional stops | 0 |
| MultiFactor | 304 | Composite score from 5+ indicators | Weighted average distance | 0 |

### 6.3 Regime Router

**Deterministic routing** (`route()`):

| Regime | Primary Strategy | Fallback |
|--------|-----------------|----------|
| TRENDING_UP | TrendFollowing | AdaptiveTrend |
| TRENDING_DOWN | TrendFollowing | AdaptiveTrend |
| RANGING | MeanReversion | OUMeanReversion |
| HIGH_VOLATILITY | Defensive | VolMomentum |
| REVERSAL | MeanReversion | Defensive |

**Probabilistic routing** (`route_probabilistic()`): Weights strategies by Bayesian posterior probability of each regime. Uses Thompson Sampling for exploration.

### 6.4 Findings

| ID | Severity | Finding | Detail |
|---|----------|---------|--------|
| F05 | HIGH | ADX not clamped to [0,100] in trend_following | Source data could exceed expected range |
| NEW-STR1 | MEDIUM | 4 of 8 strategies have 0 tests | VolMomentum, OUMeanReversion, AdaptiveTrend, MultiFactor |
| NEW-STR2 | WARNING | Breakout strategy has 0 tests | Entry/exit logic unverified |
| NEW-STR3 | WARNING | MultiFactor composite weights not configurable | Hardcoded in strategy class |

---

## 7. Safety Systems & Risk Management

### 7.1 7-Layer Protection Architecture

```
Signal Generated by Strategy
       │
       v
[1] SpiralProtection.is_in_cooldown() ─[YES]─> BLOCK
       │ After 5 consecutive losses → 60-min cooldown
       v
[2] SpiralProtection.get_sizing_multiplier() → adjust lots
       │ 3 losses → 0.5x, 4 → 0.25x
       v
[3] SignalValidator.validate() ── 11 fail-fast checks:
       │  [1] Direction != HOLD          [7] SL correctly positioned
       │  [2] Positions < 5              [8] R:R >= 1.0
       │  [3] Drawdown < 5%             [9] Margin buffer >= 80%
       │  [4] Daily Loss < 2%           [10] Correlation check (opt)
       │  [5] Confidence >= 0.65        [11] Session check (opt)
       │  [6] Stop-Loss present
       v
[4] RateLimiter.allow() ─[NO]─> DROP (10/hour max)
       │
       v
[5] gRPC dispatch to MT5 Bridge
       │
       v
[6] KillSwitch.auto_check() ── Checks AFTER dispatch:
       │  daily_loss >= max_daily_loss → activate
       │  drawdown >= max_drawdown → activate
       v
[7] KillSwitch.is_active() ── Pre-loop check (Redis-backed):
       │  Active → pause 5s, skip all processing
       │  Fail-CLOSED: if Redis unreachable, blocks trading
       v
[LOOP CONTINUES]
```

### 7.2 Kill Switch

| Aspect | Implementation | Assessment |
|--------|---------------|------------|
| State storage | Redis (`moneymaker:kill_switch`) | Good — shared state |
| Fail mode | **Fail-CLOSED** — blocks if Redis unreachable | **Excellent** — safe default |
| Cache TTL | 1.0 second (hardcoded) | Good — reduces Redis load |
| Auto-activation | daily_loss >= limit OR drawdown >= limit | Correct |
| Manual control | `activate()` / `deactivate()` methods | Good |
| Audit trail | Redis list (`moneymaker:kill_switch:audit_log`), 200-entry cap | Good |
| Hierarchical | 3 levels: PAUSE_STRATEGY, REDUCE_SIZING, FLATTEN_ALL | Good |

**Fix verified**: `main.py:305` correctly destructures `is_active()` return tuple.

### 7.3 Spiral Protection

| Aspect | Implementation | Assessment |
|--------|---------------|------------|
| Loss tracking | `consecutive_losses` counter | Good |
| Thresholds | 3 losses → 0.5x, 4 → 0.25x, 5+ → cooldown | Good — progressive |
| Cooldown | 60 minutes (configurable) | Good |
| Redis persistence | `sync_from_redis()` / `persist_to_redis()` | **FIXED** since v1.0 |
| State key | `moneymaker:spiral:{symbol}` or global | Good |

**Fix verified**: `spiral_protection.py:161-209` implements full Redis persistence with TTL.

### 7.4 Position Sizer

**Standard sizer** (`position_sizer.py`):
```
lots = (equity × risk_pct) / (SL_pips × pip_value_per_lot)
lots = lots × drawdown_multiplier
lots = clamp(lots, min_lots=0.01, max_lots=0.10)
```

**Drawdown scaling**:

| Drawdown | Multiplier |
|----------|-----------|
| 0-2% | 1.0x |
| 2-4% | 0.5x |
| 4-5% | 0.25x |
| >5% | min_lots |

**Advanced sizer** (`advanced_sizer.py`, Phase 4):
```
kelly_fraction = (confidence × win_rate - (1 - confidence)) / odds_ratio
half_kelly = kelly_fraction / 2
cvar_adjusted = half_kelly × (1 - cvar_scaling)
lots = equity × cvar_adjusted / (SL_pips × pip_value)
```

### 7.5 Instrument Tables

| Symbol | Pip Size | Pip Value (USD/lot) | Source |
|--------|----------|--------------------|----|
| EURUSD | 0.0001 | $10 | Hardcoded |
| GBPUSD | 0.0001 | $10 | Hardcoded |
| USDJPY | 0.01 | ¥1000 | Hardcoded |
| XAUUSD | 0.01 | $1 | Hardcoded |
| XAGUSD | 0.001 | $50 | Hardcoded |
| USDCHF | 0.0001 | $10 | Hardcoded |
| AUDUSD | 0.0001 | $10 | Hardcoded |
| NZDUSD | 0.0001 | $10 | Hardcoded |
| USDCAD | 0.0001 | $10 | Hardcoded |
| EURGBP | 0.0001 | £10 | Hardcoded |

### 7.6 Safety Composition Analysis

**Spiral x Drawdown interaction**:
- Drawdown scaling applied in `PositionSizer.calculate()` (Step 8)
- Spiral multiplier applied in `engine.py:308-320` (Step 8a)
- Applied **sequentially**, NOT **multiplicatively**

Example: DD=3% (0.5x via sizer) + 3 losses (0.5x via spiral) → lots = base × 0.5 × 0.5 = 0.25x
**This is actually correct** — the sequential application does multiply because spiral applies to the already-reduced lots.

**Reassessment**: F-S1 (spiral x drawdown not composed) is **PARTIALLY RESOLVED** — sequential application achieves multiplication, but the composition is implicit, not explicit. Code comment would improve clarity.

### 7.7 Findings

| ID | Severity | Finding | Status |
|---|----------|---------|--------|
| F-S1 | ~~HIGH~~ | Spiral x Drawdown NOT composed | **Reassessed** — Sequential application achieves correct multiplication. MEDIUM — needs comment |
| F-S2 | ~~HIGH~~ | Spiral state not persisted to Redis | **FIXED** |
| F-S3 | HIGH | Redis persistence NOT tested | **Open** — spiral_protection tests exist but Redis mocking unclear |
| F-S4 | HIGH | Optional validator controls NOT tested | **Open** |
| F-S5 | WARNING | No confirmation before kill activate | **Open** |
| F-S6 | WARNING | Missing DailyLossCritical alert at 2% | **Open** — alert only at 1.5% |
| F-S7 | WARNING | Hardcoded instrument tables | **Open** — requires code changes |
| F-S8 | WARNING | Margin buffer 0.80 magic number | **Open** |
| F-S9 | WARNING | Kill switch cache TTL not configurable | **Open** |
| F-S10 | WARNING | Comment/code discrepancy in auto_check | **Open** |

---

## 8. Backtesting Infrastructure

### 8.1 Architecture

The backtesting suite (Phase 1) provides event-driven historical simulation with **zero code divergence** — the same `AlgoEngine.process_bar()` runs in both backtest and production.

```
BacktestEngine
    │
    ├── DataLoader.load() → list[OHLCVBar]
    │   ├── from_csv(path)
    │   └── from_database(dsn, symbol, start, end)
    │
    ├── AlgoEngine.process_bar(symbol, tf, bar) → signal?
    │
    ├── TradeSimulator.on_signal(signal)
    │   ├── Open position with simulated fill
    │   ├── Apply spread (1.5 pips default)
    │   ├── Apply slippage (0.5 pips default)
    │   └── Track equity curve
    │
    ├── TradeSimulator.on_bar(bar)
    │   ├── Check SL/TP hits
    │   └── Update unrealized P&L
    │
    └── BacktestMetrics.compute(trades, equity_curve)
        ├── Sharpe Ratio (annualized, rf=0)
        ├── Sortino Ratio (downside deviation only)
        ├── Calmar Ratio (return / max drawdown)
        ├── Max Drawdown (peak-to-trough %)
        ├── Win Rate (% profitable trades)
        ├── Profit Factor (gross profit / gross loss)
        ├── Omega Ratio (threshold = 0)
        └── Average trade duration
```

### 8.2 TradeSimulator Audit

| Component | Implementation | Assessment |
|-----------|---------------|------------|
| Fill simulation | Market order at close + spread/2 | Simplified — no partial fills |
| Spread model | Fixed 1.5 pips | Adequate for majors, not for exotics |
| Slippage model | Fixed 0.5 pips | Adequate for liquid pairs |
| Commission | $7/lot round-trip | Standard MT5 ECN pricing |
| SL/TP check | Bar-by-bar, checks high/low against levels | Correct — uses worst-case fill |
| Equity tracking | Running equity curve with position mark-to-market | Correct |

### 8.3 Backtesting Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| No tick-level simulation | SL/TP hit order unknown within bar | Uses worst-case assumption |
| Fixed spread | Spread varies intraday (news, sessions) | Conservative fixed spread |
| No market impact | Large orders don't move price | Max lots = 0.10 (minimal impact) |
| No partial fills | All orders fully filled | Reasonable for forex retail |
| Survivorship bias | Only tests symbols that still exist | Not applicable — forex pairs stable |
| Look-ahead bias | `leakage_auditor.py` provides formal checks | Good — 5-check audit available |

### 8.4 Findings

| ID | Severity | Finding | Detail |
|---|----------|---------|--------|
| NEW-BT1 | MEDIUM | Backtest spread model fixed at 1.5 pips | Should vary by symbol and session |
| NEW-BT2 | WARNING | No backtest results persistence | Results computed but not saved to database |
| NEW-BT3 | WARNING | DataLoader has no validation for bar ordering | Out-of-order bars could produce wrong results |

---

## 9. Optimization Suite

### 9.1 Walk-Forward Optimizer

```
walk_forward.py (~192 LoC)

For each window:
    ├── In-Sample (IS): Grid search over parameter space
    │   ├── Parameter grid: user-defined per strategy
    │   ├── Objective: Sharpe ratio (default)
    │   └── Select best parameters
    ├── Out-of-Sample (OOS): Apply best params to next period
    │   └── Record OOS performance
    └── Overfit Detection:
        ├── OOS_Sharpe / IS_Sharpe ratio
        └── Threshold: ratio < 0.5 → OVERFIT WARNING
```

### 9.2 Monte Carlo Analysis

3 methods implemented:

| Method | Approach | Output |
|--------|---------|--------|
| Historical Bootstrap | Resample trade returns with replacement | Confidence intervals for Sharpe, MaxDD |
| Gaussian | Generate N(μ, σ) returns from trade statistics | Parametric confidence bands |
| Block Bootstrap | Resample consecutive blocks (preserves autocorrelation) | More realistic for trending markets |

Default: 10,000 simulations, 95% confidence interval.

### 9.3 Adaptive Parameter Tuner

```
adaptive.py (~117 LoC)

Input: dominant_cycle from spectral analysis
Output: adjusted indicator periods

RSI period = round(dominant_cycle / 2)
EMA fast = round(dominant_cycle / 3)
EMA slow = round(dominant_cycle * 2 / 3)
BB period = round(dominant_cycle / 2)
```

### 9.4 Findings

| ID | Severity | Finding | Detail |
|---|----------|---------|--------|
| NEW-OPT1 | MEDIUM | Walk-forward grid search is exhaustive (not intelligent) | Could use Bayesian optimization for large parameter spaces |
| NEW-OPT2 | WARNING | Adaptive tuner has no bounds checking on cycle periods | Very short cycles could produce RSI period=1 |
| NEW-OPT3 | WARNING | Monte Carlo does not account for transaction costs in bootstrap | Resampled trades already include costs, but path simulation doesn't |

---

## 10. Data Ingestion & Database

### 10.1 Go Data Pipeline

```
EXCHANGE (Polygon.io WebSocket)
    │
    │ RawMessage{Exchange, Symbol, Channel, Data, Timestamp}
    v
NORMALIZER (shopspring/decimal precision)
    │
    +───────+───────+
    │               │
    v               v
ZMQ PUB            DB WRITER
"bar.*.*"          COPY bulk insert
:5555              batch=1000, flush=5s, workers=2
    │               │
    v               v
algo-engine        TimescaleDB
                   (ohlcv_bars, market_ticks)
```

### 10.2 Connector Architecture

**Polygon.io** (604 LoC):
- WebSocket with exponential backoff: base=2s, max=60s, ±20% jitter
- Circuit breaker after 50 failed reconnection attempts
- Atomic state machine (`atomic.Int32`): disconnected → connecting → connected → reconnecting → closed
- Ping keepalive at 30s
- Message buffer with HWM, drops oldest when full
- `reconnectAttempts` now uses `atomic.Int32` (F-D2 FIXED)

**Binance** (255 LoC): Disabled in V1. No reconnection logic (F-D3 remains but mitigated).

### 10.3 Database Schema

#### Core Tables

| Table | Type | Chunk | Compression | Retention | Unique Constraint |
|-------|------|-------|-------------|-----------|-------------------|
| ohlcv_bars | Hypertable | 1 day | After 7 days (symbol, timeframe) | 365 days | `(time, symbol, timeframe)` |
| market_ticks | Hypertable | 1 hour | After 1 day (symbol) | 90 days | `(time, symbol)` |
| trading_signals | Regular | - | - | - | signal_id |
| trade_executions | Regular | - | - | - | order_id |
| audit_log | Regular | - | - | - | Trigger PREVENTS UPDATE/DELETE |

**Unique constraints verified**: `008_add_unique_constraints.sql` adds constraints (F-D1 FIXED).
**Retention policies verified**: `009_add_retention_policies.sql` adds 365-day and 90-day policies (F-D9 FIXED).

#### RBAC (4 roles)

| Role | Read Access | Write Access |
|------|------------|-------------|
| data_ingestion_svc | market data, macro | market data, macro, audit |
| algo_engine_svc | market, macro, events, strategy | signals, strategy, audit |
| mt5_bridge_svc | signals | executions, strategy(update), audit |
| moneymaker_admin | ALL | ALL |

#### Migration Files

| File | Purpose | Verified |
|------|---------|----------|
| 001_init.sql | Core tables + hypertables + audit trigger | YES |
| 002_strategy_tables.sql | Strategy performance tracking | YES |
| 003_economic_calendar.sql | Events, blackouts, impact rules | YES |
| 004_macro_data.sql | VIX, yields, DXY, COT | YES |
| 005_rbac.sql | 4 database roles | YES |
| 006_indexes.sql | Performance indexes | YES |
| 007_continuous_aggregates.sql | Strategy daily summary | YES |
| 008_add_unique_constraints.sql | PK on hypertables | YES |
| 009_add_retention_policies.sql | Data retention (365d/90d) | YES |

### 10.4 External Data Service

| Provider | Data | Schedule | Status |
|----------|------|----------|--------|
| CBOE | VIX index | Every 1 min | Implemented |
| FRED | Treasury yields, real rates, recession probability | Every 60 min | Implemented |
| CFTC | Commitments of Traders (COT) | Every 24h | Implemented |

**Issue**: Service is NOT in docker-compose.yml — runs locally only. No tests.

### 10.5 Findings

| ID | Severity | Finding | Status |
|---|----------|---------|--------|
| F-D1 | ~~CRITICAL~~ | Missing PRIMARY KEY on hypertables | **FIXED** — unique constraints added |
| F-D2 | ~~HIGH~~ | Data race on reconnectAttempts | **FIXED** — `atomic.Int32` |
| F-D3 | HIGH | No reconnection in binance.go | **Open** — mitigated (Binance disabled) |
| F-D4 | HIGH | Sync flush blocks main loop | **Open** |
| F-D5 | WARNING | Aggregator callback under mutex | **Open** |
| F-D6 | WARNING | Symbol map hardcoded | **Open** |
| F-D7 | WARNING | No explicit HWM on ZMQ PUB | **Open** — buffer exists with drop |
| F-D8 | WARNING | Redis in config but never used | **Open** |
| F-D9 | ~~WARNING~~ | No retention policy | **FIXED** |
| F-D10 | WARNING | SpreadAvg hardcoded to Zero | **Open** |
| F-D11 | WARNING | DSN password logging risk | **Improved** — `redactDSN()` masks password |
| F-D12 | WARNING | Alert metric names may not match | **Open** |
| F-D13 | WARNING | RBAC passwords in PostgreSQL logs | **Open** — ALTER ROLE visible |

---

## 11. MT5 Bridge & Execution

### 11.1 Architecture

| File | LoC | Purpose | Tests |
|------|-----|---------|-------|
| main.py | ~100 | Entry point, gRPC server startup | 0 |
| config.py | ~80 | MT5 connection config | 0 |
| grpc_server.py | ~200 | ExecuteTrade RPC, rate limiting | YES |
| order_manager.py | ~398 | Dedup, validation, lot clamping, execution | YES |
| position_tracker.py | ~300 | Trailing stops, closed position detection | YES |
| connector.py | ~150 | MT5 API wrapper | 0 |
| trade_recorder.py | ~120 | Trade result database persistence | YES |
| __init__.py | 3 | - | - |

### 11.2 Execution Flow

```
gRPC ExecuteTrade(TradingSignal)
    │
    ├── Rate limit (Redis, 10/min, burst 5)
    ├── Proto → Dict conversion
    │
    v
OrderManager.execute_signal(signal)
    ├── Signal age validation (max 30s) ─ FIXED since v1.0
    ├── Dedup check (60s window, IN-MEMORY)
    ├── 7 validations:
    │   [1] Direction valid (BUY/SELL)
    │   [2] Lots > 0
    │   [3] Stop-loss > 0
    │   [4] Open positions < 5
    │   [5] Spread < 30 points
    │   [6] Margin sufficient
    │   [7] Drawdown check ─ FIXED since v1.0
    ├── Lot clamping (min/max, round to vol_step)
    ├── Slippage calculation (direction-aware) ─ FIXED since v1.0
    ├── Select MARKET or LIMIT order
    └── Submit to MT5 via connector

Background (every 5s):
    PositionTracker.update()
    ├── Detect closed positions → TradeRecorder.record() ─ NEW
    └── Update trailing stops (4 modes: basic, atr, dynamic, hybrid)
```

### 11.3 Configuration Alignment

| Parameter | Algo-Engine | MT5 Bridge | Aligned? |
|-----------|-------------|-----------|----------|
| Max positions | 5 | 5 | YES |
| Max daily loss | 2.0% | 2.0% | YES (now enforced) |
| Max drawdown | 5.0% | 5.0% | **FIXED** — was 10%, now 5% |
| Max lot size | 0.10 | 1.0 | Brain more restrictive (OK) |
| Signal max age | N/A | 30s | **FIXED** — now validated |

### 11.4 Trailing Stop Logic

| Mode | Activation | Movement |
|------|-----------|----------|
| Basic | Profit > activation_pips | SL follows by trail_pips |
| ATR | Profit > ATR × multiplier | SL at price - ATR × multiplier |
| Dynamic | Profit > initial_stop × ratio | SL narrows as profit grows |
| Hybrid | Max(ATR, basic) activation | ATR-based with minimum floor |

**BUY**: SL moves UP when profit exceeds threshold. Correct.
**SELL**: SL moves DOWN when profit exceeds threshold. Correct.

### 11.5 Feedback Loop Status

**Partial implementation**:
1. `PositionTracker.update()` detects closed positions — YES
2. `TradeRecorder.record()` persists to database — YES (NEW since v1.0)
3. `main.py:454-468` polls `bridge_client.get_closed_trades()` — YES
4. `portfolio_manager.record_close()` + `spiral_protection.record_trade_result()` — YES

**Gap**: `get_closed_trades()` relies on an internal buffer in `BridgeClient` that is populated by polling. The `StreamTradeUpdates` gRPC streaming RPC is defined in proto but NOT implemented — trades are only detected when `PositionTracker.update()` runs (every 5s). If algo-engine polls every 10 bars and bars arrive every 5 minutes, trade close detection could lag by 50 minutes.

### 11.6 XAGUSD Pip Size

**Status**: Partially fixed. Position sizer has correct `0.001` for XAGUSD. Position tracker uses heuristic based on symbol name and digits — for `XAG` symbols with `digits=3`, returns `0.01` which is the pip size for silver (1 pip = $0.01 for XAG). The discrepancy between modules (0.001 in sizer vs 0.01 in tracker) stems from different pip definitions.

**Assessment**: Reduced from CRITICAL to MEDIUM — functionally acceptable but inconsistent terminology.

### 11.7 Findings

| ID | Severity | Finding | Status |
|---|----------|---------|--------|
| F-M1 | ~~CRITICAL~~ | XAGUSD pip size wrong | **Partially Fixed** — Reduced to MEDIUM |
| F-M2 | CRITICAL | No real-time feedback loop | **Partially Fixed** — Polling exists but gRPC streaming not implemented |
| F-M3 | CRITICAL | MT5 Bridge Windows-only | **Open** — Architectural constraint |
| F-M4 | HIGH | Lot clamping unsafe | **Open** — round-down can produce < vol_min |
| F-M5 | ~~HIGH~~ | Config drawdown mismatch | **FIXED** — Both 5% now |
| F-M6 | HIGH | Dedup not persistent | **Open** — in-memory dict |
| F-M7 | HIGH | Test coverage low | **Improved** — 4 test files now (up from 1) |
| F-M8 | ~~WARNING~~ | Slippage ignores direction | **FIXED** |
| F-M9 | ~~WARNING~~ | Signal age not validated | **FIXED** |
| F-M10 | WARNING | ERROR mapped to REJECTED in gRPC | **Open** |
| F-M11 | WARNING | StreamTradeUpdates not implemented | **Open** — placeholder empty |
| NEW-MT1 | MEDIUM | Trade close detection lag (up to 50 min) | Polling interval × bar frequency |

---

## 12. Infrastructure, CI/CD & Security

### 12.1 Docker Compose Stack

| Service | Image | Ports | Resources | Health Check |
|---------|-------|-------|-----------|-------------|
| postgres | timescale/timescaledb:pg16 | 5432 | - | pg_isready |
| redis | redis:7-alpine | 6379 | - | redis-cli ping (TLS-aware) |
| data-ingestion | Custom (Go) | 5555, 9090, 9091 | 1 CPU, 1G | wget healthz |
| algo-engine | Custom (Python) | 50057, 8087, 9097 | 2 CPU, 2G | urllib health |
| mt5-bridge | Custom (Python) | 50055, 9094 | 1 CPU, 512M | grpc channel_ready |
| dashboard | Custom (Python) | 8888 | 0.5 CPU, 512M | urllib health |
| prometheus | prom/prometheus:v2.50.1 | 9091→9090 | - | - |
| grafana | grafana/grafana:10.3.3 | 3000 | - | - |

### 12.2 Docker Security Checklist

| Check | Status | Notes |
|-------|--------|-------|
| Non-root containers | Partial | Go service runs as non-root; Python services need verification |
| Read-only filesystem | NO | Not configured |
| Resource limits | YES | CPU and memory limits on all services |
| Secret via env vars | YES | `${VAR:?required}` pattern |
| No default passwords | YES | DB and Redis require explicit passwords |
| Network segmentation | YES | 3 networks, backend `internal: true` |
| Health checks | YES | All services have health probes |
| Volume mounts read-only | YES | Certs, configs mounted `:ro` |
| TLS certificates | YES | Generated by `generate-certs.sh`, excluded from git |
| Image pinning | YES | Specific versions (pg16, redis:7, prometheus:v2.50.1, grafana:10.3.3) |

### 12.3 CI/CD Pipeline

**GitHub Actions (`ci.yml`)**:

| Job | Steps | Status |
|-----|-------|--------|
| python-lint-test | ruff, black, mypy, pytest | **Issue: references ml-training** |
| go-lint-test | go vet, golangci-lint, `go test -race` | OK |
| docker-build | 3 service images | OK — context fixed |

**Security Scanning (`security.yml` — weekly)**:

| Tool | Purpose | Status |
|------|---------|--------|
| pip-audit | Python CVE scanning | Active |
| govulncheck | Go vulnerability checking | Active |
| trufflehog | Secret scanning | Active |

### 12.4 CI Pipeline Issues

**NEW FINDING**: `ci.yml` references `services/ml-training` in multiple locations:
- Python install step (line ~42)
- Lint step (line ~53)
- Type check step (line ~61)
- Test step (line ~68)
- Docker build job (line ~83, ~228-231)

The ml-training service has been removed from the project. CI will fail on these steps.

### 12.5 TLS/mTLS Infrastructure

| Component | Certificate | Type | Validity |
|-----------|------------|------|----------|
| Root CA | ca.crt/ca.key | RSA 4096-bit | 365 days |
| PostgreSQL | postgres-server.crt/key | Server | 365 days |
| Redis | redis-server.crt/key | Server | 365 days |
| data-ingestion | data-ingestion.crt/key | Client+Server | 365 days |
| algo-engine | algo-engine.crt/key | Client | 365 days |
| mt5-bridge | mt5-bridge.crt/key | Server+Client | 365 days |
| console | console.crt/key | Client | 365 days |

**TLS Status**: Optional (MONEYMAKER_TLS_ENABLED=false by default). When enabled:
- PostgreSQL: sslmode=verify-full
- Redis: --tls with CA verification
- gRPC: mTLS with client+server certificates

### 12.6 OWASP Top 10 Analysis

#### 1. Injection ✅ PASS
- SQL: SQLAlchemy ORM (no raw queries)
- Command: No shell execution with user input
- gRPC/ZMQ: Binary protocols (no string concatenation)

#### 2. Authentication ✅ PASS
- Service-to-service: gRPC with mTLS (optional)
- Database: Password-based with RBAC
- Redis: Password required (`:?required` pattern)

#### 3. Sensitive Data Exposure ⚠️ MEDIUM
- Telegram token: Masked in `safe_dump()` (config.py:148) ✅
- Redis passwords: In connection URL (handled by moneymaker_common) ✅
- **Git history**: `.env` password `Trade.2026.Macena` still in history ❌
- **DSN logging**: Go service uses `redactDSN()` ✅

#### 4. Broken Access Control ✅ PASS
- Database RBAC: 4 roles with least-privilege
- No web API exposed (internal services)
- gRPC: mTLS when enabled

#### 5. Security Misconfiguration ⚠️ MEDIUM
- **Grafana anonymous admin**: `GF_AUTH_ANONYMOUS_ENABLED=true`, `GF_AUTH_ANONYMOUS_ORG_ROLE=Admin` — anyone can modify dashboards
- TLS disabled by default (acceptable for dev, not production)

#### 6. XSS ⚠️ LOW
- Dashboard (Flask/FastAPI): Needs review for template injection
- Grafana: Uses official image (patched)

#### 7. Insecure Deserialization ✅ PASS
- Protobuf (safe), JSON (standard library)
- No pickle/eval/exec

#### 8. Known Vulnerabilities ✅ TO VERIFY
- pip-audit and govulncheck in CI
- Dependencies pinned with ranges (not exact versions)

#### 9. Logging & Monitoring ✅ PASS
- Structured logging (structlog/zap)
- Audit trail (PostgreSQL, append-only)
- Prometheus metrics (28 defined)
- 10 alert rules
- Sentry integration (optional)

#### 10. Server-Side Request Forgery ✅ PASS
- No user-controlled URL fetching
- External data service uses hardcoded FRED/CBOE/CFTC URLs

### 12.7 Secret Management

| Secret | Storage | Status |
|--------|---------|--------|
| DB password | Env var (required) | OK |
| Redis password | Env var (required) | OK |
| Grafana password | Env var (default: admin) | WARNING — weak default |
| Telegram token | Env var (optional) | OK — masked in safe_dump |
| MT5 account/password | Env var | OK |
| Polygon API key | Env var | OK |
| Binance API key/secret | Env var | OK — disabled |
| `.env` in git history | **COMPROMISED** | **CRITICAL** — must rotate |

### 12.8 Monitoring Stack

**Prometheus** — 15s scrape interval, 4 targets:

| Target | Port | Metrics |
|--------|------|---------|
| data-ingestion | 9090 | ticks_received, bars_aggregated, db_writes |
| algo-engine | 9097 | pipeline_latency, signals_generated, regime_classified |
| mt5-bridge | 9094 | trades_executed, bridge_available, position_count |
| prometheus | 9090 | self-monitoring |

**10 Alert Rules**:

| Rule | Severity | Trigger | Status |
|------|----------|---------|--------|
| KillSwitchActivated | CRITICAL | kill_switch_active == 1 | OK |
| CriticalDrawdown | CRITICAL | drawdown > 5% | OK |
| NoTicksReceived | CRITICAL | no ticks 5min | OK |
| ServiceDown | CRITICAL | service down 1min | OK |
| BridgeUnavailable | CRITICAL | bridge down 2min | OK |
| HighDrawdown | WARNING | drawdown > 3% (5min) | OK |
| DailyLossApproaching | WARNING | daily_loss > 1.5% (1min) | OK |
| SpiralProtectionActive | WARNING | consecutive_losses > 3 | OK |
| HighPipelineLatency | WARNING | P99 > 100ms (5min) | OK |
| HighErrorRate | WARNING | errors > 0.1/s (5min) | OK |

**Missing**: DailyLossCritical alert at 2% (kill switch threshold). Gap between warning at 1.5% and kill switch at 2%.

**5 Grafana Dashboards**:
1. Overview — kill switch, service status, error rates, latency
2. Risk — daily loss gauge, drawdown, VaR/CVaR, Sortino, concentration
3. Data Pipeline — ticks/s, bars/s, throughput
4. Trading — signal rates, win rate, P&L, execution latency
5. Training — placeholder (ML removed)

### 12.9 Findings

| ID | Severity | Finding | Status |
|---|----------|---------|--------|
| F-I1 | CRITICAL | `.env` password in git history | **Open** — file untracked but history not cleaned |
| F-I2 | ~~HIGH~~ | CI Docker build context wrong | **FIXED** |
| F-I3 | ~~HIGH~~ | Port mismatch Dockerfile/compose | **FIXED** |
| F-I4 | ~~WARNING~~ | Redis healthcheck TLS-incompatible | **FIXED** — conditional check |
| F-I5 | WARNING | MyPy pre-commit hardcoded file list | **Open** |
| F-I6 | WARNING | Redis health check shallow | **Open** |
| F-I7 | ~~WARNING~~ | Backend network not internal | **FIXED** |
| F-I8 | WARNING | external-data not in CI | **Open** |
| F-I9 | WARNING | No Alertmanager | **Open** — custom dispatcher |
| F-I10 | WARNING | Sentry PII scrubbing incomplete | **Open** |
| NEW-CI1 | **CRITICAL** | CI references removed ml-training service | ci.yml lines ~42,53,61,68,83,228 |
| NEW-CI2 | **HIGH** | Grafana anonymous admin access in production | `GF_AUTH_ANONYMOUS_ORG_ROLE=Admin` |
| NEW-CI3 | MEDIUM | Grafana default password `admin` | `GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}` |
| NEW-CI4 | WARNING | Training dashboard placeholder (ML removed) | Dead dashboard config |
| NEW-CI5 | WARNING | No container image scanning (Trivy/Snyk) | Only pip-audit and govulncheck |

---

## 13. Test Coverage & Quality

### 13.1 Test Summary

| Service | Test Files | Test Count (est.) | LoC | Pass Rate |
|---------|-----------|-------------------|-----|-----------|
| algo-engine | 27 | ~355 | 4,245 | 100% |
| data-ingestion (Go) | 2 | ~15 | ~300 | 100% |
| mt5-bridge | 4 | ~20 | ~400 | 100% |
| python-common | ~8 | ~40 | ~500 | 100% |
| console | 0 | 0 | 0 | N/A |
| external-data | 0 | 0 | 0 | N/A |
| dashboard | 0 | 0 | 0 | N/A |
| **Total** | **~41** | **~430** | **~5,445** | **100%** |

### 13.2 Coverage by Module (Algo-Engine)

```
algo-engine/
├── Core Pipeline
│   ├── engine.py ........................... Tested via integration
│   ├── main.py ............................. 0 direct tests
│   ├── config.py ........................... Tested via validators
│   ├── grpc_client.py ...................... YES (conversion tests)
│   ├── zmq_adapter.py ...................... YES (parse tests)
│   ├── kill_switch.py ...................... YES (6 tests)
│   └── portfolio.py ........................ YES (9 tests)
│
├── Features
│   ├── pipeline.py ......................... YES (10 tests)
│   ├── technical.py ........................ YES (63 tests)
│   ├── regime.py ........................... YES (16 tests)
│   ├── mtf_analyzer.py ..................... YES
│   ├── data_quality.py ..................... 0 tests
│   ├── data_sanity.py ...................... 0 tests
│   ├── feature_drift.py .................... 0 tests
│   ├── leakage_auditor.py .................. 0 tests
│   ├── macro_features.py ................... 0 tests
│   ├── regime_shift.py ..................... 0 tests
│   └── sessions.py ......................... 0 tests
│
├── Strategies
│   ├── trend_following.py .................. YES (9 tests)
│   ├── mean_reversion.py ................... YES (9 tests)
│   ├── defensive.py ........................ YES (6 tests)
│   ├── regime_router.py .................... YES (5 tests)
│   ├── breakout.py ......................... 0 tests
│   ├── vol_momentum.py ..................... 0 tests
│   ├── ou_mean_reversion.py ................ 0 tests
│   ├── adaptive_trend.py ................... 0 tests
│   └── multi_factor.py ..................... 0 tests
│
├── Signals/Safety
│   ├── validator.py ........................ YES (15 tests)
│   ├── position_sizer.py ................... YES (8 tests)
│   ├── generator.py ........................ YES (9 tests)
│   ├── spiral_protection.py ................ YES (9 tests)
│   ├── advanced_sizer.py ................... Tested via math tests
│   ├── trailing_stop.py .................... Tested via integration
│   ├── correlation.py ...................... 0 tests
│   ├── rate_limiter.py ..................... 0 tests
│   └── signal_router.py .................... 0 tests
│
├── Math (ALL TESTED — Phase 2)
│   ├── bayesian.py ......................... YES (~260 LoC tests)
│   ├── stochastic.py ....................... YES (~250 LoC tests)
│   ├── extreme_value.py .................... YES (~250 LoC tests)
│   ├── fractal.py .......................... YES (~230 LoC tests)
│   ├── spectral.py ......................... YES (~250 LoC tests)
│   ├── ou_process.py ....................... YES (~250 LoC tests)
│   ├── copula.py ........................... YES (~280 LoC tests)
│   └── information_theory.py ............... YES (~250 LoC tests)
│
├── Backtesting (Phase 1)
│   ├── engine.py ........................... Tested via integration
│   ├── simulator.py ........................ Tested via integration
│   ├── metrics.py .......................... Tested via integration
│   └── data_loader.py ...................... 0 tests
│
├── Optimization (Phase 5)
│   ├── walk_forward.py ..................... 0 tests
│   ├── monte_carlo.py ...................... 0 tests
│   └── adaptive.py ......................... 0 tests
│
├── Analysis (10 files) ..................... 0 tests
├── Knowledge (7 files) .................... 0 tests
├── Processing (13 files) .................. 0 tests
└── Observability ........................... 0 tests
```

### 13.3 Coverage Summary

| Category | Files Tested | Files Untested | Coverage |
|----------|-------------|----------------|----------|
| Core pipeline | 7/7 | 0 | **100%** |
| Features | 4/11 | 7 | ~36% |
| Strategies | 4/9 | 5 | ~44% |
| Safety systems | 5/8 | 3 | ~63% |
| Math modules | 8/8 | 0 | **100%** |
| Backtesting | 0/4 | 4 | 0% |
| Optimization | 0/3 | 3 | 0% |
| Analysis | 0/10 | 10 | 0% |
| Knowledge | 0/7 | 7 | 0% |
| Processing | 0/13 | 13 | 0% |
| Data Ingestion (Go) | 2/6 | 4 | ~33% |
| MT5 Bridge | 4/7 | 3 | ~57% |

**Global module coverage**: ~35% of modules have at least one test (up from ~30% in v1.0).

### 13.4 Test Quality Assessment

| Aspect | Assessment |
|--------|-----------|
| Assert density | Good — 2-4 asserts per test on average |
| Edge cases | Moderate — safety tests cover boundaries well, strategies less so |
| Mock usage | Good — Redis, gRPC mocked in unit tests |
| Fixtures | Shared via conftest.py and fixtures/ directory |
| Async testing | Good — pytest-asyncio with auto mode |
| Race detection | Good — Go uses `go test -race` |

### 13.5 Missing Test Categories

| Category | Status | Priority |
|----------|--------|----------|
| E2E tick-to-trade | MISSING | HIGH |
| Integration (multi-service) | MISSING | HIGH |
| Performance/Load | MISSING | MEDIUM |
| Chaos/Resilience | MISSING | LOW |
| Security/Penetration | MISSING | MEDIUM |

### 13.6 Findings

| ID | Severity | Finding | Status |
|---|----------|---------|--------|
| F-T1 | HIGH | Zero E2E tick-to-trade test | **Open** |
| F-T2 | HIGH | Zero tests for analysis/ (10 modules) | **Open** |
| F-T3 | HIGH | Zero tests for knowledge/ (7 modules) | **Open** |
| F-T4 | HIGH | Zero tests for processing/ (13 modules) | **Open** |
| F-T5 | HIGH | Zero tests for Go connectors | **Open** — aggregator + normalizer tested |
| F-T6 | WARNING | Console has zero tests | **Open** |
| F-T7 | WARNING | External-data has zero tests | **Open** |
| F-T8 | WARNING | Diagnostic tools not in CI | **Open** |
| NEW-T1 | MEDIUM | Zero tests for optimization/ (3 modules) | walk_forward, monte_carlo, adaptive |
| NEW-T2 | MEDIUM | Zero tests for backtesting/ (4 modules) | engine, simulator, metrics, data_loader |
| NEW-T3 | MEDIUM | 5 of 9 strategies have 0 tests | breakout, vol_momentum, ou_mr, adaptive, multi_factor |

---

## 14. Dependency Audit

### 14.1 Python Dependencies (algo-engine)

| Package | Version Range | Purpose | Risk |
|---------|--------------|---------|------|
| pydantic | >=2.5, <3.0 | Settings validation | LOW |
| pydantic-settings | >=2.1, <3.0 | Env var loading | LOW |
| structlog | >=23.2, <25.0 | Structured logging | LOW |
| prometheus-client | >=0.19, <1.0 | Metrics | LOW |
| grpcio | >=1.60, <2.0 | gRPC client | LOW |
| protobuf | >=4.25, <7.0 | Proto serialization | LOW (wide range) |
| pyzmq | >=25.1, <27.0 | ZeroMQ bindings | LOW |
| numpy | >=1.26, <3.0 | Numerical computing | LOW |
| scipy | >=1.11, <2.0 | Scientific computing | LOW |
| pywavelets | >=1.5, <2.0 | Wavelet transforms | LOW |
| arch | >=6.0, <8.0 | ARCH/GARCH models | LOW |
| redis | >=5.0, <6.0 | Redis client | LOW |
| sqlalchemy | >=2.0, <3.0 | SQL ORM | LOW |
| sqlmodel | >=0.0.16, <1.0 | SQL model layer | LOW |
| asyncpg | >=0.29, <1.0 | Async PostgreSQL | LOW |

### 14.2 Go Dependencies (data-ingestion)

| Package | Version | Purpose | Risk |
|---------|---------|---------|------|
| gorilla/websocket | v1.5.3 | WebSocket client | LOW |
| go-zeromq/zmq4 | v0.17.0 | ZeroMQ PUB | LOW |
| jackc/pgx/v5 | v5.7.2 | PostgreSQL driver | LOW |
| shopspring/decimal | v1.4.0 | Decimal arithmetic | LOW |
| uber/zap | v1.27.0 | Structured logging | LOW |

### 14.3 Version Pinning Analysis

**Python**: Uses range pinning (e.g., `>=2.5,<3.0`) — good balance of stability and updates.
**Go**: Uses exact version pinning via go.sum — standard and secure.

### 14.4 License Compliance

All dependencies use permissive licenses (MIT, Apache 2.0, BSD). No GPL/copyleft concerns.

### 14.5 Findings

| ID | Severity | Finding | Detail |
|---|----------|---------|--------|
| NEW-DEP1 | MEDIUM | protobuf range too wide (>=4.25,<7.0) | Major version jump could break compatibility |
| NEW-DEP2 | WARNING | MetaTrader5 Python package not in pyproject.toml | Installed separately on Windows only |

---

## 15. Performance Analysis

### 15.1 Pipeline Latency Budget

| Stage | Target | Estimated | Status |
|-------|--------|-----------|--------|
| ZMQ receive + parse | <2ms | ~1ms | OK |
| Data quality check | <1ms | <1ms | OK |
| Feature computation (60-dim) | <20ms | ~10-15ms | OK |
| Advanced features (optional) | <15ms | ~5-10ms | OK |
| Regime classification | <5ms | ~2ms | OK |
| Strategy routing | <5ms | ~2-3ms | OK |
| Signal generation + sizing | <5ms | ~2ms | OK |
| Validation (11 checks) | <2ms | ~1ms | OK |
| gRPC dispatch | <10ms | ~5ms | OK |
| **Total** | **<100ms P99** | **~30-50ms** | **OK** |

Pipeline timeout: 5 seconds (hardcoded in `engine.py:106`). Generous margin.

### 15.2 Memory Footprint

| Component | Estimated | Notes |
|-----------|-----------|-------|
| Bar buffer (per symbol) | ~10KB | 200 bars × ~50 bytes |
| Feature pipeline state | ~5KB | 60 indicators per symbol |
| Regime classifier | ~2KB | HMM state + hysteresis |
| Math modules (all 8) | ~50KB | Online estimators |
| Portfolio state | ~1KB | Dict with counters |
| Kill switch cache | ~100B | Bool + reason string |
| Total per-symbol | ~70KB | |
| 10 symbols | ~700KB | Well within 2G container limit |

### 15.3 Decimal vs Float Performance

Decimal operations are approximately 10-100x slower than float. However:
- Financial calculations require exact precision (no IEEE 754 accumulation errors)
- Pipeline is I/O bound (ZMQ/gRPC), not CPU bound
- 5-second timeout provides massive headroom
- **Assessment**: Correct tradeoff for financial application

### 15.4 Findings

| ID | Severity | Finding | Detail |
|---|----------|---------|--------|
| NEW-PERF1 | WARNING | Pipeline timeout hardcoded at 5s | Should be configurable for different hardware |
| NEW-PERF2 | WARNING | No performance benchmarks in CI | Regression detection not automated |

---

## 16. Consolidated Findings

### 16.1 Previously Reported — Now FIXED (23 of 45)

| ID | Description | Fix Evidence |
|---|-------------|-------------|
| F01 | Kill switch tuple as bool | `main.py:305` |
| F02 | gRPC direction enum | `grpc_client.py:62` |
| F04 | Port mismatch | config.py + docker-compose aligned |
| F04-PnL | Fake PnL data | `main.py:454-468` |
| F07 | Portfolio mutable leak | `portfolio.py:78` |
| F08 | BridgeClient.close() not called | `main.py:500` |
| F12 | Dead code _parse_ohlcv | main.py rewritten |
| F13 | .env.example wrong names | env_prefix="" works correctly |
| F-D1 | Missing PRIMARY KEY | `008_add_unique_constraints.sql` |
| F-D2 | Data race reconnectAttempts | `atomic.Int32` |
| F-D9 | No retention policy | `009_add_retention_policies.sql` |
| F-FP2 | _prev_adx = 0 | `regime.py:97`: `None` |
| F-I2 | CI Docker context wrong | `context: .` with `-f` |
| F-I3 | Port mismatch Dockerfile | Updated EXPOSE |
| F-I4 | Redis healthcheck TLS | Conditional check |
| F-I7 | Backend not internal | `internal: true` |
| F-M5 | Config drawdown mismatch | Both 5% |
| F-M8 | Slippage ignores direction | Direction-aware |
| F-M9 | Signal age not validated | Age check added |
| F-S2 | Spiral not persisted | Redis persistence |
| F09 | Portfolio partial persist | Expanded fields |
| God fn | run_brain() 944 lines | AlgoEngine class |
| F-D11 | DSN logging | redactDSN() |

### 16.2 Previously Reported — Still OPEN (22)

| ID | Severity | Description |
|---|----------|-------------|
| F-I1 | **CRITICAL** | `.env` password in git history |
| F-M2 | **CRITICAL** | Feedback loop incomplete (no gRPC streaming) |
| F-M3 | **CRITICAL** | MT5 Bridge Windows-only |
| F05 | HIGH | ADX not validated [0,100] |
| F-FP1 | HIGH | 5 placeholder features |
| F-S3 | HIGH | Redis persistence not tested |
| F-S4 | HIGH | Optional validator controls not tested |
| F-D3 | HIGH | No reconnection in binance.go |
| F-D4 | HIGH | Sync flush blocks main loop |
| F-M4 | HIGH | Lot clamping unsafe |
| F-M6 | HIGH | Dedup not persistent |
| F-M7 | HIGH | MT5 Bridge test coverage low |
| F-T1 | HIGH | Zero E2E test |
| F-T2-5 | HIGH | Zero tests for analysis/knowledge/processing |
| F-S1 | MEDIUM | Spiral x drawdown implicit (comment needed) |
| F10 | MEDIUM | Unknown symbols pass silently |
| F-S5-10 | WARNING | Various safety warnings |
| F-D5-13 | WARNING | Various data warnings |
| F-M10-11 | WARNING | MT5 bridge warnings |
| F-I5,6,8-10 | WARNING | Infrastructure warnings |
| F-T6-8 | WARNING | Test coverage warnings |
| F-FP3-6 | WARNING | Feature pipeline warnings |

### 16.3 NEW Findings (17)

#### CRITICAL (1)

| ID | Finding | Location |
|---|---------|----------|
| NEW-CI1 | CI references removed ml-training service | ci.yml lines ~42,53,61,68,83,228 |

#### HIGH (3)

| ID | Finding | Location |
|---|---------|----------|
| NEW-CI2 | Grafana anonymous admin access | docker-compose.yml:311-312 |
| NEW-STR1 | 4 of 8 strategies have 0 tests | vol_momentum, ou_mr, adaptive, multi_factor |
| NEW-T3 | 5 of 9 strategies have 0 tests total | Including breakout |

#### MEDIUM (8)

| ID | Finding | Location |
|---|---------|----------|
| NEW-AE1 | algo_max_lots float→Decimal conversion | config.py:56 |
| NEW-AE2 | Pipeline timeout not configurable | engine.py:106 |
| NEW-FP1 | 10 feature/analysis modules 0 tests | feature_drift, leakage, macro, etc. |
| NEW-MATH1 | Stochastic simulation uses float | stochastic.py |
| NEW-BT1 | Backtest fixed spread model | simulator.py |
| NEW-MT1 | Trade close detection lag | main.py:448-449 |
| NEW-OPT1 | Exhaustive grid search | walk_forward.py |
| NEW-DEP1 | protobuf range too wide | pyproject.toml |

#### WARNING (5)

| ID | Finding | Location |
|---|---------|----------|
| NEW-AE3 | No gRPC circuit breaker | main.py:415-445 |
| NEW-AE4 | parse_bar_message KeyError uncaught | main.py:331 |
| NEW-CI3 | Grafana default password | docker-compose.yml:308 |
| NEW-MATH2 | OU half-life can be negative | ou_process.py |
| NEW-PERF1 | Pipeline timeout hardcoded | engine.py:106 |

---

## 17. Risk Heat Map

### 17.1 Probability x Impact Matrix

```
                    IMPACT
            Very Low   Low    Medium    High    Critical
          ┌─────────┬────────┬─────────┬────────┬─────────┐
Very High │         │        │         │        │         │
          │         │        │         │        │         │
          ├─────────┼────────┼─────────┼────────┼─────────┤
High      │         │        │ NEW-CI1 │ F-I1   │ F-M3    │
          │         │        │         │        │         │
          ├─────────┼────────┼─────────┼────────┼─────────┤
Medium    │         │ F-FP1  │ NEW-CI2 │ F-M2   │         │
          │         │ F-D4   │ F-M6   │ F-T1   │         │
          ├─────────┼────────┼─────────┼────────┼─────────┤
Low       │ F-FP3-6 │ F-S7-9 │ F-M4   │ F-S3   │         │
          │ F-D5-8  │ NEW-AE │ NEW-STR │        │         │
          ├─────────┼────────┼─────────┼────────┼─────────┤
Very Low  │ F-I5    │ MATH2-4│ NEW-BT  │        │         │
          │         │ PERF1-2│         │        │         │
          └─────────┴────────┴─────────┴────────┴─────────┘
```

### 17.2 Risk Categories

| Category | Trend | Key Risks |
|----------|-------|-----------|
| Financial | IMPROVING | Spiral+drawdown composition works; kill switch fixed |
| Operational | STABLE | MT5 Windows-only; feedback loop partial |
| Security | IMPROVING | Password in git history; Grafana anonymous admin |
| Data Integrity | IMPROVING | Primary keys added; retention policies active |
| Compliance | STABLE | Audit trail intact; RBAC defined |

---

## 18. Production Readiness Matrix

### 18.1 Per-Service Scorecard

| Dimension | data-ingestion | algo-engine | mt5-bridge | console | dashboard | external-data | monitoring |
|-----------|---------------|-------------|-----------|---------|-----------|--------------|-----------|
| Code Quality | A | A | B | B | C | B | A |
| Test Coverage | B | B | C | F | F | F | A |
| Error Handling | A | A | B | B | C | B | A |
| Monitoring | A | A | B | N/A | N/A | N/A | A |
| Security | A | A | B | B | C | B | B |
| Documentation | A | A | B | B | C | C | B |
| Configuration | A | A | B | B | B | C | A |
| Deployment | A | A | D | B | B | F | A |
| Performance | A | A | B | A | C | B | A |
| Scalability | B | B | C | A | C | B | A |
| Resilience | A | A | C | B | C | C | A |
| Observability | A | A | B | C | C | C | A |
| **Grade** | **A** | **A** | **C+** | **C** | **D+** | **D** | **A** |

### 18.2 Production Deployment Prerequisites

| # | Prerequisite | Status | Blocking? |
|---|------------|--------|-----------|
| 1 | All CRITICAL findings resolved | 3 open | **YES** |
| 2 | CI pipeline passes (clean build) | ml-training refs break it | **YES** |
| 3 | Password rotation (git history leak) | Not done | **YES** |
| 4 | Grafana auth configured | Anonymous admin | **YES** |
| 5 | MT5 Bridge deployment strategy | Windows VM needed | **YES** |
| 6 | TLS enabled for production | Optional currently | Recommended |
| 7 | E2E test passing | Not written | Recommended |
| 8 | 1 week paper trading | Not started | **YES** |
| 9 | Backup strategy (pg_dump) | Not configured | Recommended |
| 10 | Monitoring verified with live data | Not tested | Recommended |

### 18.3 Go/No-Go Decision

**Current Status: NO-GO**

Blocking items:
1. CI pipeline broken (ml-training references)
2. Grafana anonymous admin access
3. Password in git history (rotation needed)
4. MT5 Bridge deployment plan (Windows VM)
5. Paper trading not started

**Estimated time to GO**: 1-2 weeks with focused remediation.

---

## 19. Remediation Roadmap

### Phase 0: Immediate Fixes (Days 1-2)

**Security (CRITICAL)**:
- [ ] Remove ml-training references from ci.yml
- [ ] Disable Grafana anonymous access: `GF_AUTH_ANONYMOUS_ENABLED=false`
- [ ] Set strong Grafana admin password (not "admin")
- [ ] Rotate ALL passwords (DB, Redis, Grafana, API keys)
- [ ] Run `trufflehog` to verify no other leaked secrets
- [ ] Consider `git filter-branch` or BFG to remove .env from history

**Feedback Loop**:
- [ ] Implement `StreamTradeUpdates` gRPC in mt5-bridge (or increase polling frequency)

### Phase 1: Core Stability (Days 3-5)

- [ ] Fix F05: ADX range validation [0,100] in trend_following.py
- [ ] Fix F-M4: Lot clamping safety (ensure lots >= vol_min after round-down)
- [ ] Fix NEW-AE4: Wrap `parse_bar_message()` in try/except in main loop
- [ ] Fix NEW-MATH2: Guard OU half-life against negative values
- [ ] Make pipeline timeout configurable via `ALGO_PIPELINE_TIMEOUT_SEC`
- [ ] Persist dedup state to Redis (F-M6)
- [ ] Add comment explaining spiral x drawdown composition

### Phase 2: Test Coverage (Week 2)

- [ ] Write tests for 5 untested strategies (breakout, vol_momentum, ou_mr, adaptive, multi_factor)
- [ ] Write tests for CorrelationChecker and RateLimiter
- [ ] Write tests for backtesting modules (engine, simulator, metrics)
- [ ] Write tests for optimization modules (walk_forward, monte_carlo)
- [ ] Write E2E tick-to-trade test
- [ ] Target: 50% module coverage (up from ~35%)

### Phase 3: Monitoring & CI Cleanup (Week 2-3)

- [ ] Add DailyLossCritical alert at 2% (kill switch threshold)
- [ ] Remove Training dashboard placeholder
- [ ] Add container image scanning (Trivy) to CI
- [ ] Complete PII scrubbing in sentry_setup.py
- [ ] Integrate external-data service into CI/CD
- [ ] Verify all Grafana dashboards with synthetic data

### Phase 4: Production Preparation (Week 3-4)

- [ ] Deploy Docker stack on Linux (without mt5-bridge)
- [ ] Deploy MT5 Bridge natively on Windows VM
- [ ] Enable TLS for production
- [ ] Enable mTLS between gRPC services
- [ ] Configure automated DB backup (pg_dump daily)
- [ ] Start paper trading (minimum 1 week)
- [ ] Monitor and tune alert thresholds

### Effort Estimates

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 0 | 1-2 days | **IMMEDIATE** |
| Phase 1 | 2-3 days | HIGH |
| Phase 2 | 3-5 days | HIGH |
| Phase 3 | 2-3 days | MEDIUM |
| Phase 4 | 5-7 days | MEDIUM |
| **Total** | **~15-20 days** | |

---

## 20. Appendices

### A. Glossary

| Term | Definition |
|------|-----------|
| ATR | Average True Range — volatility measure |
| BB | Bollinger Bands — price channel based on standard deviation |
| CVaR | Conditional Value at Risk — expected loss beyond VaR |
| EVT | Extreme Value Theory — tail risk modeling |
| GPD | Generalized Pareto Distribution — tail distribution |
| GBM | Geometric Brownian Motion — stock price model |
| HMM | Hidden Markov Model — regime detection |
| mTLS | Mutual TLS — bidirectional certificate authentication |
| OU | Ornstein-Uhlenbeck — mean-reverting stochastic process |
| R/S | Rescaled Range — Hurst exponent estimation method |
| RBAC | Role-Based Access Control |
| SL/TP | Stop-Loss / Take-Profit |
| ZMQ | ZeroMQ — lightweight messaging library |

### B. Configuration Reference

| Env Var | Default | Range | Service |
|---------|---------|-------|---------|
| ALGO_CONFIDENCE_THRESHOLD | 0.65 | (0,1] | algo-engine |
| ALGO_MAX_DAILY_LOSS_PCT | 2.0 | [0.5,10] | algo-engine |
| ALGO_MAX_DRAWDOWN_PCT | 5.0 | [1,25] | algo-engine |
| ALGO_RISK_PER_TRADE_PCT | 1.0 | [0.1,5] | algo-engine |
| ALGO_MAX_OPEN_POSITIONS | 5 | >0 | algo-engine |
| ALGO_MAX_LOTS | 0.10 | >0 | algo-engine |
| ALGO_MAX_SIGNALS_PER_HOUR | 10 | >0 | algo-engine |
| ALGO_SPIRAL_LOSS_THRESHOLD | 3 | - | algo-engine |
| ALGO_SPIRAL_COOLDOWN_MINUTES | 60 | - | algo-engine |
| MONEYMAKER_DB_PASSWORD | (required) | - | all |
| MONEYMAKER_REDIS_PASSWORD | (required) | - | all |
| MONEYMAKER_TLS_ENABLED | false | bool | all |
| POLYGON_API_KEY | (optional) | - | data-ingestion |
| MT5_ACCOUNT | (optional) | - | mt5-bridge |
| GRAFANA_PASSWORD | admin | - | monitoring |

### C. Prometheus Metrics Reference

| Metric | Type | Labels | Service |
|--------|------|--------|---------|
| moneymaker_pipeline_latency | Histogram | symbol | algo-engine |
| moneymaker_features_computed | Counter | symbol | algo-engine |
| moneymaker_regime_classified | Counter | regime | algo-engine |
| moneymaker_signals_generated | Counter | symbol, direction | algo-engine |
| moneymaker_signals_rejected | Counter | reason | algo-engine |
| moneymaker_signal_confidence | Histogram | - | algo-engine |
| moneymaker_pipeline_timeouts | Counter | symbol | algo-engine |
| moneymaker_service_up | Gauge | service | all |
| moneymaker_error_counter | Counter | service, error_type | all |

### D. Alert Rules Quick Reference

| Alert | Severity | Condition | For |
|-------|----------|-----------|-----|
| KillSwitchActivated | CRITICAL | kill_switch_active == 1 | 0s |
| CriticalDrawdown | CRITICAL | drawdown > 5% | 0s |
| NoTicksReceived | CRITICAL | no ticks 5min | 5m |
| ServiceDown | CRITICAL | up == 0 | 1m |
| BridgeUnavailable | CRITICAL | bridge down | 2m |
| HighDrawdown | WARNING | drawdown > 3% | 5m |
| DailyLossApproaching | WARNING | daily_loss > 1.5% | 1m |
| SpiralProtectionActive | WARNING | losses > 3 | 0s |
| HighPipelineLatency | WARNING | P99 > 100ms | 5m |
| HighErrorRate | WARNING | errors > 0.1/s | 5m |

---

*This report v2.0 consolidates findings from 11 individual audit reports plus expanded analysis of mathematical modules, backtesting, optimization, strategy correctness, dependency security, and performance. All findings from v1.0 have been verified against current source code with resolution status documented. The system has shown significant improvement since v1.0 with 23 of 45 original findings resolved.*
