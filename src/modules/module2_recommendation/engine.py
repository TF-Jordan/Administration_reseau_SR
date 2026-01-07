"""
Main Recommendation Engine (Module 2).
Orchestrates the complete recommendation workflow.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.config import settings
from src.config.constants import ProductType
from src.database.models import Vehicle, Livreur
from src.database.repositories import vehicle_repository, livreur_repository

from .cache import CacheManager, get_cache_manager
from .embeddings import EmbeddingService, get_embedding_service
from .vector_store import VectorStore, get_vector_store
from .ranking import RankingService, get_ranking_service
from .schemas import (
    RecommendationRequest,
    RecommendationResult,
    SimilarProduct,
    ProductDetails,
    RankedProduct,
    IntermediateResult,
)

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Main recommendation engine implementing the complete workflow:

    1. Check Redis cache
    2. Retrieve product data from PostgreSQL
    3. Build textual description
    4. Generate embedding
    5. Search Qdrant for similar products
    6. Retrieve top-K results
    7. Build intermediate dictionary
    8. Apply final ranking
    9. Store in cache
    10. Return results
    """

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        ranking_service: Optional[RankingService] = None,
    ):
        """
        Initialize recommendation engine with all required services.

        Args:
            cache_manager: Redis cache manager
            embedding_service: Embedding generation service
            vector_store: Qdrant vector store
            ranking_service: Product ranking service
        """
        self.cache = cache_manager or get_cache_manager()
        self.embeddings = embedding_service or get_embedding_service()
        self.vectors = vector_store or get_vector_store()
        self.ranking = ranking_service or get_ranking_service()

        logger.info("RecommendationEngine initialized")

    async def recommend(
        self,
        request: RecommendationRequest,
        session: AsyncSession,
    ) -> RecommendationResult:
        """
        Execute the complete recommendation workflow.

        Args:
            request: Recommendation request with sentiment data
            session: Database session

        Returns:
            RecommendationResult with ranked recommendations
        """
        logger.info(
            f"Processing recommendation for product={request.product_id}, "
            f"client={request.client_id}, sentiment={request.sentiment_score:.2f}"
        )

        # Step 1: Check cache
        cached_result = await self.cache.get_cached_result(request)
        if cached_result:
            logger.info("Returning cached result")
            return cached_result

        # Step 2: Retrieve product data from PostgreSQL
        product_details = await self._get_product_details(
            request.product_id, request.product_type, session
        )

        if product_details is None:
            logger.warning(f"Product not found: {request.product_id}")
            return self._empty_result(request)

        # Step 3: Build textual description
        description = product_details.description

        # Step 4: Generate embedding
        query_vector = self.embeddings.encode_for_qdrant(description)

        # Step 5: Search Qdrant for similar products
        similar_products = self.vectors.search(
            product_type=request.product_type,
            query_vector=query_vector,
            top_k=request.top_k * 2,  # Get more for filtering
        )

        # Filter out the reference product itself
        similar_products = [
            p for p in similar_products if p.product_id != request.product_id
        ]

        if not similar_products:
            logger.info("No similar products found")
            return self._empty_result(request)

        # Step 6 & 7: Get top-K and build intermediate dictionary
        intermediate_dict = self._build_intermediate_dict(
            similar_products[:request.top_k],
            request.client_id,
        )

        # Step 8: Get details and apply ranking
        all_product_details = await self._get_multiple_product_details(
            [p.product_id for p in similar_products[:request.top_k]],
            request.product_type,
            session,
        )

        ranked_products = self.ranking.rank_products(
            similar_products[:request.top_k],
            all_product_details,
            request.product_type,
        )

        # Build final result
        result = RecommendationResult(
            client_id=request.client_id,
            reference_product_id=request.product_id,
            sentiment_score=request.sentiment_score,
            product_type=request.product_type,
            recommendations=ranked_products,
            total_results=len(ranked_products),
            cached=False,
            processed_at=datetime.utcnow(),
        )

        # Step 9: Store in cache
        await self.cache.store_result(request, result)

        logger.info(f"Recommendation completed: {len(ranked_products)} results")
        return result

    def recommend_sync(
        self,
        request: RecommendationRequest,
        session: Session,
    ) -> RecommendationResult:
        """
        Synchronous version for Celery tasks.

        Args:
            request: Recommendation request
            session: Sync database session

        Returns:
            RecommendationResult
        """
        logger.info(f"Processing sync recommendation for {request.product_id}")

        # Get product details
        product_details = self._get_product_details_sync(
            request.product_id, request.product_type, session
        )

        if product_details is None:
            return self._empty_result(request)

        # Generate embedding and search
        query_vector = self.embeddings.encode_for_qdrant(product_details.description)

        similar_products = self.vectors.search(
            product_type=request.product_type,
            query_vector=query_vector,
            top_k=request.top_k * 2,
        )

        similar_products = [
            p for p in similar_products if p.product_id != request.product_id
        ]

        if not similar_products:
            return self._empty_result(request)

        # Get details and rank
        all_details = self._get_multiple_product_details_sync(
            [p.product_id for p in similar_products[:request.top_k]],
            request.product_type,
            session,
        )

        ranked_products = self.ranking.rank_products(
            similar_products[:request.top_k],
            all_details,
            request.product_type,
        )

        return RecommendationResult(
            client_id=request.client_id,
            reference_product_id=request.product_id,
            sentiment_score=request.sentiment_score,
            product_type=request.product_type,
            recommendations=ranked_products,
            total_results=len(ranked_products),
            cached=False,
            processed_at=datetime.utcnow(),
        )

    async def _get_product_details(
        self,
        product_id: str,
        product_type: ProductType,
        session: AsyncSession,
    ) -> Optional[ProductDetails]:
        """Retrieve product details from PostgreSQL."""
        try:
            uuid_id = UUID(product_id)
        except ValueError:
            logger.error(f"Invalid product ID format: {product_id}")
            return None

        if product_type == ProductType.VEHICLE:
            product = await vehicle_repository.get_by_id(session, uuid_id)
            if product:
                return ProductDetails(
                    product_id=str(product.vehicle_id),
                    product_type=product_type,
                    description=product.to_description(),
                    disponible=product.disponible,
                    reputation=product.note_moyenne,
                    localisation=product.localisation,
                    metadata={
                        "brand": product.brand,
                        "model": product.model,
                        "year": product.year,
                        "prix_journalier": product.prix_journalier,
                    },
                )
        else:
            product = await livreur_repository.get_by_id(session, uuid_id)
            if product:
                return ProductDetails(
                    product_id=str(product.id),
                    product_type=product_type,
                    description=product.to_description(),
                    disponible=product.disponible,
                    reputation=product.reputation,
                    localisation=product.localisation,
                    metadata={
                        "nom_commerciale": product.nom_commerciale,
                        "nombre_livraisons": product.nombre_livraisons,
                        "statut": product.statut,
                    },
                )

        return None

    def _get_product_details_sync(
        self,
        product_id: str,
        product_type: ProductType,
        session: Session,
    ) -> Optional[ProductDetails]:
        """Sync version for Celery tasks."""
        try:
            uuid_id = UUID(product_id)
        except ValueError:
            return None

        if product_type == ProductType.VEHICLE:
            product = vehicle_repository.get_by_id_sync(session, uuid_id)
            if product:
                return ProductDetails(
                    product_id=str(product.vehicle_id),
                    product_type=product_type,
                    description=product.to_description(),
                    disponible=product.disponible,
                    reputation=product.note_moyenne,
                    localisation=product.localisation,
                    metadata={
                        "brand": product.brand,
                        "model": product.model,
                    },
                )
        else:
            product = livreur_repository.get_by_id_sync(session, uuid_id)
            if product:
                return ProductDetails(
                    product_id=str(product.id),
                    product_type=product_type,
                    description=product.to_description(),
                    disponible=product.disponible,
                    reputation=product.reputation,
                    localisation=product.localisation,
                    metadata={
                        "nom_commerciale": product.nom_commerciale,
                    },
                )

        return None

    async def _get_multiple_product_details(
        self,
        product_ids: List[str],
        product_type: ProductType,
        session: AsyncSession,
    ) -> Dict[str, ProductDetails]:
        """Get details for multiple products."""
        details = {}
        for product_id in product_ids:
            detail = await self._get_product_details(product_id, product_type, session)
            if detail:
                details[product_id] = detail
        return details

    def _get_multiple_product_details_sync(
        self,
        product_ids: List[str],
        product_type: ProductType,
        session: Session,
    ) -> Dict[str, ProductDetails]:
        """Sync version for multiple products."""
        details = {}
        for product_id in product_ids:
            detail = self._get_product_details_sync(product_id, product_type, session)
            if detail:
                details[product_id] = detail
        return details

    def _build_intermediate_dict(
        self,
        similar_products: List[SimilarProduct],
        client_id: str,
    ) -> Dict[str, IntermediateResult]:
        """
        Build intermediate dictionary as specified in requirements.

        Structure:
        {
            real_product_id: {
                "client_id": "...",
                "similarity_score": ...
            }
        }
        """
        intermediate = {}
        for product in similar_products:
            intermediate[product.product_id] = IntermediateResult(
                client_id=client_id,
                similarity_score=product.similarity_score,
            )
        return intermediate

    def _empty_result(self, request: RecommendationRequest) -> RecommendationResult:
        """Return empty result when no recommendations found."""
        return RecommendationResult(
            client_id=request.client_id,
            reference_product_id=request.product_id,
            sentiment_score=request.sentiment_score,
            product_type=request.product_type,
            recommendations=[],
            total_results=0,
            cached=False,
            processed_at=datetime.utcnow(),
        )

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all services."""
        return {
            "cache": await self.cache.health_check(),
            "embeddings": self.embeddings.health_check(),
            "vectors": self.vectors.health_check(),
        }


# Singleton instance
_engine_instance: Optional[RecommendationEngine] = None


def get_recommendation_engine() -> RecommendationEngine:
    """Get or create singleton recommendation engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RecommendationEngine()
    return _engine_instance
