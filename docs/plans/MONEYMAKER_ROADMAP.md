# MONEYMAKER Trading Ecosystem — Consolidated Roadmap

**Version**: 3.0
**Date**: 2026-03-09
**Scope**: Full ecosystem — 7 services, pure algorithmic engine

---

## Section 0: Project Status

### What Has Been Built

The MONEYMAKER ecosystem is a fully implemented quantitative trading system with 7 microservices:

| Service | Language | Source LoC | Tests | Status |
|---------|----------|-----------|-------|--------|
| **algo-engine** | Python | 12,874 | 26 modules (4,426 LoC) | Complete |
| **console** | Python | 7,307 | Partial | Complete |
| **dashboard** | Python + React | 2,197+ | Stubs | Complete |
| **mt5-bridge** | Python | 2,001 | 526 LoC | Complete |
| **data-ingestion** | Go | ~300 | Integration | Complete |
| **external-data** | Python | 1,505 | None | Complete |
| **monitoring** | Config | Prometheus + Grafana | N/A | Complete |

### Algo-Engine Architecture

The core engine runs a deterministic pipeline — no ML/AI:

```
Data Quality -> MTF Analysis -> Features -> Regime Classification
  -> Strategy Selection (regime router) -> Signal Generation
  -> Position Sizing -> Spiral Protection -> Validation -> Rate Limiter
```

**Key capabilities:**
- 10 trading strategies with Bayesian/probabilistic regime routing
- 8 optional advanced math modules (spectral, Bayesian, OU, fractal, extreme value, information theory, stochastic, copula)
- Risk management: 3-level hierarchical kill switch (fail-closed), trailing stops (4 modes inc. breakeven), spiral protection, CVaR+Half-Kelly sizer
- Backtesting: walk-forward optimization, Monte Carlo analysis (3 methods), adaptive parameter tuning
- All financial math uses `Decimal` (28-digit precision, `ROUND_HALF_EVEN`)
- Advanced modules are optional — engine works without them via graceful fallback

### Infrastructure

- Docker Compose with resource limits, network segmentation (frontend/backend/monitoring), `service_healthy` dependency checks
- TimescaleDB (PostgreSQL 16), Redis 7
- Prometheus alert rules (11 rules), Grafana provisioning
- gRPC (orders) + ZeroMQ PUB/SUB (tick data)

### What Was Fixed (Historical)

The original monolithic `main.py` (1,609 lines, 22 critical bugs) was completely rewritten as a clean `main.py` (520 lines) + `engine.py` (403 lines). All Phase 0-2 emergency fixes from the original audit have been applied: kill switch tuple unpack, safety system wiring, interface mismatches, fail-closed defaults, Docker `service_healthy`, and more. The neural network subsystem was removed entirely in favor of pure algorithmic/mathematical signal generation.

---

## Section 1: Development Standards

These rules are permanent and apply to all future development.

### Rules

1. **Verify interface before call.** Read the target function's signature and return type before writing any call. Five of the original seven critical bugs existed because calls were written without checking signatures.

2. **Fail closed, not open.** Safety systems default to the restrictive state. Kill switch defaults to active (block trading). Missing config defaults to minimum risk. Unknown state = halt.

3. **No silent exceptions.** `contextlib.suppress(Exception)` is banned. `except Exception: pass` is banned. Every handler must log at WARNING or above with `exc_info=True`.

4. **No secrets in repository.** No `.env` files, passwords, API keys, or private keys committed. `.env.example` with placeholders only. Pre-commit hooks must enforce this.

5. **Decimal for all financial math.** Never `float` for prices, lots, P&L, drawdown, equity, or any monetary value. Use `Decimal` with `ROUND_HALF_EVEN`.

6. **Platform guards.** Any POSIX-only API (e.g., `add_signal_handler`) must be guarded with `sys.platform != "win32"`. MT5 is Windows-only.

7. **Every bug fix includes a regression test.** If you fix it, prove it stays fixed.

8. **Integration tests for safety systems.** Unit testing in isolation is necessary but insufficient. Safety modules must be tested as wired into the pipeline.

9. **Ship incrementally.** Every commit compiles, passes tests, contains no dead code. One logical change per commit.

10. **No dead code.** If it's not called, delete it. Dead safety systems are worse than no safety systems because they create the illusion of protection.

---

## Section 2: Remaining Bug Fixes

### P0 — Critical

#### P0-OPEN-01: algo-engine Windows platform guard

**File:** `program/services/algo-engine/src/algo_engine/main.py:508-509`

`loop.add_signal_handler()` is called without a platform check. This raises `NotImplementedError` on Windows. The mt5-bridge already has the fix at `main.py:167`.

