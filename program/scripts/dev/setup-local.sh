#!/usr/bin/env bash
set -euo pipefail

echo "=== MONEYMAKER V1 Local Development Setup ==="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3.11+ is required but not installed."; exit 1; }
command -v go >/dev/null 2>&1 || { echo "Go 1.22+ is required but not installed."; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example -- please edit with your values"
fi

# Install shared Python library
echo "Installing shared Python library..."
pip install -e shared/python-common/

# Start infrastructure dependencies
echo "Starting PostgreSQL + TimescaleDB and Redis..."
docker compose -f infra/docker/docker-compose.yml up -d postgres redis

# Wait for services to be healthy
echo "Waiting for database..."
until docker compose -f infra/docker/docker-compose.yml exec -T postgres pg_isready -U moneymaker -d moneymaker 2>/dev/null; do
    sleep 1
done
echo "Database ready."

# Install pre-commit hooks (if pre-commit is available)
if command -v pre-commit &>/dev/null; then
    pre-commit install
    echo "Pre-commit hooks installed."
else
    echo "Optional: pip install pre-commit && pre-commit install"
fi

echo ""
echo "=== Setup complete ==="
echo "  - PostgreSQL + TimescaleDB running on localhost:5432"
echo "  - Redis running on localhost:6379"
echo ""
echo "Next steps:"
echo "  make docker-up    # Start all services"
echo "  make test          # Run all tests"
echo "  make ci            # Run full CI checks locally"
