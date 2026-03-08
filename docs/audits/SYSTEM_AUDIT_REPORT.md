# MONEYMAKER V1 — System Audit Report

> **Consolidated from 11 audit reports** | Last updated: 2026-03-09
> Scope: 7 services, ~12,877 LoC algo-engine, pure algorithmic/mathematical architecture
> All neural network and ML training code has been removed. The system operates as a rule-based algorithmic trading engine with advanced mathematical modules (stochastic, information theory, extreme value, fractal, spectral, Bayesian, OU process, copula).

---

## Executive Summary

MONEYMAKER V1 is a microservices algorithmic trading ecosystem with 7 services: data-ingestion (Go), algo-engine (Python), mt5-bridge (Python), console, dashboard, external-data, and monitoring. The architecture is well-designed with proto-first contracts, shared libraries, and network segmentation.

**Quality Score**: 7.5/10 — Solid architecture with production-blocking bugs that must be fixed before deployment.

### Critical Production Blockers

| # | Issue | Impact |
|---|-------|--------|
| 1 | Kill switch `is_active()` returns tuple but main.py treats as bool | Trading ALWAYS blocked |
| 2 | gRPC direction enum serialization broken | All signals have direction UNSPECIFIED |
| 3 | `ohlcv_bars` and `market_ticks` missing PRIMARY KEY | Duplicate data possible |
| 4 | `.env` with plaintext password committed to git history | Security compromise |
| 5 | MT5 Bridge cannot run in Docker Linux | MetaTrader5 is Windows-only |

### Findings Summary

| Severity | Count |
|----------|-------|
| CRITICO | 9 |
| ALTO | 14 |
| WARNING | 22 |
| **Total** | **45** |

---

## 1. Architecture & Service Map