**Fix:**
```python
import sys
if sys.platform != "win32":
    loop.add_signal_handler(signal.SIGINT, _shutdown)
    loop.add_signal_handler(signal.SIGTERM, _shutdown)
```

---

### P1 — MT5 Bridge Hardening

These items harden the execution layer against real-world edge cases.

#### P1-B01: Order dedup before execution [HIGH]

**File:** `mt5-bridge/src/mt5_bridge/order_manager.py:128-133`

Signal ID is recorded in `_recent_signals` AFTER `_submit_order()` succeeds. Concurrent gRPC retries can cause duplicate orders. Move dedup record BEFORE execution (after validation at line 85). Failed signals should stay in dedup window intentionally.

#### P1-B02: Margin check on unclamped lots [MEDIUM]

**File:** `mt5-bridge/src/mt5_bridge/order_manager.py:180-186`

Margin check uses raw `suggested_lots` before `_clamp_lot_size()` adjusts them. May reject valid signals. Fix: clamp first, then check margin.

#### P1-B03: Execution lock for concurrent gRPC [HIGH]

**File:** `mt5-bridge/src/mt5_bridge/order_manager.py`

No thread lock protects `_submit_order()`. Multiple concurrent gRPC calls can submit orders simultaneously. Add `threading.Lock` around the execution path.

#### P1-B04: SL/TP direction validation [MEDIUM]

**File:** `mt5-bridge/src/mt5_bridge/order_manager.py`

No validation that SL is below entry for BUY or above entry for SELL (and vice versa for TP). Inverted SL/TP silently creates orders that close immediately.

#### P1-B05: MT5 connection liveness check [HIGH]

**File:** `mt5-bridge/src/mt5_bridge/connector.py:32-34`

`is_connected` only checks a local boolean flag. If MT5 terminal crashes, flag stays `True`. Fix: call `mt5.terminal_info()` to verify actual connectivity.

#### P1-B06: MT5 automatic reconnection [HIGH]

**File:** `mt5-bridge/src/mt5_bridge/connector.py`

No reconnection logic exists. If MT5 disconnects, the bridge stays broken until manually restarted. Implement `reconnect()` with exponential backoff (max 3 retries, 5s delay).

#### P1-B07: Stale close price in position tracker [MEDIUM]

**File:** `mt5-bridge/src/mt5_bridge/position_tracker.py:68-80`

Closed position profit comes from the last snapshot, not actual close. Fix: fetch from `mt5.history_deals_get(position=ticket)` for accurate P&L.

#### P1-B08: Health check accuracy [MEDIUM]

**File:** `mt5-bridge/src/mt5_bridge/`

Health check should reflect actual MT5 terminal connection state, not just service process status.

#### P1-B09: Graceful shutdown cancels pending orders [HIGH]

On SIGTERM, pending limit orders are not cancelled. They may fill after shutdown, creating unmanaged positions. Add order cancellation to shutdown handler.

---

### P1 — Data Ingestion

#### P1-DI01: Binance WebSocket reconnection [HIGH]

**File:** `data-ingestion/internal/` (WebSocket handler)

No reconnection logic on disconnect. Implement exponential backoff (1s initial, 5min max). Track reconnections via `moneymaker_ws_reconnections_total` metric.

#### P1-DI02: Polygon message drop detection [HIGH]

**File:** `data-ingestion/internal/` (channel pipeline)

If the database writer is slow, Go channel sends block or drop messages silently. Add non-blocking send with drop counter metric (`moneymaker_messages_dropped_total`). Alert when drop rate > 10/min.

#### P1-DI03: SQL injection in batch.go [HIGH]

**File:** `data-ingestion/internal/dbwriter/batch.go:112-116`

`InsertTicksBatch` uses `fmt.Sprintf` for table name interpolation. The primary `insertTicks()` uses safe `pgx.Identifier{}`. Fix fallback to use `pgx.Identifier{}.Sanitize()`.

#### P1-DI04: ZMQ backpressure [MEDIUM]

**File:** `algo-engine/src/algo_engine/main.py` (ZMQ subscriber)

No HWM configured on ZMQ subscriber. Buffer grows unbounded if processing is slow. Fix: `zmq_sub.setsockopt(zmq.RCVHWM, 1000)`.

#### P1-DI05: API key pre-validation [LOW]

**File:** `data-ingestion/cmd/server/main.go`

Empty API keys cause cryptic failures. Validate at startup with clear error message.

---

## Section 3: Security Hardening

### 3.1 Pre-Commit Hooks [HIGH]

