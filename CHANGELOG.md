# Changelog

All notable changes to the MONEYMAKER trading system are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.0] — 2026-03-21

### Added

#### Core Services
- **data-ingestion** (Go) — Real-time WebSocket ingestion from Binance (8 crypto pairs: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX), Polygon (forex), and mock connectors. OHLCV bar aggregation on M1/M5 timeframes, ZeroMQ PUB for downstream consumers, TimescaleDB persistence.
- **algo-engine** (Python) — Quantitative signal engine: 5 strategies (MeanReversion, TrendFollowing, Breakout, MomentumSwing, StatArb), regime-aware routing, configurable feature pipeline, kill switch, spiral protection, trailing stops, walk-forward optimization, Monte Carlo simulation.
- **mt5-bridge** (Python) — MetaTrader 5 execution bridge: gRPC signal receiver, order management with deduplication, position reconciliation, SL/TP validation, trailing stop management.
- **dashboard** — FastAPI backend + React/TypeScript frontend for real-time monitoring, portfolio visualization, and system health.
- **external-data** — Macro data ingestion from FRED, CBOE (VIX), and CFTC (COT reports) with scheduled collection and caching.
- **console** — Rich TUI command center for ecosystem management, service health checks, alert testing, and diagnostics.
- **monitoring** — Prometheus + Grafana + AlertManager stack with custom recording rules and alert definitions.

#### Algo-Engine Internals (60 files, ~12,877 LoC)
- **Feature Pipeline**: ADX, ATR, RSI, EMA (fast/slow), Bollinger Bands, VWAP computed per bar.
- **Regime Classifier**: 5 market regimes (HIGH_VOLATILITY, TRENDING_UP, TRENDING_DOWN, REVERSAL, RANGING) with hysteresis (configurable consecutive-bar confirmation).
- **RegimeRouter**: Direct routing and probabilistic routing (Bayesian posteriors) to strategy selection.
- **Signal Validation**: Confidence gating, rate limiting, position limits, drawdown guards.
- **Risk Management**: CVaR + Half-Kelly position sizing, 4-mode trailing stops (fixed, ATR, percentage, chandelier), kill switch (strategy/portfolio/global levels), spiral protection with cooldown.
- **Advanced Math** (8 modules): Wavelet denoising, fractional differencing, Hurst exponent, copula dependence, GPD tail risk, spectral analysis, entropy measures, Kalman filtering.
- **Optimization**: Walk-forward analysis, Monte Carlo simulation, adaptive parameter tuning.
- **Backtesting**: Full simulation engine with realistic fills, slippage modeling, and comprehensive metrics (Sharpe, Sortino, Calmar, max drawdown, win rate).

#### Shared Libraries
- **moneymaker-common** — Decimal utilities (28-digit precision, ROUND_HALF_EVEN), structured logging, enums, Pydantic settings, Prometheus instrumentation.
- **moneymaker-proto** — Protobuf/gRPC service definitions for inter-service communication.

#### Infrastructure
- Docker Compose orchestration: 10 services across 4 isolated networks (backend, egress, frontend, monitoring).
- TimescaleDB with hypertables for OHLCV storage and continuous aggregates.
- Redis for real-time state (kill switch, spiral protection, rate limiting).
- Prometheus scraping all services with custom recording rules.
- Grafana dashboards for trading metrics and system health.
- AlertManager with configurable notification channels.

#### Testing
- 874 total tests across the algo-engine (870 pass, 2 skip, 0 failures).
- Coverage across all signal validators, strategies, risk modules, math libraries, and optimization engines.
- pytest configuration with strict markers, async support, and timeout enforcement.

### Project Hardening (2026-03-20)
- **LICENSE**: Proprietary license with financial disclaimer.
- **SECURITY.md**: Vulnerability disclosure policy with response timelines.
- **CONTRIBUTING.md**: Development standards, conventional commits, code style.
- **README files**: algo-engine, external-data, dashboard frontend — all with Mermaid diagrams, source layout trees, operational guides.
- **pyproject.toml**: Complete metadata (authors, license, readme) across all 7 packages.
- **License headers**: Added to 187 production source files (Python, Go, Proto).
- **CHANGELOG.md**: This file.
- **Test fixes**: Resolved 8 pre-existing failures (RegimeClassifier hysteresis, SpiralProtection cooldown assertion).

---

## [0.1.0] — 2024-12-01

### Added
- Initial project scaffolding and service architecture.
- Basic data ingestion pipeline.
- Prototype algo-engine with single strategy.
- MT5 bridge proof of concept.
