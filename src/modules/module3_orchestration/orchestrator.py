"""
Main Orchestrator for the recommendation system.
Coordinates the flow between Module 1 and Module 2.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from celery.result import AsyncResult
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.constants import ProductType
from src.modules.module1_sentiment import (
    SentimentAnalyzer,
    SentimentInput,
)
from src.modules.module2_recommendation import (
    RecommendationEngine,
    RecommendationRequest,
    CacheManager,
)

from .tasks import (
    process_sentiment_task,
    process_recommendation_task,
    process_full_workflow_task,
    vectorize_products_task,
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator coordinating the recommendation workflow.

    Responsibilities:
    - Orchestrate Module 1 (sentiment) and Module 2 (recommendation)
    - Manage data flow between modules
    - Handle cache management
    - Dispatch async tasks via Celery
    """

    def __init__(
        self,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None,
        recommendation_engine: Optional[RecommendationEngine] = None,
        cache_manager: Optional[CacheManager] = None,
    ):
        """
        Initialize orchestrator with required services.

        Args:
            sentiment_analyzer: Module 1 sentiment analyzer
            recommendation_engine: Module 2 recommendation engine
            cache_manager: Redis cache manager
        """
        self._sentiment_analyzer = sentiment_analyzer
        self._recommendation_engine = recommendation_engine
        self._cache_manager = cache_manager

        logger.info("Orchestrator initialized")

    @property
    def sentiment_analyzer(self) -> SentimentAnalyzer:
        """Get or create sentiment analyzer."""
        if self._sentiment_analyzer is None:
            self._sentiment_analyzer = SentimentAnalyzer()
        return self._sentiment_analyzer

    @property
    def recommendation_engine(self) -> RecommendationEngine:
        """Get or create recommendation engine."""
        if self._recommendation_engine is None:
            self._recommendation_engine = RecommendationEngine()
        return self._recommendation_engine

    @property
    def cache_manager(self) -> CacheManager:
        """Get or create cache manager."""
        if self._cache_manager is None:
            from src.modules.module2_recommendation.cache import get_cache_manager
            self._cache_manager = get_cache_manager()
        return self._cache_manager

    async def process_recommendation_request(
        self,
        product_id: str,
        client_id: str,
        commentaire: str,
        product_type: str,
        session: AsyncSession,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Process a complete recommendation request synchronously.

        Flow:
        1. Analyze sentiment (Module 1)
        2. Generate recommendations (Module 2)
        3. Return combined results

        Args:
            product_id: Product identifier
            client_id: Client identifier
            commentaire: Comment text
            product_type: Type of product
            session: Database session
            top_k: Number of recommendations

        Returns:
            Dict with sentiment and recommendation results
        """
        logger.info(
            f"Processing recommendation request: "
            f"product={product_id}, client={client_id}"
        )

        start_time = datetime.utcnow()

        # Step 1: Sentiment Analysis (Module 1)
        sentiment_input = SentimentInput(
            product_id=product_id,
            client_id=client_id,
            commentaire=commentaire,
            product_type=product_type,
        )
        sentiment_result = self.sentiment_analyzer.analyze(sentiment_input)

        logger.info(
            f"Sentiment analysis completed: score={sentiment_result.sentiment_score:.2f}"
        )

        # Step 2: Recommendation (Module 2)
        rec_request = RecommendationRequest(
            client_id=client_id,
            product_id=product_id,
            sentiment_score=sentiment_result.sentiment_score,
            product_type=ProductType(product_type),
            top_k=top_k,
        )

        rec_result = await self.recommendation_engine.recommend(rec_request, session)

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return {
            "status": "completed",
            "processing_time_seconds": processing_time,
            "sentiment": {
                "score": sentiment_result.sentiment_score,
                "label": sentiment_result.sentiment_label,
                "confidence": sentiment_result.confidence,
            },
            "recommendations": rec_result.model_dump(),
        }

    def process_async(
        self,
        product_id: str,
        client_id: str,
        commentaire: str,
        product_type: str,
        top_k: int = 10,
    ) -> str:
        """
        Process recommendation request asynchronously via Celery.

        Args:
            product_id: Product identifier
            client_id: Client identifier
            commentaire: Comment text
            product_type: Type of product
            top_k: Number of recommendations

        Returns:
            Celery task ID for status tracking
        """
        logger.info(f"Dispatching async task for product={product_id}")

        task = process_full_workflow_task.delay(
            product_id=product_id,
            client_id=client_id,
            commentaire=commentaire,
            product_type=product_type,
            top_k=top_k,
        )

        return task.id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of an async task.

        Args:
            task_id: Celery task ID

        Returns:
            Dict with task status and result if completed
        """
        result = AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready(),
        }

        if result.ready():
            if result.successful():
                response["result"] = result.get()
            else:
                response["error"] = str(result.result)

        return response

    def process_sentiment_only(
        self,
        product_id: str,
        client_id: str,
        commentaire: str,
        product_type: str,
    ) -> str:
        """
        Process only sentiment analysis asynchronously.

        Args:
            product_id: Product identifier
            client_id: Client identifier
            commentaire: Comment text
            product_type: Type of product

        Returns:
            Celery task ID
        """
        task = process_sentiment_task.delay(
            product_id=product_id,
            client_id=client_id,
            commentaire=commentaire,
            product_type=product_type,
        )
        return task.id

    def process_recommendation_only(
        self,
        client_id: str,
        product_id: str,
        sentiment_score: float,
        product_type: str,
        top_k: int = 10,
    ) -> str:
        """
        Process only recommendation asynchronously.

        Args:
            client_id: Client identifier
            product_id: Reference product ID
            sentiment_score: Pre-computed sentiment score
            product_type: Type of product
            top_k: Number of recommendations

        Returns:
            Celery task ID
        """
        task = process_recommendation_task.delay(
            client_id=client_id,
            product_id=product_id,
            sentiment_score=sentiment_score,
            product_type=product_type,
            top_k=top_k,
        )
        return task.id

    def trigger_vectorization(
        self,
        product_type: str,
        batch_size: int = 100,
    ) -> str:
        """
        Trigger product vectorization task.

        Args:
            product_type: Type of products to vectorize
            batch_size: Number of products per batch

        Returns:
            Celery task ID
        """
        task = vectorize_products_task.delay(
            product_type=product_type,
            batch_size=batch_size,
        )
        return task.id

    async def invalidate_product_cache(
        self,
        product_id: str,
        product_type: str,
    ) -> int:
        """
        Invalidate cache entries for a product.

        Args:
            product_id: Product identifier
            product_type: Type of product

        Returns:
            Number of cache entries invalidated
        """
        return await self.cache_manager.invalidate(
            product_id=product_id,
            product_type=product_type,
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all orchestrated services.

        Returns:
            Dict with health status
        """
        from src.modules.module2_recommendation.vector_store import get_vector_store
        from src.modules.module2_recommendation.embeddings import get_embedding_service
        from src.modules.module2_recommendation.cache import get_cache_manager

        cache = get_cache_manager()
        embeddings = get_embedding_service()
        vectors = get_vector_store()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "sentiment_analyzer": self.sentiment_analyzer.health_check(),
                "redis": await cache.health_check(),
                "embeddings": embeddings.health_check(),
                "qdrant": vectors.health_check(),
            },
        }


# Singleton instance
_orchestrator_instance: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get or create singleton orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = Orchestrator()
    return _orchestrator_instance
