#!/usr/bin/env bash
# MONEYMAKER V1 Launch Script — validate, build, and start the full stack
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROGRAM_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROGRAM_DIR/infra/docker/docker-compose.yml"
ENV_FILE="$PROGRAM_DIR/.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

echo -e "${CYAN}"
echo "======================================"
echo "  MONEYMAKER V1 — System Launch"
echo "======================================"
echo -e "${NC}"

# === Step 1: Validate .env ===
info "Checking .env file..."
if [ ! -f "$ENV_FILE" ]; then
    error ".env file not found at $ENV_FILE"
    echo "  Run: cp $PROGRAM_DIR/.env.example $ENV_FILE"
    echo "  Then fill in the required passwords."
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

MISSING=()
[ -z "${MONEYMAKER_DB_PASSWORD:-}" ] && MISSING+=("MONEYMAKER_DB_PASSWORD")
[ -z "${MONEYMAKER_REDIS_PASSWORD:-}" ] && MISSING+=("MONEYMAKER_REDIS_PASSWORD")
[ -z "${GRAFANA_PASSWORD:-}" ] && MISSING+=("GRAFANA_PASSWORD")

if [ ${#MISSING[@]} -gt 0 ]; then
    error "Missing required environment variables:"
    for var in "${MISSING[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "  Generate passwords with: openssl rand -base64 24"
    exit 1
fi
info ".env validated — all required passwords set"

# === Step 2: Validate Docker ===
info "Checking Docker..."
if ! command -v docker &>/dev/null; then
    error "Docker is not installed or not in PATH"
    exit 1
fi

if ! docker info &>/dev/null; then
    error "Docker daemon is not running. Start it first."
    exit 1
fi
info "Docker is available"

# === Step 3: Validate compose file ===
info "Validating docker-compose configuration..."
if ! docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config --quiet 2>/dev/null; then
    error "docker-compose.yml has syntax errors:"
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config 2>&1 | head -20
    exit 1
fi
info "docker-compose.yml is valid"

# === Step 4: Build (optional flag --no-build to skip) ===
if [ "${1:-}" != "--no-build" ]; then
    info "Building service images (this may take a few minutes)..."
    cd "$PROGRAM_DIR"
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build
    info "Build complete"
else
    info "Skipping build (--no-build)"
fi

# === Step 5: Start stack ===
info "Starting MONEYMAKER stack..."
cd "$PROGRAM_DIR"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d

# === Step 6: Wait for infrastructure health ===
info "Waiting for infrastructure services to become healthy..."
TIMEOUT=120
ELAPSED=0
INTERVAL=5

for svc in postgres redis; do
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "macena-$svc" 2>/dev/null || echo "not_found")
        if [ "$HEALTH" = "healthy" ]; then
            info "$svc is healthy"
            break
        fi
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
    done
    if [ $ELAPSED -ge $TIMEOUT ]; then
        warn "$svc did not become healthy within ${TIMEOUT}s — check logs with: docker logs macena-$svc"
    fi
done

# === Step 7: Print summary ===
echo ""
echo -e "${CYAN}======================================${NC}"
echo -e "${CYAN}  MONEYMAKER V1 Stack Status${NC}"
echo -e "${CYAN}======================================${NC}"
echo ""
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || \
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
echo ""
echo -e "${GREEN}Access Points:${NC}"
echo "  Dashboard:    http://localhost:${DASHBOARD_PORT:-8888}"
echo "  Grafana:      http://localhost:3000  (no login required)"
echo "  Prometheus:   http://localhost:9091"
echo ""
info "Launch complete. Use the MONEYMAKER Console to monitor: python moneymaker_console.py"
