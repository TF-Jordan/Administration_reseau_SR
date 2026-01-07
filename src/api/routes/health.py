"""
Health Check API endpoints.
"""

import logging
from datetime import datetime

from fastapi import APIRouter

from src.config import settings
from src.api.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of all services.",
)
async def health_check():
    """
    Comprehensive health check of all system components.

    Checks:
    - Redis cache
    - Qdrant vector database
    - Embedding service
    - Sentiment analyzer
    - Database connection
    """
    from src.modules.module2_recommendation.cache import get_cache_manager
    from src.modules.module2_recommendation.embeddings import get_embedding_service
    from src.modules.module2_recommendation.vector_store import get_vector_store
    from src.modules.module1_sentiment.analyzer import get_sentiment_analyzer
    from sqlalchemy import text
    services = {}

    # Check Redis
    try:
        cache = get_cache_manager()
        services["redis"] = await cache.health_check()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        services["redis"] = False

    # Check Qdrant
    try:
        vectors = get_vector_store()
        services["qdrant"] = vectors.health_check()
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        services["qdrant"] = False

    # Check Embeddings
    try:
        embeddings = get_embedding_service()
        services["embeddings"] = embeddings.health_check()
    except Exception as e:
        logger.error(f"Embeddings health check failed: {e}")
        services["embeddings"] = False

    # Check Sentiment Analyzer
    try:
        analyzer = get_sentiment_analyzer()
        services["sentiment_analyzer"] = analyzer.health_check()
    except Exception as e:
        logger.error(f"Sentiment analyzer health check failed: {e}")
        services["sentiment_analyzer"] = False

    # Check Database
    try:
        from src.database.connection import async_engine
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        services["database"] = False

    overall_status = "healthy" if all(services.values()) else "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services,
        version=settings.app_version,
    )


@router.get(
    "/live",
    summary="Liveness probe",
    description="Simple liveness check for Kubernetes.",
)
async def liveness():
    """Simple liveness probe - returns 200 if server is running."""
    return {"status": "alive"}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Readiness check for Kubernetes.",
)
async def readiness():
    """
    Readiness probe - checks if the application is ready to serve traffic.

    Verifies critical dependencies are available.
    """
    from src.modules.module2_recommendation.cache import get_cache_manager

    try:
        # Quick check of critical services
        cache = get_cache_manager()
        redis_ok = await cache.health_check()

        if not redis_ok:
            return {"status": "not_ready", "reason": "Redis unavailable"}

        return {"status": "ready"}

    except Exception as e:
        return {"status": "not_ready", "reason": str(e)}
