#!/usr/bin/env bash
# MONEYMAKER Rollback Script
# Reverts services to previous images recorded by deploy.sh.
#
# Usage: bash rollback.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="${SCRIPT_DIR}/../../infra/docker"
COMPOSE_BASE="${COMPOSE_DIR}/docker-compose.yml"
COMPOSE_ENV="${COMPOSE_DIR}/docker-compose.${DEPLOY_ENV:-dev}.yml"
ROLLBACK_FILE="/tmp/moneymaker-rollback-state.txt"

if [ ! -f "$ROLLBACK_FILE" ]; then
    echo "ERROR: No rollback state found at ${ROLLBACK_FILE}"
    echo "Cannot rollback without a prior deployment record."
    exit 1
fi

echo "=== MONEYMAKER Rollback ==="
echo "  Environment: ${DEPLOY_ENV:-dev}"
echo "  Timestamp:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

while IFS='=' read -r svc image; do
    if [ -z "$svc" ] || [ "$image" = "none" ]; then
        continue
    fi

    echo "Rolling back ${svc} to ${image}..."
    docker pull "$image" 2>/dev/null || {
        echo "  WARNING: Could not pull ${image}, skipping ${svc}"
        continue
    }

    CONTAINER_NAME="macena-${svc}"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true

    # Restart with previous image by setting it as override
    export DEPLOY_TAG="${image##*:}"
    docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_ENV" up -d --no-deps "${svc}" 2>/dev/null || {
        echo "  WARNING: Compose restart failed for ${svc}, trying direct docker run"
        docker run -d --name "$CONTAINER_NAME" "$image"
    }

    # Wait for health
    TIMEOUT=90
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
        STATUS=$(docker inspect "$CONTAINER_NAME" --format='{{.State.Health.Status}}' 2>/dev/null || echo "starting")
        if [ "$STATUS" = "healthy" ]; then
            echo "  ${svc}: healthy (rolled back)"
            break
        fi
        sleep 5
        ELAPSED=$((ELAPSED + 5))
    done
done < "$ROLLBACK_FILE"

echo ""
echo "=== Rollback complete ==="
echo "  Completed: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
