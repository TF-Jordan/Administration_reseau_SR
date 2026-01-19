#!/bin/bash
# ==============================================================================
# API Health Check Script
# Checks if the FastAPI application is running and responding
# ==============================================================================

set -e

# Configuration
API_HOST="${API_HOST:-localhost}"
API_PORT="${API_PORT:-8000}"
API_PREFIX="${API_PREFIX:-/api/v1}"
HEALTH_ENDPOINT="${API_PREFIX}/health/live"
TIMEOUT=5

# Perform health check
response=$(curl -sf --max-time $TIMEOUT "http://${API_HOST}:${API_PORT}${HEALTH_ENDPOINT}" || echo "FAIL")

if [ "$response" = "FAIL" ]; then
    echo "Health check failed: API not responding"
    exit 1
fi

# Check if response contains expected fields
if echo "$response" | grep -q "status"; then
    echo "Health check passed: API is healthy"
    exit 0
else
    echo "Health check failed: Unexpected response"
    exit 1
fi
