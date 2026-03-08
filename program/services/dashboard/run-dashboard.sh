#!/bin/bash
# MONEYMAKER Dashboard startup script
set -e

source ~/moneymaker-venv/bin/activate
cd "$(dirname "$0")"

# Load environment variables from project .env
ENV_FILE="$(dirname "$0")/../../.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

echo "Starting MONEYMAKER Dashboard on port ${DASHBOARD_PORT:-8888}..."
uvicorn backend.main:app \
    --host "${DASHBOARD_HOST:-0.0.0.0}" \
    --port "${DASHBOARD_PORT:-8888}" \
    --workers 1