**Status:** NOT IMPLEMENTED (release checklist incorrectly marked as done)

Create `.pre-commit-config.yaml` with:
- `python -m py_compile` on all `.py` files
- `ruff check` linting
- Secret detection (`detect-secrets` or `gitleaks`)
- No `contextlib.suppress(Exception)` pattern
- No `.env` files or `*.key` files
- No unguarded `add_signal_handler` calls

### 3.2 CI/CD Pipeline [HIGH]

**Status:** NOT IMPLEMENTED (no `.github/workflows/` directory exists)

Create `.github/workflows/ci.yml` with:
- **Lint job:** `ruff check`, `ruff format --check`
- **Type check job:** `mypy --ignore-missing-imports`
- **Unit test job:** `pytest` on Ubuntu
- **Security scan job:** `gitleaks`, `pip-audit`
- **Go job:** `go vet`, `go test`, `govulncheck` for data-ingestion
- Optional: Windows runner for mt5-bridge tests

### 3.3 gRPC TLS Silent Downgrade [HIGH]

**File:** `shared/python-common/src/moneymaker_common/grpc_credentials.py`

If TLS certs are missing, `create_client_channel` silently falls back to insecure. In production (`MONEYMAKER_ENV=production`), this must raise `ValueError`. In development, log WARNING.

### 3.4 Production Password Validation [MEDIUM]

**File:** `shared/python-common/src/moneymaker_common/config.py`

Empty password defaults (`moneymaker_db_password: str = ""`) allow unauthenticated connections. In production mode, empty passwords must cause startup failure.

### 3.5 Database URL SSL Enforcement [MEDIUM]

**File:** `shared/python-common/src/moneymaker_common/config.py`

`moneymaker_db_url` default doesn't enforce `sslmode=require`. In production, auto-append if missing.

### 3.6 Secrets in Init Scripts [MEDIUM]

**File:** `infra/docker/init-db/007_rbac_passwords.sh`

Verify no hardcoded passwords in database init scripts. All passwords must come from environment variables.

---

## Section 4: Testing Strategy

### 4.1 Current Coverage (26 Unit Test Modules)

All in `algo-engine/tests/unit/`:

| Module | Covers |
|--------|--------|
| `test_math_spectral.py` | FFT, wavelets, cycle detection |
| `test_math_bayesian.py` | Regime detection, Thompson sampling |
| `test_math_ou_process.py` | OU parameter fitting, s-scores |
| `test_math_extreme_value.py` | GPD, tail risk, CVaR |
| `test_math_fractal.py` | Hurst exponent, DFA |
| `test_math_information_theory.py` | Entropy, KL divergence |
| `test_math_stochastic.py` | GBM, Merton, Heston |
| `test_math_copula.py` | Gaussian copula, tail dependence |
| `test_pipeline.py` | Data quality, MTF, features, regime |
| `test_technical.py` | RSI, EMA, MACD, ATR, Bollinger |
| `test_technical_extended.py` | Extended indicator tests |
| `test_strategy_base.py` | Strategy interface |
| `test_trend_following.py` | Trend-following strategy |
| `test_mean_reversion.py` | Mean-reversion strategy |
| `test_regime.py` | Regime classification |
| `test_regime_router.py` | Bayesian/probabilistic routing |
| `test_build_router.py` | Router construction |
| `test_signal_generator.py` | Signal generation |
| `test_signal_validator.py` | Pre-order validation |
| `test_position_sizer.py` | Position sizing |
| `test_trailing_stop.py` | Trailing stop (4 modes) |
| `test_spiral_protection.py` | Consecutive loss protection |
| `test_kill_switch.py` | Emergency stop |
| `test_portfolio.py` | Portfolio state management |
| `test_defensive.py` | Defensive strategy |
| `test_grpc_client.py` | gRPC client |
| `test_zmq_adapter.py` | ZMQ message parsing |

### 4.2 Missing: Integration Tests [HIGH]

No integration tests exist. Create `tests/integration/`:

1. **Full pipeline test** — Feed a bar through engine, verify signal output includes position sizing, validation, and rate limiting.
2. **Kill switch blocking** — Activate kill switch, feed bar, verify no signal emitted.
3. **Position sizer wiring** — Verify `PositionSizer.calculate()` is called with actual equity and drawdown from `PortfolioStateManager`.
4. **Spiral activation** — Record N consecutive losses, verify cooldown activates and sizing multiplier drops to 0.
5. **Drawdown enforcement** — Simulate drawdown exceeding threshold, verify kill switch triggers.
6. **Data quality rejection** — Feed malformed bar (negative volume, OHLC violation), verify rejection.
7. **Validator confidence gate** — Generate signal below confidence threshold, verify rejection.

