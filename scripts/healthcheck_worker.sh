#!/bin/bash
# ==============================================================================
# Celery Worker Health Check Script
# Checks if Celery worker can connect to broker and is processing tasks
# ==============================================================================

set -e

# Configuration
TIMEOUT=5

# Check if Celery worker is running using inspect
celery_status=$(celery -A src.modules.module3_orchestration.celery_app inspect ping --timeout=$TIMEOUT 2>&1 || echo "FAIL")

if echo "$celery_status" | grep -q "pong"; then
    echo "Health check passed: Celery worker is healthy"
    exit 0
else
    echo "Health check failed: Celery worker not responding"
    echo "Status: $celery_status"
    exit 1
fi
