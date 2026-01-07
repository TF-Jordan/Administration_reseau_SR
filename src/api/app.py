"""
FastAPI application factory.
Creates and configures the main API application.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from elasticapm.contrib.starlette import make_apm_client, ElasticAPM
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import settings
from src.database.connection import init_database, close_database
from .routes import api_router

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")

    # Initialize database
    try:
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize Redis connection
    try:
        from src.modules.module2_recommendation import get_cache_manager
        cache = get_cache_manager()
        await cache.connect()
        logger.info("Redis cache connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

    # Initialize vector store
    try:
        from src.modules.module2_recommendation import get_vector_store
        from src.config.constants import ProductType
        vector_store = get_vector_store()
        vector_store.create_collection_sync(ProductType.VEHICLE)
        vector_store.create_collection_sync(ProductType.LIVREUR)
        logger.info("Qdrant collections initialized")
    except Exception as e:
        logger.error(f"Qdrant initialization failed: {e}")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Close database connections
    await close_database()

    # Close Redis connection
    try:
        from src.modules.module2_recommendation import get_cache_manager
        cache = get_cache_manager()
        await cache.disconnect()
    except Exception:
        pass

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        description="""
        # Sentiment-Based Recommendation System

        A modular microservices system for product recommendations based on sentiment analysis.

        ## Features

        - **Sentiment Analysis (Module 1)**: Analyzes customer comments using fine-tuned distil-camembert
        - **Recommendation Engine (Module 2)**: Generates semantic similarity-based recommendations
        - **Orchestration (Module 3)**: Coordinates the workflow with async task support

        ## Paths

        - **Chemin A**: Vehicle recommendations for rental platforms
        - **Chemin B**: Livreur (delivery person) recommendations for delivery platforms

        ## Architecture

        - FastAPI for API
        - Celery + Redis for async tasks
        - PostgreSQL for data storage
        - Qdrant for vector similarity search
        - ELK Stack + APM for monitoring
        """,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Elastic APM integration
    if settings.apm_enabled:
        apm_client = make_apm_client({
            'SERVICE_NAME': settings.app_name,
            'SERVER_URL': settings.apm_server_url,
            'ENVIRONMENT': settings.environment,
            'CAPTURE_BODY': 'all',
            'TRANSACTION_SAMPLE_RATE': 1.0,
        })
        app.add_middleware(ElasticAPM, client=apm_client)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.debug else "An error occurred",
            },
        )

    # Include API router
    app.include_router(api_router, prefix=settings.api_prefix)

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": f"{settings.api_prefix}/health",
        }

    return app


# Application instance
app = create_app()