### 4.3 Missing: E2E Safety Test [HIGH]

End-to-end test simulating the full safety chain:

```
Normal operation -> Loss streak (5 consecutive)
  -> Spiral protection activates (cooldown)
  -> Drawdown exceeds 3% -> Portfolio kill switch (50% size reduction)
  -> Drawdown exceeds 5% -> Global kill switch (flatten all)
  -> Manual deactivation -> Recovery with reduced sizing
```

This test must exercise the actual `AlgoEngine` class, not mocked components.

### 4.4 Missing: MT5 Bridge Tests

- Order dedup under concurrent access
- Reconnection after disconnect
- SL/TP direction validation
- Graceful shutdown order cancellation

---

## Section 5: Console Enhancement Roadmap

### 5.1 Current State

22 command modules exist in `console/src/moneymaker_console/commands/`:

```
alert.py    audit.py    brain.py    build.py    config.py
data.py     exit_cmd.py help.py     kill.py     log_ops.py
maint.py    market.py   mt5.py      perf.py     portfolio.py
risk.py     signal.py   svc.py      sys_ops.py  test_cmds.py
tool.py     __init__.py
```

Many handlers likely return "SERVICE UNAVAILABLE" stubs. Priority is connecting them to real services.

### 5.2 Priority Commands (Connect to Live Services)

| Command | Backend | Protocol |
|---------|---------|----------|
| `brain status` / `brain regime` | algo-engine REST | HTTP :8082 |
| `kill activate` / `kill deactivate` / `kill status` | Redis | Direct |
| `sys health` | All services | HTTP health endpoints |
| `risk status` / `risk limits` | algo-engine + Redis | HTTP + Redis |
| `data status` / `data gaps` | TimescaleDB | SQL |
| `mt5 positions` / `mt5 status` | mt5-bridge | gRPC :50055 |
| `perf summary` / `perf daily` | TimescaleDB | SQL |
| `signal history` | TimescaleDB | SQL |
| `market regime` / `market sessions` | algo-engine REST | HTTP :8082 |

### 5.3 Deferred Commands (Post Paper-Trading)

- `portfolio var` / `portfolio cvar` / `portfolio stress-test` — advanced analytics
- `audit security` / `audit secrets` / `audit hashchain` — compliance
- `alert telegram` / `alert rules` — notification system
- `config encrypt` / `config decrypt` — env file encryption
- `perf attribution` / `perf regime` — strategy-level analytics

### 5.4 Cleanup

- Remove or stub any `ml` command references (ML has been removed from the system)
- Verify no command imports from deleted `nn/` or `analysis/` directories

---

## Section 6: Infrastructure & Deployment

### 6.1 Docker Compose (Already Done)

The following are already implemented:
- Resource limits on all containers (cpus + memory)
- Network segmentation (frontend, backend, monitoring)
- `service_healthy` dependency checks
- Health check endpoints with interval/timeout/retries

### 6.2 Still Needed

#### AlertManager Service [MEDIUM]

Prometheus alert rules exist (11 rules in `alert_rules.yml`) but AlertManager is not in docker-compose. Add:
```yaml
alertmanager:
  image: prom/alertmanager:v0.27.0
  volumes:
    - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
  networks:
    - monitoring
```

Configure notification routing (email, Telegram, webhook).

#### Grafana Dashboard Templates [LOW]

Create provisioned dashboards for:
- Trading overview (signals/day, win rate, P&L curve)
- Risk metrics (drawdown, kill switch events, spiral activations)
- System health (service uptime, latency, error rates)
- Data ingestion (ticks/sec, gaps, reconnections)

#### Non-Root Containers [MEDIUM]

Add `USER nonroot` to all Dockerfiles. Run services as non-root for defense in depth.

#### Database Maintenance Automation [LOW]

Schedule via console `maint` commands or cron:
- `VACUUM ANALYZE` on hypertables (weekly)
- TimescaleDB compression on chunks older than 7 days
- Retention pruning on ticks older than 90 days
- Automated backups with `pg_dump`

---

## Section 7: Paper Trading Readiness Checklist

This is the gate. Every box must be checked before deploying with real (paper) money.

### Safety Gates

- [ ] All 26 unit test modules pass
- [ ] Integration tests pass (Section 4.2 — all 7 tests)
- [ ] E2E safety chain test passes (Section 4.3)
- [ ] algo-engine `main.py` Windows platform guard added (P0-OPEN-01)
- [ ] Pre-commit hooks installed and passing (Section 3.1)
- [ ] No secrets in repository (`gitleaks` scan clean)
- [ ] CI pipeline green (Section 3.2)

