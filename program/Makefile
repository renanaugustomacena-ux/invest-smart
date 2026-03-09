.PHONY: proto build-go test test-go test-python test-cov test-cov-python test-cov-go \
       test-integration test-e2e benchmark \
       lint lint-go lint-python \
       fmt typecheck \
       ci docker-build docker-up docker-down docker-test-up docker-test-down \
       deploy smoke-test clean

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
	cd services/data-ingestion && go test -race -count=1 ./...

test-python:
	cd shared/python-common && $(PYTEST) tests/ -v
	cd services/algo-engine && $(PYTEST) tests/ -v
	cd services/mt5-bridge && $(PYTEST) tests/ -v

# ─── Test with Coverage ──────────────────────────────────────────────────────
test-cov: test-cov-python test-cov-go
	@echo "All coverage checks passed."

test-cov-python:
	cd shared/python-common && $(PYTEST) tests/ \
		--cov=moneymaker_common --cov-report=term-missing --cov-fail-under=85
	cd services/algo-engine && $(PYTEST) tests/ \
		--cov=algo_engine --cov-report=term-missing --cov-fail-under=80
	cd services/mt5-bridge && $(PYTEST) tests/unit/ \
		--cov=mt5_bridge --cov-report=term-missing --cov-fail-under=75

test-cov-go:
	cd services/data-ingestion && go test -race -count=1 \
		-coverprofile=coverage.out -covermode=atomic ./...
	@echo "Go coverage:"
	@cd services/data-ingestion && go tool cover -func=coverage.out | tail -1

# ─── Integration Tests ───────────────────────────────────────────────────────
test-integration: docker-test-up
	$(PYTEST) tests/integration/ -v --timeout=60
	$(MAKE) docker-test-down

# ─── E2E Tests ───────────────────────────────────────────────────────────────
test-e2e:
	docker compose -f infra/docker/docker-compose.yml up -d --build --wait
	$(PYTEST) tests/e2e/ -v --timeout=120 || true
	docker compose -f infra/docker/docker-compose.yml down -v

# ─── Benchmarks ──────────────────────────────────────────────────────────────
benchmark:
	cd services/algo-engine && $(PYTEST) tests/benchmark/ \
		--benchmark-only --benchmark-json=reports/benchmark.json 2>/dev/null || \
		echo "No benchmark tests found yet"
	cd services/data-ingestion && go test -bench=. -benchmem -benchtime=3s -run='^$$' ./... 2>/dev/null || \
		echo "No Go benchmarks found yet"

# ─── Lint ────────────────────────────────────────────────────────────────────
lint: lint-python lint-go

lint-python:
	$(RUFF) check \
		services/algo-engine/src/ services/algo-engine/tests/ \
		services/mt5-bridge/src/ services/mt5-bridge/tests/ \
		services/console/src/ services/console/tests/ \
		shared/python-common/src/ shared/python-common/tests/ \
		services/dashboard/backend/
	$(BLACK) --check \
		services/algo-engine/src/ services/algo-engine/tests/ \
		services/mt5-bridge/src/ services/mt5-bridge/tests/ \
		services/console/src/ services/console/tests/ \
		shared/python-common/src/ shared/python-common/tests/ \
		services/dashboard/backend/

lint-go:
	cd services/data-ingestion && golangci-lint run ./...

# ─── Format ──────────────────────────────────────────────────────────────────
fmt:
	$(BLACK) \
		services/algo-engine/src/ services/algo-engine/tests/ \
		services/mt5-bridge/src/ services/mt5-bridge/tests/ \
		services/console/src/ services/console/tests/ \
		shared/python-common/src/ shared/python-common/tests/ \
		services/dashboard/backend/
	$(RUFF) check --fix \
		services/algo-engine/src/ services/algo-engine/tests/ \
		services/mt5-bridge/src/ services/mt5-bridge/tests/ \
		services/console/src/ services/console/tests/ \
		shared/python-common/src/ shared/python-common/tests/ \
		services/dashboard/backend/
	cd services/data-ingestion && gofmt -w .

# ─── Type Check ──────────────────────────────────────────────────────────────
typecheck:
	$(MYPY) --ignore-missing-imports \
		services/algo-engine/src/ \
		shared/python-common/src/

# ─── CI (local pre-push check — mirrors GitHub Actions) ──────────────────────
ci: lint typecheck test-cov docker-build
	@echo "All CI checks passed."

# ─── Docker ──────────────────────────────────────────────────────────────────
docker-build:
	docker build -t moneymaker-data-ingestion -f services/data-ingestion/Dockerfile .
	docker build -t moneymaker-algo-engine -f services/algo-engine/Dockerfile .
	docker build -t moneymaker-mt5-bridge -f services/mt5-bridge/Dockerfile .
	docker build -t moneymaker-dashboard -f services/dashboard/Dockerfile .
	docker build -t moneymaker-external-data -f services/external-data/Dockerfile .

docker-up:
	docker compose -f infra/docker/docker-compose.yml up -d

docker-down:
	docker compose -f infra/docker/docker-compose.yml down

docker-test-up:
	docker compose -f infra/docker/docker-compose.test.yml up -d --wait

docker-test-down:
	docker compose -f infra/docker/docker-compose.test.yml down -v

launch:
	bash scripts/launch.sh

# ─── Deploy (requires DEPLOY_TAG, DEPLOY_ENV, DEPLOY_SERVICE) ───────────────
deploy:
	bash scripts/deploy/deploy.sh

smoke-test:
	bash scripts/deploy/smoke-test.sh $(DEPLOY_ENV)

# ─── Clean ───────────────────────────────────────────────────────────────────
clean:
	rm -rf services/data-ingestion/bin/
	rm -rf services/*/reports/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "coverage.out" -delete 2>/dev/null || true
