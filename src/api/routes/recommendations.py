"""
Recommendation API endpoints.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, get_orchestrator_dep
from src.api.schemas import (
    RecommendationRequestSchema,
    RecommendationOnlyRequest,
    RecommendationResponse,
    FullWorkflowResponse,
    AsyncTaskResponse,
    ErrorResponse,
)
from src.modules.module3_orchestration import Orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=FullWorkflowResponse,
    responses={
        200: {"description": "Successful recommendation"},
        202: {"model": AsyncTaskResponse, "description": "Async task submitted"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Get product recommendations",
    description="""
    Process a complete recommendation request.

    This endpoint:
    1. Analyzes sentiment of the provided comment (Module 1)
    2. Generates recommendations based on semantic similarity (Module 2)
    3. Returns ranked results

    Set `async_processing=true` to process via Celery and get a task ID.
    """,
)
async def get_recommendations(
    request: RecommendationRequestSchema,
    session: AsyncSession = Depends(get_db_session),
    orchestrator: Orchestrator = Depends(get_orchestrator_dep),
):
    """Get product recommendations based on sentiment analysis."""
    logger.info(
        f"Recommendation request: product={request.product_id}, "
        f"client={request.client_id}"
    )

    try:
        if request.async_processing:
            # Async processing via Celery
            task_id = orchestrator.process_async(
                product_id=request.product_id,
                client_id=request.client_id,
                commentaire=request.commentaire,
                product_type=request.product_type.value,
                top_k=request.top_k,
            )
            return AsyncTaskResponse(
                task_id=task_id,
                status="pending",
                message="Task submitted for async processing",
            )

        # Synchronous processing
        result = await orchestrator.process_recommendation_request(
            product_id=request.product_id,
            client_id=request.client_id,
            commentaire=request.commentaire,
            product_type=request.product_type.value,
            session=session,
            top_k=request.top_k,
        )

        return result

    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/direct",
    response_model=RecommendationResponse,
    summary="Get recommendations with pre-computed sentiment",
    description="Get recommendations using an already computed sentiment score.",
)
async def get_recommendations_direct(
    request: RecommendationOnlyRequest,
    session: AsyncSession = Depends(get_db_session),
    orchestrator: Orchestrator = Depends(get_orchestrator_dep),
):
    """Get recommendations with pre-computed sentiment score."""
    from src.config.constants import ProductType
    from src.modules.module2_recommendation import (
        RecommendationEngine,
        RecommendationRequest,
    )

    try:
        engine = RecommendationEngine()
        rec_request = RecommendationRequest(
            client_id=request.client_id,
            product_id=request.product_id,
            sentiment_score=request.sentiment_score,
            product_type=request.product_type,
            top_k=request.top_k,
        )

        result = await engine.recommend(rec_request, session)
        return result.model_dump()

    except Exception as e:
        logger.error(f"Direct recommendation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/vehicles",
    summary="Get vehicle recommendations",
    description="Shortcut endpoint for vehicle recommendations.",
)
async def get_vehicle_recommendations(
    product_id: str,
    client_id: str,
    commentaire: str,
    top_k: int = 10,
    session: AsyncSession = Depends(get_db_session),
    orchestrator: Orchestrator = Depends(get_orchestrator_dep),
):
    """Get vehicle recommendations."""
    result = await orchestrator.process_recommendation_request(
        product_id=product_id,
        client_id=client_id,
        commentaire=commentaire,
        product_type="vehicle",
        session=session,
        top_k=top_k,
    )
    return result


@router.get(
    "/livreurs",
    summary="Get livreur recommendations",
    description="Shortcut endpoint for delivery person recommendations.",
)
async def get_livreur_recommendations(
    product_id: str,
    client_id: str,
    commentaire: str,
    top_k: int = 10,
    session: AsyncSession = Depends(get_db_session),
    orchestrator: Orchestrator = Depends(get_orchestrator_dep),
):
    """Get livreur recommendations."""
    result = await orchestrator.process_recommendation_request(
        product_id=product_id,
        client_id=client_id,
        commentaire=commentaire,
        product_type="livreur",
        session=session,
        top_k=top_k,
    )
    return result
