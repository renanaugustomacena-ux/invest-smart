# MONEYMAKER UNIFIED CONSOLE — MASTER IMPLEMENTATION PLAN

## Version 2.0 — Complete Ecosystem Command Center

---

## Table of Contents

1. [Executive Vision and Philosophy](#1-executive-vision-and-philosophy)
2. [Architecture and Core Infrastructure](#2-architecture-and-core-infrastructure)
3. [Command Registry and Plugin System](#3-command-registry-and-plugin-system)
4. [Command Category: `brain` — Algo Engine Control](#4-command-category-brain--algo-engine-control)
5. [Command Category: `data` — Data Ingestion Management](#5-command-category-data--data-ingestion-management)
6. [Command Category: `mt5` — MetaTrader 5 Bridge Control](#6-command-category-mt5--metatrader-5-bridge-control)
7. [Command Category: `risk` — Risk Management Engine](#7-command-category-risk--risk-management-engine)
8. [Command Category: `signal` — Signal Pipeline Management](#8-command-category-signal--signal-pipeline-management)
9. [Command Category: `market` — Market Intelligence](#9-command-category-market--market-intelligence)
10. [Command Category: `ml` — Machine Learning (Embedded in Brain)](#10-command-category-ml--machine-learning-embedded-in-brain)
11. [Command Category: `test` — Test Suite Orchestration](#11-command-category-test--test-suite-orchestration)
12. [Command Category: `build` — Build and Container Management](#12-command-category-build--build-and-container-management)
13. [Command Category: `sys` — System Operations](#13-command-category-sys--system-operations)
14. [Command Category: `config` — Configuration Management](#14-command-category-config--configuration-management)
15. [Command Category: `svc` — Service Lifecycle Management](#15-command-category-svc--service-lifecycle-management)
16. [Command Category: `maint` — Maintenance and Database Operations](#16-command-category-maint--maintenance-and-database-operations)
17. [Command Category: `kill` — Emergency Kill Switch](#17-command-category-kill--emergency-kill-switch)
18. [Command Category: `audit` — Security and Compliance Audit](#18-command-category-audit--security-and-compliance-audit)
19. [Command Category: `perf` — Performance Analytics](#19-command-category-perf--performance-analytics)
20. [Command Category: `portfolio` — Portfolio Management](#20-command-category-portfolio--portfolio-management)
21. [Command Category: `alert` — Alerting and Notification System](#21-command-category-alert--alerting-and-notification-system)
22. [Command Category: `log` — Logging and Observability](#22-command-category-log--logging-and-observability)
23. [Command Category: `tool` — Utility Tools](#23-command-category-tool--utility-tools)
24. [TUI Dashboard — Rich Interactive Interface](#24-tui-dashboard--rich-interactive-interface)
25. [CLI Mode — Non-Interactive Command Dispatch](#25-cli-mode--non-interactive-command-dispatch)
26. [Status Polling and Background Threads](#26-status-polling-and-background-threads)
27. [Service Client Layer — HTTP, gRPC, Redis, PostgreSQL](#27-service-client-layer--http-grpc-redis-postgresql)
28. [Security Considerations](#28-security-considerations)
29. [Error Handling and Resilience](#29-error-handling-and-resilience)
30. [Testing Strategy for the Console Itself](#30-testing-strategy-for-the-console-itself)
31. [Implementation Phases and Milestones](#31-implementation-phases-and-milestones)
32. [File Structure and Module Layout](#32-file-structure-and-module-layout)
33. [Full Command Reference Table](#33-full-command-reference-table)

---

## 1. Executive Vision and Philosophy

### 1.1 The Single Entry Point Principle

The MONEYMAKER Unified Console follows a fundamental principle inherited from its predecessor, the Macena CS2 Analyzer Console: **If it is not in this console, the project does not need it.** Every operational task — from starting the Algo Engine training loop to executing an emergency kill switch that closes all open MetaTrader 5 positions — must be executable from this single command center.

The original Macena console (REFERENCEONLY-console.py) demonstrated the power of this approach with approximately 1,600 lines of Python covering 9 command categories (ml, ingest, build, test, sys, set, svc, maint, tool) and supporting both a Rich TUI dashboard with four live-updating panels and a full argparse-based CLI mode. The existing MONEYMAKER console (moneymaker_console.py) expanded this to 15 categories (brain, data, mt5, risk, signal, market, test, build, sys, config, svc, maint, tool, kill, help/exit) but left most handlers as service-unavailable stubs pending gRPC integration.

The Version 2.0 console described in this plan will be a dramatically more advanced evolution. It will expand to **22 command categories** with over **150 individual sub-commands**, implementing full gRPC client connectivity to all microservices, advanced TUI panels with real-time market data visualization, multi-threaded status polling with intelligent caching, comprehensive security audit capabilities, portfolio analytics, performance dashboards, and a plugin architecture that allows new command categories to be registered without modifying core console code.

### 1.2 Why a Console Matters for a Trading System

In algorithmic trading, the difference between a profitable and catastrophic day can be measured in seconds. A well-designed console provides several critical capabilities that no web dashboard, REST API, or Grafana panel can match:

**Latency**: The console runs on the same machine (or local network) as the trading infrastructure. Commands execute with sub-second latency. There is no HTTP round-trip, no browser rendering delay, no WebSocket reconnection after a page refresh. When a trader needs to activate a kill switch, the Redis publish command fires within 50 milliseconds of pressing Enter.

**Reliability**: The console is a single Python process with minimal dependencies (Rich for TUI, psycopg2 for Postgres, redis-py for Redis, grpcio for service communication). It does not depend on a web server, a JavaScript framework, or a browser. If Docker is down, the console still works. If the network is degraded, the console still works for local operations.

**Auditability**: Every command executed through the console is logged as a structured JSON event with timestamp, command text, result summary, and execution duration. This creates a complete audit trail of every operational decision made by the operator.

**Scriptability**: The CLI mode (invoked via `python moneymaker_console.py <category> <subcmd> [args]`) enables cron jobs, CI/CD pipelines, and shell scripts to interact with the trading system programmatically. A daily health check can be a three-line bash script: `moneymaker sys health && moneymaker brain status && moneymaker mt5 positions`.

**Composability**: Commands can be chained in the interactive TUI. The console maintains state across commands within a session, allowing workflows like: check market regime → adjust risk limits → start the brain → monitor signals — all without leaving the terminal.

### 1.3 Relationship to Existing Components

This console plan describes the evolution of `program/services/console/moneymaker_console.py`. The existing 1,616-line implementation provides the foundation: the `CommandRegistry` pattern, the `TUIRenderer` class, the `StatusPoller` thread, and the dual-mode (TUI + CLI) execution model. This plan preserves all of these patterns while dramatically expanding their scope and sophistication.

The console communicates with the following services:

| Service | Directory | Language | Protocol | Port |
|---------|-----------|----------|----------|------|
| Algo Engine | `services/algo-engine/` | Python | REST + ZMQ (subscriber) | 8082 (REST), 9092 (metrics) |
| Data Ingestion | `services/data-ingestion/` | Go | HTTP + ZMQ (publisher) | 8081 (health), 5555 (ZMQ PUB) |
| MT5 Bridge | `services/mt5-bridge/` | Python | gRPC | 50055 |
| ML Training (embedded) | `services/algo-engine/src/algo_engine/nn/` | Python | Internal (Brain subprocess) | — |
| External Data | `services/external-data/` | Python | REST | 9095 |
| Dashboard | `services/dashboard/` | Python + JS | REST + WebSocket | 8000 |
| PostgreSQL/TimescaleDB | (infrastructure) | — | SQL | 5432 |
| Redis | (infrastructure) | — | Redis protocol | 6379 |
| Prometheus | `services/monitoring/` | — | HTTP | 9091 |
| Grafana | `services/monitoring/` | — | HTTP | 3000 |

The console also reads and validates environment variables defined in `program/.env` (see `.env.example` for the full list of 150+ variables covering database credentials, Redis passwords, gRPC ports, TLS certificates, API keys, and risk parameters).

### 1.4 Design Principles

1. **Fail-safe defaults**: If a service is unreachable, the console must display a clear "SERVICE UNAVAILABLE" message rather than crashing. The console itself must never fail due to an external service being down.

2. **Lazy connections**: Database, Redis, and gRPC connections are established on first use, not at import time. This ensures the console starts instantly (under 500ms) regardless of infrastructure state.

3. **Decimal precision**: All financial values (prices, P&L, drawdown percentages, lot sizes) must be displayed using `decimal.Decimal` formatting, never floating-point. This matches the system-wide design principle documented in `program/README.md`.

4. **Credential safety**: API keys, passwords, and tokens must never be displayed in full. The console masks secrets by showing only the last 4 characters (e.g., `****abcd`). This is enforced in every `config view` and `set view` handler.

5. **Structured logging**: Every command execution is logged as a JSON line to `logs/console_YYYYMMDD.json`. The log entry includes timestamp, event type, command text, result summary (truncated to 200 characters), and execution duration in milliseconds.

6. **Platform independence**: The console works on Linux, macOS, and Windows. Terminal input handling (non-blocking character reads for the TUI) uses platform-specific implementations: `termios`/`tty`/`select` on Unix, `msvcrt` on Windows.

7. **Thread safety**: All shared state between the main thread (TUI render loop) and background threads (status pollers) is protected by `threading.Lock`. The status cache is a copy-on-read dictionary.

---

## 2. Architecture and Core Infrastructure

### 2.1 Module Organization

The console will be organized as a Python package rather than a single monolithic script. This enables clean separation of concerns, easier testing, and the plugin architecture described in Section 3.

```
program/services/console/
├── moneymaker_console.py          # Entry point (main function, mode selection)
├── pyproject.toml              # Package metadata and dependencies
├── logs/                       # Structured JSON log files
├── src/
│   └── moneymaker_console/
│       ├── __init__.py         # Package init, version constant
│       ├── app.py              # Application class (wires everything together)
│       ├── registry.py         # CommandRegistry and Command dataclass
│       ├── runner.py           # Subprocess runners (_run_tool, _run_tool_live)
│       ├── logging.py          # JSON structured logging
│       ├── tui/
│       │   ├── __init__.py
│       │   ├── renderer.py     # TUIRenderer (8-panel layout)
│       │   ├── theme.py        # Rich theme definitions
│       │   ├── input.py        # Platform-specific non-blocking input
│       │   └── widgets.py      # Custom Rich renderables (sparklines, etc.)
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── parser.py       # Argparse builder
│       │   └── dispatch.py     # CLI dispatch logic
│       ├── clients/
│       │   ├── __init__.py
│       │   ├── postgres.py     # Lazy PostgreSQL connection (admin user)
│       │   ├── redis_client.py # Lazy Redis connection
│       │   ├── http_brain.py   # REST client for Algo Engine (port 8082)
│       │   ├── grpc_mt5.py     # gRPC stub for MT5 Bridge service
│       │   ├── http_data.py    # HTTP client for Data Ingestion (port 8081)
│       │   ├── http_dashboard.py # REST client for Dashboard (port 8000)
│       │   └── docker.py       # Docker Compose wrapper (infra/docker/)
│       ├── commands/
│       │   ├── __init__.py     # Auto-discovery of command modules
│       │   ├── brain.py        # brain category handlers
│       │   ├── data.py         # data category handlers
│       │   ├── mt5.py          # mt5 category handlers
│       │   ├── risk.py         # risk category handlers
│       │   ├── signal.py       # signal category handlers
│       │   ├── market.py       # market category handlers
│       │   ├── ml.py           # ml category handlers
│       │   ├── test.py         # test category handlers
│       │   ├── build.py        # build category handlers
│       │   ├── sys.py          # sys category handlers
│       │   ├── config.py       # config category handlers
│       │   ├── svc.py          # svc category handlers
│       │   ├── maint.py        # maint category handlers
│       │   ├── kill.py         # kill category handlers
│       │   ├── audit.py        # audit category handlers
│       │   ├── perf.py         # perf category handlers
│       │   ├── portfolio.py    # portfolio category handlers
│       │   ├── alert.py        # alert category handlers
│       │   ├── log.py          # log category handlers
│       │   ├── tool.py         # tool category handlers
│       │   ├── help.py         # help handler
│       │   └── exit.py         # exit handler
│       └── poller/
│           ├── __init__.py
│           ├── status_poller.py    # Background status polling thread
│           └── market_poller.py    # Real-time market data polling
└── tests/
    ├── test_registry.py
    ├── test_commands.py
    ├── test_tui.py
    ├── test_cli.py
    └── test_clients.py
```

### 2.2 Dependency Stack

The console has a minimal but carefully chosen dependency stack:

| Dependency | Version | Purpose |
|------------|---------|---------|
| `rich` | >=13.0 | TUI rendering (Layout, Panel, Table, Live, ProgressBar) |
| `psycopg2-binary` | >=2.9 | PostgreSQL/TimescaleDB queries |
| `redis` | >=5.0 | Redis state reads, kill switch, pub/sub |
| `httpx` | >=0.27 | HTTP client for REST endpoints (Brain, Data Ingestion, Dashboard) |
| `grpcio` | >=1.60 | gRPC client stub for MT5 Bridge |
| `grpcio-tools` | >=1.60 | Protobuf compilation (dev only) |
| `psutil` | >=5.9 | System resource monitoring (CPU, RAM, Disk) |
| `python-dotenv` | >=1.0 | `.env` file loading |
| `click` | >=8.1 | (Optional) Enhanced CLI argument parsing |
| `prompt_toolkit` | >=3.0 | (Optional) Advanced command-line completion and history |

All dependencies are optional except `rich`. If `psycopg2` is not installed, database commands return a clear "psycopg2 not installed" message. If `grpcio` is not installed, gRPC-dependent commands gracefully fall back to "gRPC client not available" stubs. This follows the Macena console pattern where `rich` was the only hard requirement.

### 2.3 Entry Point and Mode Selection

The console supports three execution modes, selected automatically based on command-line arguments:

```python
def main():
    """MONEYMAKER Console entry point — mode selection."""
    if len(sys.argv) > 1:
        # CLI mode: python moneymaker_console.py brain status
        sys.exit(run_cli_mode(sys.argv[1:]))
    else:
        # TUI mode: python moneymaker_console.py
        if _HAS_RICH:
            run_tui_mode()
        else:
            # Fallback: readline-based interactive mode
            run_cli_interactive()
```

**TUI Mode** (no arguments): Launches the full Rich Live dashboard with 8 panels, real-time status polling, and non-blocking keyboard input. This is the primary operational interface.

**CLI Mode** (with arguments): Dispatches a single command via argparse and exits. Designed for scripting, cron jobs, and CI/CD integration.

**Interactive CLI Fallback** (no Rich): A simple `input()` loop with `MONEYMAKER>` prompt. Used when Rich is unavailable or when the terminal does not support full-screen rendering (e.g., a remote SSH session without proper terminal type).

### 2.4 Initialization and Boot Sequence

When the console starts (in any mode), it executes the following boot sequence:

1. **Path stabilization**: Set `PROJECT_ROOT` to the repository root (three levels up from `services/console/`). Add to `sys.path` for module imports.
2. **Environment loading**: Load `program/.env` using `python-dotenv`. This populates `os.environ` with database URLs, Redis credentials, API keys, and service configuration.
3. **Logging initialization**: Create the `logs/` directory and configure the JSON structured logger.
4. **Rich theme setup**: Initialize the Rich `Console` with the MONEYMAKER color theme (cyan for info, magenta for brain, blue for market, yellow for risk, red for errors, green for success).
5. **Command registration**: Iterate through all command modules in `commands/` and register handlers with the `CommandRegistry`.
6. **Lazy client preparation**: Prepare (but do not connect) database, Redis, and gRPC client factories.

The entire boot sequence completes in under 300ms. No network connections are established until a command actually needs them.

---

## 3. Command Registry and Plugin System

### 3.1 The Command Dataclass

Each registered command is represented by a `Command` dataclass:

```python
@dataclass(slots=True)
class Command:
    handler: Callable[..., str]
    help_text: str
    category: str
    aliases: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    dangerous: bool = False
    hidden: bool = False
```

The `requires_confirmation` flag triggers a "Are you sure? [y/N]" prompt before execution. This is used for destructive commands like `mt5 close-all`, `kill activate`, and `maint prune-old`. The `dangerous` flag adds a red warning icon in the help text. The `hidden` flag excludes the command from help output (used for internal/debug commands).

### 3.2 The CommandRegistry

The `CommandRegistry` class is the central dispatch table. It maps `(category, subcmd)` tuples to `Command` objects:

```python
class CommandRegistry:
    def __init__(self):
        self._commands: dict[str, dict[str, Command]] = {}
        self._aliases: dict[str, tuple[str, str]] = {}
        self._middleware: list[Callable] = []

    def register(self, category, name, handler, help_text, **kwargs):
        ...

    def dispatch(self, category, subcmd, args) -> str:
        ...

    def dispatch_interactive(self, cmd_line: str) -> str:
        ...

    def get_help(self, category=None) -> str:
        ...

    def add_middleware(self, fn: Callable):
        """Add a middleware function that wraps every command execution."""
        ...
```

**Middleware support**: The registry supports middleware functions that wrap every command execution. This is used for:
- **Timing**: Record execution duration for every command
- **Logging**: Log every command to the JSON audit log
- **Rate limiting**: Prevent command spam in the TUI (debounce rapid Enter presses)
- **Permission checks**: (Future) Role-based access control for multi-user environments

### 3.3 Command Auto-Discovery

Command modules are automatically discovered from the `commands/` directory. Each module exports a `register(registry)` function:

```python
# commands/brain.py
def register(registry: CommandRegistry):
    registry.register("brain", "start", _brain_start, "Start the Algo Engine training loop")
    registry.register("brain", "stop", _brain_stop, "Graceful stop at next checkpoint")
    ...
```

The auto-discovery mechanism iterates through all `.py` files in `commands/`, imports them, and calls their `register()` function. This enables new command categories to be added by simply creating a new file — no changes to the core console code are required.

### 3.4 Command Aliases

Commands can have aliases for convenience. For example:
- `brain s` → `brain status`
- `k status` → `kill status`
- `q` → `exit`
- `?` → `help`

Aliases are registered via the `aliases` parameter in the `Command` dataclass and resolved during `dispatch_interactive()`.

---

## 4. Command Category: `brain` — Algo Engine Control

### 4.1 Overview

The `brain` category provides comprehensive control over the Algo Engine service, the central intelligence hub of the MONEYMAKER ecosystem. The Algo Engine operates a 14-phase pipeline that transforms raw market data into validated trading signals using a combination of classical quantitative analysis and advanced machine learning.

The Algo Engine does **not** expose a gRPC server — it is a gRPC *client* (calls MT5 Bridge's `ExecutionBridgeService`). The console communicates with the Brain via:

- **REST health endpoint** on port 8082 (`BRAIN_REST_PORT`) — `/health`
- **Prometheus metrics** on port 9092 (`BRAIN_METRICS_PORT`) — `/metrics`
- **Redis** — kill switch state, regime cache, runtime flags
- **TimescaleDB** — model registry, feature vectors, drift metrics, trade data
- **Docker Compose** — start/stop lifecycle management

When the REST endpoint is unreachable, commands fall back to database queries or display a "service unavailable" message.

### 4.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `start` | `brain start [--mode MODE]` | Start the Algo Engine's main event loop. Optional `--mode` flag selects the operating mode: `rule-based` (default), `hybrid`, `coper`, or `conservative`. |
| `stop` | `brain stop [--force]` | Graceful shutdown. Waits for the current pipeline iteration to complete before stopping. The `--force` flag sends an immediate SIGTERM to the process. |
| `pause` | `brain pause` | Pause signal generation. The Brain continues receiving data and updating internal state but does not emit any trading signals. Useful during high-volatility news events. |
| `resume` | `brain resume` | Resume signal generation after a pause. |
| `status` | `brain status` | Display comprehensive Algo Engine status including: running state, current operating mode (Rule-based/Hybrid/COPER/Conservative), active symbols, pipeline phase, last signal timestamp, signal confidence histogram, and drift monitor Z-scores. |
| `eval` | `brain eval [--dataset TEST]` | Trigger an evaluation cycle on the test dataset. Reports accuracy, precision, recall, F1 score, and Sharpe ratio on historical data. |
| `checkpoint` | `brain checkpoint` | Force an immediate state checkpoint save. The Brain normally checkpoints every N minutes; this command triggers it manually. |
| `model-info` | `brain model-info` | Display the current model architecture: number of layers, total parameters, activation functions, input feature dimensions (60-dimensional vectors), and the last training timestamp. |
| `regime` | `brain regime` | Display the current market regime classification from the Regime Ensemble (Phase 1): `TRENDING_UP`, `TRENDING_DOWN`, `RANGING`, `VOLATILE`, or `CRISIS` (5-value `RegimeType` enum), along with individual classifier votes (Rule-based, HMM, k-Means). |
| `drift` | `brain drift` | Display the Drift Monitor (Phase 8) status: Z-scores for key features, drift detection threshold, and whether the model's predictions are still aligned with current market behavior. |
| `maturity` | `brain maturity` | Display the Maturity Gating (Phase 7) status: current `MaturityState` — one of `DOUBT` (0.00x, no trading), `CRISIS` (0.00x), `LEARNING` (0.35x), `CONVICTION` (0.80x), or `MATURE` (1.00x) — along with the associated `TradingMode` (`BACKTEST_ONLY`, `PAPER_TRADING`, `MICRO_LIVE`, `FULL_LIVE`), current sizing multiplier, and the confidence decay curve. |
| `spiral` | `brain spiral` | Display Spiral Protection status: consecutive loss count, current cooldown timer, lot size reduction factor, and whether the protection is currently active. |
| `confidence` | `brain confidence [SYMBOL]` | Show the current signal confidence threshold and the confidence distribution for a specific symbol or all symbols. |
| `features` | `brain features [SYMBOL]` | Display the current feature vector for a symbol: all 60+ technical indicators (RSI, EMA, MACD, BB, ATR, etc.) with their current values. |
| `coaching` | `brain coaching` | Display the 4-component coaching system status: HybridCoaching, CorrectionEngine, NNRefinement, ProBridge, and LongitudinalEngine. Shows Ollama LLM integration status and recent coaching insights. |
| `coaching-history` | `brain coaching-history [--days N]` | Display historical coaching corrections and recommendations from the CorrectionEngine and LongitudinalEngine. |
| `skill-progress` | `brain skill-progress` | Display the trader skill progression from the RAP Coach system: perception maturity, strategy evolution, and market memory depth. |
| `sentry` | `brain sentry` | Display Sentry error tracking status (`SENTRY_DSN` integration): recent captured errors, error rate trends, and last error timestamp. |

### 4.3 Client Integration (REST + DB + Redis)

The `brain` category uses the `http_brain.py` client module, which queries the Brain's REST health endpoint, TimescaleDB, and Redis:

```python
class BrainClient:
    def __init__(self, rest_url: str = "http://localhost:8082",
                 metrics_url: str = "http://localhost:9092"):
        self._rest_url = rest_url
        self._metrics_url = metrics_url

    def get_health(self) -> dict:
        """GET /health — Brain REST health endpoint."""
        resp = httpx.get(f"{self._rest_url}/health", timeout=5)
        return resp.json()

    def get_metrics(self) -> str:
        """GET /metrics — Prometheus metrics (text format)."""
        resp = httpx.get(f"{self._metrics_url}/metrics", timeout=5)
        return resp.text

    def get_regime(self, db) -> dict:
        """Query regime from Redis cache or database."""
        ...

    def get_maturity(self, db) -> dict:
        """Query maturity state from model_registry table."""
        ...

    def get_model_info(self, db) -> dict:
        """Query model architecture from model_registry + model_metrics tables."""
        ...
```

Start/stop lifecycle is managed via Docker Compose commands (`docker compose -f infra/docker/docker-compose.yml restart algo-engine`).

### 4.4 Failure Modes and Fallbacks

If the REST health endpoint is unreachable:
1. The command handler catches `httpx.ConnectError` and logs the failure.
2. The handler falls back to TimescaleDB queries for state information (model_registry, trading_signals tables).
3. If both REST and database are unavailable, the handler returns `[warning] Algo Engine service unreachable. Check 'svc status'.`
4. The TUI Brain panel displays "DISCONNECTED" in red.

---

## 5. Command Category: `data` — Data Ingestion Management

### 5.1 Overview

The `data` category controls the Data Ingestion service, a high-performance Go application that connects to market data providers (Polygon.io, Binance, Bybit) via WebSocket, normalizes incoming ticks, aggregates them into OHLCV bars, writes them to TimescaleDB, and publishes them to the Algo Engine via ZeroMQ PUB/SUB on port 5555.

The Data Ingestion service does **not** expose a gRPC server. It provides:

- **HTTP health endpoints** on port 8081 — `/healthz`, `/readyz`, `/health`
- **ZeroMQ PUB socket** on port 5555 — publishes ticks and bars
- **PostgreSQL writes** — writes OHLCV bars and ticks to TimescaleDB (no query API)
- **Prometheus metrics** on port 9090

The console interacts with Data Ingestion via HTTP health checks, direct TimescaleDB queries for data inspection, Docker Compose for lifecycle management, and ZMQ socket monitoring for throughput stats.

### 5.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `start` | `data start` | Start the data ingestion pipeline. Connects to all configured market data providers and begins streaming. |
| `stop` | `data stop` | Graceful stop. Flushes pending writes to TimescaleDB before disconnecting from providers. |
| `status` | `data status` | Display ingestion status: active WebSocket connections, symbols being streamed, tick throughput (ticks/sec), write latency to TimescaleDB, ZMQ publish rate, and buffer utilization. |
| `symbols` | `data symbols` | List all actively ingested symbols with their current timeframe configuration (M1, M5, M15, H1). |
| `add` | `data add SYMBOL [--timeframes TFs]` | Add a new symbol to the ingestion list. Default timeframes: M1, M5, M15, H1. Example: `data add XAUUSD --timeframes M1,M5,H1`. |
| `remove` | `data remove SYMBOL` | Remove a symbol from the ingestion list. Stops streaming and unsubscribes from the provider. |
| `backfill` | `data backfill SYMBOL DAYS` | Trigger a historical data backfill for a symbol. Downloads DAYS worth of historical bars from the provider API and inserts them into TimescaleDB. |
| `gaps` | `data gaps [--days N]` | Analyze TimescaleDB for data gaps. Uses `time_bucket()` hypertable functions to find hours with fewer than expected ticks. Default: 7 days. |
| `providers` | `data providers` | List configured data providers with connection status (Connected/Disconnected/Error), last heartbeat timestamp, and message throughput. |
| `reconnect` | `data reconnect [PROVIDER]` | Force reconnection to a specific provider or all providers. Useful after network interruptions. |
| `buffer` | `data buffer` | Display the aggregation buffer status: number of pending bars per symbol per timeframe, memory usage, and flush interval. |
| `latency` | `data latency` | Display end-to-end latency metrics: provider→ingestion, ingestion→TimescaleDB, ingestion→ZMQ, measured in percentiles (p50, p95, p99). Scraped from Prometheus metrics endpoint at `:9090/metrics`. |

### 5.3 Database Queries

All `data` sub-commands query TimescaleDB directly (the Data Ingestion service has no query API):

```sql
-- data gaps: Find hours with fewer than expected bars
SELECT time_bucket('1 hour', open_time) AS bucket,
       symbol,
       count(*) AS bar_count
FROM ohlcv_bars
WHERE open_time > NOW() - INTERVAL '7 days'
GROUP BY bucket, symbol
HAVING count(*) < 4  -- expecting M1,M5,M15,H1 per hour
ORDER BY bucket DESC;

-- data symbols: Active symbols from ohlcv_bars (no ingestion_config table exists)
SELECT DISTINCT symbol,
       array_agg(DISTINCT timeframe) AS timeframes,
       max(open_time) AS last_bar_at
FROM ohlcv_bars
WHERE open_time > NOW() - INTERVAL '1 hour'
GROUP BY symbol
ORDER BY symbol;

-- data status: Tick throughput
SELECT time_bucket('1 minute', timestamp) AS bucket,
       count(*) AS tick_count
FROM market_ticks
WHERE timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY bucket
ORDER BY bucket DESC;
```

**Note on ZMQ topic format**: Ticks use topic `trade.polygon.XAU/USD`, bars use topic `bar.XAU/USD.M1`. The Brain's `zmq_adapter.py` expects a specific JSON format with `symbol`, `timeframe`, `open_time`, etc.

### 5.4 ZeroMQ Monitoring

The `data status` command includes ZeroMQ publish statistics. The console connects to the ZMQ monitoring socket (if available) to retrieve:
- Total messages published since start
- Current publish rate (messages/second)
- Subscriber count (typically 1 — the Algo Engine)
- High-water mark (HWM) setting and buffer utilization

---

## 6. Command Category: `mt5` — MetaTrader 5 Bridge Control

### 6.1 Overview

The `mt5` category controls the MT5 Bridge service, which is the execution layer of the MONEYMAKER ecosystem. The MT5 Bridge receives validated trading signals from the Algo Engine via gRPC, translates them into MetaTrader 5 operations (market orders, pending orders, position modifications, position closures), and maintains a synchronized copy of the account state in TimescaleDB.

The MT5 Bridge exposes a gRPC API on port 50055 (`MONEYMAKER_MT5_BRIDGE_GRPC_PORT`) and Prometheus metrics on port 9094.

### 6.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `connect` | `mt5 connect` | Initialize the connection to the MetaTrader 5 terminal. Uses `MT5_ACCOUNT`, `MT5_PASSWORD`, and `MT5_SERVER` from `.env`. |
| `disconnect` | `mt5 disconnect` | Gracefully disconnect from MT5. Does NOT close open positions — only stops receiving new signals. |
| `status` | `mt5 status` | Display MT5 connection status: logged in (yes/no), server name, account number, account type (Demo/Live), balance, equity, margin, free margin, margin level %, and last sync timestamp. All monetary values displayed in `Decimal` format. |
| `positions` | `mt5 positions [--symbol S]` | List all open positions with: ticket number, symbol, direction (BUY/SELL), volume (lots), open price, current price, stop loss, take profit, swap, profit/loss, and open time. Optionally filter by symbol. |
| `history` | `mt5 history [--days N] [--symbol S]` | Display trade history for the last N days (default: 7). Shows completed trades with P&L, commission, and execution quality metrics. |
| `close` | `mt5 close TICKET` | Close a specific open position by ticket number. Requires confirmation. |
| `close-all` | `mt5 close-all [--symbol S]` | **DANGEROUS**: Close ALL open positions. Requires explicit "y" confirmation. Optionally close only positions for a specific symbol. |
| `modify` | `mt5 modify TICKET --sl SL --tp TP` | Modify stop loss and/or take profit of an existing position. |
| `account` | `mt5 account` | Display full account information: name, server, currency, leverage, balance, equity, margin, free margin, margin level, deposit, and credit. |
| `sync` | `mt5 sync` | Force a complete synchronization between the MT5 terminal state and the MONEYMAKER database. Resolves discrepancies from manual trades made directly in MT5. |
| `orders` | `mt5 orders` | List all pending orders (limit orders, stop orders) with their current status and trigger conditions. |
| `autotrading` | `mt5 autotrading [on|off|status]` | Enable, disable, or check the autotrading status on the MT5 terminal. When disabled, the Bridge still receives signals but does not execute them. |
| `trailing` | `mt5 trailing [on|off|status]` | View or toggle the trailing stop system. The Bridge supports `trailing_stop_enabled` (default: true), `trailing_stop_pips` (default: 50), and `trailing_activation_pips` (default: 30). |
| `trailing-config` | `mt5 trailing-config [--pips N] [--activation N]` | Configure trailing stop parameters: `--pips` sets the trailing distance in pips, `--activation` sets the minimum profit in pips before trailing activates. |
| `rate-limit` | `mt5 rate-limit [view|set --max N --burst N]` | View or configure the Redis-based rate limiting for trade execution. Default: 10 trades/min, burst: 5. Shows current utilization and remaining capacity. |

**Note**: All MONEYMAKER orders use `magic=123456` for identification. The `mt5 positions` command displays this magic number to distinguish MONEYMAKER-managed trades from manual MT5 trades. Positions with a different magic number are shown but flagged as "EXTERNAL".

### 6.3 Safety Controls

The `mt5` category implements multiple safety layers:

1. **Confirmation prompts**: `close`, `close-all`, and `modify` commands require explicit confirmation. The prompt includes the trade details (symbol, direction, volume, P&L) so the operator can verify before confirming.

2. **Kill switch integration**: Before executing any trade command, the handler checks the Redis key `moneymaker:kill_switch`. If the kill switch is active, the command is rejected with `[error] Kill switch is ACTIVE. Deactivate first with 'kill deactivate'.`

3. **Position limits**: The console enforces `MAX_POSITION_COUNT` (default: 5) and `MAX_LOT_SIZE` (default: 1.0) from `.env`. Commands that would violate these limits are rejected.

4. **Max daily loss**: The console checks `MAX_DAILY_LOSS_PCT` (default: 2.0%) before executing trades. If the day's cumulative loss exceeds this threshold, trade commands are blocked.

---

## 7. Command Category: `risk` — Risk Management Engine

### 7.1 Overview

The `risk` category provides real-time access to the MONEYMAKER risk management engine. The risk engine operates as a gating layer between the Algo Engine's signal generation and the MT5 Bridge's trade execution. Every signal must pass an **11-point validation check** (see `signals/validator.py:89-228`) before it is allowed to execute.

### 7.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `status` | `risk status` | Display the complete risk dashboard: current drawdown (daily, weekly, total), open exposure by symbol and currency pair, correlation matrix, and circuit breaker state. |
| `limits` | `risk limits` | Show all configured risk limits: max drawdown %, max daily loss %, max positions, max lot size, max exposure per symbol, max correlated exposure, and economic calendar blackout windows. |
| `set-max-dd` | `risk set-max-dd PERCENT` | Set the maximum drawdown percentage. Example: `risk set-max-dd 5.0` sets a 5% maximum drawdown from peak equity. |
| `set-max-pos` | `risk set-max-pos N` | Set the maximum number of concurrent open positions. |
| `set-max-lot` | `risk set-max-lot SIZE` | Set the maximum lot size per trade. |
| `set-daily-loss` | `risk set-daily-loss PERCENT` | Set the maximum daily loss percentage. |
| `exposure` | `risk exposure` | Display current exposure breakdown by symbol, direction, volume, and USD equivalent. Includes correlation-adjusted exposure calculations. |
| `correlation` | `risk correlation` | Display the current correlation matrix for all traded symbols. Highlights high-correlation pairs (>0.7) that increase systemic risk. |
| `kill-switch` | `risk kill-switch` | **DANGEROUS**: Activate the global kill switch. Closes ALL positions, disables autotrading, and publishes a CRITICAL alert to all notification channels. Requires confirmation. |
| `circuit-breaker` | `risk circuit-breaker [arm|disarm|status]` | Control the automatic circuit breaker. When armed, the circuit breaker automatically activates the kill switch if any risk limit is breached. |
| `validation` | `risk validation` | Display the 11-point signal validation checklist with current pass/fail status for each check: (1) HOLD direction rejection, (2) Max open positions, (3) Max drawdown, (4) Daily loss limit, (5) Min confidence threshold, (6) Stop-loss presence & positioning, (7) Risk/reward ratio, (8) Margin sufficiency, (9) Correlation exposure (if checker provided), (10) Economic calendar blackout (if filter provided), (11) Session awareness (if classifier provided). |
| `history` | `risk history [--days N]` | Display risk event history: blocked signals (with rejection reasons), kill switch activations, circuit breaker triggers, and risk limit adjustments. |
| `spiral` | `risk spiral` | Display the Spiral Protection status from the Algo Engine: consecutive loss count, cooldown state, and lot size reduction factors. |

### 7.3 Real-Time Risk Dashboard (TUI Panel)

In TUI mode, the RISK & POSITIONS panel continuously displays:
```
RISK & POSITIONS                           
  Open Pos:  3 / 5 max                    
  Exposure:  $47,250.00 (2.1x leverage)   
  Day P&L:   -$312.50 (-0.31%)            
  Max DD:    -1.2% / 5.0% limit           
  Spiral:    INACTIVE (0 consec losses)    
  Circuit:   [ARMED]                       
  Calendar:  No events next 30m           
```

---

## 8. Command Category: `signal` — Signal Pipeline Management

### 8.1 Overview

The `signal` category provides visibility into the Algo Engine's signal generation pipeline. Signals flow through a strict validation cascade before reaching the MT5 Bridge for execution. The console allows operators to inspect every stage of this cascade.

### 8.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `status` | `signal status` | Display signal pipeline status: signals generated today, signals validated/rejected, current rate (signals/hour), rate limit (max per hour), and deduplication window state. |
| `last` | `signal last [N]` | Display the last N signals (default: 5) with full details: symbol, direction, confidence score, strategy source, timestamp, validation result, and execution status. |
| `pending` | `signal pending` | Display signals currently in the validation queue waiting for risk checks. |
| `rejected` | `signal rejected [--days N]` | Display rejected signals with rejection reasons. Useful for tuning risk parameters and understanding why the system is not trading. |
| `confidence` | `signal confidence [--threshold T]` | Display the confidence distribution histogram for generated signals. Shows what percentage of signals fall below/above the current threshold (`BRAIN_CONFIDENCE_THRESHOLD`, default: 0.65). |
| `rate` | `signal rate` | Display the current signal generation rate, the configured maximum rate (`BRAIN_MAX_SIGNALS_PER_HOUR`), and a time-series sparkline of signals per hour for the last 24 hours. |
| `strategy` | `signal strategy` | Display which strategy sourced each recent signal. Distinguishes between **advisor modes** (4-tier cascade: `COPER` → `Hybrid` → `Knowledge` → `Conservative`) and **strategy types** (`StrategyType` enum: `TREND_FOLLOWING`, `MEAN_REVERSION`, `BREAKOUT`, `SCALPING`). Advisor modes determine the decision pipeline; strategy types classify the signal's market approach. |
| `validate` | `signal validate SIGNAL_ID` | Re-run the 11-point validation against a historical signal to understand why it was accepted or rejected. |
| `replay` | `signal replay SIGNAL_ID` | Replay a historical signal through the current pipeline to see how it would be processed today. Useful for backtesting configuration changes. |

### 8.3 Database Queries

Signal data is queried from the `trading_signals` and `trade_executions` tables in TimescaleDB:

```sql
-- signal last N: Recent signals
SELECT ts.id, ts.symbol, ts.direction, ts.confidence, ts.strategy_source,
       ts.created_at, ts.validation_result, te.execution_status
FROM trading_signals ts
LEFT JOIN trade_executions te ON ts.id = te.signal_id
ORDER BY ts.created_at DESC
LIMIT {n};

-- signal rejected: Rejected signals with reasons
SELECT id, symbol, direction, confidence, rejection_reason, created_at
FROM trading_signals
WHERE validation_result = 'rejected'
  AND created_at > NOW() - INTERVAL '{days} days'
ORDER BY created_at DESC;

-- signal confidence histogram
SELECT
  width_bucket(confidence, 0, 1, 20) AS bucket,
  count(*) AS cnt
FROM trading_signals
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY bucket
ORDER BY bucket;
```

---

## 9. Command Category: `market` — Market Intelligence

### 9.1 Overview

The `market` category provides real-time market intelligence derived from the Data Ingestion service and the Algo Engine's regime detection engine. This category unifies data from multiple sources to give the operator a comprehensive view of current market conditions.

### 9.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `regime` | `market regime [SYMBOL]` | Display the current market regime classification from the `RegimeType` enum: `TRENDING_UP`, `TRENDING_DOWN`, `RANGING`, `VOLATILE`, or `CRISIS`. Shows the ensemble vote from the three classifiers (Rule-based, HMM, k-Means) and the confidence of the classification. |
| `symbols` | `market symbols` | Display all monitored symbols with current regime, volatility (ATR), and trend strength (ADX). |
| `spread` | `market spread SYMBOL` | Display the current bid-ask spread for a symbol from the MT5 Bridge, along with the average spread over the last hour and the spread threshold for signal validation. |
| `calendar` | `market calendar [--days N]` | Display upcoming economic events from the economic calendar. Highlights High-Impact events that trigger blackout windows. Shows the configured blackout period (`brain_calendar_min_impact`). |
| `volatility` | `market volatility [SYMBOL]` | Display current and historical volatility metrics: ATR (14-period), Bollinger Band width, implied volatility rank, and a volatility regime classification (Low/Normal/High/Extreme). |
| `correlation` | `market correlation` | Display the cross-symbol correlation matrix. Shows Pearson correlation coefficients over the last 20 trading days. Highlights pairs with |r| > 0.7. |
| `session` | `market session` | Display current trading session from the `SessionType` enum: `ASIAN`, `LONDON`, `NEW_YORK`, `OVERLAP_LONDON_NY`, or `OFF_HOURS` — which session is currently active, time until next session transition, and typical liquidity characteristics. |
| `news` | `market news [--impact HIGH]` | Display recent and upcoming news events from the economic calendar. Filter by impact level (Low/Medium/High). |
| `indicators` | `market indicators SYMBOL` | Display the current value of all 60+ technical indicators computed by the Algo Engine for a specific symbol: RSI, EMA(12/26), MACD, Bollinger Bands, ATR(14), Stochastic, Williams %R, CCI, OBV, and more. |
| `macro` | `market macro` | Display macroeconomic indicators from the External Data service (FRED, CBOE, CFTC): VIX, DXY, US Treasury yields, unemployment rate, CPI, and CFTC positioning data for relevant futures. Data is fetched by the `external-data` service and stored in TimescaleDB + Redis. |
| `macro-status` | `market macro-status` | Display the External Data service health: last fetch timestamps for FRED (yield curve, real rates, recession probability), CBOE (VIX spot, term structure), and CFTC (COT reports). Shows data freshness and any fetch errors. |
| `dashboard` | `market dashboard` | Open the MONEYMAKER web dashboard (port 8000) in the default browser. Shows the dashboard service status and URL. |

---

## 10. Command Category: `ml` — Machine Learning (Embedded in Brain)

### 10.1 Overview

The `ml` category provides visibility into the ML training functionality that is **embedded inside the Algo Engine service** (in the `nn/` package — 35+ modules including JEPA, GNN, MLP, Shadow Engine, and RAP Coach). There is no separate ML Training Lab service — the `services/ml-training/` directory is a placeholder (commented out in `docker-compose.yml`).

All ML commands interact with:
- **TimescaleDB** — `model_registry`, `model_metrics`, and `ml_predictions` tables
- **Filesystem** — model checkpoint files on disk
- **Brain REST endpoint** — trigger training/evaluation actions
- **Prometheus metrics** — training loss, GPU utilization from the Brain's metrics port (9092)

### 10.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `start` | `ml start [--model MODEL]` | Start a training run. Optional `--model` selects the architecture: `jepa`, `gnn`, `mlp`, or `ensemble` (default). |
| `stop` | `ml stop` | Graceful stop at the next checkpoint. |
| `pause` | `ml pause` | Pause training. Model weights and optimizer state are preserved. |
| `resume` | `ml resume` | Resume training from the last checkpoint. |
| `status` | `ml status` | Display comprehensive training status: epoch, batch, loss (train/val), learning rate, GPU utilization, estimated time remaining, and model architecture summary. |
| `throttle` | `ml throttle [0.0-1.0]` | Set the training throttle. 0.0 = full speed, 1.0 = maximum delay between batches. Useful for reducing resource usage during live trading hours. |
| `eval` | `ml eval [--dataset TEST]` | Run evaluation on the test set. Reports accuracy, F1, Sharpe ratio, and maximum drawdown on backtested signals. |
| `deploy` | `ml deploy [--model-id ID]` | Deploy a trained model to the Algo Engine. The Brain will switch to Hybrid/COPER mode once the model is loaded. |
| `rollback` | `ml rollback` | Roll back to the previous deployed model version. |
| `checkpoints` | `ml checkpoints` | List all saved model checkpoints with timestamps, validation loss, and disk size. |
| `metrics` | `ml metrics` | Display training metrics history: loss curves, learning rate schedule, gradient norms, and validation metrics over the last N epochs. |
| `hyperparams` | `ml hyperparams` | Display current hyperparameter configuration: learning rate, batch size, optimizer, weight decay, dropout rate, attention heads (for transformer architectures), and data window size. |
| `dataset` | `ml dataset` | Display training dataset statistics: number of samples, date range, feature dimensions, label distribution (buy/sell/hold), and train/val/test split sizes. |
| `shadow` | `ml shadow` | Display Shadow Engine status. The Shadow Engine runs new model predictions alongside the active model without executing trades, measuring prediction agreement and potential improvement. |

---

## 11. Command Category: `test` — Test Suite Orchestration

### 11.1 Overview

The `test` category orchestrates the full test suite across all services. Tests are executed as subprocesses, with output streaming to the console in real time (using `_run_tool_live`). The console correctly sets `PYTHONPATH` and working directory for each test runner.

### 11.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `all` | `test all` | Run the complete pytest suite for the Algo Engine service (316+ tests). Executes in `services/algo-engine/` with PYTHONPATH set to `services/algo-engine/src/`. |
| `brain-verify` | `test brain-verify` | Run the Brain Verification test suite from `tests/brain_verification/`. These tests validate the cascade logic, regime detection, and signal pipeline integrity. |
| `cascade` | `test cascade` | Run the end-to-end cascade tests from `tests/test_cascade/`. These tests simulate a complete signal flow from data receipt to trade execution. |
| `go` | `test go` | Run the Go test suite for the Data Ingestion service. Executes `go test ./...` in `services/data-ingestion/`. |
| `mt5` | `test mt5` | Run the MT5 Bridge test suite from `services/mt5-bridge/tests/`. |
| `common` | `test common` | Run the shared Python library tests from `shared/python-common/tests/`. |
| `suite` | `test suite` | Run ALL test suites sequentially (Algo Engine + Go + MT5 + Common). Displays a summary table at the end with pass/fail for each suite. |
| `lint` | `test lint` | Run linting tools: `ruff check` and `black --check` for Python, `golangci-lint run` for Go. Equivalent to `make lint`. |
| `typecheck` | `test typecheck` | Run mypy type checking on Algo Engine and shared library source code. Equivalent to `make typecheck`. |
| `ci` | `test ci` | Run the full CI pipeline: lint → typecheck → test → docker-build. Equivalent to `make ci`. |
| `coverage` | `test coverage` | Run pytest with coverage reporting. Displays a coverage summary table and writes an HTML report to `htmlcov/`. |
| `specific` | `test specific PATH` | Run a specific test file or directory. Example: `test specific tests/test_cascade/test_full_flow.py`. |

---

## 12. Command Category: `build` — Build and Container Management

### 12.1 Overview

The `build` category wraps Docker Compose build operations for individual and multi-service container builds. It also supports incremental builds with build-cache awareness, parallel builds for faster iteration, and automatic tagging with git commit hashes. This category is designed primarily for development and staging environments; production deployments should use the CI/CD pipeline.

### 12.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `all` | `build all [--no-cache]` | Build all Docker images for the MONEYMAKER ecosystem. Runs `docker compose build` from the project root. The `--no-cache` flag forces a full rebuild from scratch without using cached layers. |
| `brain` | `build brain [--no-cache]` | Build only the Algo Engine Docker image (`moneymaker-algo-engine`). Builds from `services/algo-engine/Dockerfile`. |
| `ingestion` | `build ingestion [--no-cache]` | Build only the Data Ingestion Docker image (`moneymaker-data-ingestion`). Multi-stage Go build from `services/data-ingestion/Dockerfile`. |
| `bridge` | `build bridge [--no-cache]` | Build only the MT5 Bridge Docker image (`moneymaker-mt5-bridge`). Builds from `services/mt5-bridge/Dockerfile`. |
| `dashboard` | `build dashboard [--no-cache]` | Build the Dashboard Docker image (`moneymaker-dashboard`). Includes FastAPI backend and React frontend. |
| `external` | `build external [--no-cache]` | Build the External Data service Docker image from `services/external-data/Dockerfile`. |
| `test-only` | `build test-only` | Run all test suites without building Docker images. Equivalent to `test suite`. Useful for rapid validation. |
| `proto` | `build proto` | Recompile all Protocol Buffer definitions from `shared/proto/`. Generates Python stubs in `shared/proto/gen/python/` and Go stubs in `shared/proto/gen/go/`. Equivalent to `make proto`. |
| `status` | `build status` | Display the build status of all Docker images: tag, size, creation date, and whether the image is up-to-date with the current source code (compares git hash). |
| `clean` | `build clean` | Remove build artifacts: `services/data-ingestion/bin/`, all `__pycache__` directories, and `.pyc` files. Optionally prune Docker build caches with `--docker` flag. Equivalent to `make clean`. |
| `push` | `build push [SERVICE]` | Push built Docker images to the configured container registry. Primarily for staging/production deployment pipelines. |
| `tag` | `build tag VERSION` | Tag all Docker images with a specific version string (e.g., `v1.2.3`). Uses the git commit hash as a secondary tag for traceability. |

### 12.3 Build Orchestration

The `build all` command orchestrates builds in dependency order:

1. `shared/proto` — Protocol Buffer compilation (must happen first)
2. `shared/python-common` — Shared Python library (dependency for Brain, Bridge)
3. `services/data-ingestion` — Go binary build + Docker image
4. `services/algo-engine` — Python Docker image (depends on python-common; includes embedded ML training)
5. `services/mt5-bridge` — Python Docker image (depends on python-common)
6. `services/external-data` — Python Docker image
7. `services/dashboard` — Python + JS Docker image

Each build step displays real-time output via `_run_tool_live()` and records the exit code for the final summary table.

---

## 13. Command Category: `sys` — System Operations

### 13.1 Overview

The `sys` category provides comprehensive system-level visibility into the health and resource utilization of the MONEYMAKER infrastructure. It bridges the gap between individual service status checks and whole-ecosystem observability by aggregating information from Docker, PostgreSQL, Redis, Prometheus, and the operating system.

### 13.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `status` | `sys status` | Display the full system status dashboard: all Docker container states, database connectivity, Redis connectivity, Prometheus/Grafana availability, and ZMQ publisher status. This is the single most important diagnostic command. |
| `resources` | `sys resources` | Display CPU utilization (system-wide and per-core), RAM usage (process and system), disk usage (root partition and data partition), GPU status (AMD ROCm if available), and network I/O counters. Uses `psutil` for cross-platform compatibility. |
| `health` | `sys health` | Execute a comprehensive health check across all infrastructure components: PostgreSQL (`SELECT 1`), Redis (`PING`), Docker (`docker info`), ZMQ publisher (subscribe for 1 tick), Prometheus (`/api/v1/status/buildinfo`), and Grafana (`/api/health`). Returns OK/ERRORE/NON CONNESSO for each. |
| `db` | `sys db` | Display TimescaleDB status: PostgreSQL version, database size, active connections by state, table sizes (market_ticks, ohlcv_bars, trading_signals, trade_executions, model_registry), and hypertable chunk count. |
| `redis` | `sys redis` | Display Redis status: version, uptime, memory usage (used_memory_human), number of keys per database, pub/sub channels, connected clients, and last save time. |
| `docker` | `sys docker` | Display Docker Compose status for all services: container name, state, ports, CPU/memory usage, and uptime. Runs `docker compose ps --format table`. |
| `network` | `sys network` | Display network diagnostics: REST endpoint reachability (Brain:8082, Data:8081, Dashboard:8000), gRPC reachability (MT5:50055), ZMQ socket status (PUB:5555), inter-service latency estimates, and TLS certificate expiration dates. |
| `env` | `sys env [--show-secrets]` | Display all environment variables relevant to MONEYMAKER operation. By default, secrets are masked. The `--show-secrets` flag reveals full values (requires confirmation for safety). |
| `ports` | `sys ports` | Display the port allocation table for all services, checking for conflicts. Cross-references with actual listening ports via `ss -tlnp` or `netstat -tlnp`. |
| `uptime` | `sys uptime` | Display uptime statistics for all services: time since last restart, total uptime percentage over the last 7 days, and number of restarts. Data sourced from Docker inspect. |
| `audit` | `sys audit` | Run a comprehensive system audit: check for known vulnerable dependencies, verify file permissions on `.env` and certificate files, validate TLS configuration, and check docker-compose security best practices. |
| `gpu` | `sys gpu` | Display AMD GPU status via `rocm-smi`: temperature, utilization, VRAM usage, clock speeds, and fan speed. Reports "ROCm not available" if the AMD driver is not installed. |
| `disk` | `sys disk` | Display detailed disk usage: space consumed by each service directory, database files, log files, Docker images, and model checkpoints. Identifies the largest space consumers. |

### 13.3 Health Check Implementation

The `sys health` command executes checks in parallel using `concurrent.futures.ThreadPoolExecutor` to minimize total execution time. Each check has a 5-second timeout:

```python
import concurrent.futures

def _sys_health(*args):
    checks = {
        "PostgreSQL": _check_postgres,
        "Redis": _check_redis,
        "Docker": _check_docker,
        "Prometheus": _check_prometheus,
        "Grafana": _check_grafana,
        "ZMQ Publisher": _check_zmq,
        "Algo Engine (REST:8082)": _check_brain_rest,
        "MT5 Bridge (gRPC)": _check_mt5_grpc,
        "Data Ingestion (HTTP:8081)": _check_data_http,
        "Dashboard (REST:8000)": _check_dashboard_rest,
    }
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as executor:
        futures = {
            executor.submit(fn): name
            for name, fn in checks.items()
        }
        for future in concurrent.futures.as_completed(futures, timeout=10):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = "ERRORE"
    return _format_health_table(results)
```

---

## 14. Command Category: `config` — Configuration Management

### 14.1 Overview

The `config` category manages the MONEYMAKER ecosystem configuration stored in the `.env` file and per-service YAML configuration files in `configs/development/` and `configs/production/`. It provides safe read/write access to configuration values with validation, secret masking, and environment-aware defaults.

### 14.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `view` | `config view [--category CAT]` | Display all configuration values from `.env`, with secrets masked. Optionally filter by category: `db`, `redis`, `brain`, `mt5`, `risk`, `api`, `tls`, `zmq`. |
| `validate` | `config validate` | Validate the current configuration against required variables. Checks that all REQUIRED variables in `.env.example` have non-empty values. Reports MISSING, OK, or WARNING for each. |
| `set` | `config set KEY VALUE` | Set a configuration value in the `.env` file. The key must be in the allowed list (validated against `.env.example`). Sensitive values (containing KEY, SECRET, PASSWORD, TOKEN) are masked in the confirmation output. |
| `get` | `config get KEY` | Retrieve the value of a single configuration key. Secrets are masked unless `--reveal` flag is provided (requires confirmation). |
| `diff` | `config diff` | Compare the current `.env` file against `.env.example` to identify missing keys, extra keys, and changed default values. |
| `broker` | `config broker KEY` | Set the broker API key. Shortcut for `config set POLYGON_API_KEY <KEY>`. |
| `risk` | `config risk KEY VALUE` | Set a risk-related configuration parameter. Shortcut for setting `BRAIN_MAX_*` and `MAX_*` variables. Validates that the value is within acceptable bounds. |
| `reload` | `config reload` | Force a hot-reload of configuration by re-reading the `.env` file and applying changes to running services via their REST endpoints or Docker restart. Not all services support hot-reload; those that don't will require a restart. |
| `export` | `config export [--format yaml|json]` | Export the current configuration (with secrets masked) to stdout in the specified format. Useful for documentation and change tracking. |
| `import` | `config import FILE` | Import configuration from a YAML or JSON file. Merges with existing `.env` values. Requires confirmation for each changed key. |
| `template` | `config template [--env ENV]` | Generate a clean `.env` file from the `.env.example` template, pre-filled with environment-specific defaults (development vs. production). |
| `encrypt` | `config encrypt` | Encrypt the `.env` file using a master passphrase stored in the system keyring. Produces `.env.enc` for safe storage in version control. |
| `decrypt` | `config decrypt` | Decrypt `.env.enc` back to `.env` using the master passphrase from the system keyring. |

### 14.3 Allowed Configuration Keys

To prevent accidental misconfiguration, the `config set` command validates keys against a whitelist derived from `.env.example`. The whitelist is grouped into categories:

- **Database**: `MONEYMAKER_DB_HOST`, `MONEYMAKER_DB_PORT`, `MONEYMAKER_DB_NAME`, `MONEYMAKER_DB_USER`, `MONEYMAKER_DB_PASSWORD`
- **Redis**: `MONEYMAKER_REDIS_HOST`, `MONEYMAKER_REDIS_PORT`, `MONEYMAKER_REDIS_PASSWORD`
- **Brain**: `BRAIN_CONFIDENCE_THRESHOLD`, `BRAIN_MAX_SIGNALS_PER_HOUR`, `BRAIN_MAX_OPEN_POSITIONS`, etc.
- **MT5**: `MT5_ACCOUNT`, `MT5_PASSWORD`, `MT5_SERVER`, `MT5_TIMEOUT_MS`
- **Risk**: `MAX_POSITION_COUNT`, `MAX_LOT_SIZE`, `MAX_DAILY_LOSS_PCT`, `MAX_DRAWDOWN_PCT`
- **API Keys**: `POLYGON_API_KEY`, `MONEYMAKER_BINANCE_API_KEY`, `MONEYMAKER_BINANCE_API_SECRET`, etc.
- **TLS**: `MONEYMAKER_TLS_ENABLED`, `MONEYMAKER_TLS_CA_CERT`

---

## 15. Command Category: `svc` — Service Lifecycle Management

### 15.1 Overview

The `svc` category provides high-level lifecycle management for all Docker-based microservices. It wraps `docker compose` commands with additional intelligence: dependency-aware startup ordering, health check verification, log aggregation, and resource scaling.

### 15.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `up` | `svc up [SERVICE...]` | Start all services (or specific services) using `docker compose up -d`. Starts in dependency order: database → Redis → data-ingestion → algo-engine → mt5-bridge → monitoring. |
| `down` | `svc down [SERVICE...]` | Stop all services (or specific services) using `docker compose down`. Graceful shutdown with configurable timeout. |
| `restart` | `svc restart SERVICE` | Restart a specific service. Performs `docker compose restart <service>` and waits for the health check to pass. |
| `status` | `svc status` | Display the status of all Docker Compose services: container name, state (running/stopped/restarting), health (healthy/unhealthy), ports, CPU%, memory usage, and uptime. |
| `logs` | `svc logs SERVICE [--follow] [--tail N]` | Display logs for a specific service. Default: last 50 lines. The `--follow` flag streams logs in real-time (equivalent to `-f`). |
| `scale` | `svc scale SERVICE N` | Scale a service to N replicas. Useful for load-testing or running multiple data ingestion instances for different markets. |
| `exec` | `svc exec SERVICE COMMAND` | Execute a command inside a running service container. Example: `svc exec algo-engine bash` opens a shell in the Brain container. |
| `inspect` | `svc inspect SERVICE` | Display detailed container inspection data: image, volumes, networks, environment variables (masked), resource limits, and restart policy. |
| `pull` | `svc pull [SERVICE...]` | Pull the latest Docker images from the registry for all or specific services. |
| `prune` | `svc prune` | Remove stopped containers, unused images, and dangling volumes. Requires confirmation. Frees disk space. |
| `compose-config` | `svc compose-config` | Display the effective Docker Compose configuration after variable interpolation. Useful for debugging environment variable resolution. |
| `health` | `svc health [SERVICE]` | Run the Docker health check for a specific service or all services. Reports healthy/unhealthy with the last health check output. |

### 15.3 Dependency-Aware Startup

The `svc up` command implements intelligent startup ordering based on the MONEYMAKER service dependency graph:

```
Level 0 (infrastructure): postgres, redis
Level 1 (data layer):     data-ingestion
Level 2 (intelligence):   algo-engine, external-data
Level 3 (execution):      mt5-bridge
Level 4 (frontend):       dashboard
Level 5 (monitoring):     prometheus, grafana
```

**Note**: ML training is embedded in the Algo Engine service (no separate `ml-training` container). Docker Compose commands use `-f infra/docker/docker-compose.yml` from the `program/` project root.

Each level waits for the previous level's services to report "healthy" before starting. The health check poll interval is 2 seconds with a maximum wait of 60 seconds per level.

---

## 16. Command Category: `maint` — Maintenance and Database Operations

### 16.1 Overview

The `maint` category provides database maintenance, data lifecycle management, and system housekeeping operations. These commands are typically run during off-market hours or scheduled maintenance windows.

### 16.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `vacuum` | `maint vacuum` | Run PostgreSQL `VACUUM ANALYZE` on all tables. Reclaims disk space and updates query planner statistics. Typically runs in 1-5 minutes depending on database size. |
| `reindex` | `maint reindex` | Rebuild all database indexes. Fixes index bloat and improves query performance. Runs `REINDEX DATABASE moneymaker_brain`. Requires `autocommit = True` on the connection. |
| `clear-cache` | `maint clear-cache [--redis]` | Remove all `__pycache__` directories and `.pytest_cache` directories from the project tree. Optionally flush Redis cache with `--redis` flag. |
| `retention` | `maint retention` | Display data retention policies: how long each table's data is kept before automatic pruning (trade_executions: 730 days, trading_signals: 730 days, strategy_performance: 365 days, market_ticks: configurable, ohlcv_bars: configurable). |
| `backup` | `maint backup [--compress]` | Create a full database backup using `pg_dump`. Saves to `logs/moneymaker_backup_YYYYMMDD_HHMMSS.sql`. The `--compress` flag produces a `.sql.gz` file using gzip compression. |
| `restore` | `maint restore FILE` | Restore a database from a backup file. **DANGEROUS**: Requires confirmation. Drops and recreates all tables. |
| `prune-old` | `maint prune-old DAYS [--dry-run]` | Delete data older than DAYS from drift logs and performance snapshots. The `--dry-run` flag shows what would be deleted without actually deleting. Requires confirmation unless `--dry-run`. |
| `migrate` | `maint migrate [--dry-run]` | Run pending database migrations (Alembic or custom SQL scripts). The `--dry-run` flag shows the migration SQL without executing. |
| `table-sizes` | `maint table-sizes` | Display the size of every table in the database, sorted by size descending. Includes index size and total relations size. |
| `chunk-stats` | `maint chunk-stats` | Display TimescaleDB hypertable chunk statistics: number of chunks per table, chunk intervals, oldest/newest chunk, and compression status. |
| `compress` | `maint compress [--older-than DAYS]` | Enable TimescaleDB native compression on eligible chunks. Compresses chunks older than DAYS (default: 30). Can achieve 10-20x compression on market tick data. |
| `dead-code` | `maint dead-code` | Run dead code detection across the Python codebase. Uses `vulture` or a custom AST analyzer to find unused functions, imports, and variables. |
| `sanitize` | `maint sanitize [-y]` | Run project sanitization: remove temporary files, fix file permissions, validate directory structure, and check for committed secrets. |
| `integrity` | `maint integrity` | Verify database integrity: check foreign key constraints, validate SHA-256 audit hash chains on trade records, and detect orphaned records. |

### 16.3 Automated Maintenance Schedule

The console can be integrated with `cron` for automated maintenance via CLI mode:

```cron
# Daily at 3 AM: VACUUM and retention pruning
0 3 * * * /usr/bin/python /path/to/moneymaker_console.py maint vacuum
5 3 * * * /usr/bin/python /path/to/moneymaker_console.py maint prune-old 90

# Weekly on Sunday at 4 AM: full backup and reindex
0 4 * * 0 /usr/bin/python /path/to/moneymaker_console.py maint backup --compress
30 4 * * 0 /usr/bin/python /path/to/moneymaker_console.py maint reindex

# Monthly: TimescaleDB compression
0 5 1 * * /usr/bin/python /path/to/moneymaker_console.py maint compress --older-than 60
```

---

## 17. Command Category: `kill` — Emergency Kill Switch

### 17.1 Overview

The `kill` category provides manual control over the MONEYMAKER global kill switch. The kill switch is a Redis-backed emergency mechanism that immediately halts all trading activity. When activated, it:

1. Sets the Redis key `moneymaker:kill_switch` with a JSON payload containing the activation timestamp and reason.
2. Publishes a `CRITICAL` alert on the `moneymaker:alerts` Redis pub/sub channel.
3. The Algo Engine, upon reading this key, stops emitting new signals.
4. The MT5 Bridge, upon reading this key, closes all open positions (if `auto_close_on_kill` is enabled).
5. The Dashboard displays a red KILL SWITCH ACTIVE banner.

### 17.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `status` | `kill status` | Check the current kill switch state. Returns either `[ACTIVE] Kill switch active. Reason: ...` or `[INACTIVE] Kill switch not active. Trading allowed.` |
| `activate` | `kill activate [REASON...]` | **DANGEROUS**: Activate the kill switch with an optional reason. If no reason is provided, defaults to "Manual activation from console". Requires confirmation. Publishes CRITICAL alert via Redis pub/sub. |
| `deactivate` | `kill deactivate` | Deactivate the kill switch. Removes the Redis key and publishes an INFO alert that trading has been restored. Requires confirmation. |
| `history` | `kill history [--days N]` | Display the kill switch activation/deactivation history from the console logs. Shows timestamp, reason, operator, and duration of each activation. |
| `test` | `kill test` | Test the kill switch mechanism without actually activating it. Verifies Redis connectivity, pub/sub delivery, and that all services are subscribed to the alert channel. Returns a test report. |

### 17.3 Redis Kill Switch Protocol

The kill switch uses a simple Redis key/value protocol:

```json
// Key: moneymaker:kill_switch
{
    "active": true,
    "reason": "Market flash crash detected — manual intervention",
    "activated_at": 1709784000.123,
    "activated_by": "console_operator",
    "auto_close_positions": true
}
```

All services poll this key every 1 second. When the key is set, services enter a safe mode where no new trades are opened and (optionally) existing positions are closed.

---

## 18. Command Category: `audit` — Security and Compliance Audit

### 18.1 Overview

The `audit` category provides comprehensive security auditing capabilities for the MONEYMAKER ecosystem. These commands verify that the system meets security best practices for financial trading applications: credential management, TLS configuration, Docker security, dependency vulnerabilities, and audit trail integrity.

### 18.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `security` | `audit security` | Run a full security audit: check `.env` file permissions (should be 600), verify no secrets are committed to git, validate TLS certificates, check Docker security (no `--privileged`, no root users), and verify Redis is password-protected. |
| `secrets` | `audit secrets [--deep]` | Scan the repository for committed secrets: API keys, passwords, tokens, and private keys. Uses regex pattern matching against common secret formats. The `--deep` flag scans git history. |
| `tls` | `audit tls` | Verify TLS configuration: check certificate validity dates, verify CA chain trust, check cipher suite strength, and report days until certificate expiration for each service. |
| `dependencies` | `audit dependencies` | Scan all Python and Go dependencies for known vulnerabilities. Uses `pip-audit` for Python and `govulncheck` for Go. Reports CVE IDs, severity, and recommended upgrade versions. |
| `permissions` | `audit permissions` | Check file and directory permissions on sensitive files: `.env`, certificate files, private keys, database backup files, and log files. Flags overly permissive permissions. |
| `docker` | `audit docker` | Audit Docker configuration: check for `--privileged` containers, verify no root user execution, validate read-only filesystem mounts, check resource limits, and verify network isolation. |
| `hashchain` | `audit hashchain` | Verify the SHA-256 hash chain on the `trade_records` table. Each trade record includes a hash of the previous record plus its own data, creating an immutable audit trail. This command verifies the chain is unbroken. |
| `compliance` | `audit compliance` | Generate a compliance report summarizing: audit trail integrity, data retention compliance, credential management status, TLS status, and access control configuration. Suitable for regulatory review. |
| `env` | `audit env` | Audit the `.env` file specifically: check that all REQUIRED variables are set, passwords meet minimum length (16 characters), no default values are used in production, and sensitive variables are not logged in plaintext. |
| `report` | `audit report [--format md|json]` | Generate a comprehensive audit report combining all audit sub-commands. Output as Markdown or JSON. Saved to `AUDIT_REPORTS/audit_YYYYMMDD_HHMMSS.md`. |

### 18.3 Hash Chain Verification

The audit hash chain is implemented in `moneymaker_common.audit_pg.PostgresAuditTrail`, which uses a buffered approach with `asyncpg`. The hash chain links audit log entries (not trade records directly) using SHA-256:

```python
# Actual implementation uses PostgresAuditTrail from moneymaker_common.audit_pg
# Hash chain is maintained on the audit_log table with buffered inserts
record_hash = sha256(previous_hash + serialized_audit_entry)
```

The `audit hashchain` command:
1. Fetches all audit log entries ordered by sequence ASC
2. Recomputes each hash based on the previous entry's hash and the serialized audit data
3. Compares the recomputed hash with the stored hash
4. Reports any mismatches (indicating tampered or corrupted audit entries)

A healthy hash chain produces: `[success] Hash chain verified: 1,247 entries, 0 mismatches.`

---

## 19. Command Category: `perf` — Performance Analytics

### 19.1 Overview

The `perf` category provides historical trading performance analytics directly from the console. It queries TimescaleDB for trade records and computes standard quantitative finance metrics: Sharpe ratio, win rate, profit factor, maximum drawdown, and P&L attribution by symbol, strategy, and time period.

### 19.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `summary` | `perf summary [--days N]` | Display a comprehensive performance summary for the last N days (default: 30): total P&L, win rate, average win/loss, largest win/loss, Sharpe ratio, Sortino ratio, profit factor, maximum drawdown, recovery period, and total trades. |
| `daily` | `perf daily [--days N]` | Display daily P&L for the last N trading days. Includes a sparkline chart and highlights the best/worst days. |
| `weekly` | `perf weekly [--weeks N]` | Display weekly P&L with cumulative equity curve. |
| `monthly` | `perf monthly [--months N]` | Display monthly P&L table with strategy-level breakdown. |
| `by-symbol` | `perf by-symbol [--days N]` | Display P&L breakdown by traded symbol. Shows which symbols are profitable and which are losing. |
| `by-strategy` | `perf by-strategy [--days N]` | Display P&L breakdown by advisor mode (COPER, Hybrid, Knowledge, Conservative) and by strategy type (`TREND_FOLLOWING`, `MEAN_REVERSION`, `BREAKOUT`, `SCALPING`). |
| `by-session` | `perf by-session [--days N]` | Display P&L breakdown by trading session (`ASIAN`, `LONDON`, `NEW_YORK`, `OVERLAP_LONDON_NY`, `OFF_HOURS`). Identifies which sessions are most and least profitable. |
| `by-regime` | `perf by-regime [--days N]` | Display P&L breakdown by market regime at time of trade entry (`TRENDING_UP`, `TRENDING_DOWN`, `RANGING`, `VOLATILE`, `CRISIS`). |
| `drawdown` | `perf drawdown [--days N]` | Display the drawdown curve: current drawdown from peak, maximum drawdown, average drawdown, and time spent in drawdown states. |
| `equity` | `perf equity [--days N]` | Display the equity curve as an ASCII chart (using Rich's built-in rendering). Shows equity at each trade close. |
| `trades` | `perf trades [--days N] [--symbol S]` | List individual trades with full details: entry/exit time, symbol, direction, volume, entry/exit price, P&L, commission, and swap. |
| `expectancy` | `perf expectancy` | Calculate and display system expectancy: (Win Rate × Average Win) - (Loss Rate × Average Loss). A positive expectancy indicates a profitable system. |
| `risk-adjusted` | `perf risk-adjusted` | Display risk-adjusted return metrics: Sharpe ratio, Sortino ratio, Calmar ratio, Information ratio, and MAR ratio. Includes confidence intervals. |
| `correlation-pnl` | `perf correlation-pnl` | Analyze correlation between P&L streams of different symbols. Reports diversification benefit and identifies symbols whose P&L is negatively correlated (good for portfolio construction). |

### 19.3 SQL Queries for Performance Analytics

Performance analytics rely on efficient TimescaleDB queries:

```sql
-- perf summary: Core metrics (uses trade_executions table)
WITH trades AS (
    SELECT
        te.id, te.symbol, te.direction, ts.confidence,
        te.pnl, te.commission, te.swap,
        te.opened_at, te.closed_at,
        ts.strategy_source, ts.regime_at_entry
    FROM trade_executions te
    JOIN trading_signals ts ON te.signal_id = ts.id
    WHERE te.closed_at IS NOT NULL
      AND te.closed_at > NOW() - INTERVAL '{days} days'
)
SELECT
    count(*) AS total_trades,
    sum(pnl) AS total_pnl,
    avg(CASE WHEN pnl > 0 THEN pnl END) AS avg_win,
    avg(CASE WHEN pnl < 0 THEN pnl END) AS avg_loss,
    count(CASE WHEN pnl > 0 THEN 1 END)::float /
        NULLIF(count(*), 0) AS win_rate,
    sum(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) /
        NULLIF(abs(sum(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)), 0)
        AS profit_factor
FROM trades;

-- perf daily: Daily P&L
SELECT
    date_trunc('day', closed_at) AS trade_date,
    sum(pnl) AS daily_pnl,
    count(*) AS trades
FROM trade_executions
WHERE closed_at IS NOT NULL
  AND closed_at > NOW() - INTERVAL '{days} days'
GROUP BY trade_date
ORDER BY trade_date;
```

---

## 20. Command Category: `portfolio` — Portfolio Management

### 20.1 Overview

The `portfolio` category provides real-time portfolio analysis and optimization tools. It combines open position data from the MT5 Bridge with historical performance data from TimescaleDB to give the operator a complete view of portfolio composition, risk allocation, and optimization opportunities.

### 20.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `overview` | `portfolio overview` | Display the current portfolio overview: total equity, open P&L, margin utilization, number of positions by symbol and direction, and overall portfolio beta to major indices. |
| `allocation` | `portfolio allocation` | Display current capital allocation by symbol, strategy, and direction. Shows percentage of equity allocated to each position and identifies concentration risk. |
| `heat-map` | `portfolio heat-map` | Display an ASCII heat map of position P&L by symbol and time. Uses colored blocks (green for profit, red for loss) to visualize which positions are performing well. |
| `optimize` | `portfolio optimize` | Suggest portfolio rebalancing actions based on Modern Portfolio Theory (MPT): optimal position sizing using the Markowitz mean-variance framework, adjusted for the current correlation matrix and risk tolerance. |
| `var` | `portfolio var [--confidence 95]` | Calculate Value at Risk (VaR) for the current portfolio at the specified confidence level (default: 95%). Uses historical simulation with 252-day rolling window. Reports daily VaR in USD and as a percentage of equity. |
| `cvar` | `portfolio cvar [--confidence 95]` | Calculate Conditional Value at Risk (CVaR / Expected Shortfall) — the expected loss in the worst (1-confidence)% of scenarios. More conservative than VaR. |
| `stress-test` | `portfolio stress-test [--scenario SCENARIO]` | Run stress tests against predefined scenarios: `flash-crash` (-5% in 1 minute), `rate-hike` (sudden interest rate increase), `correlation-break` (historical correlations collapse), `liquidity-dry` (spreads widen 10x). Reports estimated portfolio impact. |
| `compare` | `portfolio compare [--days N]` | Compare current portfolio performance against benchmarks: S&P 500, risk-free rate, buy-and-hold for each symbol, and a balanced 60/40 portfolio. |

---

## 21. Command Category: `alert` — Alerting and Notification System

### 21.1 Overview

The `alert` category manages the MONEYMAKER alerting and notification system. Alerts can be delivered via multiple channels: Telegram bot, email, Redis pub/sub, console log, and system notifications. The console allows operators to configure alert rules, test delivery channels, and review alert history.

### 21.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `status` | `alert status` | Display the current alerting system status: configured channels, delivery success rates, pending alerts in queue, and last alert sent. |
| `channels` | `alert channels` | List all configured notification channels with their status (active/inactive), delivery success rate, and last test timestamp. |
| `test` | `alert test [CHANNEL]` | Send a test alert to a specific channel or all channels. Verifies end-to-end delivery. |
| `rules` | `alert rules` | List all configured alert rules: condition, severity level, target channels, cooldown period, and whether the rule is currently active. |
| `add-rule` | `alert add-rule CONDITION SEVERITY` | Add a new alert rule. Example: `alert add-rule "drawdown > 3%" critical --channel telegram`. |
| `remove-rule` | `alert remove-rule RULE_ID` | Remove an alert rule by ID. |
| `history` | `alert history [--days N] [--severity SEV]` | Display alert history: timestamp, severity, message, channel, and delivery status. Filter by severity (info/warning/critical). |
| `mute` | `alert mute [MINUTES]` | Mute all non-critical alerts for N minutes (default: 60). Critical alerts (kill switch, max drawdown) are never muted. |
| `unmute` | `alert unmute` | Unmute alerts immediately. |
| `telegram` | `alert telegram [--bot-token TOKEN] [--chat-id ID]` | Configure or test the Telegram notification channel. If arguments are provided, sets the bot token and chat ID. If no arguments, sends a test message. |

---

## 22. Command Category: `log` — Logging and Observability

### 22.1 Overview

The `log` category provides centralized access to logs produced by all MONEYMAKER services. It aggregates Docker container logs, console command logs, and application-specific log files into a unified interface.

### 22.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `view` | `log view [SERVICE] [--tail N]` | View recent log entries for a specific service or all services. Default: last 50 lines. Sources logs from Docker containers. |
| `console` | `log console [--days N]` | View the console's own structured JSON log file for today or the last N days. Shows all executed commands with timestamps. |
| `search` | `log search QUERY [--service S]` | Search logs for a specific text pattern across all services. Uses `docker logs` with grep or searches local log files. |
| `errors` | `log errors [--service S] [--days N]` | Display only ERROR-level log entries across all services. Highlights stack traces and exception messages. |
| `export` | `log export SERVICE --from FROM --to TO --output FILE` | Export logs for a specific service within a time range to a file. Useful for post-incident analysis and sharing with support. |
| `rotate` | `log rotate` | Trigger log rotation: archive old log files, compress them with gzip, and delete files older than the retention period (default: 30 days). |
| `level` | `log level SERVICE LEVEL` | Change the log level for a running service (DEBUG/INFO/WARNING/ERROR). Applies via REST config hot-reload if supported, otherwise requires service restart. |
| `metrics` | `log metrics` | Display log volume metrics: lines per minute per service, error rate trends, and disk space consumed by logs. |

---

## 23. Command Category: `tool` — Utility Tools

### 23.1 Overview

The `tool` category provides miscellaneous utility commands that do not fit neatly into other categories. These are convenience tools for operators and developers.

### 23.2 Sub-Commands

| Sub-Command | Syntax | Description |
|-------------|--------|-------------|
| `list` | `tool list` | List all registered commands across all categories with their help text. Comprehensive command reference. |
| `logs` | `tool logs` | Shortcut for viewing the most recent console log file. Shows the last 20 JSON log entries. |
| `env-check` | `tool env-check` | Quick check that the Python environment has all required dependencies installed. Reports missing or outdated packages. |
| `shell` | `tool shell SERVICE` | Open an interactive Python shell (IPython if available) with pre-loaded connections to databases and service clients. Useful for ad-hoc queries and debugging. |
| `sql` | `tool sql QUERY` | Execute a raw SQL query against TimescaleDB and display results in a Rich table. **DANGEROUS**: SELECT-only queries are allowed by default; DML requires `--unsafe` flag. |
| `redis-cli` | `tool redis-cli COMMAND` | Execute a Redis command and display the result. Example: `tool redis-cli GET moneymaker:kill_switch`. |
| `benchmark` | `tool benchmark` | Run a quick benchmark of console-to-service communication latency: gRPC call time, Redis ping time, Postgres query time, and ZMQ subscribe latency. |
| `version` | `tool version` | Display version information for all MONEYMAKER components: console version, Python version, Docker version, Go version, PostgreSQL version, and Redis version. |
| `whoami` | `tool whoami` | Display the current operator identity: system username, MT5 account number, environment (dev/staging/prod), and console session start time. |
| `motd` | `tool motd` | Display the Message of the Day: system status summary, overnight events, pending alerts, and today's economic calendar highlights. Designed to be the first command an operator runs each morning. |

---

## 24. TUI Dashboard — Rich Interactive Interface

### 24.1 Layout Architecture

The TUI dashboard uses Rich's `Layout` system to create an 8-panel split-screen interface. The layout is structured as follows:

```
┌─────────────────────────────────────────────────────────┐
│                     HEADER (3 rows)                     │
│  MONEYMAKER TRADING CONSOLE v2.0  |  2026-03-07 04:15:00  │
│  [MT5: CONNECTED] [Data: STREAMING] [Brain: ACTIVE]    │
├──────────────────────┬──────────────────────────────────┤
│   MARKET DATA        │        AI BRAIN                  │
│   Symbols: 6 active  │  State:  TRAINING (Hybrid)      │
│   Regime:  TREND_UP  │  Epoch:  142 / 500              │
│   Last:    1.08542   │  Loss:   0.0234                 │
│   Spread:  1.2 pips  │  LR:     0.0001                 │
│   Session: LONDON    │  Drift:  NORMAL (z=0.4)         │
├──────────────────────┤  Maturity: MATURE (1.0x)→FULL   │
│   RISK & POSITIONS   ├──────────────────────────────────┤
│   Open: 3 / 5 max    │        SYSTEM                   │
│   Exposure: $47,250  │  CPU:    23%                    │
│   Day P&L: -$312.50  │  RAM:    4.2 / 16.0 GB         │
│   Max DD:  -1.2%/5%  │  GPU:    AMD RX 9070 XT (42°C) │
│   Spiral:  INACTIVE  │  DB:     OK (142 MB)            │
│   Circuit: [ARMED]   │  Redis:  OK (23 MB, 1,247 keys)│
│   Calendar: Clear    │  Disk:   47% used               │
├──────────────────────┴──────────────────────────────────┤
│                    COMMAND INTERFACE                     │
│  > Last: [success] brain status returned OK             │
│  MONEYMAKER> brain sta_                                    │
│                                                         │
│  brain   start|stop|pause|resume|status|eval|regime|    │
│          maturity|coaching|skill-progress|sentry|...    │
│  data    start|stop|status|symbols|add|remove|backfill  │
│  mt5     connect|status|positions|trailing|rate-limit   │
│  risk    status|limits|exposure|kill-switch|circuit-br  │
│  signal  status|last|pending|rejected|confidence|rate   │
│  market  regime|symbols|spread|calendar|volatility      │
│  ml      start|stop|pause|resume|status|deploy|shadow   │
│  perf    summary|daily|by-symbol|by-strategy|drawdown   │
│  test    all|brain-verify|cascade|go|suite|lint|ci      │
│  build   all|brain|ingestion|bridge|proto|clean         │
│  sys     status|resources|health|db|redis|network       │
│  config  view|validate|set|get|diff|reload|encrypt      │
│  svc     up|down|restart|status|logs|scale|exec         │
│  maint   vacuum|reindex|backup|prune-old|compress       │
│  kill    status|activate|deactivate|test                │
│  audit   security|secrets|tls|dependencies|hashchain    │
│  portfolio overview|allocation|var|stress-test          │
│  alert   status|channels|test|rules|mute|telegram       │
│  log     view|console|search|errors|rotate              │
│  tool    list|shell|sql|redis-cli|benchmark|version     │
│  help    exit                                           │
└─────────────────────────────────────────────────────────┘
```

### 24.2 Panel Update Strategy

The TUI uses a **dirty-flag** rendering strategy to minimize CPU usage:

1. The `StatusPoller` thread runs in the background, querying all services every 2 seconds.
2. When the poller detects a change in status (via lightweight hash comparison), it sets the renderer's `_dirty` flag.
3. The render loop checks the dirty flag at `TUI_REFRESH_PER_SECOND` (8 Hz).
4. If dirty, the loop calls `renderer.update_panels()` to update all panel content in-place, then `live.refresh()` to repaint the terminal.
5. If not dirty, the loop sleeps for `TUI_INPUT_POLL_INTERVAL_S` (100ms) and checks for keyboard input.

This approach ensures:
- No flickering (panels are updated in-place, not rebuilt)
- Low CPU usage (only repaints on actual changes or input)
- Responsive input (100ms polling interval for keystrokes)

### 24.3 Non-Blocking Input Handler

The TUI must read keyboard input without blocking the render loop. This requires platform-specific implementations:

**Unix (Linux/macOS)**: Uses `termios` to set the terminal to cbreak mode, then `select.select()` with a 0-second timeout to check if input is available. If available, reads one character with `sys.stdin.read(1)`.

**Windows**: Uses `msvcrt.kbhit()` to check for available input, then `msvcrt.getwch()` to read one wide character.

Both implementations support:
- Enter (CR/LF): Submit the command buffer
- Backspace (BS/DEL): Remove the last character from the buffer
- Ctrl+C: Graceful exit
- Printable characters: Append to the command buffer

### 24.4 Command History and Auto-Completion

The TUI maintains a command history buffer (last 100 commands) accessible with Up/Down arrow keys. The history is persisted to `logs/.console_history` between sessions.

Auto-completion is triggered by the Tab key:
- First Tab: Complete the category name (e.g., `br` → `brain`)
- Second Tab: Show available sub-commands for the current category
- With `prompt_toolkit` (optional): Full fuzzy-match completion with a dropdown menu

---

## 25. CLI Mode — Non-Interactive Command Dispatch

### 25.1 Argparse Structure

The CLI mode builds a comprehensive argparse parser with nested subparsers for each command category. The parser is auto-generated from the `CommandRegistry` to ensure CLI and TUI commands are always in sync:

```python
def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moneymaker",
        description=f"MONEYMAKER Trading Console v{_VERSION}",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_VERSION}")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--quiet", action="store_true", help="Suppress non-essential output")

    subparsers = parser.add_subparsers(dest="category", help="Command category")

    for cat in registry.categories:
        cat_parser = subparsers.add_parser(cat, help=f"{cat} commands")
        cat_parser.add_argument("subcmd", nargs="?", default="", help="Sub-command")
        cat_parser.add_argument("args", nargs="*", help="Additional arguments")

    return parser
```

### 25.2 JSON Output Mode

The `--json` flag enables machine-readable JSON output for all commands. This enables programmatic consumption by monitoring scripts, CI/CD pipelines, and the web dashboard:

```bash
$ python moneymaker_console.py --json brain status
{
  "category": "brain",
  "subcmd": "status",
  "result": {
    "state": "TRAINING",
    "mode": "hybrid",
    "epoch": 142,
    "loss": 0.0234,
    "lr": 0.0001,
    "drift_zscore": 0.4,
    "maturity_state": "MATURE",
    "trading_mode": "FULL_LIVE"
  },
  "exit_code": 0,
  "duration_ms": 45
}
```

### 25.3 Exit Codes

CLI mode returns standardized exit codes:
- `0`: Success
- `1`: Command execution error
- `2`: Invalid arguments / unknown command
- `3`: Service unavailable
- `4`: Permission denied (e.g., kill switch active, daily loss exceeded)
- `5`: Confirmation required but not provided (non-interactive mode)

---

## 26. Status Polling and Background Threads

### 26.1 StatusPoller Architecture

The `StatusPoller` is a daemon thread that periodically queries all services and caches the results for the TUI renderer. It runs independently of the render loop to prevent blocking:

```python
class StatusPoller:
    _STATUS_POLL_INTERVAL_S = 2.0

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=3)

    def get(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._cache)

    def _poll_loop(self):
        while not self._stop.is_set():
            cache = self._poll_all()
            with self._lock:
                self._cache = cache
            self._stop.wait(self._STATUS_POLL_INTERVAL_S)
```

### 26.2 Poll Sources

Each poll cycle queries the following sources (all with 5-second timeouts):

1. **PostgreSQL**: `SELECT 1` health check + table statistics
2. **Redis**: `PING` + `INFO memory` + `GET moneymaker:kill_switch`
3. **Docker**: `docker compose -f infra/docker/docker-compose.yml ps --format json`
4. **Algo Engine (REST)**: `GET http://localhost:8082/health`
5. **MT5 Bridge (gRPC)**: `HealthCheck()` + `GetPositions()`
6. **Data Ingestion (HTTP)**: `GET http://localhost:8081/healthz`
7. **Dashboard (REST)**: `GET http://localhost:8000/api/health`
8. **System resources**: `psutil.cpu_percent()`, `psutil.virtual_memory()`, `psutil.disk_usage()`
9. **GPU**: `rocm-smi` (if available)

Failed checks populate the cache with fallback values (`"DISCONNECTED"`, `"N/A"`, `0`) rather than raising exceptions. This ensures the TUI always renders, even when services are down.

### 26.3 MarketPoller (Optional)

A dedicated `MarketPoller` thread can subscribe to the ZeroMQ data feed to display real-time price updates in the MARKET DATA panel. This provides sub-second price updates without polling overhead:

```python
class MarketPoller:
    def __init__(self, zmq_endpoint: str = "tcp://localhost:5555"):
        self._endpoint = zmq_endpoint
        self._prices: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _subscribe_loop(self):
        ctx = zmq.Context()
        sock = ctx.socket(zmq.SUB)
        sock.connect(self._endpoint)
        sock.setsockopt_string(zmq.SUBSCRIBE, "")
        while not self._stop.is_set():
            if sock.poll(timeout=1000):
                msg = sock.recv_json()
                with self._lock:
                    self._prices[msg["symbol"]] = msg
```

---

## 27. Service Client Layer — HTTP, gRPC, Redis, PostgreSQL

### 27.1 Client Factory Pattern

All service clients follow the Lazy Singleton pattern to minimize startup time and handle connection failures gracefully:

```python
class ClientFactory:
    _instances: dict[str, Any] = {}

    @classmethod
    def get_postgres(cls):
        if "postgres" not in cls._instances:
            cls._instances["postgres"] = PostgresClient()
        return cls._instances["postgres"]

    @classmethod
    def get_redis(cls):
        if "redis" not in cls._instances:
            cls._instances["redis"] = RedisClient()
        return cls._instances["redis"]

    @classmethod
    def get_brain(cls):
        if "brain" not in cls._instances:
            cls._instances["brain"] = BrainRestClient()  # REST on port 8082
        return cls._instances["brain"]

    @classmethod
    def get_data_ingestion(cls):
        if "data" not in cls._instances:
            cls._instances["data"] = DataIngestionHttpClient()  # HTTP on port 8081
        return cls._instances["data"]
```

### 27.2 Connection Resilience

All clients implement automatic reconnection with exponential backoff:
- Initial retry delay: 1 second
- Maximum retry delay: 30 seconds
- Maximum retries per command: 3
- Connection timeout: 5 seconds

If a connection fails during a command, the handler catches the exception and returns a formatted error message. The TUI panel shows `RECONNECTING...` in yellow during retry attempts.

### 27.3 Protocol Contracts

The console uses different protocols for different services:

- **MT5 Bridge (gRPC)**: Uses stubs from `shared/proto/` — `execution.proto` for trade execution RPCs, `trading_signal.proto` for signal delivery
- **Algo Engine (REST)**: HTTP client for `/health` endpoint on port 8082; Prometheus scraping on port 9092
- **Data Ingestion (HTTP)**: HTTP client for `/healthz`, `/readyz`, `/health` endpoints on port 8081
- **Dashboard (REST)**: HTTP client for API endpoints on port 8000
- **PostgreSQL**: Direct SQL queries via `psycopg2` (admin user with `ADMIN_DB_PASSWORD`)
- **Redis**: Direct commands via `redis-py`

**Note on database RBAC**: Docker Compose defines per-service database users (`DI_DB_PASSWORD`, `BRAIN_DB_PASSWORD`, `MT5_DB_PASSWORD`). The console should use the `ADMIN_DB_PASSWORD` for full read access across all tables.

---

## 28. Security Considerations

### 28.1 Credential Handling

- **Environment variables**: All credentials are loaded from `os.environ`, never from hardcoded values.
- **Secret masking**: The `config view`, `sys env`, and `set view` commands mask secret values by default (showing only `****` + last 4 characters).
- **No logging of secrets**: The structured JSON logger strips secret values from command arguments before writing to the log file.
- **File permissions**: The console verifies that `.env` has `0600` permissions (user read/write only) and warns if overly permissive.

### 28.2 Command Confirmation

Dangerous commands require explicit `y` confirmation before execution:
- `mt5 close-all`: Lists positions to be closed before prompting
- `kill activate`: Shows the kill switch impact before prompting
- `maint restore`: Shows the backup file size and warns about data loss
- `maint prune-old`: Shows the number of records to be deleted (dry-run first)
- `risk kill-switch`: Equivalent to `kill activate`

### 28.3 Rate Limiting

The TUI implements a command debouncer that prevents accidental double-submission. If the same command is submitted twice within 500ms, the second submission is silently ignored. This prevents issues from rapid Enter-key presses.

### 28.4 Network Security

When `MONEYMAKER_TLS_ENABLED=true`:
- All gRPC channels use `grpc.ssl_channel_credentials()` with the CA certificate
- Mutual TLS (mTLS) is used for inter-service authentication with per-service client certificates
- PostgreSQL connections use `sslmode=verify-full`
- Redis connections use TLS with certificate verification

---

## 29. Error Handling and Resilience

### 29.1 Error Categories

The console categorizes errors into four levels:

1. **INFO** (`[info]`): Informational messages, no action required
2. **WARNING** (`[warning]`): Non-critical issues (service degraded, fallback active)
3. **ERROR** (`[error]`): Command failed, but console remains operational
4. **CRITICAL**: Console startup failure (missing Python, missing Rich)

### 29.2 Exception Handling Strategy

Every command handler wraps its execution in a try/except block:

```python
def dispatch(self, category, subcmd, args):
    try:
        result = cmd.handler(*args)
        _log_event("dispatch_ok", category=category, subcmd=subcmd)
        return result
    except grpc.RpcError as e:
        _log_event("dispatch_grpc_error", error=str(e))
        return f"[warning] Service communication error: {e.details()}"
    except psycopg2.Error as e:
        _log_event("dispatch_db_error", error=str(e))
        return f"[error] Database error: {e.pgerror or str(e)}"
    except redis.RedisError as e:
        _log_event("dispatch_redis_error", error=str(e))
        return f"[warning] Redis error: {e}"
    except Exception as e:
        _log_event("dispatch_unexpected_error", error=str(e), traceback=traceback.format_exc())
        return f"[error] Unexpected error: {e}"
```

### 29.3 Graceful Degradation

The console operates in degraded mode when services are unavailable:
- **No PostgreSQL**: Database-dependent commands return "Database unavailable". TUI panels show "N/A" for DB metrics.
- **No Redis**: Kill switch status shows "Unknown". Alert delivery may fail. Signal caching is disabled.
- **No Docker**: Service lifecycle commands use fallback subprocess management. Container metrics show "Docker unavailable".
- **No REST/gRPC**: Service control commands fall back to database queries or Docker status checks, or return "Service unavailable" stubs.
- **No psutil**: System resource monitoring is disabled. The SYSTEM panel shows a minimal fallback.
- **No Rich**: The console falls back to a plain readline-based interactive mode.

---

## 30. Testing Strategy for the Console Itself

### 30.1 Unit Tests

Unit tests for the console are located in `services/console/tests/`:

- **`test_registry.py`**: Test command registration, dispatch, alias resolution, middleware, and help generation.
- **`test_commands.py`**: Test individual command handlers with mocked service clients. Each command module has a corresponding test file.
- **`test_tui.py`**: Test TUI renderer layout generation and panel content formatting. Uses Rich's `Console(file=StringIO())` for capture-based testing.
- **`test_cli.py`**: Test argparse parser construction and CLI dispatch logic.
- **`test_clients.py`**: Test service client connection handling, retry logic, and error translation.

### 30.2 Integration Tests

Integration tests verify end-to-end command execution with real (or containerized) services:

```bash
# Start test infrastructure
docker compose -f infra/docker/docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/ -v --timeout=30

# Tear down
docker compose -f infra/docker/docker-compose.test.yml down
```

### 30.3 Smoke Tests

A smoke test script validates that all command categories respond without crashing:

```python
for category in registry.categories:
    for subcmd in registry._commands[category]:
        result = registry.dispatch(category, subcmd, [])
        assert "[error] Unexpected error" not in result, f"Crash in {category} {subcmd}"
```

---

## 31. Implementation Phases and Milestones

### Phase 1: Foundation (Week 1-2)
- Restructure `moneymaker_console.py` into the package layout described in Section 2.1
- Implement the enhanced `CommandRegistry` with middleware, aliases, and auto-discovery
- Port all existing 15 command categories from the current monolithic console
- Set up unit tests for registry and dispatch logic
- Verify TUI and CLI modes work with the new package structure

### Phase 2: Service Client Integration (Week 3-4)
- Implement HTTP REST client for Algo Engine (port 8082) and Data Ingestion (port 8081)
- Implement gRPC client for MT5 Bridge (port 50055)
- Implement HTTP client for Dashboard (port 8000)
- Implement PostgreSQL (admin user) and Redis client wrappers with retry logic
- Replace "service unavailable" stubs with real REST/gRPC calls where services are running
- Add connection health monitoring to the StatusPoller
- Implement the `sys health` parallel health check

### Phase 3: New Command Categories (Week 5-6)
- Implement `audit` category (security scanning, hash chain verification, compliance report)
- Implement `perf` category (performance analytics, Sharpe ratio, drawdown analysis)
- Implement `portfolio` category (allocation, VaR, stress testing)
- Implement `alert` category (Telegram integration, rule management, channel testing)
- Implement `log` category (centralized log aggregation, search, rotation)

### Phase 4: TUI Enhancement (Week 7-8)
- Expand the TUI from 4 panels to 8 panels
- Add real-time price updates via ZMQ subscription (MarketPoller)
- Implement command history (Up/Down arrows) and auto-completion (Tab)
- Add ASCII sparkline charts for equity curves and P&L trends
- Implement the `--json` output mode for CLI

### Phase 5: Security Hardening (Week 9-10)
- Implement TLS support for all gRPC clients (mutual TLS)
- Add `.env` encryption/decryption with system keyring
- Comprehensive security audit integration
- Rate limiting and command debouncing
- File permission validation on startup

### Phase 6: Polish and Documentation (Week 11-12)
- Complete all unit and integration tests (target: 90% coverage)
- Write operator manual with command reference and workflow examples
- Performance optimization (startup time < 300ms, TUI CPU < 5%)
- Cross-platform validation (Linux, macOS, Windows)
- Final review and release as v2.0

---

## 32. File Structure and Module Layout

### 32.1 Complete File Tree

```
program/services/console/
├── moneymaker_console.py              # Entry point (~50 lines)
├── pyproject.toml                  # Package deps: rich, psycopg2, redis, grpcio, psutil
├── README.md                       # Operator manual
├── logs/
│   ├── console_20260307.json      # Structured command log
│   └── .console_history           # Command history (persisted)
├── src/
│   └── moneymaker_console/
│       ├── __init__.py            # __version__ = "2.0.0"
│       ├── app.py                 # Application wiring (~200 lines)
│       ├── registry.py            # CommandRegistry + Command (~250 lines)
│       ├── runner.py              # _run_tool, _run_tool_live (~100 lines)
│       ├── logging.py             # JSON structured logger (~60 lines)
│       ├── tui/
│       │   ├── renderer.py        # TUIRenderer with 8 panels (~400 lines)
│       │   ├── theme.py           # Rich Theme definition (~30 lines)
│       │   ├── input.py           # Non-blocking input (Unix/Win) (~80 lines)
│       │   └── widgets.py         # Sparklines, progress bars (~150 lines)
│       ├── cli/
│       │   ├── parser.py          # Auto-generated argparse (~100 lines)
│       │   └── dispatch.py        # CLI dispatch + JSON output (~80 lines)
│       ├── clients/
│       │   ├── postgres.py        # Lazy PostgreSQL client (~120 lines)
│       │   ├── redis_client.py    # Lazy Redis client (~100 lines)
│       │   ├── http_brain.py      # Algo Engine REST client (~150 lines)
│       │   ├── grpc_mt5.py        # MT5 Bridge gRPC stub (~120 lines)
│       │   ├── http_data.py       # Data Ingestion HTTP client (~100 lines)
│       │   ├── http_dashboard.py  # Dashboard REST client (~80 lines)
│       │   └── docker.py          # Docker Compose wrapper (~80 lines)
│       ├── commands/
│       │   ├── brain.py           # ~300 lines (14 sub-commands)
│       │   ├── data.py            # ~250 lines (12 sub-commands)
│       │   ├── mt5.py             # ~300 lines (12 sub-commands)
│       │   ├── risk.py            # ~250 lines (13 sub-commands)
│       │   ├── signal.py          # ~200 lines (9 sub-commands)
│       │   ├── market.py          # ~250 lines (10 sub-commands)
│       │   ├── ml.py              # ~300 lines (14 sub-commands)
│       │   ├── test.py            # ~200 lines (12 sub-commands)
│       │   ├── build.py           # ~200 lines (12 sub-commands)
│       │   ├── sys_ops.py         # ~350 lines (13 sub-commands)
│       │   ├── config.py          # ~250 lines (13 sub-commands)
│       │   ├── svc.py             # ~200 lines (12 sub-commands)
│       │   ├── maint.py           # ~300 lines (14 sub-commands)
│       │   ├── kill.py            # ~150 lines (5 sub-commands)
│       │   ├── audit.py           # ~300 lines (10 sub-commands)
│       │   ├── perf.py            # ~350 lines (14 sub-commands)
│       │   ├── portfolio.py       # ~250 lines (8 sub-commands)
│       │   ├── alert.py           # ~200 lines (10 sub-commands)
│       │   ├── log_ops.py         # ~150 lines (8 sub-commands)
│       │   ├── tool.py            # ~200 lines (10 sub-commands)
│       │   ├── help.py            # ~30 lines
│       │   └── exit.py            # ~10 lines
│       └── poller/
│           ├── status_poller.py   # Background status polling (~150 lines)
│           └── market_poller.py   # ZMQ price subscription (~100 lines)
└── tests/
    ├── test_registry.py           # ~200 lines
    ├── test_commands/             # Per-module test files
    ├── test_tui.py                # ~150 lines
    ├── test_cli.py                # ~100 lines
    └── test_clients.py            # ~200 lines
```

### 32.2 Estimated Total Size

| Component | Est. Lines of Code |
|-----------|-------------------|
| Core (app, registry, runner, logging) | ~660 |
| TUI (renderer, theme, input, widgets) | ~660 |
| CLI (parser, dispatch) | ~180 |
| Clients (postgres, redis, 3× HTTP, 1× gRPC, docker) | ~770 |
| Commands (22 modules) | ~4,890 |
| Pollers (status, market) | ~250 |
| Tests | ~650 |
| **Total** | **~8,060** |

This represents a roughly **5x expansion** from the current 1,616-line monolithic console, structured as clean, testable, modular Python code.

---

## 33. Full Command Reference Table

The complete command reference across all 22 categories, totaling **190+ sub-commands**:

| # | Category | Sub-Command | Description |
|---|----------|-------------|-------------|
| 1 | `brain` | `start` | Start Algo Engine event loop |
| 2 | `brain` | `stop` | Graceful stop |
| 3 | `brain` | `pause` | Pause signal generation |
| 4 | `brain` | `resume` | Resume signal generation |
| 5 | `brain` | `status` | Comprehensive status |
| 6 | `brain` | `eval` | Evaluate on test set |
| 7 | `brain` | `checkpoint` | Force checkpoint save |
| 8 | `brain` | `model-info` | Model architecture details |
| 9 | `brain` | `regime` | Market regime classification |
| 10 | `brain` | `drift` | Drift monitor Z-scores |
| 11 | `brain` | `maturity` | Maturity gating status |
| 12 | `brain` | `spiral` | Spiral protection status |
| 13 | `brain` | `confidence` | Confidence distribution |
| 14 | `brain` | `features` | Current feature vector |
| 14a | `brain` | `coaching` | Coaching system status |
| 14b | `brain` | `coaching-history` | Coaching correction history |
| 14c | `brain` | `skill-progress` | RAP Coach skill progression |
| 14d | `brain` | `sentry` | Sentry error tracking status |
| 15 | `data` | `start` | Start data ingestion |
| 16 | `data` | `stop` | Stop ingestion |
| 17 | `data` | `status` | Ingestion status |
| 18 | `data` | `symbols` | Active symbols list |
| 19 | `data` | `add` | Add symbol |
| 20 | `data` | `remove` | Remove symbol |
| 21 | `data` | `backfill` | Historical backfill |
| 22 | `data` | `gaps` | Data gap analysis |
| 23 | `data` | `providers` | Provider status |
| 24 | `data` | `reconnect` | Force reconnection |
| 25 | `data` | `buffer` | Buffer status |
| 26 | `data` | `latency` | Latency percentiles |
| 27 | `mt5` | `connect` | Connect to MT5 |
| 28 | `mt5` | `disconnect` | Disconnect from MT5 |
| 29 | `mt5` | `status` | MT5 connection status |
| 30 | `mt5` | `positions` | Open positions |
| 31 | `mt5` | `history` | Trade history |
| 32 | `mt5` | `close` | Close position |
| 33 | `mt5` | `close-all` | Close ALL positions ⚠️ |
| 34 | `mt5` | `modify` | Modify SL/TP |
| 35 | `mt5` | `account` | Account info |
| 36 | `mt5` | `sync` | Force sync |
| 37 | `mt5` | `orders` | Pending orders |
| 38 | `mt5` | `autotrading` | Toggle autotrading |
| 38a | `mt5` | `trailing` | Trailing stop control |
| 38b | `mt5` | `trailing-config` | Trailing stop config |
| 38c | `mt5` | `rate-limit` | Rate limiting view/set |
| 39 | `risk` | `status` | Risk dashboard |
| 40 | `risk` | `limits` | Current limits |
| 41 | `risk` | `set-max-dd` | Set max drawdown |
| 42 | `risk` | `set-max-pos` | Set max positions |
| 43 | `risk` | `set-max-lot` | Set max lot size |
| 44 | `risk` | `set-daily-loss` | Set daily loss limit |
| 45 | `risk` | `exposure` | Exposure breakdown |
| 46 | `risk` | `correlation` | Symbol correlations |
| 47 | `risk` | `kill-switch` | Global kill switch ⚠️ |
| 48 | `risk` | `circuit-breaker` | Circuit breaker control |
| 49 | `risk` | `validation` | 11-point checklist |
| 50 | `risk` | `history` | Risk event history |
| 51 | `risk` | `spiral` | Spiral protection |
| 52 | `signal` | `status` | Pipeline status |
| 53 | `signal` | `last` | Recent signals |
| 54 | `signal` | `pending` | Pending signals |
| 55 | `signal` | `rejected` | Rejected signals |
| 56 | `signal` | `confidence` | Confidence histogram |
| 57 | `signal` | `rate` | Signal rate |
| 58 | `signal` | `strategy` | Strategy attribution |
| 59 | `signal` | `validate` | Re-validate signal |
| 60 | `signal` | `replay` | Replay signal |
| 61 | `market` | `regime` | Market regime |
| 62 | `market` | `symbols` | Symbols + regime |
| 63 | `market` | `spread` | Current spread |
| 64 | `market` | `calendar` | Economic calendar |
| 65 | `market` | `volatility` | Volatility metrics |
| 66 | `market` | `correlation` | Cross-symbol correlation |
| 67 | `market` | `session` | Trading sessions |
| 68 | `market` | `news` | Economic news |
| 69 | `market` | `indicators` | Technical indicators |
| 70 | `market` | `macro` | Macroeconomic data |
| 70a | `market` | `macro-status` | External Data service status |
| 70b | `market` | `dashboard` | Open web dashboard |
| 71 | `ml` | `start` | Start training |
| 72 | `ml` | `stop` | Stop training |
| 73 | `ml` | `pause` | Pause training |
| 74 | `ml` | `resume` | Resume training |
| 75 | `ml` | `status` | Training status |
| 76 | `ml` | `throttle` | Set throttle |
| 77 | `ml` | `eval` | Evaluate model |
| 78 | `ml` | `deploy` | Deploy model |
| 79 | `ml` | `rollback` | Rollback model |
| 80 | `ml` | `checkpoints` | List checkpoints |
| 81 | `ml` | `metrics` | Training metrics |
| 82 | `ml` | `hyperparams` | Hyperparameters |
| 83 | `ml` | `dataset` | Dataset statistics |
| 84 | `ml` | `shadow` | Shadow Engine status |
| 85 | `test` | `all` | Full pytest suite |
| 86 | `test` | `brain-verify` | Brain verification |
| 87 | `test` | `cascade` | E2E cascade tests |
| 88 | `test` | `go` | Go test suite |
| 89 | `test` | `mt5` | MT5 Bridge tests |
| 90 | `test` | `common` | Shared lib tests |
| 91 | `test` | `suite` | ALL tests |
| 92 | `test` | `lint` | Linting |
| 93 | `test` | `typecheck` | Type checking |
| 94 | `test` | `ci` | Full CI pipeline |
| 95 | `test` | `coverage` | Coverage report |
| 96 | `test` | `specific` | Specific test path |
| 97 | `build` | `all` | Build all images |
| 98 | `build` | `brain` | Build Algo Engine |
| 99 | `build` | `ingestion` | Build Data Ingestion |
| 100 | `build` | `bridge` | Build MT5 Bridge |
| 101 | `build` | `dashboard` | Build Dashboard |
| 102 | `build` | `external` | Build External Data |
| 103 | `build` | `test-only` | Tests without build |
| 104 | `build` | `proto` | Recompile Protobuf |
| 105 | `build` | `status` | Image build status |
| 106 | `build` | `clean` | Remove artifacts |
| 107 | `build` | `push` | Push to registry |
| 108 | `build` | `tag` | Tag images |
| 109 | `sys` | `status` | Full system status |
| 110 | `sys` | `resources` | CPU/RAM/GPU/Disk |
| 111 | `sys` | `health` | Health check (all) |
| 112 | `sys` | `db` | TimescaleDB status |
| 113 | `sys` | `redis` | Redis status |
| 114 | `sys` | `docker` | Docker status |
| 115 | `sys` | `network` | Network diagnostics |
| 116 | `sys` | `env` | Environment variables |
| 117 | `sys` | `ports` | Port allocation |
| 118 | `sys` | `uptime` | Service uptime |
| 119 | `sys` | `audit` | System audit |
| 120 | `sys` | `gpu` | AMD GPU status |
| 121 | `sys` | `disk` | Disk usage detail |
| 122 | `config` | `view` | View config |
| 123 | `config` | `validate` | Validate config |
| 124 | `config` | `set` | Set config value |
| 125 | `config` | `get` | Get config value |
| 126 | `config` | `diff` | Compare with example |
| 127 | `config` | `broker` | Set broker API key |
| 128 | `config` | `risk` | Set risk parameter |
| 129 | `config` | `reload` | Hot-reload config |
| 130 | `config` | `export` | Export config |
| 131 | `config` | `import` | Import config |
| 132 | `config` | `template` | Generate template |
| 133 | `config` | `encrypt` | Encrypt .env |
| 134 | `config` | `decrypt` | Decrypt .env |
| 135 | `svc` | `up` | Start services |
| 136 | `svc` | `down` | Stop services |
| 137 | `svc` | `restart` | Restart service |
| 138 | `svc` | `status` | Container status |
| 139 | `svc` | `logs` | Service logs |
| 140 | `svc` | `scale` | Scale replicas |
| 141 | `svc` | `exec` | Execute in container |
| 142 | `svc` | `inspect` | Container details |
| 143 | `svc` | `pull` | Pull images |
| 144 | `svc` | `prune` | Prune unused |
| 145 | `svc` | `compose-config` | Show compose config |
| 146 | `svc` | `health` | Container health |
| 147 | `maint` | `vacuum` | VACUUM ANALYZE |
| 148 | `maint` | `reindex` | Rebuild indexes |
| 149 | `maint` | `clear-cache` | Clear caches |
| 150 | `maint` | `retention` | Retention policies |
| 151 | `maint` | `backup` | Database backup |
| 152 | `maint` | `restore` | Restore backup ⚠️ |
| 153 | `maint` | `prune-old` | Delete old data ⚠️ |
| 154 | `maint` | `migrate` | Run migrations |
| 155 | `maint` | `table-sizes` | Table size report |
| 156 | `maint` | `chunk-stats` | Hypertable chunks |
| 157 | `maint` | `compress` | TimescaleDB compress |
| 158 | `maint` | `dead-code` | Dead code detection |
| 159 | `maint` | `sanitize` | Project sanitization |
| 160 | `maint` | `integrity` | DB integrity check |
| 161 | `kill` | `status` | Kill switch state |
| 162 | `kill` | `activate` | Activate kill switch ⚠️ |
| 163 | `kill` | `deactivate` | Deactivate kill switch |
| 164 | `kill` | `history` | Activation history |
| 165 | `kill` | `test` | Test mechanism |
| 166 | `audit` | `security` | Full security audit |
| 167 | `audit` | `secrets` | Secrets scanner |
| 168 | `audit` | `tls` | TLS verification |
| 169 | `audit` | `dependencies` | Vulnerability scan |
| 170 | `audit` | `permissions` | File permissions |
| 171 | `audit` | `docker` | Docker security |
| 172 | `audit` | `hashchain` | Hash chain verify |
| 173 | `audit` | `compliance` | Compliance report |
| 174 | `audit` | `env` | .env audit |
| 175 | `audit` | `report` | Full audit report |
| 176 | `perf` | `summary` | Performance summary |
| 177 | `perf` | `daily` | Daily P&L |
| 178 | `perf` | `weekly` | Weekly P&L |
| 179 | `perf` | `monthly` | Monthly P&L |
| 180 | `perf` | `by-symbol` | P&L by symbol |
| 181 | `perf` | `by-strategy` | P&L by strategy |
| 182 | `perf` | `by-session` | P&L by session |
| 183 | `perf` | `by-regime` | P&L by regime |
| 184 | `perf` | `drawdown` | Drawdown analysis |
| 185 | `perf` | `equity` | Equity curve |
| 186 | `perf` | `trades` | Trade list |
| 187 | `perf` | `expectancy` | System expectancy |
| 188 | `perf` | `risk-adjusted` | Risk-adjusted returns |
| 189 | `perf` | `correlation-pnl` | P&L correlation |
| 190 | `portfolio` | `overview` | Portfolio overview |
| 191 | `portfolio` | `allocation` | Capital allocation |
| 192 | `portfolio` | `heat-map` | P&L heat map |
| 193 | `portfolio` | `optimize` | MPT optimization |
| 194 | `portfolio` | `var` | Value at Risk |
| 195 | `portfolio` | `cvar` | Conditional VaR |
| 196 | `portfolio` | `stress-test` | Stress scenarios |
| 197 | `portfolio` | `compare` | Benchmark comparison |
| 198 | `alert` | `status` | Alert system status |
| 199 | `alert` | `channels` | Notification channels |
| 200 | `alert` | `test` | Test alert delivery |
| 201 | `alert` | `rules` | Alert rules list |
| 202 | `alert` | `add-rule` | Add alert rule |
| 203 | `alert` | `remove-rule` | Remove alert rule |
| 204 | `alert` | `history` | Alert history |
| 205 | `alert` | `mute` | Mute alerts |
| 206 | `alert` | `unmute` | Unmute alerts |
| 207 | `alert` | `telegram` | Telegram config |
| 208 | `log` | `view` | View service logs |
| 209 | `log` | `console` | Console log |
| 210 | `log` | `search` | Search logs |
| 211 | `log` | `errors` | Error log filter |
| 212 | `log` | `export` | Export logs |
| 213 | `log` | `rotate` | Rotate logs |
| 214 | `log` | `level` | Change log level |
| 215 | `log` | `metrics` | Log volume metrics |
| 216 | `tool` | `list` | List all commands |
| 217 | `tool` | `logs` | Recent log shortcut |
| 218 | `tool` | `env-check` | Dependency check |
| 219 | `tool` | `shell` | Interactive shell |
| 220 | `tool` | `sql` | Execute SQL query |
| 221 | `tool` | `redis-cli` | Execute Redis cmd |
| 222 | `tool` | `benchmark` | Latency benchmark |
| 223 | `tool` | `version` | Version info |
| 224 | `tool` | `whoami` | Operator identity |
| 225 | `tool` | `motd` | Message of the Day |
| 226 | `help` | — | Show help |
| 227 | `exit` | — | Exit console |

---

**Total: 22 command categories, 240+ sub-commands, 8-panel TUI dashboard, full CLI mode with JSON output, 6 implementation phases over 12 weeks.**

*This plan represents the definitive specification for the MONEYMAKER Unified Console v2.0 — the single command center that controls every aspect of the trading ecosystem. If it is not in this console, the project does not need it.*
