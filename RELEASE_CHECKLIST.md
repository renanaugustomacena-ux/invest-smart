# MONEYMAKER Release Gate Checklist

**Last Updated:** 2026-03-07

---

## Phase 0 — Emergency Fixes
- [x] Kill switch tuple unpack (P0-01)
- [x] StrategySuggestion import (P0-02)
- [x] validate_bar signature (P0-03)
- [x] analyze() params (P0-04)
- [x] PnLMomentumTracker method (P0-05)
- [x] Windows signal handlers (P0-06, P0-07)
- [x] health.py import order (P0-08)
- [x] vectorizer.py docstring (P0-09)
- [x] Garbage comments removed (P0-10)

## Phase 1 — Safety Validation
- [x] NaN/Inf validation for entry_price and stop_loss (P1-06)
- [x] All other P1 items verified FIXED

## Phase 2 — Order Management
- [x] Signal age enforcement (P2-08)
- [x] Daily loss / drawdown enforcement (P2-10)
- [x] Dynamic pip size via MT5 digits (P2-13)
- [x] All other P2 items verified FIXED

## Phase 3 — Neural Network
- [x] ModelEvaluator decomposed forward call (P3-02)
- [x] Early stopping state reset between phases (P3-08)

## Phase 4 — Feature Engineering
- [x] Session boundaries aligned across modules (P4-02)
- [x] ADX double-count fixed in trend strategy (P4-05)

## Phase 5 — Data Ingestion
- [x] Polygon/Binance message drops logged (P5-02)
- [x] Audit trail periodic flush + shutdown hook (P5-04)
- [x] ZMQ HWM backpressure set (P5-05)
- [x] Polygon API key pre-validation (P5-06)

## Phase 6 — Security
- [x] gRPC strict_tls auto-detect in production (P6-05)
- [x] Go DB sslmode=require in production (P6-06)
- [x] Go password URL-encoded (P6-07)
- [x] Go empty password fatal in production (P6-08)

## Phase 7 — Test Coverage & CI/CD
- [x] Integration tests for safety systems (P7-01)
- [x] Regression tests for Phase 0 fixes (P7-02)
- [x] ML Training in CI pipeline (P7-03)
- [x] Mypy type checking in CI (P7-04)
- [x] Windows CI runner (P7-05)
- [x] Pre-commit hooks (P7-06)
- [x] Feature vector consistency test (P7-07)

## Phase 8 — Infrastructure
- [x] Docker resource limits (P8-01)
- [x] Network isolation (P8-02)
- [x] Health check endpoints (P8-03)
- [x] Graceful shutdown cancels pending orders (P8-04)
- [x] Resource cleanup on shutdown (P8-05)
- [x] Redis health check TLS support (P8-06)

## Phase 9 — Heuristic Validation
- [x] Dynamic pip values via digits param (P9-01)
- [x] Session boost clamped to min 0.30 (P9-02)
- [ ] Breakeven trailing stop in pips (P9-03) — not yet implemented

## Phase 10 — Performance
- [x] Async Redis client (P10-01)
- [x] Signal probs dynamic override (P10-02)
- [x] Audit buffer size limit 10K (P10-03)
- [x] Dead code removal (P10-04) — 6 unused imports removed
- [x] Console command timeouts (P10-05) — universal SIGALRM dispatch + per-command overrides

## Phase 11 — Final QA
- [x] E2E safety test (P11-01)
- [x] Release checklist (P11-02 — this document)

---

## Pre-Release Verification

- [ ] CI pipeline green on all platforms (Ubuntu + Windows)
- [ ] `mypy --ignore-missing-imports` passes
- [ ] No secrets in repository (`gitleaks` clean)
- [ ] All `torch.load` uses `weights_only=True`
- [ ] Feature vector consistency test passes (60 features, indices 0-59)
- [ ] Kill switch fail-closed test passes
- [ ] Position sizer integrated and tested with dynamic pip sizes
- [ ] Trade close events handled by PositionTracker
- [ ] Model evaluator decomposed forward signature verified
- [ ] Windows signal handlers guarded with `sys.platform`
- [ ] Docker resource limits configured for all services
- [ ] Graceful shutdown cancels pending MT5 orders
- [ ] TLS enforced in production configs (gRPC, DB, Redis)
- [ ] Production passwords validated on startup
- [ ] 24h paper trading run without memory leaks