### 1.1 Service Topology

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
|  | data-ingestion   | ==============> | algo-engine      |        |
|  | (Go)             |   :5555        | (Python)          |        |
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
|  +------------------+  +------------------+                       |
|  | Prometheus       |  | Grafana          |                       |
|  | (:9091->9090)    |  | (:3000)          |                       |
|  +------------------+  +------------------+                       |
+------------------------------------------------------------------+
```

### 1.2 Communication Protocols

| Source | Destination | Protocol | Port | Status |
|--------|------------|----------|------|--------|
| Polygon.io | data-ingestion | WebSocket/HTTPS | ext | OK |
| Binance | data-ingestion | WebSocket | ext | OK (disabled in V1) |
| data-ingestion | PostgreSQL | TCP/SQL | 5432 | OK |
| data-ingestion | algo-engine | ZeroMQ PUB/SUB | 5555 | OK |
| algo-engine | PostgreSQL | TCP/SQL (asyncpg) | 5432 | OK |
| algo-engine | Redis | TCP | 6379 | OK |
| algo-engine | mt5-bridge | gRPC | 50055 | OK |
| mt5-bridge | MetaTrader 5 | MT5 API (Windows) | local | **CRITICO** — Windows-only |
| Prometheus | all services | HTTP scrape | varies | See port issues below |

### 1.3 Network Segmentation (Docker)

3 Docker networks with appropriate isolation:
- **frontend**: Grafana (:3000), Prometheus
- **backend**: PostgreSQL, Redis, data-ingestion, algo-engine, mt5-bridge
- **monitoring**: Prometheus, Grafana, data-ingestion, algo-engine, mt5-bridge

### 1.4 Port Mapping — CRITICAL ISSUE (F04)

The algo-engine has a **complete port mismatch** between Dockerfile, docker-compose, and config defaults:

| Component | Dockerfile EXPOSE | docker-compose | config.py default | Pydantic env var |
|-----------|------------------|----------------|-------------------|-----------------|
| algo-engine gRPC | 50052 | 50054:50054 | 50052 | BRAIN_GRPC_PORT |
| algo-engine REST | 8082 | 8080:8080 | 8082 | BRAIN_REST_PORT |
| algo-engine metrics | 9092 | 9093:9093 | 9092 | BRAIN_METRICS_PORT |

**Impact**: The service is internally healthy but **unreachable** from Prometheus, Console, and any external client. The env var port override is NOT passed in docker-compose.

Additionally, `.env.example` uses the wrong env var name (`MONEYMAKER_BRAIN_GRPC_PORT` instead of `BRAIN_GRPC_PORT`) — Pydantic with `env_prefix=""` will never read it.

**data-ingestion health port** is also wrong: docker-compose maps `8081:8080` but the Go service listens on port 9091 (MetricsPort+1).

### 1.5 Shared Libraries

**moneymaker_common (Python)** — 12 modules, quality 8/10:
config, enums, metrics (28 Prometheus metrics), decimal_utils, logging (structlog), audit (hash chain), audit_pg, ratelimit, health, secrets, grpc_credentials, exceptions.

**go-common (Go)** — 4 modules: config, health, logging, ratelimit.

### 1.6 Console Blockers — Proto Definitions Missing

The 30+ console commands that interact with services have fallback placeholders. For real operation, the following RPC definitions are needed in proto files:

- **algo-engine** (`algo_engine.proto`): StartTraining, StopTraining, GetStatus, RunEvaluation, SaveCheckpoint, GetModelInfo
- **data-ingestion** (`data_ingestion.proto`): Start, Stop, GetStatus, ListSymbols, AddSymbol, RemoveSymbol, Backfill
- **mt5-bridge** (`mt5_bridge.proto`): Connect, Disconnect, GetStatus, GetPositions, GetHistory, CloseAll, GetSpread

All 3 services need `grpc.health.v1.Health` for the StatusPoller.

---

## 2. Algo-Engine Core Pipeline

### 2.1 Architecture Overview

The algo-engine is the heart of MONEYMAKER with the main loop in `main.py` (~1,609 LoC). The architecture follows a **cascade with graceful degradation**: data → features → regime → strategy → validation → dispatch gRPC.

Currently **only rule-based strategies are operational** (trend following, mean reversion, defensive, plus the new advanced strategies: vol_momentum, ou_mean_reversion, adaptive_trend, multi_factor).

### 2.2 Signal Flow

```
ZMQ SUB (tcp://data-ingestion:5555)
    |
    | topic: "bar.{symbol}.{timeframe}"
    v
zmq_adapter.py → OHLCVBar
    |
    v
FeaturePipeline.process(bar) → feature dict (60-dim)
    |
    v
RegimeClassifier.classify(features) → regime
    |
    v
RegimeRouter / Strategy Selection
    |
    v
SignalGenerator.generate_signal() → signal with SL/TP (ATR-based)
    |
    v
SignalValidator.validate() → 11 checks fail-fast
    |
    v
PositionSizer.calculate() → lots
    |
    v
SpiralProtection.check() → permission?
    |
    v
KillSwitch.is_active() → blocked? ← BUG: always True (F01)
    |
    v
CorrelationChecker.check() → currency exposure OK?
    |
    v
RateLimiter.allow() → under limit?
    |
    v
gRPC SendSignal() → MT5 Bridge ← BUG: direction UNSPECIFIED (F02)
```

### 2.3 CRITICAL BUGS

**F01 — Kill Switch Return Type Mismatch** (`main.py:887,1316` + `kill_switch.py:104`):

```python
# kill_switch.py:104 — returns tuple
async def is_active(self) -> tuple[bool, str]:
    return self._cached_active, self._cached_reason

# main.py:887 — treats tuple as bool
if await kill_switch.is_active():  # tuple ALWAYS truthy!
    continue  # SKIP ALL — trading BLOCKED
```

**Impact**: Trading is ALWAYS blocked because a non-empty tuple is truthy.

**Fix**: `is_active, reason = await kill_switch.is_active()` then `if is_active:`

**F02 — gRPC Direction Always UNSPECIFIED** (`grpc_client.py:60-61`):

```python
direction_str = str(signal.get("direction", "HOLD"))  # str(Direction.BUY) = "Direction.BUY"
direction_enum = _DIRECTION_MAP.get(direction_str, 0)  # "Direction.BUY" not in map → 0

_DIRECTION_MAP = {"BUY": 1, "SELL": 2, "HOLD": 3}  # expects "BUY", not "Direction.BUY"
```

**Impact**: All signals have direction=0 (UNSPECIFIED) in protobuf → MT5 Bridge rejects or has undefined behavior.

**Fix**: Extract `.value` from the enum: `direction_str = raw_dir.value if hasattr(raw_dir, "value") else str(raw_dir)`

### 2.4 Additional Findings

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| F05 | ALTO | ADX not validated for range [0,100] in trend_following | `trend_following.py` |
| F07 | ALTO | `get_state()` leaks mutable reference to `_positions_detail` | `portfolio.py:~79` |
| F08 | ALTO | `BridgeClient.close()` never called — resource leak | `main.py:~1518` |
| F09 | WARNING | Portfolio state partially persisted to Redis (only daily_loss_pct) | `portfolio.py:151-174` |
| F10 | WARNING | Unknown symbols pass silently through CorrelationChecker | `correlation.py:~94` |
| F12 | WARNING | `_parse_ohlcv_payload()` defined but never called — dead code | `main.py:269-301` |
| F04 | ALTO | PnL tracker records fake data (pnl=0, is_win=True) at fill time | `main.py:~1388` |

### 2.5 God Function Warning

`run_brain()` in `main.py` is a **944-line function** (lines 600-1544) with 5+ nesting levels. Contains initialization, ZMQ loop, strategy cascade, gRPC dispatch, error handling, and shutdown. `orchestrator.py` (205 LoC) implements a cleaner cascade but is **never imported** — dead code.

---

## 3. Feature Pipeline & Regime Classification

### 3.1 60-Dimensional Feature Vector

The pipeline (`pipeline.py` + `technical.py`) produces ~34 technical indicators via Decimal arithmetic:

| Indices | Group | Features |
|---------|-------|----------|
| 0-5 | Price | OHLCV normalized + spread |
| 6-15 | Trend | SMA ratios, DEMA, MACD (line/signal/hist), ADX |
| 16-25 | Momentum | RSI, Stochastic K/D, CCI, Williams %R, ROC, DI ratio |
| 26-33 | Volatility | ATR%, BB upper/lower/width, Keltner, Historical Vol, Parkinson |
| 34-40 | Volume | OBV norm, VWAP ratio, CMF, Chaikin Osc, Force Index, Vol ratio |
| 41-50 | Context | Hour sin/cos, DayOfWeek sin/cos, session, VIX, DXY, SPX corr |
| 51-59 | Microstructure | Bid-ask, OB imbalance, tick direction, trade flow, VPIN |

All indicator formulas verified mathematically correct (RSI Wilder smoothing, MACD, Bollinger, ATR, ADX, Stochastic, OBV, CCI, etc.).

### 3.2 Placeholder Features (8.3%)

5 of 60 features are zero/constant placeholders:

| Index | Feature | Value | Reason |
|-------|---------|-------|--------|
| 37 | Chaikin Oscillator | 0.0 | Requires ADL series |
| 40 | Volume Profile Value Area | 0.5 | Not implemented |
| 55 | Realised Vol 5min | 0.0 | Sub-minute data unavailable |
| 57 | Hurst Exponent | 0.5 | Too costly for real-time |
| 58 | VPIN | 0.0 | Not implemented |

### 3.3 Regime Classification

**5 regimes** (priority order):

| Regime | Condition | Confidence |
|--------|-----------|-----------|
| HIGH_VOLATILITY | ATR > 2x avg_ATR | 0.50 + (ratio-2)x0.25 |
| TRENDING_UP | ADX > 25 AND EMA_fast > EMA_slow | 0.50 + ADX/100 |
| TRENDING_DOWN | ADX > 25 AND EMA_fast < EMA_slow | 0.50 + ADX/100 |
| REVERSAL | ADX was >40, now declining + extreme RSI | 0.55 |
| RANGING (default) | ADX < 20, narrow bands | 0.70 |

**BUG**: `_prev_adx` initialized to ZERO → first reversal after startup never detected because `0 < 40` is always true.

**Ensemble classifier** (416 LoC): Rule=0.50, HMM=0.30, kMeans=0.20 weighted voting with hysteresis requiring `P(new) > P(old) + 0.15` for 3 consecutive bars.

### 3.4 Additional Feature Modules

- **data_quality.py**: OHLCV validation (High >= max(O,C), spike detection)
- **data_sanity.py**: Statistical plausibility checks
- **feature_drift.py**: Distributional drift detection via Z-score
- **leakage_auditor.py**: 5-check formal data leakage audit
- **macro_features.py**: Macroeconomic features from Redis (VIX, yield, DXY)
- **regime_shift.py**: KL-divergence regime transition detection
- **sessions.py**: Confidence adjustment per trading session

### 3.5 Analysis Modules

- **manipulation_detector.py**: Spoofing/fake breakout/churn detection (25% blind without L2 order book data)
- **signal_quality.py**: Shannon entropy for market clarity
- **price_level_analyzer.py**: Support/resistance zone classification
- **pnl_momentum.py**: Win/loss streak tracker with time-decay
- **market_belief.py**: Bayesian posterior regime model

### 3.6 Findings

| # | Severity | Finding | Detail |
|---|----------|---------|--------|
| F-FP1 | ALTO | 5 placeholder features (8.3%) | Indices 37,40,55,57,58 are zero/constant |
| F-FP2 | ALTO | `_prev_adx` initialized to 0 | First reversal after startup not detected |
| F-FP3 | WARNING | Spoofing detector blind without L2 data | 25% of manipulation index always 0 |
| F-FP4 | WARNING | Spread feature always 0.5 in ensemble | HMM/kMeans input partially constant |
| F-FP5 | WARNING | `bb_squeeze` not calculated | Used in heuristics but never produced |
| F-FP6 | WARNING | GBM parameters not calibrated | scenario_analyzer mu/sigma must be provided externally |

---

## 4. Safety Systems & Risk Management

### 4.1 Architecture — 7 Independent Protection Layers

The safety architecture is **solid and well-designed** (~85-90% complete) with defense-in-depth:

```
Signal Generated
       |
       v
[1] RateLimiter.allow() ──[NO]──> DROP (anti-spam, 10/hour max)
       |
       v
[2] KillSwitch.is_active() ──[YES]──> ABORT (emergency, Redis-backed)
       |
       v
[3] PositionSizer.calculate() ── equity x risk% / (SL x pip_value)
       |                         with drawdown scaling:
       |                         0-2%→1x, 2-4%→0.5x, 4-5%→0.25x, >5%→min
       v
[4] SignalValidator.validate() ── 11 fail-fast checks:
       |  [1] Direction != HOLD        [7] SL correctly positioned
       |  [2] Positions < 5            [8] R:R >= 1.0
       |  [3] Drawdown < 5%           [9] Margin sufficient (80%)
       |  [4] Daily Loss < 2%         [10] Correlation OK (optional)
       |  [5] Confidence >= 0.65      [11] Session OK (optional)
       |  [6] Stop-Loss present
       v
[5] CorrelationChecker ── max 3.0 net positions per currency
       |
       v
[6] SpiralProtection ── progressive reduction after consecutive losses
       |  3 losses → 0.5x, 4 → 0.25x, 5+ → cooldown (60min)
       v
[7] Signal → MT5 Bridge (gRPC)
```

### 4.2 Key Thresholds

| Parameter | Value | Source |
|-----------|-------|--------|
| Max Open Positions | 5 | `brain_max_open_positions` |
| Max Daily Loss | 2.0% | `brain_max_daily_loss_pct` |
| Max Drawdown | 5.0% | `brain_max_drawdown_pct` |
| Min Confidence | 0.65 | `brain_confidence_threshold` |
| Risk per Trade | 1.0% | `brain_risk_per_trade_pct` |
| Max Lots | 0.10 | `brain_max_lots` |
| Min Lots | 0.01 | Hardcoded |
| Default Equity | $1,000 | `brain_default_equity` |
| Leverage | 100:1 | `brain_default_leverage` |
| Spiral Threshold | 3 losses | `brain_spiral_loss_threshold` |
| Spiral Max Losses | 5 losses | `brain_spiral_max_losses` |
| Spiral Cooldown | 60 min | `brain_spiral_cooldown_minutes` |
| Max Signals/Hour | 10 | `brain_max_signals_per_hour` |
| Kill Switch Cache | 1.0s | Hardcoded |

### 4.3 Instrument Tables

Position sizer uses hardcoded instrument tables:

```
PIP_SIZES: EURUSD=0.0001, GBPUSD=0.0001, USDJPY=0.01, XAUUSD=0.01, XAGUSD=0.001 (10 pairs)
PIP_VALUES: EURUSD=$10, XAUUSD=$1, XAGUSD=$50 (12 pairs, USD per pip per lot)
```

### 4.4 Test Coverage

| Component | Unit Tests | Coverage |
|-----------|-----------|----------|
| KillSwitch | 6 | ~70% |
| SpiralProtection | 8 | ~75% |
| PositionSizer | 10 | ~80% |
| SignalValidator | 14 | ~85% (gates 1-9 only) |
| Portfolio | 9 | ~70% (no Redis test) |
| CorrelationChecker | 0 | 0% |
| RateLimiter | 0 | 0% |
| **Total** | **45+** | **~65% average** |

### 4.5 Findings

| # | Severity | Finding | Detail |
|---|----------|---------|--------|
| F-S1 | ALTO | Spiral x Drawdown NOT composed | Multipliers operate independently. DD 3% (0.5x) + 3 losses (0.5x) should give 0.25x but don't multiply |
| F-S2 | ALTO | Spiral state not persisted to Redis | In-memory only. Crash resets consecutive_losses to 0 |
| F-S3 | ALTO | Redis persistence NOT tested | `sync_from_redis()` and `persist_to_redis()` have zero tests |
| F-S4 | ALTO | Optional validator controls NOT tested | Correlation, session, calendar checks untested when active |
| F-S5 | WARNING | No confirmation before kill activate | Accidental typo in console could halt all trading |
| F-S6 | WARNING | Missing DailyLossCritical alert | Alert only at 1.5% (warning), but kill switch triggers at 2% |
| F-S7 | WARNING | Hardcoded instrument tables | Adding instruments requires code changes |
| F-S8 | WARNING | Margin buffer 0.80 magic number | Not configurable |
| F-S9 | WARNING | Kill switch cache TTL not configurable | 1-second hardcoded |
| F-S10 | WARNING | Comment/code discrepancy in auto_check | Comment says "2x limit" but code checks 1x (code is more protective) |

---

## 5. Data Ingestion & Database

### 5.1 Go Data Pipeline Architecture

```
EXCHANGE (Polygon.io / Binance WebSocket)
    |
    | RawMessage{Exchange, Symbol, Channel, Data, Timestamp}
    v
NORMALIZER (shopspring/decimal precision)
    |
    +---+---+
    |       |
    v       v
ZMQ PUB   DB WRITER
"bar.*"   COPY bulk insert (batch=1000, flush=5s, workers=2)
    |       |
    v       v
ALGO-ENGINE TIMESCALEDB (ohlcv_bars, market_ticks)
```

**Data Ingestion**: 13 Go source files, well-architected with connector interface pattern (Polygon, Binance, Mock implementations).

### 5.2 Connectors

**Polygon.io** (581 LoC): WebSocket with auth, reconnection with exponential backoff (base 2s, max 60s, ±20% jitter), circuit breaker after 50 attempts, ping keepalive at 30s.

**Binance** (255 LoC): Simpler connector, currently **disabled** in config. Missing reconnection logic — disconnection is fatal.

**Mock** (248 LoC): Functional options pattern for testing.

### 5.3 Database Schema

#### Core Tables (001_init.sql)

| Table | Type | Chunk | Compression |
|-------|------|-------|-------------|
| ohlcv_bars | Hypertable | 1 day | after 7 days (by symbol, timeframe) |
| market_ticks | Hypertable | 1 hour | after 1 day (by symbol) |
| trading_signals | Regular | - | - |
| trade_executions | Regular | - | - |
| audit_log | Regular | - | trigger PREVENTS UPDATE/DELETE |

**audit_log**: Append-only with SHA-256 hash chain. Tamper-proof by design.

#### Additional Tables
- **Strategy**: strategy_performance (hypertable), strategy_daily_summary (continuous aggregate)
- **Economic Calendar**: economic_events, trading_blackouts, event_impact_rules with auto-blackout triggers
- **Macro Data**: vix_data, yield_curve_data, real_rates_data, dxy_data, cot_reports, recession_probability

#### RBAC (4 roles, least-privilege)

| Role | Read | Write |
|------|------|-------|
| data_ingestion_svc | market data, macro | market data, macro, audit |
| algo_engine_svc | market, macro, events, strategy | signals, strategy, audit |
| mt5_bridge_svc | signals | executions, strategy(update), audit |
| moneymaker_admin | ALL | ALL |

### 5.4 External Data Service

Scheduler-based service for macroeconomic data:
- **VIX** (CBOE, every 1 min): Regime classification (calm/elevated/panic)
- **Yield/Rates** (FRED, every 60 min): Treasury curve, real rates, recession probability
- **COT** (CFTC, every 24h): Institutional positioning sentiment

**Note**: external-data service is NOT in docker-compose.yml — runs locally only.

### 5.5 Findings

| # | Severity | Finding | Detail |
|---|----------|---------|--------|
| F-D1 | **CRITICO** | `ohlcv_bars` and `market_ticks` missing PRIMARY KEY/UNIQUE | Duplicates possible, `ON CONFLICT DO NOTHING` never triggers |
| F-D2 | ALTO | Data race on `reconnectAttempts` in polygon.go | Non-atomic int read/written without mutex |
| F-D3 | ALTO | No reconnection logic in binance.go | Service dies on disconnection (mitigated: Binance disabled) |
| F-D4 | ALTO | Sync flush fallback blocks main loop under backpressure | writer.go:305-314 annuls async design |
| F-D5 | WARNING | Aggregator callback called under mutex lock | Slow callback blocks entire main loop |
| F-D6 | WARNING | Symbol map hardcoded in main.go (30+ mappings) | Requires recompilation to add symbols |
| F-D7 | WARNING | No High-Water Mark on ZMQ PUB socket | Unbounded memory if subscriber is slow |
| F-D8 | WARNING | Redis configured in config.yaml but never used | Implement or remove |
| F-D9 | WARNING | No retention policy on hypertables | Data grows unbounded |
| F-D10 | WARNING | SpreadAvg hardcoded to Zero in DBWriter | writer.go:337, never calculated |
| F-D11 | WARNING | DSN password in logs risk | main.go:61-67, credential leak if logged |
| F-D12 | WARNING | Alert rule metric names may not match code | `moneymaker_kill_switch_active` vs `moneymaker_brain_kill_switch_active` |
| F-D13 | WARNING | RBAC passwords in plaintext in PostgreSQL logs | ALTER ROLE exposes password |

**Fix for F-D1**: `ALTER TABLE ohlcv_bars ADD CONSTRAINT pk_ohlcv PRIMARY KEY (time, symbol, timeframe);` and `ALTER TABLE market_ticks ADD CONSTRAINT pk_ticks PRIMARY KEY (time, symbol);`

---

## 6. MT5 Bridge & Execution

### 6.1 Architecture

7 source files, 1,414 LoC: gRPC server, order manager, position tracker, trailing stop.

**Execution Flow**:
```
gRPC ExecuteTrade (TradingSignal)
    |
    +-> Rate limit check (Redis, 10 req/min, burst 5)
    +-> Proto → Dict conversion
    |
    v
OrderManager.execute_signal(signal)
    +-> Dedup check (60s window, in-memory)
    +-> Validate: direction, lots>0, SL>0, positions<5, spread<30pts, margin
    +-> Clamp lot size (min/max, round to vol_step)
    +-> Select MARKET or LIMIT order
    +-> Submit to MT5 via connector
    |
    v
Background (every 5s): PositionTracker.update()
    +-> Detect closed positions (logged but NOT published)
    +-> Update trailing stops
```

### 6.2 Trailing Stop Logic

**BUY** (correct): SL moves UP when profit exceeds activation threshold.

**SELL**: Functionally correct but counterintuitive. The condition `new_sl < current_sl` updates only when the new SL is better (closer to current price for a SELL).

### 6.3 CRITICAL: XAGUSD Pip Size Bug

```python
if "JPY" in symbol or "XAU" in symbol:
    pip_size = Decimal("0.01")
else:
    pip_size = Decimal("0.0001")  # XAGUSD gets 0.0001, should be 0.001
```

Silver (XAGUSD) gets the wrong pip size, making trailing stop distances **10x off**.

### 6.4 Configuration Mismatches

| Parameter | Brain | MT5 Bridge | Aligned? |
|-----------|-------|-----------|----------|
| Max positions | 5 | 5 | OK |
| Max daily loss | 2.0% | 2.0% (NOT enforced) | WARNING |
| Max drawdown | 5.0% | 10.0% (NOT enforced) | **MISMATCH** |
| Max lot size | 0.10 | 1.0 | Brain more restrictive |

3 config parameters defined but never used: `max_daily_loss_pct`, `max_drawdown_pct`, `signal_max_age_sec`.

### 6.5 Feedback Loop — BROKEN

- `PositionTracker.update()` detects closed positions and logs them
- `build_trade_result()` exists to format results
- BUT results are **never published** anywhere — not to database, audit trail, or brain
- Trade close results cannot feed back into portfolio state or strategy learning

### 6.6 Findings

| # | Severity | Finding | Detail |
|---|----------|---------|--------|
| F-M1 | **CRITICO** | XAGUSD pip size wrong | Silver gets 0.0001 instead of 0.001, trailing stop 10x off |
| F-M2 | **CRITICO** | No feedback loop for closed trades | Results logged but not published anywhere |
| F-M3 | **CRITICO** | MT5 Bridge cannot run in Docker Linux | MetaTrader5 Python is Windows-only |
| F-M4 | ALTO | Lot clamping potentially unsafe | Round-down can produce lots < vol_min |
| F-M5 | ALTO | Config mismatch creates false security | max_drawdown_pct=10% defined but unused, Brain uses 5% |
| F-M6 | ALTO | Dedup not persistent | In-memory dict, restart = possible duplicate orders |
| F-M7 | ALTO | Test coverage 4.3% | Only 6 tests for 1,414 LoC |
| F-M8 | WARNING | Slippage calculation ignores direction | BUY vs SELL not distinguished in metrics |
| F-M9 | WARNING | Signal age not validated | `signal_max_age_sec=30` defined but never checked |
| F-M10 | WARNING | ERROR mapped to REJECTED in gRPC | Loses diagnostic information |
| F-M11 | WARNING | StreamTradeUpdates not implemented | Proto RPC defined but placeholder empty |

---

## 7. Infrastructure, CI/CD & Security

### 7.1 CRITICAL: Password in Git History

The file `program/infra/docker/.env` containing password `Trade.2026.Macena` is **tracked in git** — committed before the gitignore rule was added. Even after removal from tracking, the password remains in git history.

**Required**: `git rm --cached program/infra/docker/.env`, rotate ALL passwords, verify with `trufflehog`.

### 7.2 CI/CD Pipeline

**GitHub Actions** (`ci.yml`):
- Job 1: Python lint+test (ruff, black, mypy, pytest)
- Job 2: Go lint+test (go vet, golangci-lint, `go test -race`)
- Job 3: Docker build (3 services)

**Security scanning** (`security.yml` — weekly):
- pip-audit (Python vulnerabilities)
- govulncheck (Go CVEs)
- trufflehog (secret scanning)

**CRITICAL BUG in CI Docker build**: Build context points to `services/X` instead of root. Dockerfiles do `COPY shared/` which requires root as context. The Makefile does it correctly.

### 7.3 TLS/mTLS Infrastructure

`generate-certs.sh` (275 LoC) generates:
- Root CA (4096-bit RSA, 365 days)
- PostgreSQL + Redis server certs
- 4 service certs with mTLS (server+client auth)

Certificates properly excluded from git via `.gitignore`.

### 7.4 Monitoring Stack

**Prometheus** (33 LoC config): 15s scrape interval, 4 targets.

**10 Alert Rules**:

| Rule | Severity | Trigger |
|------|----------|---------|
| KillSwitchActivated | CRITICAL | kill_switch_active == 1 (immediate) |
| CriticalDrawdown | CRITICAL | drawdown > 5% (immediate) |
| HighDrawdown | WARNING | drawdown > 3% (5min) |
| DailyLossApproaching | WARNING | daily_loss > 1.5% (1min) |
| SpiralProtectionActive | WARNING | consecutive_losses > 3 (immediate) |
| NoTicksReceived | CRITICAL | no ticks for 5min |
| HighPipelineLatency | WARNING | P99 > 100ms (5min) |
| ServiceDown | CRITICAL | service down for 1min |
| HighErrorRate | WARNING | errors > 0.1/s (5min) |
| BridgeUnavailable | CRITICAL | MT5 Bridge down for 2min |

**5 Grafana Dashboards** (4,333 LoC total):
1. Overview — kill switch, service status, error rates, latency
2. Risk — daily loss gauge, drawdown, VaR/CVaR, Sortino, concentration
3. Data Pipeline — ticks/s, bars/s, throughput
4. Trading — signal rates, win rate, P&L, execution latency
5. Training — metrics placeholders

### 7.5 Application Observability

- **Structured logging**: JSON (Python structlog + Go zap) for ELK/Loki
- **Sentry**: Optional error tracking with PII scrubbing (hostname → "moneymaker-node")
- **Alert dispatcher**: Rate-limited (30s default, 5s for CRITICAL) async multi-channel
- **Telegram**: HTML-formatted notifications
- **RASP**: SHA-256 integrity verification of critical files
- **Health checks**: Kubernetes-standard `/healthz`, `/readyz`, `/health` (Go)

### 7.6 PII Scrubbing — Incomplete (from AUDIT_05)

`sentry_setup.py` needs:
1. Function `_scrub_pii(value: str) -> str` — removes user home paths
2. Callback `_before_send(event, hint)` sanitizing: server_name, stacktrace paths, breadcrumbs
3. pytest gate: `if "pytest" in sys.modules: return False`
4. Wire `before_send=_before_send` to `sentry_sdk.init()`

### 7.7 Security Posture

**Strengths**:
- RBAC database (4 roles, least-privilege)
- Immutable audit trail (trigger prevents UPDATE/DELETE)
- TLS/mTLS with generation script
- Non-default passwords required (`:?` operator)
- 3-network Docker segmentation
- Secret scanning in CI (trufflehog)
- Vulnerability scanning (pip-audit + govulncheck)
- Non-root containers
- Pre-commit hooks (private key detection)
- Race detection (`go test -race`)

**Weaknesses**:
- `.env` committed with password — CRITICAL
- CI Docker build context wrong — ALTO
- Redis healthcheck TLS-incompatible
- No container scanning (Trivy)
- No SAST (Bandit)
- No automated DB backup

### 7.8 Findings

| # | Severity | Finding | Detail |
|---|----------|---------|--------|
| F-I1 | **CRITICO** | `.env` with password tracked in git | `Trade.2026.Macena` compromised |
| F-I2 | ALTO | CI Docker build context wrong | `services/X` instead of root with `-f` |
| F-I3 | ALTO | Port mismatch Dockerfile vs compose | EXPOSE documents wrong ports |
| F-I4 | WARNING | Redis healthcheck TLS-incompatible | `redis-cli ping` fails with TLS enabled |
| F-I5 | WARNING | MyPy pre-commit with hardcoded file list | Paths may not match at runtime |
| F-I6 | WARNING | Redis health check shallow in health.py | Only import check, not actual connectivity |
| F-I7 | WARNING | Backend network not `internal: true` | Services reachable from host |
| F-I8 | WARNING | external-data not in CI | No lint/test/build |
| F-I9 | WARNING | No Alertmanager | Custom dispatcher, no alert persistence |
| F-I10 | WARNING | Sentry PII scrubbing incomplete | Needs _before_send callback |

---

## 8. Test Coverage & Quality

### 8.1 Test Summary

| Service | Tests | LoC | Pass Rate |
|---------|-------|-----|-----------|
| algo-engine (Python) | 353 | 4,257 | 100% |
| data-ingestion (Go) | 9 | 211 | 100% |
| mt5-bridge (Python) | 5 | 150 | 100% |
| console | 0 | 0 | N/A |
| external-data | 0 | 0 | N/A |
| **Total** | **367** | **4,618** | **100%** |

### 8.2 Coverage by Module

```
algo-engine/
├── features/
│   ├── pipeline.py ........................ 10 tests
│   ├── technical.py ....................... 63 tests (32+31)
│   ├── regime*.py ......................... 16 tests
│   ├── data_quality.py .................... 0 tests
│   ├── data_sanity.py ..................... 0 tests
│   ├── feature_drift.py ................... 0 tests
│   ├── leakage_auditor.py ................. 0 tests
│   └── (8 more files) .................... 0 tests
├── strategies/
│   ├── trend_following.py ................. 9 tests
│   ├── mean_reversion.py .................. 9 tests
│   ├── defensive.py ....................... 6 tests
│   └── regime_router.py ................... 5 tests
├── signals/
│   ├── generator.py ....................... 9 tests
│   ├── validator.py ....................... 15 tests
│   ├── position_sizer.py .................. 8 tests
│   ├── spiral_protection.py ............... 9 tests
│   ├── kill_switch.py ..................... 6 tests
│   ├── signal_router.py ................... 0 tests
│   └── correlation.py ..................... 0 tests
├── analysis/ (10 files) ................... 0 tests
├── knowledge/ (7 files) ................... 0 tests
├── processing/ (13 files) ................. 0 tests
└── observability/ ......................... 0 tests

data-ingestion/
├── aggregator/ ............................ 9 tests
├── connectors/ ............................ 0 tests
├── normalizer/ ............................ 0 tests
├── publisher/ ............................. 0 tests
└── dbwriter/ .............................. 0 tests

mt5-bridge/
├── grpc_server.py ......................... 5 tests
├── order_manager.py ....................... 0 tests
├── position_tracker.py .................... 0 tests
└── connector.py ........................... 0 tests
```

### 8.3 Coverage Summary

| Category | Files Tested | Files Untested | Coverage |
|----------|-------------|----------------|----------|
| Core pipeline | 15 | 3 | ~83% |
| Safety systems | 5/5 | 0 | **100%** |
| Strategies | 5/5 | 0 | **100%** |
| Features | 4/16 | 12 | ~25% |
| Analysis | 0/10 | 10 | **0%** |
| Knowledge | 0/7 | 7 | **0%** |
| Processing | 0/13 | 13 | **0%** |
| Data Ingestion (Go) | 1/5 | 4 | ~20% |
| MT5 Bridge | 1/4 | 3 | ~25% |

**Global estimated coverage**: ~30% of modules have at least one test.

### 8.4 Diagnostic Tools

34 standalone diagnostic scripts (12,285 LoC) exist for manual system inspection but are **not integrated into CI**. Includes feature audit, DB health, dead code detector, integrity manifest, and a 16-section brain verification suite.

### 8.5 Findings

| # | Severity | Finding | Detail |
|---|----------|---------|--------|
| F-T1 | ALTO | Zero E2E tick-to-trade test | No test verifying complete data → signal → order flow |
| F-T2 | ALTO | Zero tests for analysis/ (10 modules) | No verification on analysis pipeline |
| F-T3 | ALTO | Zero tests for knowledge/ (7 modules) | Knowledge base untested |
| F-T4 | ALTO | Zero tests for processing/ (13 modules) | Data processing untested |
| F-T5 | ALTO | Zero tests for Go connectors | Only aggregator tested |
| F-T6 | WARNING | Console has zero tests | 15 command categories untested |
| F-T7 | WARNING | External-data has zero tests | CBOE/CFTC/FRED providers untested |
| F-T8 | WARNING | Diagnostic tools not in CI | 34 tools only for manual use |

---

## 9. Open-Source Integration Opportunities

Analysis of 12 open-source trading projects identified best-of-breed patterns applicable to MONEYMAKER.

### 9.1 Recommended Integrations

| Pattern | Source Project | Target in MONEYMAKER | Effort |
|---------|--------------|---------------------|--------|
| Protections middleware (CooldownPeriod, MaxDrawdown, StoplossGuard) | Freqtrade | `signals/protections.py` | 1 day |
| Strategy declarative parameters (minimal_roi, stoploss) | Freqtrade IStrategy | `strategies/base.py` | 2 hours |
| Backtesting engine (event-driven, analyzers) | Backtrader Cerebro | `algo-engine/backtest/` | 3-5 days |
| Analyzers (Sharpe, Calmar, MaxDrawdown, WinRate) | Backtrader | `backtest/analyzers.py` | 1 day |
| Alpha 158 factors (selected subset, ~25 features) | VnPy Alpha | `features/alpha_factors.py` | 2-3 days |
| TWAP/Iceberg execution algorithms | VnPy | `mt5-bridge/algo_executor.py` | 2 days |
| Telegram active commands (/status, /profit, /kill) | Freqtrade | `console/telegram_commands.py` | 2 days |
| Bracket orders (OCO for SL+TP) | Nautilus | `mt5-bridge/order_manager.py` | 1 day |
| Hyperopt parameter optimization | Freqtrade/Optuna | optimization module | 3-5 days |

### 9.2 Projects NOT to Adopt

| Project | Reason |
|---------|--------|
| Gekko | Archived 2018, Node.js, unmaintained |
| Lean | C#, over-engineered for MONEYMAKER |
| Nautilus Rust core | Too complex to integrate (design patterns only) |
| CCXT as primary exchange | MONEYMAKER uses MT5 for forex; CCXT is crypto-only |
| Hummingbot market-making | MONEYMAKER is directional trading |

### 9.3 Priority Tiers

**Tier 1 — Immediate Impact** (Week 1-2): Protections middleware, Telegram commands, strategy parameters, bracket orders.

**Tier 2 — Strategic Value** (Week 3-6): Backtesting engine, Alpha factors, TWAP/Iceberg execution, Hyperopt.

---

## 10. Consolidated Findings Table

All findings from all sections, deduplicated and ordered by severity.

### CRITICO (Production Blocking)

| ID | Section | Finding | Impact |
|----|---------|---------|--------|
| F01 | 2 | Kill switch `is_active()` tuple treated as bool | Trading ALWAYS blocked |
| F02 | 2 | gRPC direction enum serialization broken | All signals UNSPECIFIED |
| F-D1 | 5 | `ohlcv_bars` and `market_ticks` missing PRIMARY KEY | Duplicate data, backtest errors |
| F-I1 | 7 | `.env` with password `Trade.2026.Macena` in git | Security compromise |
| F-M1 | 6 | XAGUSD pip size wrong (0.0001 vs 0.001) | Trailing stop 10x off for silver |
| F-M2 | 6 | No feedback loop for closed trades | Portfolio state stale after trade close |
| F-M3 | 6 | MT5 Bridge cannot run in Docker Linux | Windows-only MetaTrader5 package |
| F04 | 1 | algo-engine port mismatch (total) | Service unreachable from monitoring/console |
| F04-PnL | 2 | PnL tracker records fake data (pnl=0, is_win=True) | Gating decisions unreliable |

### ALTO (Fix Before Deploy)

| ID | Section | Finding | Impact |
|----|---------|---------|--------|
| F-FP1 | 3 | 5 placeholder features (8.3% of vector) | Wasted feature capacity |
| F-FP2 | 3 | `_prev_adx` initialized to 0 | First reversal undetected |
| F-S1 | 4 | Spiral x Drawdown not composed | Over-sized positions under dual stress |
| F-S2 | 4 | Spiral state not persisted to Redis | Lost after restart |
| F-S3 | 4 | Redis persistence not tested | daily_loss could zero after restart |
| F-S4 | 4 | Optional validator controls not tested | Correlation/session untested when active |
| F-D2 | 5 | Data race on reconnectAttempts (polygon.go) | Backoff incorrect, potential panic |
| F-D3 | 5 | No reconnection in binance.go | Fatal disconnection (mitigated: disabled) |
| F-D4 | 5 | Sync flush blocks main loop | Async design nullified under backpressure |
| F-M4 | 6 | Lot clamping unsafe | lots < vol_min after round-down |
| F-M5 | 6 | Config mismatch (drawdown 5% vs 10%) | False security, never enforced in bridge |
| F-M6 | 6 | Dedup not persistent | Duplicate orders after crash |
| F-M7 | 6 | MT5 Bridge test coverage 4.3% | Critical code paths untested |
| F-I2 | 7 | CI Docker build context wrong | Docker builds fail in CI |
| F05 | 2 | ADX not validated for range [0,100] | Bad confidence values masked by min() |
| F07 | 2 | Portfolio mutable list leak | External callers can corrupt state |
| F08 | 2 | BridgeClient.close() never called | Resource leak |
| F13 | 1 | .env.example uses wrong env var names | Port override never works |
| F-T1 | 8 | Zero E2E tick-to-trade test | Complete flow unverified |
| F-T2-5 | 8 | Zero tests for analysis/knowledge/processing/Go connectors | Major coverage gaps |

### WARNING

| ID | Section | Finding |
|----|---------|---------|
| F-FP3-6 | 3 | Spoofing blind, spread placeholder, bb_squeeze missing, GBM uncalibrated |
| F-S5-10 | 4 | No kill confirm, missing alert, hardcoded instruments, magic numbers |
| F-D5-13 | 5 | Aggregator mutex, hardcoded symbols, no ZMQ HWM, unused Redis, no retention, etc. |
| F-M8-11 | 6 | Slippage unsigned, signal age unchecked, ERROR→REJECTED, StreamTradeUpdates stub |
| F-I4-10 | 7 | Redis TLS healthcheck, MyPy paths, shallow health, network not internal, PII scrubbing |
| F-T6-8 | 8 | Console/external-data untested, diagnostic tools not in CI |
| F09 | 2 | Portfolio state partially persisted |
| F12 | 2 | Dead code `_parse_ohlcv_payload()` |

---

## 11. Remediation Roadmap

### Phase 0: Immediate Fixes (Days 1-2)

**Security**:
- [ ] Remove `.env` from git tracking: `git rm --cached program/infra/docker/.env`
- [ ] Rotate ALL passwords (DB, Redis, Grafana)
- [ ] Run `trufflehog` scan locally to verify no other secrets

**Production Blockers**:
- [ ] Fix F01: Destructure kill switch tuple in main.py (`is_active, reason = await kill_switch.is_active()`)
- [ ] Fix F02: Extract `.value` from Direction enum in grpc_client.py
- [ ] Fix F-D1: Add PRIMARY KEY to `ohlcv_bars` and `market_ticks`
- [ ] Fix F04: Align algo-engine ports (config.py defaults → 50054/8080/9093, update Dockerfile EXPOSE)
- [ ] Fix F13: Correct env var names in .env.example

### Phase 1: Core Bug Fixes (Days 3-5)

- [ ] Fix F-M1: Add XAGUSD pip size condition in position_tracker.py
- [ ] Fix F07: Return `list(self._positions_detail)` copy in portfolio.py
- [ ] Fix F08: Add `await bridge_client.close()` in shutdown handler
- [ ] Fix F-FP2: Initialize `_prev_adx` to None in regime.py
- [ ] Fix F-M4: Add final validation `if lots < vol_min: lots = vol_min` after round-down
- [ ] Fix F-I2: Correct Docker build context in ci.yml (use `.` with `-f` flag)
- [ ] Fix F05: Add ADX range validation [0,100] in trend_following.py

### Phase 2: Safety Hardening (Week 2)

- [ ] Implement spiral x drawdown composition: `final = spiral_mult x dd_factor`
- [ ] Persist spiral state to Redis (`moneymaker:spiral_state` key)
- [ ] Align drawdown limits: Brain 5% and MT5 Bridge 5%
- [ ] Implement signal age validation in order_manager
- [ ] Make dedup persistent via Redis (`SETNX` + `EXPIRE`)
- [ ] Add DailyLossCritical Prometheus alert at 2%
- [ ] Fix Redis healthcheck for TLS compatibility

### Phase 3: Test Coverage (Week 2-3)

- [ ] Write E2E tick-to-trade test
- [ ] Add tests for CorrelationChecker (currently 0 tests)
- [ ] Add tests for RateLimiter (currently 0 tests)
- [ ] Add OrderManager tests (execute_signal, validate, lot clamping, dedup)
- [ ] Add PositionTracker tests (trailing stop BUY/SELL, pip sizes)
- [ ] Add Go connector tests (Polygon reconnection)
- [ ] Target: 50% module coverage (up from ~30%)

### Phase 4: Feedback Loop & Monitoring (Week 3-4)

- [ ] Implement trade result publishing (Redis pub/sub or gRPC streaming)
- [ ] Wire portfolio.record_close() from MT5 Bridge trade results
- [ ] Configure Telegram bot for active commands
- [ ] Configure Sentry DSN for error tracking
- [ ] Complete PII scrubbing in sentry_setup.py
- [ ] Verify all 5 Grafana dashboards with live data
- [ ] Test all 10 Prometheus alert rules

### Phase 5: Production Deployment (Week 4+)

- [ ] Deploy Docker stack on Linux host (without mt5-bridge)
- [ ] Deploy MT5 Bridge natively on Windows VM
- [ ] Generate TLS certificates for production
- [ ] Enable mTLS between all gRPC services
- [ ] Add backend network `internal: true`
- [ ] Implement automated DB backup (pg_dump)
- [ ] Monitor paper trading for 1+ week before live

---

*This report consolidates findings from 11 individual audit reports covering architecture, core pipeline, features, safety, data ingestion, MT5 execution, infrastructure, testing, and open-source integration analysis. All neural network, ML training, and AI-specific content has been excluded as those components have been removed from the codebase.*
