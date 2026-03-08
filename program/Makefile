.PHONY: proto build-go test test-go test-python \
       lint lint-go lint-python \
       fmt typecheck \
       ci docker-build docker-up docker-down clean

# Python tools — use venv if it exists, otherwise assume system PATH.
# Use absolute paths so targets that `cd` into subdirectories still find tools.
VENV_BIN := $(wildcard $(CURDIR)/.venv/bin)
ifdef VENV_BIN
  PYTHON := $(CURDIR)/.venv/bin/python
  RUFF   := $(CURDIR)/.venv/bin/ruff
  BLACK  := $(CURDIR)/.venv/bin/black
  MYPY   := $(CURDIR)/.venv/bin/mypy
  PYTEST := $(CURDIR)/.venv/bin/python -m pytest
else
  PYTHON := python
  RUFF   := ruff
  BLACK  := black
  MYPY   := mypy
  PYTEST := python -m pytest
endif

# ─── Protobuf ────────────────────────────────────────────────────────────────
proto:
	@echo "Compiling Protocol Buffers..."
	$(MAKE) -C shared/proto all

# ─── Build ───────────────────────────────────────────────────────────────────
build-go:
	cd services/data-ingestion && go build -o bin/data-ingestion ./cmd/server/

# ─── Test ────────────────────────────────────────────────────────────────────
test: test-python test-go

test-go:
	cd services/data-ingestion && go test ./...

test-python:
	cd shared/python-common && $(PYTEST) tests/ -v
	cd services/algo-engine && $(PYTEST) tests/ -v
	cd services/mt5-bridge && $(PYTEST) tests/ -v

# ─── Lint ────────────────────────────────────────────────────────────────────
lint: lint-python lint-go

lint-python:
	$(RUFF) check \
		services/algo-engine/src/ services/algo-engine/tests/ \
		services/mt5-bridge/src/ services/mt5-bridge/tests/ \
		shared/python-common/src/ shared/python-common/tests/
	$(BLACK) --check \
		services/algo-engine/src/ services/algo-engine/tests/ \
		services/mt5-bridge/src/ services/mt5-bridge/tests/ \
		shared/python-common/src/ shared/python-common/tests/

lint-go:
	cd services/data-ingestion && golangci-lint run ./...

# ─── Format ──────────────────────────────────────────────────────────────────
fmt:
	$(BLACK) \
		services/algo-engine/src/ services/algo-engine/tests/ \
		services/mt5-bridge/src/ services/mt5-bridge/tests/ \
		shared/python-common/src/ shared/python-common/tests/
	$(RUFF) check --fix \
		services/algo-engine/src/ services/algo-engine/tests/ \
		services/mt5-bridge/src/ services/mt5-bridge/tests/ \
		shared/python-common/src/ shared/python-common/tests/
	cd services/data-ingestion && gofmt -w .

# ─── Type Check ──────────────────────────────────────────────────────────────
typecheck:
	$(MYPY) --ignore-missing-imports \
		services/algo-engine/src/ \
		shared/python-common/src/

# ─── CI (local pre-push check — mirrors GitHub Actions) ─────────────────────
ci: lint typecheck test docker-build
	@echo "All CI checks passed."

# ─── Docker ──────────────────────────────────────────────────────────────────
docker-build:
	docker build -t moneymaker-data-ingestion -f services/data-ingestion/Dockerfile .
	docker build -t moneymaker-algo-engine -f services/algo-engine/Dockerfile .
	docker build -t moneymaker-mt5-bridge -f services/mt5-bridge/Dockerfile .
	docker build -t moneymaker-dashboard -f services/dashboard/Dockerfile .

docker-up:
	docker compose -f infra/docker/docker-compose.yml up -d

docker-down:
	docker compose -f infra/docker/docker-compose.yml down

launch:
	bash scripts/launch.sh

# ─── Clean ───────────────────────────────────────────────────────────────────
clean:
	rm -rf services/data-ingestion/bin/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