### Configuration (Paper Trading with $1,000 Equity)

- [ ] `algo_default_equity` = `1000`
- [ ] `algo_max_lots` = `0.10`
- [ ] `algo_risk_per_trade_pct` = `1.0` (1% risk per trade)
- [ ] `algo_max_drawdown_pct` = `5.0`
- [ ] `algo_max_daily_loss_pct` = `2.0`
- [ ] `algo_spiral_loss_threshold` = `3`
- [ ] `algo_spiral_max_losses` = `5`
- [ ] Kill switch levels: strategy 5% DD, portfolio 3% DD (50% size), global 5% DD (flatten)

### Operational

- [ ] Docker stack starts with all services healthy
- [ ] ZMQ data feed flowing (at least 1 tick/minute for subscribed pairs)
- [ ] Kill switch test passes (activate -> verify trading blocked -> deactivate)
- [ ] Console `sys health` shows all services GREEN
- [ ] Prometheus alert rules loaded and firing correctly
- [ ] 24-hour unattended run: no memory leaks, no crashes, no orphaned connections

---

## Appendix A: Issue Tracking Reference

Maps original remediation plan IDs to current status.

| Phase | IDs | Status | Notes |
|-------|-----|--------|-------|
| Phase 0 | P0-01 to P0-10 | FIXED | main.py + engine.py completely rewritten |
| Phase 1 | P1-01 to P1-09 | FIXED | Safety systems wired, fail-closed defaults |
| Phase 2 | P2-01 to P2-13 | PARTIALLY OPEN | MT5 bridge items remain (Section 2) |
| Phase 3 | P3-01 to P3-08 | OBSOLETE | All ML/neural network code removed |
| Phase 4 | P4-01 to P4-05 | OBSOLETE | ML feature pipeline removed |
| Phase 5 | P5-01 to P5-06 | PARTIALLY OPEN | Data ingestion items remain (Section 2) |
| Phase 6 | P6-01 to P6-09 | PARTIALLY OPEN | Security items remain (Section 3) |
| Phase 7 | P7-01 to P7-07 | OPEN | CI/CD and integration tests needed (Sections 3-4) |
| Phase 8 | P8-01 to P8-06 | MOSTLY DONE | Docker limits + networks done; AlertManager pending |
| Phase 9 | P9-01 to P9-03 | DONE | Dynamic pips, session clamp, breakeven all implemented |
| Phase 10 | P10-01 to P10-05 | DONE | Async Redis, audit limits, dead code removed |

### Release Checklist Discrepancies

The previous `RELEASE_CHECKLIST.md` marked these as complete, but they are NOT implemented:
- **P7-05 (Windows CI runner)** — No `.github/workflows/` directory exists
- **P7-06 (Pre-commit hooks)** — No `.pre-commit-config.yaml` exists
- **P7-03 (ML training in CI)** — Obsolete (ML removed), but CI itself doesn't exist

---

## Appendix B: Discarded Content

The following content from the original 5 plan documents was discarded:

| Content | Source Document | Reason |
|---------|----------------|--------|
| Phase 3: Neural Network Integrity (8 items) | Master Remediation Plan | All ML/AI removed from project |
| Phase 4: Feature vector training/inference mismatch | Master Remediation Plan | No ML training pipeline exists |
| `torch.load` security items (P6-03) | Master Remediation Plan | PyTorch not a dependency |
| `ccxt` dependency item (P6-09) | Master Remediation Plan | Already fixed in Phase 0 |
| ML command category specification | Console Plan | ML removed from system |
| Safety-first Bug 1 (daily loss reset) | Safety-First Design | Fixed in portfolio.py rewrite |
| Safety-first Bug 2 (kill switch TypeError) | Safety-First Design | Fixed in kill_switch.py rewrite |
| Safety-first Bug 3 (Docker depends_on) | Safety-First Design | Already uses `service_healthy` |
| Spiral protection implementation plan | Safety-First Implementation | `spiral_protection.py` exists (188 LoC) |
| TDD task list (Days 1-6) | Safety-First Implementation | All tasks completed in rewrite |
| Release checklist (all phases) | Release Checklist | Superseded by Section 7 |
| Italian-language design spec | Safety-First Design | Content preserved in English above |
| Co-Authored-By attribution rules | Safety-First Implementation | Violates project commit policy |
| Neural network architecture praise | Master Remediation Plan | Neural network no longer exists |
| Original `main.py` failure analysis | Master Remediation Plan | `main.py` completely rewritten |
