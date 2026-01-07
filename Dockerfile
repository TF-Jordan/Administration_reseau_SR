# Multi-stage Dockerfile for Sentiment Recommendation System

# Stage 1: Base image with dependencies
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies with retry and increased timeout
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt

# Stage 2: API Server
FROM base AS api

COPY src/ /app/src/
COPY .env.example /app/.env

# Create directory for models (mount your model here)
RUN mkdir -p /app/src/modules/module1_sentiment/models

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Celery Worker
FROM base AS worker

COPY src/ /app/src/
COPY .env.example /app/.env

# Create directory for models
RUN mkdir -p /app/src/modules/module1_sentiment/models

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

CMD ["celery", "-A", "src.modules.module3_orchestration.celery_app", "worker", "--loglevel=info"]

# Stage 4: Celery Beat (Scheduler)
FROM base AS beat

COPY src/ /app/src/
COPY .env.example /app/.env

RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

CMD ["celery", "-A", "src.modules.module3_orchestration.celery_app", "beat", "--loglevel=info"]

# Stage 5: Flower (Celery monitoring)
FROM base AS flower

COPY src/ /app/src/
COPY .env.example /app/.env

RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 5555

CMD ["celery", "-A", "src.modules.module3_orchestration.celery_app", "flower", "--port=5555"]
