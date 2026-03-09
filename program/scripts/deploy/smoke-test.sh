#!/usr/bin/env bash
# MONEYMAKER Post-Deployment Smoke Tests
# Verifies all services are healthy after deployment.
#
# Usage: bash smoke-test.sh [environment]

set -euo pipefail

ENV="${1:-dev}"
FAIL=0
TOTAL=0
PASSED=0

check_health() {
    local name="$1"
    local url="$2"
    TOTAL=$((TOTAL + 1))

    if curl -sf --max-time 10 "$url" > /dev/null 2>&1; then
        echo "  OK:   ${name} (${url})"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL: ${name} (${url})"
        FAIL=1
    fi
}

check_container() {
    local name="$1"
    local container="$2"
    TOTAL=$((TOTAL + 1))

    STATUS=$(docker inspect "$container" --format='{{.State.Health.Status}}' 2>/dev/null || echo "not_found")
    if [ "$STATUS" = "healthy" ]; then
        echo "  OK:   ${name} (container: ${container}, status: healthy)"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL: ${name} (container: ${container}, status: ${STATUS})"
        FAIL=1
    fi
}

echo "=== MONEYMAKER Smoke Tests (${ENV}) ==="
echo ""
echo "Health endpoints:"
check_health "data-ingestion" "http://localhost:8081/healthz"
check_health "algo-engine"    "http://localhost:9097/"
check_health "dashboard"      "http://localhost:8888/health"
check_health "prometheus"     "http://localhost:9091/-/healthy"
check_health "grafana"        "http://localhost:3000/api/health"

echo ""
echo "Metrics endpoints:"
check_health "data-ingestion metrics" "http://localhost:9090/metrics"
check_health "algo-engine metrics"    "http://localhost:9097/metrics"
check_health "mt5-bridge metrics"     "http://localhost:9094/metrics"

echo ""
echo "Container health:"
check_container "postgres"       "macena-postgres"
check_container "redis"          "macena-redis"
check_container "data-ingestion" "macena-data-ingestion"
check_container "algo-engine"    "macena-algo-engine"
check_container "mt5-bridge"     "macena-mt5-bridge"
check_container "dashboard"      "macena-dashboard"

echo ""
echo "=== Results: ${PASSED}/${TOTAL} passed ==="

if [ $FAIL -ne 0 ]; then
    echo "SMOKE TEST FAILED"
    exit 1
fi

echo "All smoke tests passed."
