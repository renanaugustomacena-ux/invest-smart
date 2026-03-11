#!/usr/bin/env bash
# MONEYMAKER Market Hours Check
# Blocks production deployments during forex market hours.
#
# Forex market hours: Sunday 22:00 UTC to Friday 22:00 UTC
# Safe deployment window: Friday 22:00 UTC to Sunday 22:00 UTC
#
# Set FORCE_MARKET_HOURS=true to override (emergency only).

set -euo pipefail

DOW=$(date -u +%u)   # 1=Monday .. 7=Sunday
HOUR=$(date -u +%H)

echo "Current UTC: $(date -u '+%A %H:%M') (DOW=${DOW}, HOUR=${HOUR})"

# Market is CLOSED when:
#   - Saturday (DOW=6): all day
#   - Friday (DOW=5) after 22:00
#   - Sunday (DOW=7) before 22:00
MARKET_CLOSED=false
if [ "$DOW" -eq 6 ]; then
    MARKET_CLOSED=true
elif [ "$DOW" -eq 5 ] && [ "$HOUR" -ge 22 ]; then
    MARKET_CLOSED=true
elif [ "$DOW" -eq 7 ] && [ "$HOUR" -lt 22 ]; then
    MARKET_CLOSED=true
fi

if [ "$MARKET_CLOSED" = "true" ]; then
    echo "SAFE: Forex market is closed. Deployment allowed."
    exit 0
fi

# Market is open
if [ "${FORCE_MARKET_HOURS:-false}" = "true" ]; then
    echo "WARNING: Deploying during market hours (emergency override active)"
    exit 0
fi

echo "BLOCKED: Forex market is open."
echo "Production deployments are only allowed when the market is closed:"
echo "  Friday 22:00 UTC → Sunday 22:00 UTC"
echo ""
echo "To override for emergencies, set force_market_hours=true in the workflow."
exit 1
