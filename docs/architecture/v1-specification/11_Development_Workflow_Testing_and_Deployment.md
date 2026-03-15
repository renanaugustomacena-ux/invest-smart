# MONEYMAKER V1 -- Development Workflow, Testing, and Deployment

> **Autore** | Renan Augusto Macena

---

## Table of Contents

1. [Development Philosophy](#111-development-philosophy)
2. [Repository Structure](#112-repository-structure)
3. [Local Development Environment](#113-local-development-environment)
4. [Coding Standards and Style](#114-coding-standards-and-style)
5. [Version Control Strategy](#115-version-control-strategy)
6. [Testing Strategy -- Unit Tests](#116-testing-strategy--unit-tests)
7. [Testing Strategy -- Integration Tests](#117-testing-strategy--integration-tests)
8. [Testing Strategy -- End-to-End Tests](#118-testing-strategy--end-to-end-tests)
9. [Testing Strategy -- Backtesting and Validation](#119-testing-strategy--backtesting-and-validation)
10. [Continuous Integration](#1110-continuous-integration)
11. [Continuous Deployment](#1111-continuous-deployment)
12. [Docker and Containerization](#1112-docker-and-containerization)
13. [Proxmox Deployment](#1113-proxmox-deployment)
14. [Database Migrations](#1114-database-migrations)
15. [Configuration Management](#1115-configuration-management)
16. [Documentation Standards](#1116-documentation-standards)
17. [Development Tooling](#1117-development-tooling)

---

## 11.1 Development Philosophy

### Measure Twice, Cut Once

MONEYMAKER is a financial system. Every line of code that runs in production has the potential to move real money, open real positions, and incur real losses. This is not a web application where a bug means a broken layout or a slow page load. In MONEYMAKER, a bug can mean an incorrect position size, a missed stop-loss, or a signal that fires when it should remain silent. The consequences are measured in currency, not inconvenience.

This reality shapes every aspect of our development workflow. We do not write code and hope it works. We do not push to production on Friday afternoon. We do not skip tests because we are confident. We do not refactor critical financial logic without a comprehensive test suite verifying every edge case. We measure twice and cut once -- and then we measure again after cutting.

The development philosophy rests on six pillars that govern how every contributor to the MONEYMAKER codebase works.

### Pillar 1: Test-Driven Development for Financial Logic

Any code path that touches money -- position sizing calculations, risk limit enforcement, order construction, stop-loss computation, margin utilization checks, drawdown measurement -- is written test-first. The developer writes the test before writing the implementation. The test captures the expected behavior: given these inputs (account equity, signal confidence, current exposure, volatility regime), the system should produce this output (position size of X lots, or rejection with reason Y). Only after the test exists does the developer write the implementation to make it pass.

This is not optional. It is not a suggestion. It is a hard requirement for any code that participates in the financial decision pipeline. The reason is straightforward: financial logic must be correct under all conditions, including edge cases that the developer might not naturally consider. Writing the test first forces the developer to think about the contract -- what should happen when equity is zero? What should happen when the signal confidence is exactly at the threshold? What should happen when two opposing signals arrive simultaneously? These questions are easier to answer in the calm, deliberate context of test writing than in the heat of implementation.

### Pillar 2: Code Review Is Mandatory

No code reaches the main branch without being reviewed by at least one other pair of eyes. For financial logic, risk management changes, and execution bridge modifications, two reviewers are required. The reviewer is not looking for style violations -- the linter catches those. The reviewer is looking for logical errors, missing edge cases, incorrect assumptions about market behavior, and violations of the architectural principles defined in these documents.

Code review serves a second, equally important purpose: knowledge distribution. Every review is a teaching moment. The reviewer learns how the author approached the problem. The author learns from the reviewer's feedback. Over time, the entire team develops a shared understanding of the codebase, reducing bus factor and improving the quality of future contributions.

### Pillar 3: Feature Branches and Incremental Delivery

All development happens on feature branches. The main branch is always in a deployable state. This is an absolute invariant. If main is broken, everything stops until it is fixed. Feature branches are short-lived -- ideally no more than a few days. Long-lived branches accumulate merge conflicts, diverge from the evolving codebase, and become increasingly difficult to review. If a feature is too large to implement in a few days, it is decomposed into smaller increments that can be merged independently, each leaving main in a working state.

Incremental delivery means that every merge to main adds a complete, tested, documented unit of functionality. We do not merge half-finished features behind feature flags (though feature flags have their place, as discussed in section 11.15). We do not merge code that "will be tested later." Every merge is a complete thought: the code works, the tests pass, the documentation is updated, and the system is better than it was before the merge.

### Pillar 4: Documentation Before Code

For any significant feature or architectural change, the developer writes a design document before writing code. This document describes the problem being solved, the proposed solution, the alternatives considered and why they were rejected, the impact on existing services, and the testing strategy. The design document is reviewed and approved before implementation begins.

This is not bureaucracy. It is insurance. A design document forces the developer to think through the problem completely before committing to an implementation. It surfaces architectural conflicts early, when they are cheap to resolve. It creates a permanent record of why decisions were made, which is invaluable when a future developer (or the same developer six months later) needs to understand the rationale behind a design choice.

### Pillar 5: Incremental Delivery Over Big Bang Releases

We deploy small changes frequently rather than large changes infrequently. A deployment that changes three lines of configuration is easy to reason about, easy to test, and easy to roll back if something goes wrong. A deployment that changes three thousand lines across five services is a nightmare to debug when something breaks -- and something always breaks.

Our deployment pipeline supports this philosophy: it is fast enough to deploy multiple times per day, automated enough that deployment is not a burden, and instrumented enough that we can detect problems within minutes of a deployment completing.

### Pillar 6: Defensive Programming

Every function that accepts external input validates that input. Every network call has a timeout. Every database query has a connection timeout and a statement timeout. Every configuration value has a sensible default. Every error path is explicitly handled -- no bare except clauses, no swallowed exceptions, no "this should never happen" comments without a corresponding assertion or log. The system assumes that everything that can go wrong will go wrong, and it handles failure gracefully rather than catastrophically.

---

## 11.2 Repository Structure

### Monorepo Strategy

MONEYMAKER V1 uses a monorepo -- a single Git repository containing all services, shared libraries, infrastructure configuration, tests, documentation, and deployment scripts. This choice is deliberate and reflects the tightly integrated nature of the ecosystem. When a change to the shared protocol buffer definitions affects three services, we want that change to be a single commit, a single review, and a single CI run that validates all affected services. A polyrepo (one repository per service) would require coordinated multi-repo changes, version pinning of shared libraries, and complex dependency management. For a team of our size, the operational overhead of a polyrepo outweighs its benefits.

### Directory Layout

```
moneymaker-v1/
|
|-- services/
|   |-- data-ingestion/              # Go service
|   |   |-- cmd/
|   |   |   +-- server/
|   |   |       +-- main.go
|   |   |-- internal/
|   |   |   |-- connectors/          # Exchange-specific connectors
|   |   |   |   |-- binance.go
|   |   |   |   |-- mt5.go
|   |   |   |   +-- mock.go
|   |   |   |-- normalizer/          # Data normalization
|   |   |   |-- publisher/           # ZeroMQ publisher
|   |   |   +-- health/
|   |   |-- pkg/                     # Exported packages
|   |   |-- go.mod
|   |   |-- go.sum
|   |   |-- Dockerfile
|   |   +-- README.md
|   |
|   |-- algo-engine/                    # Python service
|   |   |-- src/
|   |   |   +-- algo_engine/
|   |   |       |-- __init__.py
|   |   |       |-- main.py
|   |   |       |-- evaluation/
|   |   |       |   |-- engine.py
|   |   |       |   |-- strategy_loader.py
|   |   |       |   +-- ensemble.py
|   |   |       |-- strategies/
|   |   |       |   |-- base.py
|   |   |       |   |-- trend_following.py
|   |   |       |   |-- mean_reversion.py
|   |   |       |   +-- regime_router.py
|   |   |       |-- features/
|   |   |       |   |-- pipeline.py
|   |   |       |   |-- technical.py
|   |   |       |   +-- macro.py
|   |   |       |-- signals/
|   |   |       |   |-- generator.py
|   |   |       |   +-- validator.py
|   |   |       +-- config.py
|   |   |-- tests/
|   |   |   |-- unit/
|   |   |   |-- integration/
|   |   |   +-- conftest.py
|   |   |-- pyproject.toml
|   |   |-- Dockerfile
|   |   +-- README.md
|   |
|   |   |-- notebooks/               # Jupyter research notebooks
|   |   |-- pyproject.toml
|   |   |-- Dockerfile
|   |   +-- README.md
|   |
|   |-- mt5-bridge/                  # Python service
|   |   |-- src/
|   |   |   +-- mt5_bridge/
|   |   |       |-- __init__.py
|   |   |       |-- main.py
|   |   |       |-- connector.py
|   |   |       |-- order_manager.py
|   |   |       |-- position_tracker.py
|   |   |       |-- health.py
|   |   |       +-- config.py
|   |   |-- tests/
|   |   |-- pyproject.toml
|   |   |-- Dockerfile
|   |   +-- README.md
|   |
|   |-- risk-manager/                # Python service
|   |   |-- src/
|   |   |   +-- risk_manager/
|   |   |       |-- __init__.py
|   |   |       |-- main.py
|   |   |       |-- position_sizer.py
|   |   |       |-- circuit_breaker.py
|   |   |       |-- kill_switch.py
|   |   |       |-- drawdown.py
|   |   |       |-- exposure.py
|   |   |       +-- config.py
|   |   |-- tests/
|   |   |-- pyproject.toml
|   |   |-- Dockerfile
|   |   +-- README.md
|   |
|   +-- monitoring/                  # Python + config
|       |-- src/
|       |   +-- monitoring/
|       |       |-- __init__.py
|       |       |-- dashboard.py     # Streamlit
|       |       |-- alerts.py
|       |       +-- config.py
|       |-- grafana/
|       |   |-- dashboards/
|       |   +-- provisioning/
|       |-- prometheus/
|       |   +-- prometheus.yml
|       |-- pyproject.toml
|       |-- Dockerfile
|       +-- README.md
|
|-- shared/
|   |-- proto/                       # Protocol Buffer definitions
|   |   |-- market_data.proto
|   |   |-- trading_signal.proto
|   |   |-- risk_check.proto
|   |   |-- order.proto
|   |   |-- health.proto
|   |   +-- Makefile                 # Proto compilation targets
|   |-- python-common/               # Shared Python utilities
|   |   |-- src/
|   |   |   +-- moneymaker_common/
|   |   |       |-- __init__.py
|   |   |       |-- logging.py       # Structured logging setup
|   |   |       |-- config.py        # Base configuration
|   |   |       |-- metrics.py       # Prometheus helpers
|   |   |       |-- health.py        # Health check protocol
|   |   |       |-- serialization.py
|   |   |       +-- exceptions.py    # Shared exception hierarchy
|   |   +-- pyproject.toml
|   +-- go-common/                   # Shared Go packages
|       |-- logging/
|       |-- config/
|       |-- health/
|       +-- go.mod
|
|-- infrastructure/
|   |-- docker/
|   |   |-- docker-compose.yml       # Full ecosystem
|   |   |-- docker-compose.dev.yml   # Dev overrides
|   |   |-- docker-compose.test.yml  # Test configuration
|   |   +-- .env.example
|   |-- ansible/
|   |   |-- playbooks/
|   |   |   |-- deploy.yml
|   |   |   |-- rollback.yml
|   |   |   |-- setup-vm.yml
|   |   |   +-- update-config.yml
|   |   |-- inventory/
|   |   |   |-- production.yml
|   |   |   +-- staging.yml
|   |   |-- roles/
|   |   +-- group_vars/
|   |       |-- all.yml
|   |       +-- vault.yml            # Ansible Vault encrypted
|   |-- proxmox/
|   |   |-- vm-templates/
|   |   +-- scripts/
|   |       |-- create-vm.sh
|   |       +-- gpu-passthrough.sh
|   +-- terraform/                   # Optional IaC for Proxmox
|       +-- main.tf
|
|-- tests/
|   |-- e2e/                         # End-to-end tests
|   |   |-- test_full_pipeline.py
|   |   |-- test_circuit_breaker.py
|   |   |-- test_recovery.py
|   |   +-- conftest.py
|   |-- performance/                 # Load and stress tests
|   |   |-- locustfile.py
|   |   +-- benchmark_strategy.py
|   |-- backtesting/                 # Historical validation
|   |   |-- test_walk_forward.py
|   |   |-- test_regime_detection.py
|   |   +-- conftest.py
|   +-- fixtures/                    # Shared test data
|       |-- market_data/
|       |-- signals/
|       +-- configs/
|
|-- docs/
|   |-- architecture/
|   |   +-- decisions/               # Architecture Decision Records
|   |       |-- ADR-001-monorepo.md
|   |       |-- ADR-002-zmq-vs-grpc.md
|   |       +-- ADR-003-timescaledb.md
|   |-- runbooks/
|   |   |-- incident-response.md
|   |   |-- deployment.md
|   |   +-- rollback.md
|   |-- api/
|   +-- onboarding/
|       +-- getting-started.md
|
|-- scripts/
|   |-- dev/
|   |   |-- setup-local.sh           # One-command local setup
|   |   |-- seed-db.sh               # Database seeding
|   |   |-- generate-protos.sh       # Proto compilation
|   |   +-- run-all-tests.sh
|   |-- ops/
|   |   |-- health-check.sh
|   |   |-- backup-db.sh
|   |   +-- rotate-logs.sh
|   +-- data/
|       |-- download-historical.py
|       +-- import-fixtures.py
|
|-- configs/
|   |-- development/
|   |   |-- algo-engine.yaml
|   |   |-- risk-manager.yaml
|   |   +-- data-ingestion.yaml
|   |-- staging/
|   |   |-- algo-engine.yaml
|   |   +-- risk-manager.yaml
|   +-- production/
|       |-- algo-engine.yaml
|       +-- risk-manager.yaml
|
|-- Makefile                          # Top-level make targets
|-- pyproject.toml                    # Workspace-level config
|-- .pre-commit-config.yaml
|-- .gitignore
|-- .env.example
+-- README.md
```

### Naming Conventions

All directories use lowercase with hyphens for separation: `data-ingestion`, `risk-manager`, `algo-engine`. Python packages within `src/` use underscores: `algo_engine`, `risk_manager`. This follows the standard Python packaging convention where the installable package name (hyphenated) differs from the importable module name (underscored).

Test files mirror the source structure. If `services/risk-manager/src/risk_manager/position_sizer.py` contains the position sizing logic, its tests live at `services/risk-manager/tests/unit/test_position_sizer.py`. Integration tests for the same service live at `services/risk-manager/tests/integration/test_position_sizer_integration.py`.

Configuration files use the pattern `{environment}/{service-name}.yaml`. Secrets never appear in configuration files -- they are injected through environment variables, as described in section 11.15.

Proto files are named after the domain concept they define: `market_data.proto`, `trading_signal.proto`, `risk_check.proto`. Generated code is committed to the repository to avoid requiring proto compilation as part of every build.

---

## 11.3 Local Development Environment

### Prerequisites and Setup

Every developer working on MONEYMAKER must have a local environment that can run, test, and debug any service in the ecosystem. The goal is that a new developer can go from a fresh machine to a running local instance of the full ecosystem in under thirty minutes. Here is what is required.

**Python 3.11+.** All Python services target Python 3.11 as the minimum version. We use 3.11 specifically for its improved error messages, performance improvements (the faster CPython initiative), exception groups, and `tomllib` in the standard library. Python 3.12 or 3.13 are acceptable but all CI runs target 3.11 as the baseline.

**Poetry or uv for dependency management.** Each Python service has its own `pyproject.toml` and its own virtual environment. We use Poetry for dependency resolution and lock file generation, with uv as an optional fast alternative for developers who prefer it. The lock file (`poetry.lock` or `uv.lock`) is committed to the repository to ensure reproducible builds.

**Go 1.22+.** The Data Ingestion Service is written in Go. Developers working on this service need Go 1.22 or later. Go modules handle dependency management.

**Docker and Docker Compose.** The infrastructure dependencies -- PostgreSQL, TimescaleDB, Redis, Prometheus, Grafana -- run in Docker containers locally. No developer is expected to install these services natively. Docker Compose provides a one-command startup for the entire dependency stack.

**Pre-commit.** Git hooks are managed through pre-commit, ensuring that every commit is automatically checked for formatting, linting, and type errors before it reaches the repository.

### Virtual Environment Isolation

Each Python service maintains its own virtual environment. This is non-negotiable. The Algo Engine has different dependencies than the Risk Manager. Sharing a virtual environment between services leads to version conflicts.

The `pyproject.toml` for each service specifies its dependencies precisely:

```toml
# services/risk-manager/pyproject.toml
[project]
name = "moneymaker-risk-manager"
version = "1.0.0"
description = "MONEYMAKER V1 Risk Management Service"
requires-python = ">=3.11"
license = {text = "Proprietary"}

[project.dependencies]
pydantic = ">=2.5,<3.0"
pydantic-settings = ">=2.1,<3.0"
structlog = ">=23.2,<25.0"
prometheus-client = ">=0.19,<1.0"
grpcio = ">=1.60,<2.0"
protobuf = ">=4.25,<5.0"
sqlalchemy = ">=2.0,<3.0"
asyncpg = ">=0.29,<1.0"
redis = ">=5.0,<6.0"
numpy = ">=1.26,<2.0"

[project.optional-dependencies]
dev = [
    "pytest>=7.4,<9.0",
    "pytest-cov>=4.1,<6.0",
    "pytest-asyncio>=0.23,<1.0",
    "pytest-mock>=3.12,<4.0",
    "hypothesis>=6.92,<7.0",
    "black>=23.12,<25.0",
    "ruff>=0.1.9,<1.0",
    "mypy>=1.8,<2.0",
    "isort>=5.13,<6.0",
    "pre-commit>=3.6,<4.0",
]

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "W", "I", "N", "UP", "S", "B", "A", "C4", "SIM", "TCH"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short --strict-markers"
markers = [
    "unit: Unit tests (fast, no external dependencies)",
    "integration: Integration tests (require database/redis)",
    "slow: Slow tests (backtesting, performance)",
]

[tool.coverage.run]
source = ["src/risk_manager"]
branch = true

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]
```

### Pre-Commit Hooks

Pre-commit hooks are the first line of defense against code quality regressions. They run automatically before every commit, catching issues before they enter the repository.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
        args: [--unsafe]
      - id: check-toml
      - id: check-json
      - id: check-added-large-files
        args: [--maxkb=1000]
      - id: check-merge-conflict
      - id: debug-statements
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        args: [--line-length=100]

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [--profile=black, --line-length=100]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.5
          - types-redis
          - types-protobuf
        args: [--strict]

  - repo: https://github.com/hadolint/hadolint
    rev: v2.12.0
    hooks:
      - id: hadolint-docker
```

These hooks enforce: Black for formatting (line length 100, Python 3.11 target), isort for import ordering (Black-compatible profile), Ruff for fast linting (replaces flake8, pylint for most checks), mypy for type checking (strict mode), Hadolint for Dockerfile linting, and several general hygiene checks (trailing whitespace, large files, private keys, merge conflict markers).

### Docker Compose for Local Dependencies

The local development environment uses Docker Compose to run infrastructure dependencies. Developers do not need to install PostgreSQL, TimescaleDB, Redis, or Prometheus locally.

```yaml
# infrastructure/docker/docker-compose.dev.yml
version: "3.9"

services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    container_name: moneymaker-dev-postgres
    environment:
      POSTGRES_USER: moneymaker_dev
      POSTGRES_PASSWORD: dev_password_not_for_production
      POSTGRES_DB: moneymaker_dev
    ports:
      - "5432:5432"
    volumes:
      - moneymaker_dev_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U moneymaker_dev"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: moneymaker-dev-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  prometheus:
    image: prom/prometheus:latest
    container_name: moneymaker-dev-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ../prometheus/prometheus-dev.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    container_name: moneymaker-dev-grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_AUTH_ANONYMOUS_ENABLED: "true"
    volumes:
      - ../grafana/provisioning:/etc/grafana/provisioning
      - ../grafana/dashboards:/var/lib/grafana/dashboards

volumes:
  moneymaker_dev_pgdata:
```

### Mock MT5 for Local Development

MetaTrader 5 is a Windows application that cannot run natively on Linux development machines. For local development, we provide a mock MT5 connector that simulates the MT5 API surface. This mock accepts orders, simulates fills at realistic prices with configurable slippage, maintains a virtual position book, and publishes events over the same gRPC interface that the real MT5 bridge uses. The mock is deterministic when given a fixed random seed, which is essential for reproducible testing.

```python
# services/mt5-bridge/src/mt5_bridge/mock_connector.py
"""Mock MT5 connector for local development and testing."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from mt5_bridge.config import MT5Config


@dataclass
class MockPosition:
    """Simulated open position."""

    ticket: int
    symbol: str
    direction: str  # "BUY" or "SELL"
    volume: float
    open_price: float
    open_time: datetime
    stop_loss: float | None = None
    take_profit: float | None = None


class MockMT5Connector:
    """Simulates MT5 API for local development.

    Provides deterministic behavior when initialized with a fixed seed.
    Supports configurable slippage, partial fills, and simulated latency.
    """

    def __init__(self, config: MT5Config, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._config = config
        self._positions: dict[int, MockPosition] = {}
        self._next_ticket = 100000
        self._connected = True

    async def send_order(
        self, symbol: str, direction: str, volume: float, price: float, **kwargs: Any
    ) -> dict[str, Any]:
        """Simulate order execution with realistic slippage."""
        slippage = self._rng.gauss(0, 0.00005)  # 0.5 pip std dev
        fill_price = price + slippage if direction == "BUY" else price - slippage

        ticket = self._next_ticket
        self._next_ticket += 1

        self._positions[ticket] = MockPosition(
            ticket=ticket,
            symbol=symbol,
            direction=direction,
            volume=volume,
            open_price=fill_price,
            open_time=datetime.now(timezone.utc),
            stop_loss=kwargs.get("stop_loss"),
            take_profit=kwargs.get("take_profit"),
        )

        return {
            "retcode": 10009,  # TRADE_RETCODE_DONE
            "ticket": ticket,
            "price": fill_price,
            "volume": volume,
        }
```

### Environment Variables and .env Files

Local development uses `.env` files for service configuration. A `.env.example` file is committed to the repository as a template; the actual `.env` file is in `.gitignore` and never committed.

```bash
# .env.example -- Copy to .env and customize
MONEYMAKER_ENV=development
MONEYMAKER_LOG_LEVEL=DEBUG
MONEYMAKER_LOG_FORMAT=console

# Database
MONEYMAKER_DB_HOST=localhost
MONEYMAKER_DB_PORT=5432
MONEYMAKER_DB_NAME=moneymaker_dev
MONEYMAKER_DB_USER=moneymaker_dev
MONEYMAKER_DB_PASSWORD=dev_password_not_for_production

# Redis
MONEYMAKER_REDIS_HOST=localhost
MONEYMAKER_REDIS_PORT=6379

# Algo Engine
MONEYMAKER_MODEL_PATH=./models/latest

# MT5 Bridge
MONEYMAKER_MT5_MOCK=true
MONEYMAKER_MT5_HOST=localhost
MONEYMAKER_MT5_PORT=8443

# Risk Manager
MONEYMAKER_MAX_POSITION_SIZE=0.01
MONEYMAKER_MAX_DAILY_LOSS_PCT=2.0
MONEYMAKER_CIRCUIT_BREAKER_THRESHOLD=3
```

### VS Code Configuration

A shared `.vscode/settings.json` is committed to the repository to ensure consistent editor behavior across the team:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=100"],
    "python.linting.enabled": true,
    "python.linting.mypyEnabled": true,
    "python.linting.mypyArgs": ["--strict"],
    "editor.formatOnSave": true,
    "editor.rulers": [100],
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true,
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    },
    "[go]": {
        "editor.defaultFormatter": "golang.go",
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    }
}
```

---

## 11.4 Coding Standards and Style

### Python Style Rules

All Python code in the MONEYMAKER ecosystem follows a consistent style. These rules are not suggestions -- they are enforced by automated tooling and verified in code review.

**PEP 8 compliance** is the baseline, with the following customizations:

- **Line length: 100 characters.** The default PEP 8 recommendation of 79 characters was designed for an era of 80-column terminals. Modern screens and code review tools handle 100 characters comfortably. Black enforces this.
- **Type hints are required on all function signatures.** Every function parameter and every return value must have a type annotation. This is enforced by mypy in strict mode. Type hints are not optional documentation -- they are machine-checked contracts. A function that accepts `equity: float` and `risk_per_trade: float` and returns `float` communicates far more than a function that accepts unnamed arguments and returns an untyped result.
- **Google-style docstrings.** Every public function, class, and module must have a docstring following Google's Python docstring convention. The docstring describes what the function does (not how it does it), its parameters, its return value, and any exceptions it raises.

```python
def calculate_position_size(
    equity: float,
    risk_per_trade: float,
    stop_loss_distance: float,
    pip_value: float,
    max_lots: float = 10.0,
) -> float:
    """Calculate position size based on fixed-fractional risk model.

    Determines the number of lots to trade such that a stop-loss hit results
    in a loss no greater than the specified percentage of account equity.

    Args:
        equity: Current account equity in account currency.
        risk_per_trade: Maximum risk as a fraction of equity (e.g., 0.01 for 1%).
        stop_loss_distance: Distance from entry to stop-loss in pips.
        pip_value: Value of one pip for one standard lot in account currency.
        max_lots: Hard maximum on position size regardless of calculation.

    Returns:
        Position size in lots, rounded down to two decimal places.

    Raises:
        ValueError: If equity is non-positive, risk_per_trade is not in (0, 1),
            or stop_loss_distance is not positive.
    """
    if equity <= 0:
        raise ValueError(f"Equity must be positive, got {equity}")
    if not 0 < risk_per_trade < 1:
        raise ValueError(f"Risk per trade must be in (0, 1), got {risk_per_trade}")
    if stop_loss_distance <= 0:
        raise ValueError(f"Stop-loss distance must be positive, got {stop_loss_distance}")

    risk_amount = equity * risk_per_trade
    raw_lots = risk_amount / (stop_loss_distance * pip_value)
    clamped_lots = min(raw_lots, max_lots)
    return float(int(clamped_lots * 100) / 100)  # Round down to 0.01
```

**Structured JSON logging.** All services use `structlog` for structured logging. Log messages are key-value pairs, not formatted strings. This makes logs machine-parseable, searchable in Grafana/Loki, and consistent across services.

```python
import structlog

logger = structlog.get_logger(__name__)

# Correct -- structured key-value pairs
logger.info(
    "position_size_calculated",
    equity=account.equity,
    risk_pct=risk_per_trade,
    stop_loss_pips=stop_loss_distance,
    result_lots=position_size,
    symbol=signal.symbol,
)

# Incorrect -- formatted string (do not do this)
# logger.info(f"Calculated position size {position_size} for {signal.symbol}")
```

**Pydantic BaseSettings for configuration.** All service configuration is defined as Pydantic BaseSettings models. This provides type validation, environment variable binding, default values, and automatic documentation of available settings.

```python
from pydantic import Field
from pydantic_settings import BaseSettings


class RiskManagerConfig(BaseSettings):
    """Configuration for the Risk Manager service."""

    model_config = {"env_prefix": "MONEYMAKER_RISK_"}

    max_position_size_lots: float = Field(
        default=1.0,
        description="Maximum position size in lots for any single trade",
        gt=0,
    )
    max_daily_loss_pct: float = Field(
        default=2.0,
        description="Maximum daily loss as percentage of equity",
        gt=0,
        le=10.0,
    )
    circuit_breaker_consecutive_losses: int = Field(
        default=3,
        description="Number of consecutive losses before circuit breaker trips",
        ge=2,
    )
    circuit_breaker_cooldown_minutes: int = Field(
        default=60,
        description="Minutes to wait after circuit breaker trips",
        ge=5,
    )
    max_correlated_exposure_pct: float = Field(
        default=5.0,
        description="Maximum total exposure across correlated instruments",
        gt=0,
    )
```

**Async/await for I/O-bound services.** Services that perform network I/O -- the Algo Engine (receiving data, sending signals), the Risk Manager (checking positions, querying the database), and the MT5 Bridge (communicating with MetaTrader) -- use async/await throughout. Blocking I/O calls are never mixed with async code. If a library does not support async natively, it is called through `asyncio.to_thread()` or replaced with an async-native alternative.

**Naming conventions.** Variables and functions use `snake_case`. Classes use `PascalCase`. Constants use `UPPER_SNAKE_CASE`. Private attributes and methods are prefixed with a single underscore. No double-underscore name mangling unless absolutely necessary. Boolean variables and methods use `is_`, `has_`, or `can_` prefixes: `is_circuit_breaker_active`, `has_open_positions`, `can_accept_new_trade`.

**No magic numbers.** Every numeric literal in the codebase must be assigned to a named constant or configuration value. Writing `if drawdown > 0.15` is forbidden; write `if drawdown > MAX_ACCEPTABLE_DRAWDOWN` where `MAX_ACCEPTABLE_DRAWDOWN` is defined in the configuration. This makes the code self-documenting and ensures that thresholds can be adjusted without searching through source files.

### Go Style Rules

The Data Ingestion Service follows standard Go conventions: `gofmt` for formatting, `golint` and `go vet` for linting, and the effective Go guidelines for naming and structure. Error handling follows the Go idiom of checking errors immediately after the call that produces them. Context propagation uses `context.Context` for cancellation and timeouts. Logging uses `slog` (structured logging in the standard library as of Go 1.21).

---

## 11.5 Version Control Strategy

### Branching Model

MONEYMAKER V1 uses a simplified trunk-based development model with short-lived feature branches. The main branch (`main`) is always deployable. All development happens on feature branches that branch from `main` and merge back into `main` through pull requests.

We do not use GitFlow's `develop`, `release/*`, or `hotfix/*` branches. GitFlow adds complexity that is justified for projects with multiple concurrent release streams and long release cycles. MONEYMAKER deploys from a single branch to a single environment (with a staging step), and our release cycle is continuous. The simplicity of trunk-based development reduces cognitive overhead, eliminates merge conflicts between long-lived branches, and encourages the small, frequent merges that our development philosophy demands.

```
Main Branch (always deployable)
|
|---[feature/add-regime-detection]----> PR ---> merge to main
|
|---[fix/position-size-rounding]------> PR ---> merge to main
|
|---[refactor/risk-manager-async]-----> PR ---> merge to main
|
|---[infra/update-docker-compose]-----> PR ---> merge to main
```

### Branch Naming Convention

Branch names follow a strict convention that encodes the type of change and a brief description:

```
{type}/{short-description}

Types:
  feature/    -- New functionality
  fix/        -- Bug fix
  refactor/   -- Code restructuring without behavior change
  test/       -- Adding or updating tests
  docs/       -- Documentation changes
  infra/      -- Infrastructure, CI/CD, Docker changes
  perf/       -- Performance improvements
  chore/      -- Maintenance tasks (dependency updates, etc.)

Examples:
  feature/walk-forward-validation
  fix/circuit-breaker-reset-timing
  refactor/risk-manager-to-async
  test/position-sizer-edge-cases
  infra/add-gpu-passthrough-ansible
```

Branch names use lowercase letters, numbers, and hyphens only. No underscores, no uppercase, no special characters. The description should be concise but meaningful -- a reader should understand the purpose of the branch from its name alone.

### Conventional Commits

All commit messages follow the Conventional Commits specification. This provides a standardized format that enables automated changelog generation, semantic versioning, and clear history.

```
{type}({scope}): {description}

[optional body]

[optional footer(s)]

Types:
  feat:      New feature
  fix:       Bug fix
  refactor:  Code change that neither fixes a bug nor adds a feature
  test:      Adding or correcting tests
  docs:      Documentation only changes
  style:     Formatting, missing semicolons, etc. (no logic change)
  perf:      Performance improvement
  ci:        CI/CD pipeline changes
  chore:     Maintenance (dependency updates, etc.)
  build:     Build system or external dependency changes

Scopes:
  risk-manager, algo-engine, mt5-bridge, data-ingestion,
  monitoring, shared, infra, docs

Examples:
  feat(risk-manager): add correlated exposure check across instrument groups
  fix(mt5-bridge): handle partial fill response from MT5 terminal
  refactor(algo-engine): extract feature pipeline into separate module
  test(risk-manager): add property-based tests for position sizing
  ci(infra): add GPU test stage to pipeline
  docs(onboarding): update local setup instructions for Python 3.12

Breaking changes:
  feat(risk-manager)!: change position sizing API to accept RiskContext object

  BREAKING CHANGE: The calculate_position_size function now requires a
  RiskContext dataclass instead of individual parameters. All callers
  must be updated.
```

### Pull Request Template

Every pull request uses a standard template that ensures consistency and completeness:

```markdown
## Summary
<!-- What does this PR do? Why is it needed? -->

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Refactoring
- [ ] Infrastructure / CI/CD
- [ ] Documentation
- [ ] Tests

## Services Affected
- [ ] Algo Engine
- [ ] Risk Manager
- [ ] MT5 Bridge
- [ ] Data Ingestion
- [ ] ML Training
- [ ] Monitoring
- [ ] Shared Libraries
- [ ] Infrastructure

## Testing
<!-- How was this tested? Include test commands and output. -->
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] Backtesting validated (if applicable)

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Type hints added for all new functions
- [ ] Docstrings added for all new public functions
- [ ] No secrets or credentials in the code
- [ ] Breaking changes documented
- [ ] Configuration changes documented
- [ ] Related documentation updated
```

### Semantic Versioning

MONEYMAKER follows semantic versioning (SemVer) for releases: `MAJOR.MINOR.PATCH`. The version is maintained in a single source of truth -- the root `pyproject.toml` -- and propagated to all services during the build process.

- **MAJOR** increments when there are breaking changes to inter-service APIs (proto definitions, gRPC contracts, configuration schemas).
- **MINOR** increments when new features are added in a backward-compatible manner (new strategies, new data sources, new risk controls).
- **PATCH** increments for backward-compatible bug fixes, performance improvements, and documentation updates.

A `CHANGELOG.md` is maintained at the repository root and updated with every release. Changelog entries are generated from Conventional Commit messages using `git-cliff` or a similar tool, then reviewed and edited for clarity before release.

### Git Hooks

In addition to the pre-commit hooks described in section 11.3, we use a commit-msg hook to validate that commit messages follow the Conventional Commits format:

```bash
#!/usr/bin/env bash
# .git/hooks/commit-msg (managed by pre-commit)

commit_msg=$(cat "$1")
pattern='^(feat|fix|refactor|test|docs|style|perf|ci|chore|build)(\(.+\))?!?: .{1,72}'

if ! echo "$commit_msg" | head -1 | grep -qE "$pattern"; then
    echo "ERROR: Commit message does not follow Conventional Commits format."
    echo ""
    echo "Expected: {type}({scope}): {description}"
    echo "Example:  feat(risk-manager): add circuit breaker cooldown logic"
    echo ""
    echo "Your message: $(head -1 "$1")"
    exit 1
fi
```

---

## 11.6 Testing Strategy -- Unit Tests

### Philosophy

Unit tests are the foundation of MONEYMAKER's quality assurance pyramid. They are fast (the entire unit test suite runs in under sixty seconds), isolated (no database, no network, no filesystem dependencies), and focused (each test verifies a single behavior of a single unit). A unit is typically a function or a method. A unit test answers one question: "Given these inputs, does this function produce the expected output?"

For a trading system, unit tests are especially critical because they verify the mathematical correctness of financial calculations. A rounding error in position sizing, a sign error in P&L calculation, or an off-by-one in drawdown tracking can compound over thousands of trades into significant financial impact. Unit tests catch these errors before they reach production.

### Framework and Configuration

All Python services use `pytest` as the test framework. We use pytest over unittest because of its simpler syntax (plain functions instead of test classes), powerful fixture system, excellent plugin ecosystem, and superior error reporting.

The test configuration in `pyproject.toml` (shown in section 11.3) establishes the following conventions:

- Tests are discovered in the `tests/` directory of each service.
- Tests are marked with `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.slow` to allow selective execution.
- The default test run executes only unit tests: `pytest -m unit`.
- Coverage is measured by `pytest-cov` and must meet or exceed 80% for the service to pass CI.
- Async tests are handled automatically by `pytest-asyncio` with `asyncio_mode = "auto"`.

### Coverage Targets

The coverage target is 80% line coverage as a minimum, with branch coverage enabled. This is a floor, not a ceiling. Critical modules -- position sizing, risk checks, signal validation, order construction -- should approach 95% or higher. Utility code, configuration loaders, and simple data classes may have lower coverage without concern.

Coverage is measured per-service, not globally. Each service's CI step runs `pytest --cov=src/{service_name} --cov-report=term-missing --cov-fail-under=80`. If coverage drops below 80%, the CI pipeline fails and the PR cannot be merged.

Coverage metrics are tracked over time in Grafana. A declining coverage trend triggers a team discussion about testing discipline.

### Arrange-Act-Assert Pattern

Every unit test follows the Arrange-Act-Assert (AAA) pattern. This pattern provides a clear, consistent structure that makes tests easy to read, write, and maintain.

```python
def test_position_size_basic_calculation() -> None:
    """Position size should be risk amount divided by (SL distance * pip value)."""
    # Arrange
    equity = 10_000.0
    risk_per_trade = 0.01  # 1%
    stop_loss_distance = 50.0  # 50 pips
    pip_value = 10.0  # $10 per pip per lot (standard lot EURUSD)

    # Act
    result = calculate_position_size(
        equity=equity,
        risk_per_trade=risk_per_trade,
        stop_loss_distance=stop_loss_distance,
        pip_value=pip_value,
    )

    # Assert
    # Risk amount = $10,000 * 0.01 = $100
    # Position size = $100 / (50 pips * $10/pip) = 0.20 lots
    assert result == 0.20


def test_position_size_clamped_to_max() -> None:
    """Position size should never exceed max_lots regardless of calculation."""
    # Arrange
    equity = 1_000_000.0
    risk_per_trade = 0.02
    stop_loss_distance = 10.0
    pip_value = 10.0
    max_lots = 5.0

    # Act
    result = calculate_position_size(
        equity=equity,
        risk_per_trade=risk_per_trade,
        stop_loss_distance=stop_loss_distance,
        pip_value=pip_value,
        max_lots=max_lots,
    )

    # Assert
    assert result == max_lots


def test_position_size_rounds_down() -> None:
    """Position size should round down to nearest 0.01 lots, never up."""
    # Arrange -- values chosen to produce a non-round result
    equity = 10_000.0
    risk_per_trade = 0.01
    stop_loss_distance = 33.0  # Produces 0.030303... lots
    pip_value = 10.0

    # Act
    result = calculate_position_size(
        equity=equity,
        risk_per_trade=risk_per_trade,
        stop_loss_distance=stop_loss_distance,
        pip_value=pip_value,
    )

    # Assert -- should round DOWN to 0.30, not up to 0.31
    assert result == 0.30


def test_position_size_rejects_zero_equity() -> None:
    """Position sizing should reject zero or negative equity."""
    with pytest.raises(ValueError, match="Equity must be positive"):
        calculate_position_size(
            equity=0.0,
            risk_per_trade=0.01,
            stop_loss_distance=50.0,
            pip_value=10.0,
        )
```

### Mocking Strategy

Unit tests must be isolated from external dependencies. We use `pytest-mock` (a thin wrapper around `unittest.mock`) and `unittest.mock.AsyncMock` for async functions. The mocking strategy follows clear rules:

**Mock at the boundary.** We mock external dependencies (database, Redis, network, MT5, file system) at the point where our code crosses the boundary. We do not mock internal functions unless testing a specific interaction pattern.

**Mock return values, not implementations.** A mock should return realistic data, not empty objects. If a database query mock returns an empty list when it should return a list of positions, the test is not exercising the real code path.

**Prefer dependency injection over patching.** Instead of patching `redis.Redis` at the module level, inject the Redis client as a constructor parameter. This makes tests cleaner and avoids the fragility of patch paths.

```python
# Prefer this -- dependency injection
class RiskChecker:
    def __init__(self, db: DatabaseClient, redis: RedisClient) -> None:
        self._db = db
        self._redis = redis

    async def check_daily_loss(self, account_id: str) -> bool:
        closed_pnl = await self._db.get_daily_closed_pnl(account_id)
        open_pnl = await self._redis.get_open_positions_pnl(account_id)
        total_pnl = closed_pnl + open_pnl
        return total_pnl > -self._config.max_daily_loss


# In tests -- clean injection of mocks
async def test_daily_loss_check_within_limits() -> None:
    # Arrange
    mock_db = AsyncMock(spec=DatabaseClient)
    mock_db.get_daily_closed_pnl.return_value = -50.0

    mock_redis = AsyncMock(spec=RedisClient)
    mock_redis.get_open_positions_pnl.return_value = -30.0

    checker = RiskChecker(db=mock_db, redis=mock_redis)

    # Act
    result = await checker.check_daily_loss("account-001")

    # Assert
    assert result is True  # Total loss of $80 is within limits
```

### Fixtures

Pytest fixtures provide reusable test data and setup logic. We define fixtures at multiple levels:

- **Service-level fixtures** in `services/{name}/tests/conftest.py` for service-specific objects.
- **Shared fixtures** in `tests/fixtures/` for cross-service test data (sample market data, example signals, reference configurations).

```python
# services/risk-manager/tests/conftest.py
import pytest
from risk_manager.config import RiskManagerConfig
from risk_manager.position_sizer import PositionSizer


@pytest.fixture
def default_config() -> RiskManagerConfig:
    """Standard risk configuration for testing."""
    return RiskManagerConfig(
        max_position_size_lots=10.0,
        max_daily_loss_pct=2.0,
        circuit_breaker_consecutive_losses=3,
        circuit_breaker_cooldown_minutes=60,
        max_correlated_exposure_pct=5.0,
    )


@pytest.fixture
def position_sizer(default_config: RiskManagerConfig) -> PositionSizer:
    """Position sizer with default configuration."""
    return PositionSizer(config=default_config)


@pytest.fixture
def sample_signal() -> dict:
    """A realistic trading signal for testing."""
    return {
        "symbol": "EURUSD",
        "direction": "BUY",
        "confidence": 0.75,
        "strategy": "trend_following",
        "entry_price": 1.08500,
        "stop_loss": 1.08000,
        "take_profit": 1.09500,
        "timeframe": "H1",
        "regime": "trending",
        "timestamp": "2026-02-21T10:30:00Z",
    }


@pytest.fixture
def account_state() -> dict:
    """Simulated account state for testing."""
    return {
        "equity": 50_000.0,
        "balance": 50_200.0,
        "margin_used": 2_500.0,
        "free_margin": 47_500.0,
        "margin_level_pct": 2008.0,
        "open_positions": 2,
        "daily_closed_pnl": -150.0,
        "consecutive_losses": 1,
    }
```

### What to Test

The following categories of logic require comprehensive unit test coverage:

**Position sizing.** Every formula path: fixed-fractional, volatility-adjusted, Kelly criterion variant. Edge cases: zero equity, maximum lots cap, minimum lot size floor, exact boundary values, non-round results that require rounding.

**Risk rules.** Circuit breaker activation and deactivation. Drawdown limit enforcement. Correlation-based exposure limits. Daily loss limits. Consecutive loss counting. Each rule is tested in isolation with inputs that trigger the rule, inputs that are just below the threshold, and inputs that are well within acceptable limits.

**Order validation.** Stop-loss and take-profit price validation. Minimum distance checks. Volume validation against broker minimums and maximums. Symbol validation. Direction validation. Every field that the MT5 bridge accepts must be validated, and every invalid combination must produce a clear rejection.

**Feature engineering.** Technical indicators (RSI, MACD, Bollinger Bands, ATR) produce correct values for known input sequences. Feature normalization produces values in the expected range. Missing data handling (NaN propagation, forward fill, interpolation) works correctly.

**Data parsing.** Exchange-specific message formats are parsed correctly. Malformed messages produce clear errors rather than silent corruption. Timestamp normalization handles timezone conversions correctly. Price precision is preserved through the parsing pipeline.

**Configuration validation.** Invalid configuration values are rejected with clear error messages. Default values are applied when optional fields are omitted. Environment variable binding works correctly. Conflicting configuration values are detected.

### Parameterized Tests

When testing a function across many input combinations, we use `@pytest.mark.parametrize` to avoid test code duplication:

```python
@pytest.mark.parametrize(
    "equity, risk_pct, sl_pips, pip_val, expected",
    [
        (10_000, 0.01, 50, 10.0, 0.20),     # Standard case
        (10_000, 0.02, 50, 10.0, 0.40),     # Higher risk
        (10_000, 0.01, 100, 10.0, 0.10),    # Wider stop
        (10_000, 0.01, 50, 1.0, 2.00),      # Lower pip value (mini lot)
        (100_000, 0.01, 50, 10.0, 2.00),    # Larger account
        (1_000, 0.01, 50, 10.0, 0.02),      # Small account
        (500, 0.01, 200, 10.0, 0.00),       # Very small -- rounds to 0
    ],
    ids=[
        "standard",
        "higher_risk",
        "wider_stop",
        "mini_lots",
        "large_account",
        "small_account",
        "tiny_account_rounds_to_zero",
    ],
)
def test_position_size_parameterized(
    equity: float,
    risk_pct: float,
    sl_pips: float,
    pip_val: float,
    expected: float,
) -> None:
    """Position sizing produces correct results across a range of inputs."""
    result = calculate_position_size(
        equity=equity,
        risk_per_trade=risk_pct,
        stop_loss_distance=sl_pips,
        pip_value=pip_val,
    )
    assert result == expected
```

### Property-Based Testing with Hypothesis

For mathematical functions where the space of valid inputs is large, we supplement example-based tests with property-based tests using the Hypothesis library. Property-based tests do not check specific input-output pairs; they check invariants that must hold for all valid inputs.

```python
from hypothesis import given, settings, assume
from hypothesis import strategies as st


@given(
    equity=st.floats(min_value=100, max_value=10_000_000, allow_nan=False),
    risk_pct=st.floats(min_value=0.001, max_value=0.10, allow_nan=False),
    sl_pips=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False),
    pip_value=st.floats(min_value=0.01, max_value=100.0, allow_nan=False),
)
@settings(max_examples=1000)
def test_position_size_invariants(
    equity: float, risk_pct: float, sl_pips: float, pip_value: float
) -> None:
    """Position sizing must satisfy mathematical invariants for all valid inputs."""
    result = calculate_position_size(
        equity=equity,
        risk_per_trade=risk_pct,
        stop_loss_distance=sl_pips,
        pip_value=pip_value,
    )

    # Invariant 1: Result is never negative
    assert result >= 0.0

    # Invariant 2: Result never exceeds max_lots (default 10.0)
    assert result <= 10.0

    # Invariant 3: Risk from this position never exceeds intended risk
    actual_risk = result * sl_pips * pip_value
    intended_risk = equity * risk_pct
    assert actual_risk <= intended_risk + 0.01  # Allow for rounding

    # Invariant 4: Result has at most 2 decimal places
    assert result == round(result, 2)

    # Invariant 5: Result was rounded down, not up
    raw = (equity * risk_pct) / (sl_pips * pip_value)
    assert result <= min(raw, 10.0) + 0.001  # Small epsilon for float precision


@given(
    drawdown_values=st.lists(
        st.floats(min_value=-0.5, max_value=0.5, allow_nan=False),
        min_size=1,
        max_size=100,
    ),
)
def test_drawdown_tracker_never_reports_positive_drawdown(
    drawdown_values: list[float],
) -> None:
    """Drawdown should always be zero or negative (a loss from peak)."""
    tracker = DrawdownTracker()
    for value in drawdown_values:
        tracker.update(value)

    # Drawdown is always <= 0 (it represents distance below peak)
    assert tracker.current_drawdown <= 0.0
    assert tracker.max_drawdown <= 0.0
```

Property-based testing is particularly valuable for financial calculations because it can discover edge cases that a developer would never think to test manually -- extreme values, boundary conditions, and unusual combinations that exercise rare code paths.

---

## 11.7 Testing Strategy -- Integration Tests

### Purpose and Scope

Integration tests verify that components work correctly when connected to real infrastructure dependencies -- a real PostgreSQL database, a real Redis instance, real gRPC channels. They operate at a level above unit tests: where unit tests verify that a function computes the correct result given mocked inputs, integration tests verify that the function can actually retrieve those inputs from a database, process them, and store the results.

Integration tests are slower than unit tests (seconds per test instead of milliseconds), require running infrastructure (provided by Docker Compose or testcontainers), and are more complex to write and maintain. But they catch an entire category of bugs that unit tests cannot: SQL syntax errors, incorrect ORM mappings, Redis serialization mismatches, gRPC proto incompatibilities, connection pool exhaustion, and transaction isolation issues.

### Test Database

Integration tests run against a dedicated test database that is created fresh for each test session and destroyed afterward. This ensures test isolation -- no test depends on data left behind by a previous test, and no test contaminates the developer's local development database.

```python
# tests/integration/conftest.py
import asyncio
from typing import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from moneymaker_common.config import DatabaseConfig


TEST_DB_URL = "postgresql+asyncpg://moneymaker_test:test_password@localhost:5432/moneymaker_test"


@pytest_asyncio.fixture(scope="session")
async def test_db_engine():
    """Create a test database engine for the entire test session."""
    # Create the test database
    sys_conn = await asyncpg.connect(
        user="moneymaker_dev",
        password="dev_password_not_for_production",
        host="localhost",
        port=5432,
        database="postgres",
    )
    await sys_conn.execute("DROP DATABASE IF EXISTS moneymaker_test")
    await sys_conn.execute("CREATE DATABASE moneymaker_test OWNER moneymaker_dev")
    await sys_conn.close()

    engine = create_async_engine(TEST_DB_URL, echo=False)

    # Run migrations
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Enable TimescaleDB extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))

    yield engine

    await engine.dispose()

    # Clean up: drop test database
    sys_conn = await asyncpg.connect(
        user="moneymaker_dev",
        password="dev_password_not_for_production",
        host="localhost",
        port=5432,
        database="postgres",
    )
    await sys_conn.execute("DROP DATABASE IF EXISTS moneymaker_test")
    await sys_conn.close()


@pytest_asyncio.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session that rolls back after each test."""
    session_factory = async_sessionmaker(test_db_engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()  # Each test gets a clean slate
```

The key technique here is the transactional fixture: each test runs inside a database transaction that is rolled back at the end of the test. This is dramatically faster than creating and destroying the database for each test, while still providing full isolation.

### Test Redis

A dedicated Redis database (database index 15) is used for integration tests. It is flushed before each test to ensure isolation:

```python
@pytest_asyncio.fixture
async def test_redis():
    """Provide a clean Redis connection for integration tests."""
    import redis.asyncio as aioredis

    client = aioredis.Redis(host="localhost", port=6379, db=15, decode_responses=True)
    await client.flushdb()  # Clean slate for each test

    yield client

    await client.flushdb()
    await client.aclose()
```

### Service-to-Service Integration Tests

These tests verify that two services can communicate correctly over their shared protocol. For gRPC-based communication, the test starts a real gRPC server for the provider service and a real gRPC client for the consumer service, and verifies that requests and responses are correctly serialized, transmitted, and deserialized.

```python
@pytest.mark.integration
async def test_risk_check_grpc_round_trip(
    risk_manager_server: RiskManagerServer,
    risk_client: RiskManagerClient,
) -> None:
    """Verify that a risk check request survives the gRPC round trip."""
    # Arrange
    request = RiskCheckRequest(
        signal_id="sig-001",
        symbol="EURUSD",
        direction="BUY",
        confidence=0.82,
        proposed_volume=0.50,
        entry_price=1.08500,
        stop_loss=1.08000,
        take_profit=1.09500,
        account_equity=50_000.0,
        current_exposure={"EURUSD": 0.30, "GBPUSD": 0.20},
    )

    # Act
    response = await risk_client.check_risk(request)

    # Assert
    assert response.approved is True
    assert response.adjusted_volume == 0.50  # No adjustment needed
    assert response.risk_score < 0.5
    assert response.rejection_reason == ""
```

### gRPC Contract Testing

Contract tests verify that the Protocol Buffer definitions are compatible between the producer and consumer. When a `.proto` file changes, the contract tests detect if the change breaks backward compatibility:

```python
@pytest.mark.integration
def test_proto_backward_compatibility() -> None:
    """Verify that current proto definitions are backward-compatible with v1."""
    from google.protobuf import descriptor_pool

    # Load the current descriptor
    current = descriptor_pool.Default().FindMessageTypeByName(
        "moneymaker.trading.TradingSignal"
    )

    # Verify required fields still exist
    required_fields = ["signal_id", "symbol", "direction", "confidence", "timestamp"]
    current_field_names = {f.name for f in current.fields}

    for field in required_fields:
        assert field in current_field_names, (
            f"Required field '{field}' missing from TradingSignal proto. "
            f"This is a breaking change."
        )
```

### Database Migration Tests

Migration tests verify that Alembic migrations can be applied and rolled back cleanly. They run against a fresh database and apply migrations one at a time, verifying the schema state after each migration:

```python
@pytest.mark.integration
def test_migrations_apply_cleanly(test_db_url: str) -> None:
    """Every migration should apply cleanly to a fresh database."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    # Apply all migrations from scratch
    command.upgrade(alembic_cfg, "head")

    # Verify we can generate a diff and it is empty
    # (no model changes that are not captured in migrations)
    from alembic.autogenerate import compare_metadata

    # ... verification logic
```

### MT5 Mock Integration Tests

The mock MT5 connector described in section 11.3 is used for integration tests that verify the full order lifecycle without connecting to a real MetaTrader terminal:

```python
@pytest.mark.integration
async def test_order_lifecycle_with_mock_mt5(
    mock_mt5: MockMT5Connector,
    order_manager: OrderManager,
) -> None:
    """Test the full lifecycle: submit order -> fill -> track -> close."""
    # Submit order
    order_result = await order_manager.submit_order(
        symbol="EURUSD",
        direction="BUY",
        volume=0.10,
        price=1.08500,
        stop_loss=1.08000,
        take_profit=1.09500,
    )
    assert order_result.status == "FILLED"
    ticket = order_result.ticket

    # Verify position is tracked
    positions = await order_manager.get_open_positions()
    assert len(positions) == 1
    assert positions[0].ticket == ticket

    # Close position
    close_result = await order_manager.close_position(ticket)
    assert close_result.status == "CLOSED"

    # Verify position is no longer tracked
    positions = await order_manager.get_open_positions()
    assert len(positions) == 0
```

### Testcontainers

For CI environments where Docker Compose is not pre-configured, we use `testcontainers-python` to spin up ephemeral containers programmatically within the test session:

```python
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL+TimescaleDB container for the test session."""
    with PostgresContainer(
        image="timescale/timescaledb:latest-pg16",
        user="moneymaker_test",
        password="test_password",
        dbname="moneymaker_test",
    ) as pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container():
    """Start a Redis container for the test session."""
    with RedisContainer(image="redis:7-alpine") as r:
        yield r
```

Testcontainers automatically pull the required Docker images, start containers on random available ports (avoiding port conflicts with local services), and clean up after the test session completes. This makes integration tests fully self-contained and reproducible on any machine with Docker installed.

---

## 11.8 Testing Strategy -- End-to-End Tests

### Full Ecosystem Testing

End-to-end (E2E) tests validate the entire MONEYMAKER ecosystem working together. They start every service -- Data Ingestion, Algo Engine, Risk Manager, MT5 Bridge, Database, Redis, Monitoring -- and verify that data flows correctly from ingestion through signal generation through risk checking through execution. These tests are the final gate before deployment.

E2E tests run in a dedicated Docker Compose environment that mirrors production as closely as possible:

```yaml
# infrastructure/docker/docker-compose.test.yml
version: "3.9"

services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: moneymaker_test
      POSTGRES_PASSWORD: test_password
      POSTGRES_DB: moneymaker_test
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U moneymaker_test"]
      interval: 3s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      timeout: 3s
      retries: 10

  data-ingestion:
    build:
      context: ../../services/data-ingestion
      dockerfile: Dockerfile
    environment:
      MONEYMAKER_ENV: test
      MONEYMAKER_DATA_SOURCE: mock
    depends_on:
      redis:
        condition: service_healthy

  algo-engine:
    build:
      context: ../../services/algo-engine
      dockerfile: Dockerfile
    environment:
      MONEYMAKER_ENV: test
      MONEYMAKER_MODEL_PATH: /models/test-model
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy

  risk-manager:
    build:
      context: ../../services/risk-manager
      dockerfile: Dockerfile
    environment:
      MONEYMAKER_ENV: test
      MONEYMAKER_RISK_MAX_DAILY_LOSS_PCT: 5.0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  mt5-bridge:
    build:
      context: ../../services/mt5-bridge
      dockerfile: Dockerfile
    environment:
      MONEYMAKER_ENV: test
      MONEYMAKER_MT5_MOCK: "true"
    depends_on:
      redis:
        condition: service_healthy

  e2e-runner:
    build:
      context: ../../
      dockerfile: tests/e2e/Dockerfile
    environment:
      MONEYMAKER_ENV: test
    depends_on:
      data-ingestion:
        condition: service_started
      algo-engine:
        condition: service_started
      risk-manager:
        condition: service_started
      mt5-bridge:
        condition: service_started
    command: ["pytest", "tests/e2e/", "-v", "--tb=long", "-x"]
```

### Scenario Tests

E2E tests are organized around scenarios -- complete workflows that exercise the system from end to end. Each scenario tells a story.

**Happy Path -- Signal to Execution.** This is the golden path: data arrives, the Algo Engine generates a signal, the Risk Manager approves it, the MT5 Bridge executes the order, and the position appears in the tracking system. The test verifies every step.

```python
@pytest.mark.e2e
async def test_happy_path_signal_to_execution(e2e_ecosystem: EcosystemFixture) -> None:
    """Data ingestion -> AI signal -> risk approval -> MT5 execution."""
    # Step 1: Inject market data into the data ingestion mock source
    await e2e_ecosystem.inject_market_data(
        symbol="EURUSD",
        candles=generate_trending_candles(count=100, direction="up"),
    )

    # Step 2: Wait for Algo Engine to process and generate a signal
    signal = await e2e_ecosystem.wait_for_signal(
        symbol="EURUSD",
        timeout_seconds=30,
    )
    assert signal is not None
    assert signal.direction == "BUY"  # Uptrend should produce BUY
    assert signal.confidence > 0.5

    # Step 3: Verify Risk Manager approved the signal
    risk_decision = await e2e_ecosystem.get_risk_decision(signal.signal_id)
    assert risk_decision.approved is True

    # Step 4: Verify MT5 Bridge executed the order
    order = await e2e_ecosystem.wait_for_order(
        signal_id=signal.signal_id,
        timeout_seconds=10,
    )
    assert order.status == "FILLED"
    assert order.symbol == "EURUSD"
    assert order.direction == "BUY"
    assert order.volume > 0

    # Step 5: Verify position appears in tracking
    positions = await e2e_ecosystem.get_open_positions()
    assert any(p.ticket == order.ticket for p in positions)
```

**Circuit Breaker Scenario.** This test verifies that the circuit breaker trips after consecutive losses and prevents new trades during the cooldown period:

```python
@pytest.mark.e2e
async def test_circuit_breaker_trips_after_consecutive_losses(
    e2e_ecosystem: EcosystemFixture,
) -> None:
    """Three consecutive losing trades should trip the circuit breaker."""
    # Generate three losing trades
    for i in range(3):
        await e2e_ecosystem.inject_market_data(
            symbol="EURUSD",
            candles=generate_fake_signal_candles(direction="up"),
        )
        signal = await e2e_ecosystem.wait_for_signal("EURUSD", timeout_seconds=30)
        assert signal is not None

        # Simulate the trade hitting stop-loss
        await e2e_ecosystem.simulate_price_move(
            symbol="EURUSD",
            target_price=signal.stop_loss - 0.0005,  # Below stop-loss
        )

        # Wait for position to close at stop-loss
        await e2e_ecosystem.wait_for_position_close(timeout_seconds=15)

    # Now inject another signal -- it should be rejected by circuit breaker
    await e2e_ecosystem.inject_market_data(
        symbol="EURUSD",
        candles=generate_trending_candles(count=100, direction="down"),
    )
    signal = await e2e_ecosystem.wait_for_signal("EURUSD", timeout_seconds=30)

    if signal:
        risk_decision = await e2e_ecosystem.get_risk_decision(signal.signal_id)
        assert risk_decision.approved is False
        assert "circuit_breaker" in risk_decision.rejection_reason.lower()
```

**Recovery Scenario.** This test verifies that the system recovers correctly after a service restart -- positions are reloaded from the database, risk state is reconstructed, and trading resumes:

```python
@pytest.mark.e2e
async def test_system_recovery_after_brain_restart(
    e2e_ecosystem: EcosystemFixture,
) -> None:
    """Algo Engine should recover state after restart without losing positions."""
    # Open a position
    await e2e_ecosystem.inject_market_data(
        symbol="EURUSD",
        candles=generate_trending_candles(count=100, direction="up"),
    )
    signal = await e2e_ecosystem.wait_for_signal("EURUSD", timeout_seconds=30)
    order = await e2e_ecosystem.wait_for_order(signal.signal_id, timeout_seconds=10)

    # Restart the Algo Engine service
    await e2e_ecosystem.restart_service("algo-engine")

    # Verify position is still tracked after restart
    positions = await e2e_ecosystem.get_open_positions()
    assert any(p.ticket == order.ticket for p in positions)

    # Verify the brain can still generate new signals
    await e2e_ecosystem.inject_market_data(
        symbol="GBPUSD",
        candles=generate_trending_candles(count=100, direction="down"),
    )
    new_signal = await e2e_ecosystem.wait_for_signal("GBPUSD", timeout_seconds=30)
    assert new_signal is not None
```

**Kill Switch Scenario.** This test verifies that activating the kill switch immediately closes all positions and prevents new trades:

```python
@pytest.mark.e2e
async def test_kill_switch_closes_all_positions(
    e2e_ecosystem: EcosystemFixture,
) -> None:
    """Kill switch activation must close all positions within 5 seconds."""
    # Open multiple positions
    for symbol in ["EURUSD", "GBPUSD", "USDJPY"]:
        await e2e_ecosystem.open_test_position(symbol=symbol, volume=0.10)

    positions_before = await e2e_ecosystem.get_open_positions()
    assert len(positions_before) == 3

    # Activate kill switch
    await e2e_ecosystem.activate_kill_switch(reason="E2E test")

    # All positions should close within 5 seconds
    await asyncio.sleep(5)
    positions_after = await e2e_ecosystem.get_open_positions()
    assert len(positions_after) == 0

    # New signals should be rejected
    await e2e_ecosystem.inject_market_data(
        symbol="EURUSD",
        candles=generate_trending_candles(count=50, direction="up"),
    )
    signal = await e2e_ecosystem.wait_for_signal("EURUSD", timeout_seconds=15)
    if signal:
        risk_decision = await e2e_ecosystem.get_risk_decision(signal.signal_id)
        assert risk_decision.approved is False
        assert "kill_switch" in risk_decision.rejection_reason.lower()
```

### Performance Benchmarks

E2E tests include performance benchmarks that verify the system meets its latency and throughput requirements:

```python
@pytest.mark.e2e
@pytest.mark.slow
async def test_signal_to_execution_latency(e2e_ecosystem: EcosystemFixture) -> None:
    """End-to-end latency from data arrival to order execution must be under 500ms."""
    latencies = []

    for _ in range(20):
        start = time.monotonic()
        await e2e_ecosystem.inject_market_data(
            symbol="EURUSD",
            candles=generate_trending_candles(count=50, direction="up"),
        )
        signal = await e2e_ecosystem.wait_for_signal("EURUSD", timeout_seconds=10)
        order = await e2e_ecosystem.wait_for_order(signal.signal_id, timeout_seconds=5)
        elapsed = time.monotonic() - start
        latencies.append(elapsed)

        # Clean up for next iteration
        await e2e_ecosystem.close_all_positions()

    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

    assert avg_latency < 0.300, f"Average latency {avg_latency:.3f}s exceeds 300ms"
    assert p95_latency < 0.500, f"P95 latency {p95_latency:.3f}s exceeds 500ms"
    assert p99_latency < 1.000, f"P99 latency {p99_latency:.3f}s exceeds 1000ms"
```

### Soak Tests

Soak tests run the system continuously for an extended period (one hour or more) under realistic load, monitoring for memory leaks, connection pool exhaustion, file descriptor leaks, and performance degradation over time. They are run nightly rather than on every PR.

```python
@pytest.mark.e2e
@pytest.mark.slow
async def test_soak_one_hour(e2e_ecosystem: EcosystemFixture) -> None:
    """Run the system for 1 hour under load, checking for resource leaks."""
    start_metrics = await e2e_ecosystem.collect_metrics()
    start_time = time.monotonic()
    duration_seconds = 3600  # 1 hour
    signals_processed = 0

    while time.monotonic() - start_time < duration_seconds:
        await e2e_ecosystem.inject_market_data(
            symbol="EURUSD",
            candles=generate_random_candles(count=10),
        )
        await asyncio.sleep(1)  # One signal per second
        signals_processed += 1

        # Check system health every 5 minutes
        if signals_processed % 300 == 0:
            health = await e2e_ecosystem.check_all_health()
            assert all(s.healthy for s in health.values()), (
                f"Service unhealthy after {signals_processed} signals: {health}"
            )

    end_metrics = await e2e_ecosystem.collect_metrics()

    # Memory should not grow more than 20% over the soak period
    for service in ["algo-engine", "risk-manager", "mt5-bridge"]:
        memory_growth = (
            end_metrics[service].memory_mb - start_metrics[service].memory_mb
        ) / start_metrics[service].memory_mb
        assert memory_growth < 0.20, (
            f"{service} memory grew by {memory_growth:.1%} "
            f"({start_metrics[service].memory_mb:.0f}MB -> "
            f"{end_metrics[service].memory_mb:.0f}MB)"
        )
```

---

## 11.9 Testing Strategy -- Backtesting and Validation

### Historical Data Replay

Backtesting is the process of running the trading strategy against historical market data to evaluate its performance. In MONEYMAKER, backtesting is not a separate system -- it uses the same Algo Engine and Risk Manager code that runs in production, but feeds it historical data instead of live data. This ensures that the backtesting results accurately reflect the behavior of the production system.

The backtesting framework replays historical data bar-by-bar through the full pipeline: feature engineering, signal generation, risk checking, and simulated execution. Each step uses the same code path as live trading, with only the data source and execution layer swapped out.

```python
class BacktestEngine:
    """Replays historical data through the production trading pipeline.

    Uses the same Algo Engine and Risk Manager code as production,
    with a simulated execution engine that tracks virtual positions.
    """

    def __init__(
        self,
        model_path: str,
        config: BacktestConfig,
        initial_equity: float = 100_000.0,
    ) -> None:
        self._model = load_model(model_path)
        self._config = config
        self._brain = AIBrain(model=self._model, config=config.brain_config)
        self._risk_manager = RiskManager(config=config.risk_config)
        self._executor = SimulatedExecutor(
            initial_equity=initial_equity,
            slippage_model=config.slippage_model,
            commission_model=config.commission_model,
        )
        self._results: list[TradeResult] = []

    async def run(
        self,
        data: pd.DataFrame,
        symbol: str,
    ) -> BacktestReport:
        """Run backtest on historical data.

        Args:
            data: OHLCV DataFrame with DatetimeIndex.
            symbol: Trading symbol (e.g., "EURUSD").

        Returns:
            BacktestReport with performance metrics and trade log.
        """
        for timestamp, bar in data.iterrows():
            # Update the simulated market state
            self._executor.update_market_price(symbol, bar["close"])

            # Check for stop-loss and take-profit hits on open positions
            self._executor.check_exit_conditions(bar["high"], bar["low"])

            # Generate features and signal (same code as production)
            features = self._brain.compute_features(symbol, data.loc[:timestamp])
            signal = self._brain.generate_signal(features)

            if signal is not None:
                # Risk check (same code as production)
                risk_result = self._risk_manager.check(
                    signal=signal,
                    account_state=self._executor.account_state,
                )
                if risk_result.approved:
                    self._executor.execute(signal, risk_result.adjusted_volume)

        return self._generate_report()
```

### Walk-Forward Validation

Walk-forward validation is the gold standard for evaluating trading strategies. It prevents overfitting by ensuring that the model is always evaluated on data it has never seen during training. The process divides historical data into sequential segments, trains on earlier segments, and tests on the immediately following segment:

```
|--- Train Window 1 ---|--- Test 1 ---|
         |--- Train Window 2 ---|--- Test 2 ---|
                  |--- Train Window 3 ---|--- Test 3 ---|
                           |--- Train Window 4 ---|--- Test 4 ---|
```

```python
class WalkForwardValidator:
    """Implements walk-forward validation for trading strategies.

    Divides data into rolling train/test windows to prevent look-ahead bias.
    Reports out-of-sample metrics that reflect realistic performance.
    """

    def __init__(
        self,
        train_window_days: int = 252,    # 1 year of trading days
        test_window_days: int = 63,       # 1 quarter
        step_days: int = 21,              # 1 month step
        min_trades_per_window: int = 30,  # Statistical significance
    ) -> None:
        self._train_window = train_window_days
        self._test_window = test_window_days
        self._step = step_days
        self._min_trades = min_trades_per_window

    def validate(
        self,
        data: pd.DataFrame,
        model_factory: Callable,
        strategy_config: StrategyConfig,
    ) -> WalkForwardReport:
        """Run walk-forward validation across all windows.

        Returns:
            WalkForwardReport with per-window and aggregate metrics.
        """
        windows = self._generate_windows(data)
        window_results: list[WindowResult] = []

        for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
            train_data = data.loc[train_start:train_end]
            test_data = data.loc[test_start:test_end]

            # Train model on training window
            model = model_factory()
            model.fit(train_data)

            # Backtest on test window (out-of-sample)
            engine = BacktestEngine(model=model, config=strategy_config)
            result = engine.run(test_data)

            if result.total_trades < self._min_trades:
                logger.warning(
                    "insufficient_trades_in_window",
                    window=i,
                    trades=result.total_trades,
                    required=self._min_trades,
                )

            window_results.append(WindowResult(
                window_index=i,
                train_period=(train_start, train_end),
                test_period=(test_start, test_end),
                metrics=result.metrics,
                trades=result.trades,
            ))

        return self._compile_report(window_results)
```

### Out-of-Sample Testing

Beyond walk-forward validation, we reserve a final holdout period that is never used for any training, hyperparameter tuning, or model selection. This "lockbox" dataset provides the ultimate sanity check before deploying a model to production. If the model performs well on walk-forward test windows but poorly on the final holdout, it suggests that the walk-forward procedure itself introduced subtle overfitting (for example, through hyperparameter choices influenced by aggregate walk-forward results).

The holdout period is at least six months of recent data. It is applied exactly once per model version. Results from the holdout test are recorded but never used to modify the model -- doing so would defeat the purpose of the holdout.

### Transaction Cost Modeling

Backtesting without realistic transaction costs produces dangerously misleading results. MONEYMAKER's backtesting framework models three components of transaction costs:

**Spread.** The bid-ask spread is modeled per-symbol using historical spread data. For major pairs like EURUSD, the spread averages 0.8-1.2 pips during liquid hours and widens to 2-5 pips during low-liquidity periods (Asian session open, major news events). The backtest applies the appropriate spread based on the time of day.

**Slippage.** Market orders are filled at prices that differ from the quoted price, especially during volatile conditions. The backtest models slippage as a random variable drawn from a distribution calibrated to historical fill data: typically 0-0.5 pips for normal conditions, 0-3 pips for volatile conditions.

**Commission.** Broker commissions are modeled as a fixed cost per lot per side (round-turn). The default value is calibrated to the broker's actual commission schedule.

```python
@dataclass
class TransactionCostModel:
    """Models realistic trading costs for backtesting."""

    spread_by_symbol: dict[str, SpreadModel]
    slippage_std_pips: float = 0.3
    commission_per_lot_round_turn: float = 7.0  # USD

    def calculate_entry_cost(
        self,
        symbol: str,
        volume: float,
        timestamp: datetime,
        volatility: float,
    ) -> float:
        """Calculate total cost of entering a position."""
        spread_cost = self.spread_by_symbol[symbol].get_spread(
            timestamp=timestamp,
            volatility=volatility,
        ) * volume * self._pip_value(symbol)

        slippage_cost = abs(
            random.gauss(0, self.slippage_std_pips)
        ) * volume * self._pip_value(symbol)

        commission = self.commission_per_lot_round_turn * volume / 2  # Half on entry

        return spread_cost + slippage_cost + commission
```

### Data Snooping Prevention

Data snooping -- the unconscious or deliberate use of future information in strategy calibration and evaluation -- is one of the most insidious threats to backtest validity. MONEYMAKER implements several safeguards:

**Strict temporal ordering.** The feature engineering pipeline enforces that features at time T are computed using only data available at or before time T. No future values are used, even accidentally. This is validated by a test that checks for look-ahead bias in every feature computation.

**Feature timestamp validation.** Every feature includes a `computed_at` timestamp and a `data_through` timestamp. The `data_through` timestamp must be strictly less than the signal generation timestamp. If this invariant is violated, the backtest framework raises an error.

**Separate hyperparameter tuning.** Hyperparameters are tuned only on the training portion of the walk-forward windows, never on the test portion. The hyperparameter search uses cross-validation within the training window, not the test window.

**No manual cherry-picking.** Walk-forward results are reported for all windows, not just the best-performing ones. Aggregate metrics (mean, median, worst-case) are the primary evaluation criteria, not individual window performance.

### Statistical Significance

A backtest that produces positive returns is not necessarily evidence of a profitable strategy. The returns could be due to chance. MONEYMAKER requires statistical significance testing before a strategy is promoted to production:

**Minimum trade count.** A backtest must contain at least 200 trades for statistical relevance. Strategies that trade infrequently (fewer than 200 trades over the backtest period) require longer backtest periods.

**t-test on returns.** A one-sample t-test determines whether the mean per-trade return is significantly different from zero. A p-value below 0.05 is required for promotion.

**Monte Carlo permutation test.** The trade returns are randomly shuffled 10,000 times, and the Sharpe ratio of each shuffled sequence is computed. The actual Sharpe ratio must exceed the 95th percentile of the permuted distribution to demonstrate that the strategy's performance is not attributable to random ordering of returns.

**Regime stability.** The strategy must be profitable in at least 60% of walk-forward windows. A strategy that is highly profitable in one window and deeply unprofitable in others is fragile and should not be deployed.

### Automated Backtest Reports

Every backtest run produces a standardized report that is stored in the database and viewable through the monitoring dashboard:

```python
@dataclass
class BacktestReport:
    """Comprehensive backtest results."""

    # Identification
    report_id: str
    model_version: str
    strategy: str
    symbol: str
    backtest_period: tuple[datetime, datetime]
    generated_at: datetime

    # Performance metrics
    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    calmar_ratio: float
    profit_factor: float

    # Trade statistics
    total_trades: int
    win_rate_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    largest_win_pct: float
    largest_loss_pct: float
    avg_holding_period_hours: float
    max_consecutive_wins: int
    max_consecutive_losses: int

    # Risk metrics
    avg_exposure_pct: float
    max_exposure_pct: float
    var_95_pct: float  # Value at Risk (95th percentile)
    cvar_95_pct: float  # Conditional VaR

    # Statistical tests
    ttest_pvalue: float
    monte_carlo_percentile: float
    walk_forward_consistency_pct: float

    # Transaction costs
    total_spread_cost: float
    total_slippage_cost: float
    total_commission_cost: float
    cost_as_pct_of_gross_profit: float
```

---

## 11.10 Continuous Integration

### Pipeline Architecture

MONEYMAKER uses GitHub Actions as its CI platform. The pipeline is triggered on every push to a feature branch and on every pull request targeting `main`. The pipeline is structured as a sequence of stages, where each stage must pass before the next begins. Failure at any stage stops the pipeline and notifies the developer.

```
+----------+     +-----------+     +-------------+     +----------+
|          |     |           |     |             |     |          |
|   Lint   |---->| Unit Test |---->| Integration |---->| Security |
|          |     |           |     |    Test     |     |   Scan   |
+----------+     +-----------+     +-------------+     +----------+
                                                            |
                                                            v
                                                    +--------------+
                                                    |              |
                                                    | Docker Build |
                                                    |   & Push     |
                                                    +--------------+
                                                            |
                                                            v
                                                    +--------------+
                                                    |              |
                                                    |   Coverage   |
                                                    |   Report     |
                                                    +--------------+
```

### CI Pipeline Definition

```yaml
# .github/workflows/ci.yml
name: MONEYMAKER CI Pipeline

on:
  push:
    branches: [main, "feature/**", "fix/**", "refactor/**"]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"
  GO_VERSION: "1.22"
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ghcr.io/${{ github.repository }}

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # ─── Stage 1: Lint ──────────────────────────────────
  lint-python:
    name: Lint Python
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: lint-pip-${{ hashFiles('**/pyproject.toml') }}

      - name: Install linting tools
        run: pip install black==23.12.1 isort==5.13.2 ruff==0.1.9 mypy==1.8.0

      - name: Run Black
        run: black --check --line-length 100 services/ shared/ tests/

      - name: Run isort
        run: isort --check-only --profile black --line-length 100 services/ shared/ tests/

      - name: Run Ruff
        run: ruff check services/ shared/ tests/

      - name: Run mypy
        run: |
          for service in algo-engine risk-manager mt5-bridge monitoring; do
            echo "::group::mypy services/$service"
            cd services/$service
            pip install -e ".[dev]" --quiet
            mypy src/
            cd ../..
            echo "::endgroup::"
          done

  lint-go:
    name: Lint Go
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: ${{ env.GO_VERSION }}

      - name: Run golangci-lint
        uses: golangci/golangci-lint-action@v4
        with:
          working-directory: services/data-ingestion
          version: latest

  lint-docker:
    name: Lint Dockerfiles
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Hadolint
        uses: hadolint/hadolint-action@v3.1.0
        with:
          recursive: true

  # ─── Stage 2: Unit Tests ────────────────────────────
  unit-tests:
    name: Unit Tests (${{ matrix.service }})
    needs: [lint-python, lint-go, lint-docker]
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        service:
          - algo-engine
          - risk-manager
          - mt5-bridge
          - monitoring
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pip
            services/${{ matrix.service }}/.venv
          key: deps-${{ matrix.service }}-${{ hashFiles(format('services/{0}/pyproject.toml', matrix.service)) }}

      - name: Install dependencies
        run: |
          cd services/${{ matrix.service }}
          python -m venv .venv
          source .venv/bin/activate
          pip install -e ".[dev]" --quiet
          pip install -e ../../shared/python-common --quiet

      - name: Run unit tests
        run: |
          cd services/${{ matrix.service }}
          source .venv/bin/activate
          pytest tests/unit/ \
            -m unit \
            --cov=src/ \
            --cov-report=xml:coverage.xml \
            --cov-report=term-missing \
            --cov-fail-under=80 \
            --junitxml=junit.xml \
            -v

      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-${{ matrix.service }}
          path: services/${{ matrix.service }}/coverage.xml

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: junit-${{ matrix.service }}
          path: services/${{ matrix.service }}/junit.xml

  unit-tests-go:
    name: Unit Tests (data-ingestion)
    needs: [lint-python, lint-go, lint-docker]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: ${{ env.GO_VERSION }}

      - name: Run Go tests
        run: |
          cd services/data-ingestion
          go test -v -race -coverprofile=coverage.out ./...
          go tool cover -func=coverage.out

      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-data-ingestion
          path: services/data-ingestion/coverage.out

  # ─── Stage 3: Integration Tests ─────────────────────
  integration-tests:
    name: Integration Tests
    needs: [unit-tests, unit-tests-go]
    runs-on: ubuntu-latest
    services:
      postgres:
        image: timescale/timescaledb:latest-pg16
        env:
          POSTGRES_USER: moneymaker_test
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: moneymaker_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U moneymaker_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install all services
        run: |
          python -m venv .venv
          source .venv/bin/activate
          for service in algo-engine risk-manager mt5-bridge monitoring; do
            pip install -e "services/$service[dev]" --quiet
          done
          pip install -e shared/python-common --quiet

      - name: Run Alembic migrations
        env:
          MONEYMAKER_DB_HOST: localhost
          MONEYMAKER_DB_PORT: 5432
          MONEYMAKER_DB_NAME: moneymaker_test
          MONEYMAKER_DB_USER: moneymaker_test
          MONEYMAKER_DB_PASSWORD: test_password
        run: |
          source .venv/bin/activate
          alembic upgrade head

      - name: Run integration tests
        env:
          MONEYMAKER_DB_HOST: localhost
          MONEYMAKER_DB_PORT: 5432
          MONEYMAKER_DB_NAME: moneymaker_test
          MONEYMAKER_DB_USER: moneymaker_test
          MONEYMAKER_DB_PASSWORD: test_password
          MONEYMAKER_REDIS_HOST: localhost
          MONEYMAKER_REDIS_PORT: 6379
        run: |
          source .venv/bin/activate
          pytest tests/ -m integration -v --tb=long -x

  # ─── Stage 4: Security Scan ─────────────────────────
  security-scan:
    name: Security Scan
    needs: [unit-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Run Bandit (Python security linter)
        run: |
          pip install bandit[toml]
          bandit -r services/ shared/ -c pyproject.toml -f json -o bandit-report.json || true
          bandit -r services/ shared/ -c pyproject.toml

      - name: Run Safety (dependency vulnerability check)
        run: |
          pip install safety
          for service in algo-engine risk-manager mt5-bridge monitoring; do
            echo "::group::Safety check: $service"
            cd services/$service
            pip install -e . --quiet
            safety check --full-report
            cd ../..
            echo "::endgroup::"
          done

      - name: Run Trivy (filesystem scan)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          scan-ref: .
          severity: HIGH,CRITICAL

  # ─── Stage 5: Docker Build ──────────────────────────
  docker-build:
    name: Docker Build (${{ matrix.service }})
    needs: [integration-tests, security-scan]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service:
          - data-ingestion
          - algo-engine
          - risk-manager
          - mt5-bridge
          - monitoring
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/${{ matrix.service }}/Dockerfile
          push: ${{ github.ref == 'refs/heads/main' }}
          tags: |
            ${{ env.IMAGE_PREFIX }}/${{ matrix.service }}:${{ github.sha }}
            ${{ env.IMAGE_PREFIX }}/${{ matrix.service }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ─── Stage 6: Coverage Report ───────────────────────
  coverage-report:
    name: Coverage Report
    needs: [unit-tests, unit-tests-go]
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4

      - name: Download all coverage artifacts
        uses: actions/download-artifact@v4
        with:
          pattern: coverage-*
          merge-multiple: true

      - name: Generate coverage summary
        run: |
          pip install coverage
          coverage combine *.xml || true
          coverage report --show-missing
```

### Pipeline Triggers and Caching

The CI pipeline uses several optimizations to keep build times short:

**Concurrency control.** The `concurrency` setting cancels any in-progress CI run for the same branch when a new push arrives. This prevents wasted compute on superseded commits.

**Matrix strategy.** Unit tests run in parallel for each service using a matrix strategy. A failure in one service does not cancel tests for other services (`fail-fast: false`), allowing developers to see all failures at once.

**Dependency caching.** Pip packages and Go modules are cached using `actions/cache`. The cache key includes the hash of the dependency files (`pyproject.toml`, `go.mod`), so the cache is invalidated when dependencies change.

**Build layer caching.** Docker builds use GitHub Actions cache (`type=gha`) to cache intermediate layers. This reduces Docker build times from minutes to seconds for builds that only change application code without modifying dependencies.

**Secrets management.** Database passwords, API keys, and other secrets are stored as GitHub Actions secrets and injected as environment variables. They never appear in workflow files or logs.

---

## 11.11 Continuous Deployment

### Deployment Strategy

MONEYMAKER follows a staged deployment strategy: changes that pass CI are first deployed to a staging environment for validation, then promoted to production after automated and manual checks confirm correct behavior. The goal is to deploy frequently (multiple times per week) with confidence.

```
+--------+     +---------+     +----------------+     +------------+
|        |     |         |     |                |     |            |
| CI Pass|---->| Staging |---->| Deployment     |---->| Production |
|        |     | Deploy  |     | Gate (Manual)  |     | Deploy     |
+--------+     +---------+     +----------------+     +------------+
                    |                                       |
                    v                                       v
              +-----------+                           +-----------+
              | Smoke     |                           | Smoke     |
              | Tests     |                           | Tests     |
              +-----------+                           +-----------+
                    |                                       |
                    v                                       v
              +-----------+                           +-----------+
              | Monitor   |                           | Monitor   |
              | 30 min    |                           | 60 min    |
              +-----------+                           +-----------+
```

### Staging Environment

The staging environment is a complete replica of the production ecosystem running on the same Proxmox server in separate VMs. It uses the same Docker images, the same configuration structure, and the same monitoring stack. The only differences are: it connects to a paper trading account (not a live account), it uses a separate database, and its resource allocations are smaller.

Staging deployments are triggered automatically when a commit is merged to `main` and CI passes. The deployment process:

1. Pull the new Docker images (tagged with the commit SHA) to the staging VMs.
2. Run database migrations in staging.
3. Perform a rolling restart of services in dependency order: Database first, then Data Ingestion, then Algo Engine, then Risk Manager, then MT5 Bridge, then Monitoring.
4. Run automated smoke tests against the staging environment.
5. Monitor staging for 30 minutes, checking for error rate spikes, latency degradation, and health check failures.

### Rolling Updates

Services are updated one at a time using rolling updates. During a rolling update, the old version of a service continues running until the new version passes its health check. If the new version fails to start or fails its health check, the rollout is automatically halted and the old version remains active.

For single-instance services (which is the case in MONEYMAKER V1, where each service runs as one instance), "rolling update" means: start the new container, wait for its health check to pass, then stop the old container. There is a brief period where both containers are running, but only one is receiving traffic (determined by the service discovery mechanism -- in our case, Docker Compose service names or direct IP targeting via Ansible).

### Blue-Green Deployments

For high-risk deployments -- changes to the Risk Manager, MT5 Bridge, or core Algo Engine strategy logic -- we use blue-green deployments. Two complete environments exist: Blue (currently serving) and Green (receiving the update). Traffic is switched from Blue to Green only after Green passes all health checks, smoke tests, and a manual verification step.

```
Before deployment:
  Blue  (v1.2.3) <--- [ACTIVE] --- Traffic
  Green (v1.2.2) --- [IDLE]

During deployment:
  Blue  (v1.2.3) <--- [ACTIVE] --- Traffic
  Green (v1.2.4) --- [STARTING, HEALTH CHECKS]

After verification:
  Blue  (v1.2.3) --- [STANDBY]
  Green (v1.2.4) <--- [ACTIVE] --- Traffic

Rollback (if needed):
  Blue  (v1.2.3) <--- [ACTIVE] --- Traffic    (instant switch)
  Green (v1.2.4) --- [STOPPED]
```

Blue-green deployments provide instant rollback: if the new version misbehaves in production, traffic is switched back to the old version in seconds, without waiting for a container restart.

### Canary Deployments for AI Models

AI model updates carry unique risk because model behavior is inherently probabilistic. A model that performed well in backtesting and walk-forward validation might behave unexpectedly on live data due to distribution shift. For model deployments, we use a canary strategy:

1. Deploy the new model alongside the existing model.
2. Route a small percentage of signals (10%) through the new model while the existing model continues to handle 90%.
3. Compare the signal quality, risk metrics, and simulated P&L of the new model against the existing model over a defined evaluation period (one trading week).
4. If the new model meets or exceeds the performance of the existing model, gradually increase its traffic share (10% -> 25% -> 50% -> 100%).
5. If the new model underperforms, roll back to the existing model with no impact on live trading.

### Deployment Gates

Certain deployments require manual approval before proceeding. The deployment gate is implemented as a GitHub Actions environment with required reviewers:

```yaml
# In the deployment workflow
deploy-production:
  name: Deploy to Production
  needs: [deploy-staging, smoke-test-staging]
  runs-on: ubuntu-latest
  environment:
    name: production
    url: https://moneymaker-monitoring.internal
  steps:
    - name: Deploy to production VMs
      run: |
        ansible-playbook \
          -i infrastructure/ansible/inventory/production.yml \
          infrastructure/ansible/playbooks/deploy.yml \
          --extra-vars "image_tag=${{ github.sha }}"
```

The `production` environment is configured in GitHub with required reviewers. The deployment is paused until an authorized team member approves it through the GitHub UI. This provides a human checkpoint for high-impact changes.

### Rollback Procedure

Rollback is a first-class operation, not an afterthought. Every deployment records the previous version, and rollback restores that version:

```bash
# Rollback to previous version
ansible-playbook \
  -i infrastructure/ansible/inventory/production.yml \
  infrastructure/ansible/playbooks/rollback.yml \
  --extra-vars "service=risk-manager"
```

The rollback playbook:

1. Identifies the previous Docker image tag from the deployment history.
2. Pulls the previous image (which is still in the local Docker cache or registry).
3. Stops the current container.
4. Starts a container with the previous image.
5. Verifies health checks pass.
6. Sends an alert notification with the rollback details.

Rollback does not reverse database migrations. Migrations are designed to be forward-only and backward-compatible (see section 11.14), so a rollback to the previous application version works with the current database schema.

### Database Migration Deployment

Database migrations are deployed as a separate step before application deployment. The migration process:

1. Run migrations against the staging database first.
2. Verify that the staging application works with the new schema.
3. Run migrations against the production database during a maintenance window (if the migration involves heavy operations like adding indexes to large tables) or inline with the deployment (if the migration is lightweight).
4. Deploy the new application version.

This two-phase approach ensures that a failed migration does not leave the system in an inconsistent state where the application expects a schema that does not exist.

### Configuration Deployment

Configuration changes follow the same staging-to-production pipeline as code changes. Configuration files are versioned in Git, and changes to configuration trigger the CI pipeline. Sensitive configuration (secrets, API keys) is managed through Ansible Vault and deployed separately from application configuration.

---

## 11.12 Docker and Containerization

### Dockerfile Best Practices

Every MONEYMAKER service is packaged as a Docker image. Our Dockerfiles follow a strict set of best practices that optimize for build speed, image size, security, and reproducibility.

**Multi-stage builds.** All Python service Dockerfiles use multi-stage builds: a builder stage installs dependencies and compiles wheels, and a final stage copies only the installed packages and application code. This keeps the final image small by excluding build tools, header files, and the pip cache.

**Slim base images.** We use `python:3.11-slim` as the base image, not `python:3.11` (which includes the full Debian distribution) and not `python:3.11-alpine` (which uses musl libc and breaks many Python packages that rely on glibc). The slim variant provides a good balance of compatibility and size.

**Non-root execution.** Containers run as a non-root user. The Dockerfile creates a dedicated `moneymaker` user and switches to it before the CMD instruction. This limits the damage that a compromised container can inflict.

**Health checks.** Every Dockerfile includes a HEALTHCHECK instruction that verifies the service is responding to requests. Docker uses this to determine when a container is ready to receive traffic and when it needs to be restarted.

**Deterministic builds.** Dependency installation uses lock files (poetry.lock) and pinned versions. The `--no-cache-dir` flag prevents pip from caching downloaded packages inside the container. The `PYTHONDONTWRITEBYTECODE=1` environment variable prevents Python from writing .pyc files.

Here is the reference Dockerfile for the Risk Manager service:

```dockerfile
# services/risk-manager/Dockerfile
# ─── Stage 1: Builder ─────────────────────────────────
FROM python:3.11-slim AS builder

# Prevent Python from writing bytecode and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies (needed for some Python packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for layer caching)
COPY services/risk-manager/pyproject.toml services/risk-manager/poetry.lock* ./service/
COPY shared/python-common/pyproject.toml ./shared/

# Install dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip setuptools wheel && \
    pip install ./shared/ && \
    pip install ./service/

# Copy application source
COPY shared/python-common/src/ ./shared/src/
COPY services/risk-manager/src/ ./service/src/

# Install the application itself
RUN pip install ./shared/ ./service/

# ─── Stage 2: Runtime ─────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime-only dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 moneymaker && \
    useradd --uid 1000 --gid moneymaker --create-home moneymaker

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /build/service/src/ /app/src/
COPY --from=builder /build/shared/src/ /app/shared/

WORKDIR /app

# Switch to non-root user
USER moneymaker

# Health check -- hits the /health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose service port
EXPOSE 8080

# Use tini as init system (handles signals properly)
ENTRYPOINT ["tini", "--"]

# Start the service
CMD ["python", "-m", "risk_manager.main"]
```

### Go Service Dockerfile

The Data Ingestion Service uses a Go-specific multi-stage build that produces a statically linked binary:

```dockerfile
# services/data-ingestion/Dockerfile
# ─── Stage 1: Builder ─────────────────────────────────
FROM golang:1.22-alpine AS builder

RUN apk add --no-cache git ca-certificates

WORKDIR /build

COPY services/data-ingestion/go.mod services/data-ingestion/go.sum ./
RUN go mod download

COPY services/data-ingestion/ .

# Build statically linked binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-s -w" -o /moneymaker-data-ingestion ./cmd/server/

# ─── Stage 2: Runtime ─────────────────────────────────
FROM gcr.io/distroless/static-debian12

COPY --from=builder /moneymaker-data-ingestion /usr/local/bin/
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

USER nonroot:nonroot

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/usr/local/bin/moneymaker-data-ingestion", "--healthcheck"]

EXPOSE 8081

ENTRYPOINT ["/usr/local/bin/moneymaker-data-ingestion"]
```

The Go final stage uses `distroless/static` -- the smallest possible base image that contains nothing but the binary and CA certificates. The resulting image is typically under 20MB.

### Docker Compose -- Full Ecosystem

The production Docker Compose file defines the full ecosystem with proper dependency ordering, resource limits, health checks, and network isolation:

```yaml
# infrastructure/docker/docker-compose.yml
version: "3.9"

x-common-environment: &common-env
  MONEYMAKER_ENV: production
  MONEYMAKER_LOG_LEVEL: INFO
  MONEYMAKER_LOG_FORMAT: json

x-healthcheck-defaults: &healthcheck-defaults
  interval: 15s
  timeout: 5s
  retries: 3
  start_period: 30s

services:
  # ─── Database Layer ──────────────────────────────────
  postgres:
    image: timescale/timescaledb:latest-pg16
    container_name: moneymaker-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${MONEYMAKER_DB_USER}
      POSTGRES_PASSWORD: ${MONEYMAKER_DB_PASSWORD}
      POSTGRES_DB: ${MONEYMAKER_DB_NAME}
      POSTGRES_INITDB_ARGS: "--data-checksums"
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - moneymaker_pgdata:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    deploy:
      resources:
        limits:
          cpus: "4.0"
          memory: 16G
        reservations:
          cpus: "2.0"
          memory: 8G
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD-SHELL", "pg_isready -U ${MONEYMAKER_DB_USER}"]
    networks:
      - moneymaker-internal

  redis:
    image: redis:7-alpine
    container_name: moneymaker-redis
    restart: unless-stopped
    command: >
      redis-server
        --maxmemory 2gb
        --maxmemory-policy allkeys-lru
        --appendonly yes
        --appendfsync everysec
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - moneymaker_redis_data:/data
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 3G
        reservations:
          cpus: "0.5"
          memory: 2G
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "redis-cli", "ping"]
    networks:
      - moneymaker-internal

  # ─── Data Layer ──────────────────────────────────────
  data-ingestion:
    image: ${REGISTRY}/data-ingestion:${IMAGE_TAG:-latest}
    container_name: moneymaker-data-ingestion
    restart: unless-stopped
    environment:
      <<: *common-env
      MONEYMAKER_REDIS_HOST: redis
      MONEYMAKER_REDIS_PORT: 6379
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
        reservations:
          cpus: "1.0"
          memory: 2G
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "/usr/local/bin/moneymaker-data-ingestion", "--healthcheck"]
    networks:
      - moneymaker-internal

  # ─── Intelligence Layer ──────────────────────────────
  algo-engine:
    image: ${REGISTRY}/algo-engine:${IMAGE_TAG:-latest}
    container_name: moneymaker-algo-engine
    restart: unless-stopped
    environment:
      <<: *common-env
      MONEYMAKER_DB_HOST: postgres
      MONEYMAKER_REDIS_HOST: redis
      MONEYMAKER_MODEL_PATH: /models/production
    volumes:
      - moneymaker_models:/models:ro
    deploy:
      resources:
        limits:
          cpus: "4.0"
          memory: 8G
        reservations:
          cpus: "2.0"
          memory: 4G
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      data-ingestion:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    networks:
      - moneymaker-internal

  # ─── Risk Layer ──────────────────────────────────────
  risk-manager:
    image: ${REGISTRY}/risk-manager:${IMAGE_TAG:-latest}
    container_name: moneymaker-risk-manager
    restart: unless-stopped
    environment:
      <<: *common-env
      MONEYMAKER_DB_HOST: postgres
      MONEYMAKER_REDIS_HOST: redis
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
        reservations:
          cpus: "1.0"
          memory: 2G
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    networks:
      - moneymaker-internal

  # ─── Execution Layer ─────────────────────────────────
  mt5-bridge:
    image: ${REGISTRY}/mt5-bridge:${IMAGE_TAG:-latest}
    container_name: moneymaker-mt5-bridge
    restart: unless-stopped
    environment:
      <<: *common-env
      MONEYMAKER_DB_HOST: postgres
      MONEYMAKER_REDIS_HOST: redis
      MONEYMAKER_MT5_HOST: ${MT5_TERMINAL_HOST}
      MONEYMAKER_MT5_PORT: ${MT5_TERMINAL_PORT}
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 1G
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      risk-manager:
        condition: service_healthy
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    networks:
      - moneymaker-internal

  # ─── Monitoring Layer ────────────────────────────────
  prometheus:
    image: prom/prometheus:latest
    container_name: moneymaker-prometheus
    restart: unless-stopped
    volumes:
      - ../prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - moneymaker_prometheus_data:/prometheus
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 4G
    healthcheck:
      <<: *healthcheck-defaults
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:9090/-/healthy"]
    networks:
      - moneymaker-internal

  grafana:
    image: grafana/grafana:latest
    container_name: moneymaker-grafana
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
    ports:
      - "127.0.0.1:3000:3000"
    volumes:
      - ../grafana/provisioning:/etc/grafana/provisioning:ro
      - ../grafana/dashboards:/var/lib/grafana/dashboards:ro
      - moneymaker_grafana_data:/var/lib/grafana
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G
    depends_on:
      prometheus:
        condition: service_healthy
    networks:
      - moneymaker-internal

  monitoring-dashboard:
    image: ${REGISTRY}/monitoring:${IMAGE_TAG:-latest}
    container_name: moneymaker-monitoring-dashboard
    restart: unless-stopped
    environment:
      <<: *common-env
      MONEYMAKER_DB_HOST: postgres
      MONEYMAKER_REDIS_HOST: redis
    ports:
      - "127.0.0.1:8501:8501"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - moneymaker-internal

volumes:
  moneymaker_pgdata:
    driver: local
  moneymaker_redis_data:
    driver: local
  moneymaker_models:
    driver: local
  moneymaker_prometheus_data:
    driver: local
  moneymaker_grafana_data:
    driver: local

networks:
  moneymaker-internal:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### Image Tagging Strategy

Docker images are tagged with both the Git commit SHA and a semantic version:

- `ghcr.io/moneymaker/risk-manager:a1b2c3d` -- commit SHA for traceability
- `ghcr.io/moneymaker/risk-manager:1.2.3` -- semantic version for releases
- `ghcr.io/moneymaker/risk-manager:latest` -- latest build from main (mutable tag)

The commit SHA tag is immutable and used for deployment. The `latest` tag is a convenience for development. Production deployments always specify the exact commit SHA, never `latest`.

### Resource Limits and Networks

Every container has explicit CPU and memory limits. This prevents a misbehaving service from consuming all host resources and affecting other services. The limits are calibrated to the Proxmox VM's allocated resources and the service's observed resource usage.

All MONEYMAKER services communicate over a dedicated Docker bridge network (`moneymaker-internal`). Ports are bound to `127.0.0.1` only, preventing external access. External access is provided through an Nginx reverse proxy (described in Document 12 -- Security).

---

## 11.13 Proxmox Deployment

### Deployment Architecture

MONEYMAKER V1 runs on a single Proxmox VE server (AMD Ryzen 9 7950X, 128GB DDR5 RAM, AMD RX 9070 XT GPU, NVMe storage). The ecosystem is distributed across multiple Proxmox VMs, each dedicated to a specific workload class:

```
Proxmox VE Host (bare metal)
|
|-- VM 100: moneymaker-data          (4 vCPU, 16GB RAM)
|   |-- PostgreSQL + TimescaleDB
|   +-- Redis
|
|-- VM 101: moneymaker-compute       (8 vCPU, 32GB RAM)
|   |-- Algo Engine
|   |-- Risk Manager
|   +-- MT5 Bridge
|
|-- VM 102: moneymaker-ingestion     (4 vCPU, 8GB RAM)
|   +-- Data Ingestion Service (Go)
|
|-- VM 104: moneymaker-monitor       (4 vCPU, 8GB RAM)
|   |-- Prometheus
|   |-- Grafana
|   +-- Streamlit Dashboard
|
+-- VM 105: moneymaker-staging       (4 vCPU, 16GB RAM)
    +-- Complete staging environment
```

### Ansible Playbooks

Deployment is automated through Ansible. Playbooks define the deployment process declaratively, ensuring that deployments are reproducible and auditable.

```yaml
# infrastructure/ansible/playbooks/deploy.yml
---
- name: Deploy MONEYMAKER services
  hosts: "{{ target_hosts | default('production') }}"
  become: true
  serial: 1  # Deploy to one host at a time
  vars:
    image_tag: "{{ lookup('env', 'IMAGE_TAG') | default('latest') }}"

  pre_tasks:
    - name: Verify deployment prerequisites
      assert:
        that:
          - image_tag != 'latest' or moneymaker_env == 'staging'
          - ansible_facts['os_family'] == 'Debian'
        fail_msg: "Production deployments require an explicit image tag"

    - name: Create deployment record
      uri:
        url: "http://{{ monitoring_host }}:8080/api/deployments"
        method: POST
        body_format: json
        body:
          environment: "{{ moneymaker_env }}"
          image_tag: "{{ image_tag }}"
          deployer: "{{ lookup('env', 'USER') }}"
          timestamp: "{{ ansible_date_time.iso8601 }}"
      ignore_errors: true

  roles:
    - role: docker-login
      vars:
        registry: "{{ docker_registry }}"
        username: "{{ vault_registry_user }}"
        password: "{{ vault_registry_password }}"

    - role: pull-images
      vars:
        services: "{{ moneymaker_services[inventory_hostname] }}"
        tag: "{{ image_tag }}"

    - role: run-migrations
      when: "'data' in group_names"
      vars:
        db_host: localhost
        db_name: "{{ vault_db_name }}"
        db_user: "{{ vault_db_user }}"
        db_password: "{{ vault_db_password }}"

    - role: deploy-services
      vars:
        services: "{{ moneymaker_services[inventory_hostname] }}"
        tag: "{{ image_tag }}"

  post_tasks:
    - name: Run smoke tests
      command: >
        docker exec moneymaker-{{ item }} python -m {{ item.replace('-', '_') }}.healthcheck
      loop: "{{ moneymaker_services[inventory_hostname] }}"
      register: smoke_results
      retries: 3
      delay: 10
      until: smoke_results.rc == 0

    - name: Verify all health checks pass
      uri:
        url: "http://localhost:8080/health"
        method: GET
        status_code: 200
      register: health_check
      retries: 5
      delay: 10
      until: health_check.status == 200

    - name: Update deployment record with success
      uri:
        url: "http://{{ monitoring_host }}:8080/api/deployments/{{ deployment_id }}"
        method: PATCH
        body_format: json
        body:
          status: "success"
          completed_at: "{{ ansible_date_time.iso8601 }}"
      ignore_errors: true
```

### Ansible Vault for Secrets

All sensitive configuration -- database passwords, API keys, broker credentials, registry credentials -- is encrypted using Ansible Vault. The vault password is stored securely and provided to the deployment pipeline through an environment variable or a vault password file.

```yaml
# infrastructure/ansible/group_vars/vault.yml (encrypted)
vault_db_password: "encrypted_production_password_here"
vault_redis_password: "encrypted_redis_password_here"
vault_mt5_password: "encrypted_mt5_password_here"
vault_registry_password: "encrypted_registry_token_here"
vault_grafana_admin_password: "encrypted_grafana_password_here"
```

### Deployment Order

Services are deployed in dependency order to ensure that each service's dependencies are available when it starts:

1. **Database layer** (PostgreSQL, Redis) -- always first, always verified healthy before proceeding.
2. **Data Ingestion** -- needs Redis for publishing.
3. **Algo Engine** -- needs Redis for data subscription, PostgreSQL for state.
4. **Risk Manager** -- needs PostgreSQL for risk state, Redis for real-time data.
5. **MT5 Bridge** -- needs Risk Manager for approval, PostgreSQL for trade logging.
6. **Monitoring** -- needs all services running to scrape metrics.

Each step waits for the health check of the deployed service to pass before proceeding to the next step. If a health check fails after the configured number of retries, the deployment is aborted and the operator is notified.

### Smoke Tests and Health Verification

After deployment, automated smoke tests verify that each service is functioning correctly:

```bash
#!/usr/bin/env bash
# scripts/ops/health-check.sh
set -euo pipefail

SERVICES=(
    "postgres:5432:pg_isready -U moneymaker"
    "redis:6379:redis-cli ping"
    "data-ingestion:8081:/health"
    "algo-engine:8080:/health"
    "risk-manager:8080:/health"
    "mt5-bridge:8080:/health"
    "prometheus:9090:/-/healthy"
    "grafana:3000:/api/health"
)

echo "=== MONEYMAKER Health Check ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

ALL_HEALTHY=true

for entry in "${SERVICES[@]}"; do
    IFS=: read -r name port endpoint <<< "$entry"
    printf "%-20s " "$name"

    if curl -sf "http://localhost:$port$endpoint" > /dev/null 2>&1; then
        echo "[HEALTHY]"
    else
        echo "[UNHEALTHY]"
        ALL_HEALTHY=false
    fi
done

echo ""
if [ "$ALL_HEALTHY" = true ]; then
    echo "Status: ALL SERVICES HEALTHY"
    exit 0
else
    echo "Status: ONE OR MORE SERVICES UNHEALTHY"
    exit 1
fi
```

### Runbooks

Deployment runbooks are maintained in `docs/runbooks/` and cover every operational procedure:

- **deployment.md** -- Step-by-step deployment procedure, including pre-deployment checks, deployment commands, post-deployment verification, and rollback instructions.
- **rollback.md** -- How to roll back each service independently, including database migration considerations.
- **incident-response.md** -- What to do when something goes wrong in production: triage, escalation, communication, resolution, post-mortem.
- **scaling.md** -- How to add resources to a VM, add a new VM, or redistribute services across VMs.

---

## 11.14 Database Migrations

### Alembic Configuration

MONEYMAKER uses Alembic for database schema migrations. Alembic provides version-controlled, reversible schema changes that can be applied programmatically. The migration configuration lives in the repository root:

```
alembic/
|-- alembic.ini
|-- env.py
|-- versions/
|   |-- 001_20260115_create_trades_table.py
|   |-- 002_20260118_add_signals_table.py
|   |-- 003_20260201_create_hypertable_ohlcv.py
|   |-- 004_20260210_add_risk_events.py
|   +-- 005_20260218_add_model_registry.py
+-- script.py.mako
```

### Naming Convention

Migration files follow a strict naming convention: `{sequence}_{date}_{description}.py`. The sequence number is a three-digit zero-padded integer. The date is in YYYYMMDD format. The description uses underscores and lowercase. This convention ensures that migrations are ordered correctly and are self-documenting.

```python
# alembic/versions/003_20260201_create_hypertable_ohlcv.py
"""Create hypertable for OHLCV data.

Revision ID: a3b4c5d6e7f8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-01 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = "a3b4c5d6e7f8"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create OHLCV table and convert to TimescaleDB hypertable."""
    op.create_table(
        "ohlcv",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("open", sa.Numeric(18, 8), nullable=False),
        sa.Column("high", sa.Numeric(18, 8), nullable=False),
        sa.Column("low", sa.Numeric(18, 8), nullable=False),
        sa.Column("close", sa.Numeric(18, 8), nullable=False),
        sa.Column("volume", sa.Numeric(24, 8), nullable=False),
        sa.Column("metadata", JSONB, server_default="{}"),
    )

    # Create indexes before converting to hypertable
    op.create_index(
        "ix_ohlcv_symbol_timeframe_time",
        "ohlcv",
        ["symbol", "timeframe", "time"],
    )

    # Convert to TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('ohlcv', 'time', "
        "chunk_time_interval => INTERVAL '7 days', "
        "if_not_exists => TRUE)"
    )

    # Enable compression on chunks older than 30 days
    op.execute(
        "ALTER TABLE ohlcv SET (timescaledb.compress, "
        "timescaledb.compress_segmentby = 'symbol,timeframe', "
        "timescaledb.compress_orderby = 'time DESC')"
    )
    op.execute(
        "SELECT add_compression_policy('ohlcv', INTERVAL '30 days', "
        "if_not_exists => TRUE)"
    )


def downgrade() -> None:
    """Remove OHLCV hypertable.

    WARNING: This will delete all OHLCV data. Only use in development.
    """
    op.execute("SELECT remove_compression_policy('ohlcv', if_exists => TRUE)")
    op.drop_table("ohlcv")
```

### Forward-Only in Production

In production, migrations are forward-only. We never run `alembic downgrade` in production. If a migration introduces a problem, we write a new migration that fixes it. This policy exists because `downgrade()` functions are rarely tested as thoroughly as `upgrade()` functions, and running an untested downgrade on a production database with live data is an unacceptable risk.

Downgrade functions are still written and maintained -- they are useful in development and staging. But they are treated as development conveniences, not production safety mechanisms.

### Schema vs. Data Migrations

We distinguish between schema migrations (adding tables, columns, indexes) and data migrations (transforming existing data, backfilling new columns, updating enum values). Schema migrations are fast and low-risk. Data migrations can be slow and high-risk, especially on large tables.

Data migrations that touch large tables (millions of rows) are handled differently:

1. The new column is added with a default value (schema migration).
2. The data is backfilled in batches using a separate script that runs outside the Alembic transaction (data migration script).
3. The default value is removed and the column is made NOT NULL if needed (follow-up schema migration).

This three-step approach avoids holding a long-running transaction that locks the table.

### Zero-Downtime Migrations

All migrations are designed to be compatible with both the current and previous versions of the application. This means:

- **Adding a column:** Add it with a default value or as nullable. The old application ignores it.
- **Removing a column:** First deploy a new application version that does not use the column. Then remove the column in a subsequent migration.
- **Renaming a column:** Create the new column, copy data, update the application to use the new column, then drop the old column.
- **Adding an index:** Use `CREATE INDEX CONCURRENTLY` (not supported inside a transaction, so the migration uses `op.execute()` with `op.get_context().autocommit = True`).

### TimescaleDB-Specific Migrations

TimescaleDB hypertables have special migration considerations:

- Converting a regular table to a hypertable must happen before data is inserted (or the data must be migrated through a temporary table).
- Compression policies must be added after the hypertable is created.
- Continuous aggregates (materialized views) require careful migration because they depend on the underlying hypertable schema.
- Retention policies (automatic data deletion) are added through `add_retention_policy()` and must be coordinated with the backup strategy.

### Migration Testing

Every migration is tested before deployment:

1. **Dry run in CI:** The CI pipeline applies all migrations from scratch to a fresh database and verifies the resulting schema matches the SQLAlchemy models (no drift).
2. **Staging first:** Migrations are applied to the staging database before production.
3. **Backup before migration:** A database backup is taken immediately before running migrations in production.
4. **Timing estimate:** For data migrations on large tables, the migration script includes an estimated runtime and a progress indicator.

---

## 11.15 Configuration Management

### Twelve-Factor App Principles

MONEYMAKER follows the Twelve-Factor App methodology for configuration. The core principle is: **configuration that varies between environments (development, staging, production) must be stored in environment variables, not in code.** This means:

- Database connection strings are environment variables, not hardcoded strings.
- API keys and secrets are environment variables, never committed to the repository.
- Feature flags are environment variables or managed through a configuration service.
- Service endpoints (hostnames, ports) are environment variables.

Configuration that does not vary between environments -- algorithm parameters, default timeout values, data schemas -- lives in configuration files committed to the repository.

### Configuration Hierarchy

MONEYMAKER uses a layered configuration system where each layer can override the previous one:

```
Priority (highest to lowest):
  1. Environment variables          (runtime overrides)
  2. .env file                      (local development)
  3. Environment-specific YAML      (configs/{env}/{service}.yaml)
  4. Service-default YAML           (configs/default/{service}.yaml)
  5. Pydantic model defaults        (code defaults)
```

Pydantic BaseSettings implements this hierarchy automatically:

```python
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def yaml_config_source(settings: BaseSettings) -> dict[str, Any]:
    """Load configuration from environment-specific YAML file."""
    env = settings.model_config.get("env", "development")
    service = settings.model_config.get("service_name", "default")
    config_path = Path(f"configs/{env}/{service}.yaml")

    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


class AIBrainConfig(BaseSettings):
    """Configuration for the Algo Engine service.

    Values are loaded from (in priority order):
    1. Environment variables prefixed with MONEYMAKER_BRAIN_
    2. configs/{env}/algo-engine.yaml
    3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_prefix="MONEYMAKER_BRAIN_",
        env_nested_delimiter="__",
    )

    # Model configuration
    model_path: str = Field(
        default="/models/production/latest",
        description="Path to the production model directory",
    )
    ensemble_method: str = Field(
        default="weighted_average",
        description="Method to combine ensemble predictions",
    )
    confidence_threshold: float = Field(
        default=0.60,
        description="Minimum confidence to emit a signal",
        ge=0.0,
        le=1.0,
    )

    # Data subscription
    symbols: list[str] = Field(
        default=["EURUSD", "GBPUSD", "USDJPY"],
        description="Symbols to monitor for trading signals",
    )
    timeframes: list[str] = Field(
        default=["M15", "H1", "H4"],
        description="Timeframes to analyze",
    )

    # Performance tuning
    feature_cache_ttl_seconds: int = Field(
        default=300,
        description="TTL for cached feature computations",
        ge=60,
    )
    max_concurrent_evaluations: int = Field(
        default=4,
        description="Maximum parallel strategy evaluation requests",
        ge=1,
    )
```

### Feature Flags

Feature flags allow new functionality to be deployed to production but activated selectively. They are essential for canary deployments, A/B testing of model versions, and safe rollout of behavioral changes.

```python
class FeatureFlags(BaseSettings):
    """Feature flags for gradual rollout of new functionality."""

    model_config = SettingsConfigDict(env_prefix="MONEYMAKER_FF_")

    enable_regime_detection_v2: bool = Field(
        default=False,
        description="Use the new regime detection algorithm",
    )
    enable_correlation_exposure_check: bool = Field(
        default=True,
        description="Check correlated instrument exposure before trading",
    )
    enable_adaptive_position_sizing: bool = Field(
        default=False,
        description="Use volatility-adjusted position sizing",
    )
    canary_model_traffic_pct: float = Field(
        default=0.0,
        description="Percentage of signals routed to canary model (0-100)",
        ge=0.0,
        le=100.0,
    )
```

Feature flags are controlled through environment variables, allowing them to be toggled without redeployment. A flag change is an environment variable change, which can be applied by restarting the service or (for flags that support hot-reloading) by sending a configuration reload signal.

### Configuration Audit Trail

Every configuration change is logged. When a service starts, it logs its complete configuration (with secrets redacted) at the INFO level. When a configuration value changes at runtime (through hot-reloading), the change is logged with the old and new values. This audit trail is critical for debugging incidents -- knowing that a configuration change preceded a problem narrows the investigation significantly.

```python
def log_config_on_startup(config: BaseSettings) -> None:
    """Log the service configuration at startup, redacting secrets."""
    config_dict = config.model_dump()

    # Redact sensitive fields
    sensitive_keys = {"password", "secret", "token", "key", "credential"}
    for key in config_dict:
        if any(s in key.lower() for s in sensitive_keys):
            config_dict[key] = "***REDACTED***"

    logger.info("service_configuration_loaded", **config_dict)
```

---

## 11.16 Documentation Standards

### Architecture Decision Records (ADRs)

Every significant architectural decision is recorded as an Architecture Decision Record (ADR). ADRs capture not just the decision, but the context in which it was made and the alternatives that were considered. This is invaluable for future developers who need to understand why the system is built the way it is.

ADRs follow a standard format:

```markdown
# ADR-003: Use TimescaleDB for Time-Series Data

## Status
Accepted

## Date
2026-01-15

## Context
MONEYMAKER needs to store billions of OHLCV candles across multiple symbols
and timeframes. The data must support fast time-range queries, automatic
data lifecycle management (compression, retention), and standard SQL
compatibility for analytics.

## Decision
Use TimescaleDB (as a PostgreSQL extension) for all time-series data
storage.

## Alternatives Considered
1. **InfluxDB** -- Purpose-built time-series DB. Rejected because it
   uses a custom query language (Flux/InfluxQL) and requires learning a
   new operational model. Limited join support.
2. **ClickHouse** -- Excellent for analytics. Rejected because it is
   column-oriented and optimized for batch analytics, not real-time
   OLTP-style inserts. Operational complexity is high.
3. **Plain PostgreSQL** -- No time-series optimizations. Partitioning
   must be managed manually. No built-in compression or retention
   policies.

## Consequences
- We get automatic chunk-based partitioning, compression, and retention.
- We retain full SQL compatibility and can use SQLAlchemy/asyncpg.
- We must manage the TimescaleDB extension version alongside PostgreSQL.
- Hypertable creation and compression policies must be handled in
  migrations.
```

ADRs are numbered sequentially and stored in `docs/architecture/decisions/`. They are never deleted or modified after acceptance -- if a decision is reversed, a new ADR records the reversal and references the original.

### API Documentation

API documentation is generated from the source of truth:

- **gRPC APIs** are documented through the `.proto` files. Every message and RPC method includes a documentation comment. Tools like `protoc-gen-doc` generate HTML or Markdown documentation from the proto definitions.
- **REST APIs** (health checks, monitoring endpoints) are documented through OpenAPI/Swagger specs generated from the Python code using FastAPI's automatic documentation.
- **Internal APIs** (Python module interfaces) are documented through Google-style docstrings. Sphinx generates searchable HTML documentation from the docstrings.

### Runbooks

Runbooks are step-by-step procedures for operational tasks. They are written for an operator who may be under stress during an incident, so they are explicit, unambiguous, and include verification steps after each action.

Every runbook follows this structure:

1. **When to use this runbook** -- the triggering condition.
2. **Prerequisites** -- what access and tools are needed.
3. **Steps** -- numbered, explicit instructions. No vague directives like "check the logs" -- instead, "run `docker logs moneymaker-risk-manager --tail 100 --since 10m` and look for lines containing `ERROR` or `CRITICAL`."
4. **Verification** -- how to confirm the procedure worked.
5. **Escalation** -- what to do if the procedure does not resolve the issue.

### Per-Service Documentation

Each service has a `README.md` in its directory that covers:

- What the service does (one paragraph).
- How to run it locally.
- Configuration options (table of environment variables).
- API endpoints.
- How to run its tests.
- Known limitations and technical debt.
- Links to relevant ADRs and design documents.

---

## 11.17 Development Tooling

### Makefile

The top-level Makefile provides a unified interface for all development tasks. Developers should rarely need to remember long commands or service-specific incantations -- `make` wraps them all.

```makefile
# Makefile -- MONEYMAKER V1 Development Commands
.PHONY: help setup lint test test-unit test-integration test-e2e \
        build up down logs clean migrate seed proto profile

SHELL := /bin/bash
PYTHON := python3.11
SERVICES := algo-engine risk-manager mt5-bridge monitoring

# ─── Help ──────────────────────────────────────────────
help: ## Show this help message
 @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Setup ─────────────────────────────────────────────
setup: ## Set up local development environment from scratch
 @echo "=== Setting up MONEYMAKER development environment ==="
 @echo "Installing pre-commit hooks..."
 pip install pre-commit
 pre-commit install
 pre-commit install --hook-type commit-msg
 @echo "Creating virtual environments for each service..."
 @for svc in $(SERVICES); do \
  echo "  Setting up $$svc..."; \
  cd services/$$svc && \
  $(PYTHON) -m venv .venv && \
  source .venv/bin/activate && \
  pip install -e ".[dev]" --quiet && \
  pip install -e ../../shared/python-common --quiet && \
  deactivate && \
  cd ../..; \
 done
 @echo "Starting infrastructure dependencies..."
 docker compose -f infrastructure/docker/docker-compose.dev.yml up -d
 @echo "Running database migrations..."
 $(MAKE) migrate
 @echo "=== Setup complete ==="

# ─── Linting ───────────────────────────────────────────
lint: ## Run all linters
 black --check --line-length 100 services/ shared/ tests/
 isort --check-only --profile black --line-length 100 services/ shared/ tests/
 ruff check services/ shared/ tests/
 @for svc in $(SERVICES); do \
  echo "mypy: $$svc"; \
  cd services/$$svc && source .venv/bin/activate && \
  mypy src/ && deactivate && cd ../..; \
 done

lint-fix: ## Run linters and auto-fix issues
 black --line-length 100 services/ shared/ tests/
 isort --profile black --line-length 100 services/ shared/ tests/
 ruff check --fix services/ shared/ tests/

# ─── Testing ──────────────────────────────────────────
test: test-unit ## Run all fast tests (alias for test-unit)

test-unit: ## Run unit tests for all services
 @for svc in $(SERVICES); do \
  echo "=== Unit tests: $$svc ==="; \
  cd services/$$svc && source .venv/bin/activate && \
  pytest tests/unit/ -m unit --cov=src/ --cov-report=term-missing \
   --cov-fail-under=80 -v && \
  deactivate && cd ../..; \
 done

test-integration: ## Run integration tests (requires Docker dependencies)
 @echo "Ensuring infrastructure is running..."
 docker compose -f infrastructure/docker/docker-compose.dev.yml up -d
 @sleep 5
 pytest tests/ -m integration -v --tb=long

test-e2e: ## Run end-to-end tests (builds and runs full ecosystem)
 docker compose -f infrastructure/docker/docker-compose.test.yml up --build --abort-on-container-exit
 docker compose -f infrastructure/docker/docker-compose.test.yml down -v

test-all: lint test-unit test-integration ## Run lint + unit + integration tests

# ─── Docker ────────────────────────────────────────────
build: ## Build all Docker images
 @for svc in $(SERVICES) data-ingestion; do \
  echo "Building $$svc..."; \
  docker build -t moneymaker/$$svc:dev -f services/$$svc/Dockerfile .; \
 done

up: ## Start the full ecosystem locally
 docker compose -f infrastructure/docker/docker-compose.yml \
  -f infrastructure/docker/docker-compose.dev.yml up -d

down: ## Stop all services
 docker compose -f infrastructure/docker/docker-compose.yml \
  -f infrastructure/docker/docker-compose.dev.yml down

logs: ## Tail logs from all services
 docker compose -f infrastructure/docker/docker-compose.yml logs -f --tail=50

logs-%: ## Tail logs from a specific service (e.g., make logs-risk-manager)
 docker logs -f --tail=100 moneymaker-$*

# ─── Database ─────────────────────────────────────────
migrate: ## Run database migrations
 alembic upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new MSG="add_foo_table")
 alembic revision --autogenerate -m "$(MSG)"

migrate-history: ## Show migration history
 alembic history --verbose

seed: ## Seed the database with development data
 $(PYTHON) scripts/data/import-fixtures.py
 $(PYTHON) scripts/dev/seed-db.sh

# ─── Protobuf ─────────────────────────────────────────
proto: ## Compile Protocol Buffer definitions
 cd shared/proto && $(MAKE) all

# ─── Profiling and Debugging ──────────────────────────
profile-%: ## Profile a service with py-spy (e.g., make profile-algo-engine)
 py-spy record -o profiles/$*_$(shell date +%Y%m%d_%H%M%S).svg \
  --pid $$(docker inspect -f '{{.State.Pid}}' moneymaker-$*)

# ─── Cleanup ──────────────────────────────────────────
clean: ## Remove build artifacts, caches, and virtual environments
 find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
 find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
 find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
 find . -type f -name "*.pyc" -delete 2>/dev/null || true
 find . -type f -name "coverage.xml" -delete 2>/dev/null || true
 @for svc in $(SERVICES); do rm -rf services/$$svc/.venv; done

clean-docker: ## Remove all MONEYMAKER Docker resources
 docker compose -f infrastructure/docker/docker-compose.yml down -v --rmi local
 docker image prune -f --filter "label=project=moneymaker"
```

### Scripts Directory

The `scripts/` directory contains utilities that are too complex for Makefile targets but too operational to live in the application code:

**`scripts/dev/setup-local.sh`** -- One-command local environment setup. Installs system dependencies, creates virtual environments, starts Docker containers, runs migrations, seeds the database, and verifies that everything works.

**`scripts/dev/seed-db.sh`** -- Populates the development database with realistic test data: historical OHLCV candles for the configured symbols, sample trades, strategy configuration entries, and configuration snapshots.

**`scripts/dev/generate-protos.sh`** -- Compiles `.proto` files to Python and Go source code. Handles the installation of `protoc` and the required plugins if they are not already installed.

**`scripts/data/download-historical.py`** -- Downloads historical market data from exchange APIs and stores it in the database. Used to bootstrap the development database with real data for backtesting and feature engineering development.

### Profiling Tools

When performance is a concern, we use specialized profiling tools:

**py-spy** for CPU profiling. py-spy attaches to a running Python process (even inside a Docker container) and generates flame graphs without modifying the application or adding instrumentation. It is the go-to tool for identifying hot spots in the signal generation pipeline or risk checking logic.

```bash
# Generate a flame graph for the Algo Engine process
py-spy record -o flame_algo_engine.svg --pid $(pgrep -f "algo_engine.main") --duration 60

# Top-style live view
py-spy top --pid $(pgrep -f "risk_manager.main")
```

**cProfile** for detailed function-level profiling. When py-spy identifies a hot spot, cProfile provides granular call counts and cumulative time for each function in the call chain:

```python
import cProfile
import pstats

def profile_feature_pipeline(data: pd.DataFrame) -> None:
    """Profile the feature engineering pipeline."""
    profiler = cProfile.Profile()
    profiler.enable()

    pipeline = FeaturePipeline()
    features = pipeline.compute(data)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")
    stats.print_stats(30)  # Top 30 functions
```

**tracemalloc** for memory profiling. tracemalloc tracks memory allocations and identifies the source code lines responsible for the most memory usage. This is critical for detecting memory leaks in long-running services:

```python
import tracemalloc

tracemalloc.start()

# ... run the service for a period ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")

print("=== Top 20 Memory Allocations ===")
for stat in top_stats[:20]:
    print(stat)
```

**memray** for comprehensive memory analysis. memray provides detailed memory profiling with flame graphs, allocation tracking, and leak detection. It is used for deep investigations when tracemalloc identifies a problem area:

```bash
# Record memory usage
memray run --output profile.bin -m risk_manager.main

# Generate flame graph
memray flamegraph profile.bin --output memory_flame.html

# Generate summary
memray summary profile.bin
```

### Load Testing with Locust

Locust provides load testing for MONEYMAKER's internal APIs. We use it to verify that the system handles the expected throughput and to identify bottlenecks under load:

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between, events
import json
import random


class RiskManagerUser(HttpUser):
    """Simulates risk check requests at production-like rates."""

    wait_time = between(0.1, 0.5)  # 2-10 requests per second per user
    host = "http://localhost:8080"

    @task(10)
    def check_risk(self) -> None:
        """Submit a risk check request."""
        payload = {
            "signal_id": f"sig-{random.randint(100000, 999999)}",
            "symbol": random.choice(["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]),
            "direction": random.choice(["BUY", "SELL"]),
            "confidence": round(random.uniform(0.5, 0.95), 2),
            "proposed_volume": round(random.uniform(0.01, 1.0), 2),
            "entry_price": round(random.uniform(1.0, 1.5), 5),
            "stop_loss": round(random.uniform(0.9, 1.4), 5),
            "take_profit": round(random.uniform(1.1, 1.6), 5),
            "account_equity": 50000.0,
        }
        self.client.post(
            "/api/risk-check",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    @task(2)
    def health_check(self) -> None:
        """Hit the health endpoint."""
        self.client.get("/health")

    @task(1)
    def get_positions(self) -> None:
        """Query open positions."""
        self.client.get("/api/positions")
```

Running the load test:

```bash
# Run Locust with 50 concurrent users, ramping up 5 users per second
locust -f tests/performance/locustfile.py \
    --headless \
    --users 50 \
    --spawn-rate 5 \
    --run-time 5m \
    --host http://localhost:8080 \
    --csv results/load_test
```

The results are saved as CSV files and can be visualized in Grafana or analyzed directly. Key metrics: median response time, 95th percentile response time, requests per second, and error rate. Our targets: median response time under 10ms for health checks, under 50ms for risk checks, and zero errors under normal load.

---

## Summary

This document has defined the complete development workflow, testing strategy, and deployment pipeline for the MONEYMAKER V1 trading ecosystem. The key principles are:

1. **Test-first for financial logic.** Every calculation that touches money is verified by unit tests, property-based tests, and integration tests before it reaches production.
2. **Automated quality gates.** Pre-commit hooks, CI pipelines, and coverage requirements prevent regressions from reaching the main branch.
3. **Staged deployment.** Changes flow from feature branches through CI, staging, deployment gates, and production with automated verification at each stage.
4. **Observability.** Every deployment is monitored, every configuration change is logged, and every incident is investigated through structured logs and metrics.
5. **Rollback as a first-class operation.** Every deployment can be reversed in seconds, and database migrations are designed to be forward-compatible.
6. **Infrastructure as code.** Docker Compose, Ansible playbooks, and Alembic migrations ensure that the entire ecosystem can be reproduced from the repository alone.

These practices are not optional. They are the engineering discipline that allows a small team to operate a complex, real-money trading system with confidence. The next document (Document 12 -- Security, Compliance, and Audit) covers the security measures that protect the system from external threats and internal errors.

*fine del documento 11 -- Development Workflow, Testing, and Deployment*
