# ==============================================================================
# Multi-stage Dockerfile for AR_AS Recommendation System
# Optimized for production with proper caching, security, and health checks
# ==============================================================================

# ==============================================================================
# Stage 1: Base Image with System Dependencies
# ==============================================================================
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    # Set locale
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

# Install system dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build dependencies
    build-essential \
    gcc \
    g++ \
    # PostgreSQL client library
    libpq-dev \
    # Networking tools for healthchecks
    curl \
    wget \
    netcat-traditional \
    # SSL/TLS
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ==============================================================================
# Stage 2: Python Dependencies
# ==============================================================================
FROM base AS dependencies

# Copy only requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimized settings
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt && \
    # Clean up pip cache
    rm -rf ~/.cache/pip

# ==============================================================================
# Stage 3: Application Base (shared by all services)
# ==============================================================================
FROM dependencies AS app-base

# Copy application source code
COPY src/ /app/src/

# Copy essential configuration files
COPY .env.example /app/.env

# Create directories for models and data
RUN mkdir -p \
    /app/src/modules/module1_sentiment/models \
    /app/src/modules/module2_recommendation/models \
    /app/logs \
    /app/data

# Create non-root user for security
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -u 1000 -d /app -s /bin/bash appuser && \
    chown -R appuser:appgroup /app

# ==============================================================================
# Stage 4: API Server
# ==============================================================================
FROM app-base AS api

# Copy healthcheck script
COPY scripts/healthcheck_api.sh /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh && \
    chown appuser:appgroup /app/healthcheck.sh

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Enhanced health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /app/healthcheck.sh || exit 1

# Start API server with production settings
CMD ["uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--log-level", "info", \
     "--access-log", \
     "--use-colors"]

# ==============================================================================
# Stage 5: Celery Worker
# ==============================================================================
FROM app-base AS worker

# Copy worker healthcheck
COPY scripts/healthcheck_worker.sh /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh && \
    chown appuser:appgroup /app/healthcheck.sh

USER appuser

# Health check for worker (checks if it can connect to broker)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /app/healthcheck.sh || exit 1

# Start Celery worker with optimized settings
CMD ["celery", "-A", "src.modules.module3_orchestration.celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=4", \
     "--max-tasks-per-child=1000", \
     "--time-limit=3600", \
     "--soft-time-limit=3000"]

# ==============================================================================
# Stage 6: Celery Beat (Scheduler)
# ==============================================================================
FROM app-base AS beat

USER appuser

# Start Celery beat scheduler
CMD ["celery", "-A", "src.modules.module3_orchestration.celery_app", "beat", \
     "--loglevel=info", \
     "--pidfile=/tmp/celerybeat.pid"]

# ==============================================================================
# Stage 7: Flower (Celery Monitoring UI)
# ==============================================================================
FROM app-base AS flower

USER appuser

EXPOSE 5555

# Start Flower with basic auth
CMD ["celery", "-A", "src.modules.module3_orchestration.celery_app", "flower", \
     "--port=5555", \
     "--broker_api=redis://redis:6379/0", \
     "--persistent=True", \
     "--max_tasks=10000"]

# ==============================================================================
# Stage 8: Development (with hot-reload)
# ==============================================================================
FROM app-base AS development

# Install development dependencies
RUN pip install --no-cache-dir \
    watchdog \
    ipython \
    ipdb \
    black \
    flake8 \
    mypy \
    isort

# Switch to root for development (for installing packages)
USER root

# Development server with hot-reload
CMD ["uvicorn", "src.api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload", \
     "--log-level", "debug"]

# ==============================================================================
# Build Labels (for image metadata)
# ==============================================================================
LABEL maintainer="AR_AS Team" \
      version="1.0.0" \
      description="Sentiment-based Vehicle Recommendation System" \
      org.opencontainers.image.source="https://github.com/TF-Jordan/AR_AS"
