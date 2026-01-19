"""
Livreur Ranking API endpoints (Module 4).

This module provides a stateless ranking service for delivery persons
based on multi-criteria decision making (AHP + TOPSIS).
"""

import logging
from fastapi import APIRouter, HTTPException, status, Query

from src.modules.module4_livreur_ranking import (
    RankingRequestSchema,
    RankingResponseSchema,
    get_orchestrator,
)
from src.api.schemas import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/rank",
    response_model=RankingResponseSchema,
    responses={
        200: {"description": "Successful ranking"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Rank delivery persons for an announcement",
    description="""
    Ranks delivery persons (livreurs) for a delivery announcement using
    multi-criteria decision making.

    **Process:**
    1. **Spatial Filtering (Phase 1)**: Filters candidates based on geographic
       proximity using spherical ellipse method
    2. **AHP Weight Calculation (Phase 2)**: Calculates criteria weights based
       on delivery type (standard/express/sameday)
    3. **TOPSIS Ranking (Phase 3)**: Ranks eligible candidates using TOPSIS
       multi-criteria decision algorithm

    **Criteria:**
    - Geographic proximity (distance to pickup and delivery)
    - Reputation (rating 0-10)
    - Capacity (max weight in kg)
    - Vehicle type (velo/moto/voiture/camion)

    **Response:**
    Returns ALL delivery persons ranked by score (0-1), with detailed
    statistics about spatial filtering and AHP weights used.

    **Query Parameters:**
    - `include_details` (default: false): Include detailed TOPSIS calculations
      (normalized scores, weighted scores, distances to ideal solutions)
    """,
)
async def rank_livreurs(
    request: RankingRequestSchema,
    include_details: bool = Query(
        default=False,
        description="Include detailed TOPSIS scores in response"
    )
) -> RankingResponseSchema:
    """
    Rank delivery persons for a delivery announcement.

    Args:
        request: Ranking request with announcement and candidates
        include_details: Whether to include detailed TOPSIS calculations

    Returns:
        RankingResponseSchema with ranked delivery persons
    """
    logger.info(
        f"Ranking request for annonce {request.annonce.annonce_id} "
        f"with {len(request.livreurs_candidats)} candidates"
    )

    try:
        # Get orchestrator instance
        orchestrator = get_orchestrator()

        # Perform ranking
        response = orchestrator.rank_livreurs(
            request=request,
            include_details=include_details
        )

        logger.info(
            f"Ranking complete for {request.annonce.annonce_id}: "
            f"{len(response.livreurs_classes)} livreurs ranked"
        )

        return response

    except ValueError as e:
        logger.error(f"Validation error in ranking: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ranking error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check for Module 4",
    description="Check if Module 4 (Livreur Ranking) is operational"
)
async def health_check():
    """
    Health check endpoint for Module 4.

    Returns:
        Dict with module status and component availability
    """
    try:
        # Verify orchestrator can be instantiated
        orchestrator = get_orchestrator()

        # Verify all components are available
        components = {
            "spatial_filter": orchestrator.spatial_filter is not None,
            "ahp_calculator": orchestrator.ahp_calculator is not None,
            "topsis_ranker": orchestrator.topsis_ranker is not None,
        }

        all_ok = all(components.values())

        return {
            "status": "healthy" if all_ok else "degraded",
            "module": "module4_livreur_ranking",
            "components": components,
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "module": "module4_livreur_ranking",
            "error": str(e)
        }
