#!/usr/bin/env bash
# MONEYMAKER Deployment Script
# Deploys services from GHCR to the target environment.
#
# Required env vars:
#   DEPLOY_TAG      - Image tag to deploy (e.g., dev-abc1234, 1.2.3)
#   DEPLOY_ENV      - Target environment (dev, staging, production)
#   DEPLOY_SERVICE  - Service name or "all"
#
# Usage: DEPLOY_TAG=1.2.3 DEPLOY_ENV=production DEPLOY_SERVICE=all bash deploy.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="${SCRIPT_DIR}/../../infra/docker"
COMPOSE_BASE="${COMPOSE_DIR}/docker-compose.yml"
COMPOSE_ENV="${COMPOSE_DIR}/docker-compose.${DEPLOY_ENV}.yml"
LOCK_FILE="/var/lock/moneymaker-deploy.lock"
ROLLBACK_FILE="/tmp/moneymaker-rollback-state.txt"

# Validate inputs
: "${DEPLOY_TAG:?DEPLOY_TAG is required}"
: "${DEPLOY_ENV:?DEPLOY_ENV is required}"
: "${DEPLOY_SERVICE:?DEPLOY_SERVICE is required}"

if [ ! -f "$COMPOSE_ENV" ]; then
    echo "ERROR: Compose override not found: ${COMPOSE_ENV}"
    exit 1
fi

echo "=== MONEYMAKER Deployment ==="
echo "  Tag:         ${DEPLOY_TAG}"
echo "  Environment: ${DEPLOY_ENV}"
echo "  Service:     ${DEPLOY_SERVICE}"
echo "  Timestamp:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# 1. Acquire deployment lock (prevent concurrent deployments)
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "ERROR: Another deployment is in progress. Aborting."
    exit 1
fi
echo "Deployment lock acquired."

# 2. Determine services to deploy
ALL_SERVICES="data-ingestion algo-engine mt5-bridge dashboard"
if [ "${DEPLOY_SERVICE}" = "all" ]; then
    SERVICES="$ALL_SERVICES"
else
    SERVICES="${DEPLOY_SERVICE}"
fi

# 3. Record current state for rollback
> "$ROLLBACK_FILE"
for svc in $SERVICES; do
    CONTAINER_NAME="macena-${svc}"
    CURRENT_IMAGE=$(docker inspect "$CONTAINER_NAME" --format='{{.Config.Image}}' 2>/dev/null || echo "none")
    echo "${svc}=${CURRENT_IMAGE}" >> "$ROLLBACK_FILE"
    echo "  Current ${svc}: ${CURRENT_IMAGE}"
done
echo ""

# 4. Export tag and pull new images
export DEPLOY_TAG
echo "Pulling images..."
for svc in $SERVICES; do
    echo "  Pulling ${svc}:${DEPLOY_TAG}..."
    docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_ENV" pull "${svc}" 2>/dev/null || {
        echo "ERROR: Failed to pull ${svc}:${DEPLOY_TAG}"
        exit 1
    }
done
echo ""

# 5. Rolling restart in dependency order
# Order: infrastructure deps first, then leaf services
DEPLOY_ORDER="data-ingestion algo-engine mt5-bridge dashboard"

echo "Starting rolling restart..."
for svc in $DEPLOY_ORDER; do
    if echo "$SERVICES" | grep -qw "$svc"; then
        echo "  Restarting ${svc}..."
        docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_ENV" up -d --no-deps "${svc}"

        # Wait for healthy
        CONTAINER_NAME="macena-${svc}"
        TIMEOUT=120
        ELAPSED=0
        while [ $ELAPSED -lt $TIMEOUT ]; do
            STATUS=$(docker inspect "$CONTAINER_NAME" --format='{{.State.Health.Status}}' 2>/dev/null || echo "starting")
            if [ "$STATUS" = "healthy" ]; then
                echo "  ${svc}: healthy (${ELAPSED}s)"
                break
            fi
            sleep 5
            ELAPSED=$((ELAPSED + 5))
        done

        if [ $ELAPSED -ge $TIMEOUT ]; then
            echo "ERROR: ${svc} failed health check after ${TIMEOUT}s"
            echo "Container logs:"
            docker logs --tail=50 "$CONTAINER_NAME" 2>&1
            echo ""
            echo "Triggering rollback..."
            exit 1
        fi
    fi
done

echo ""
echo "=== Deployment complete ==="
echo "  Tag:         ${DEPLOY_TAG}"
echo "  Environment: ${DEPLOY_ENV}"
echo "  Services:    ${SERVICES}"
echo "  Completed:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
