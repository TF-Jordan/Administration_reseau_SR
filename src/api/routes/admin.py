"""
Administration API endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import require_auth
from src.api.schemas import VectorizationRequest, AsyncTaskResponse
from src.config.constants import ProductType
from src.modules.module3_orchestration.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/vectorize",
    response_model=AsyncTaskResponse,
    summary="Trigger product vectorization",
    description="Start vectorization of all products for a given type.",
)
async def trigger_vectorization(
    request: VectorizationRequest,
    auth: dict = Depends(require_auth),
):
    """
    Trigger vectorization of products.

    This creates/updates vectors in Qdrant for all products of the specified type.
    Requires authentication.
    """
    logger.info(f"Vectorization request: {request.product_type}")

    try:
        orchestrator = get_orchestrator()
        task_id = orchestrator.trigger_vectorization(
            product_type=request.product_type.value,
            batch_size=request.batch_size,
        )

        return AsyncTaskResponse(
            task_id=task_id,
            status="pending",
            message=f"Vectorization started for {request.product_type}",
        )

    except Exception as e:
        logger.error(f"Vectorization trigger error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/cache/invalidate",
    summary="Invalidate cache",
    description="Invalidate cache entries for a specific product.",
)
async def invalidate_cache(
    product_id: str,
    product_type: ProductType,
    auth: dict = Depends(require_auth),
):
    """
    Invalidate cache entries for a product.

    Removes all cached recommendations related to the specified product.
    """
    logger.info(f"Cache invalidation request: {product_id}")

    try:
        orchestrator = get_orchestrator()
        count = await orchestrator.invalidate_product_cache(
            product_id=product_id,
            product_type=product_type.value,
        )

        return {
            "message": f"Invalidated {count} cache entries",
            "product_id": product_id,
            "product_type": product_type,
        }

    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/collections/{product_type}",
    summary="Get collection info",
    description="Get Qdrant collection statistics.",
)
async def get_collection_info(
    product_type: ProductType,
):
    """Get information about a Qdrant collection."""
    from src.modules.module2_recommendation.vector_store import get_vector_store

    try:
        vector_store = get_vector_store()
        info = vector_store.get_collection_info(product_type)
        return info

    except Exception as e:
        logger.error(f"Collection info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/token",
    summary="Generate API token",
    description="Generate a JWT token for API authentication (for testing).",
)
async def generate_token(client_id: str, secret: str):
    """
    Generate an API token for testing.

    In production, use proper authentication flow.
    """
    from src.config import settings
    from src.api.dependencies import create_access_token

    # Simple secret check for demo purposes
    if secret != settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret",
        )

    token = create_access_token({"sub": client_id, "type": "api"})

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }
