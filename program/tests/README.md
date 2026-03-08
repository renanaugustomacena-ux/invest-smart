# Tests

End-to-end tests and shared test fixtures for the MONEYMAKER ecosystem.

## Structure

```
tests/
├── e2e/        # End-to-end integration tests (full pipeline)
└── fixtures/   # Shared test data and mock configurations
```

> **Unit tests** for each service live inside their respective `services/<name>/tests/` directories.

## Running Tests

```bash
# All tests (unit + e2e)
make test

# Python unit tests only
make test-python

# Go unit tests only
make test-go

# Specific service
cd services/algo-engine && python -m pytest tests/ -v
cd services/mt5-bridge && python -m pytest tests/ -v
cd services/data-ingestion && go test ./...
```

## Test Markers

Python tests use custom markers for selective execution:

```bash
# Skip integration tests (requires running services)
python -m pytest -m "not integration" tests/

# Only integration tests
python -m pytest -m integration tests/
```
