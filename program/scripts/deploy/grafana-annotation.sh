#!/usr/bin/env bash
# MONEYMAKER Grafana Deployment Annotation
# Creates a deployment annotation in Grafana for tracking.
#
# Usage: bash grafana-annotation.sh <service> <tag> <environment>
#
# Required env vars:
#   GRAFANA_HOST    - Grafana hostname (e.g., localhost or 10.0.5.10)
#   GRAFANA_API_KEY - Grafana API key with annotation write permission

set -euo pipefail

SERVICE="${1:?Usage: grafana-annotation.sh <service> <tag> <environment>}"
TAG="${2:?Missing tag argument}"
ENV="${3:?Missing environment argument}"

: "${GRAFANA_HOST:?GRAFANA_HOST is required}"
: "${GRAFANA_API_KEY:?GRAFANA_API_KEY is required}"

TIMESTAMP_MS=$(($(date +%s) * 1000))

RESPONSE=$(curl -sf -X POST "http://${GRAFANA_HOST}:3000/api/annotations" \
    -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"time\": ${TIMESTAMP_MS},
        \"text\": \"Deployed ${SERVICE} ${TAG} to ${ENV}\",
        \"tags\": [\"deployment\", \"${ENV}\", \"${SERVICE}\"]
    }" 2>/dev/null) || {
    echo "WARNING: Failed to create Grafana annotation (non-fatal)"
    exit 0
}

echo "Grafana annotation created: ${RESPONSE}"
