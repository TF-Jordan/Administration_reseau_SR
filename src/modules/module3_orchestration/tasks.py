"""
Celery tasks for asynchronous processing.
"""

import logging
from typing import Dict, Any, Optional

from celery import shared_task

from src.config.constants import ProductType
from src.database.connection import get_sync_session
from src.modules.module1_sentiment import SentimentAnalyzer, SentimentInput
from src.modules.module2_recommendation import (
    RecommendationEngine,
    RecommendationRequest,
)

from .celery_app import celery_app, BaseTask

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask, name="process_sentiment")
def process_sentiment_task(
    self,
    product_id: str,
    client_id: str,
    commentaire: str,
    product_type: str,
) -> Dict[str, Any]:
    """
    Celery task for sentiment analysis.

    Args:
        product_id: Product identifier
        client_id: Client identifier
        commentaire: Comment text to analyze
        product_type: Type of product (vehicle)

    Returns:
        Dict with sentiment analysis results
    """
    logger.info(f"Processing sentiment for product={product_id}, client={client_id}")

    try:
        analyzer = SentimentAnalyzer()
        input_data = SentimentInput(
            product_id=product_id,
            client_id=client_id,
            commentaire=commentaire,
            product_type=product_type,
        )

        result = analyzer.analyze(input_data)

        return {
            "client_id": result.client_id,
            "product_id": result.product_id,
            "sentiment_score": result.sentiment_score,
            "sentiment_label": result.sentiment_label,
            "confidence": result.confidence,
            "product_type": result.product_type,
        }

    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        raise self.retry(exc=e)


@celery_app.task(bind=True, base=BaseTask, name="process_recommendation")
def process_recommendation_task(
    self,
    client_id: str,
    product_id: str,
    sentiment_score: float,
    product_type: str,
    top_k: int = 10,
) -> Dict[str, Any]:
    """
    Celery task for recommendation generation.

    Args:
        client_id: Client identifier
        product_id: Reference product ID
        sentiment_score: Sentiment score from analysis
        product_type: Type of products to recommend
        top_k: Number of recommendations

    Returns:
        Dict with recommendation results
    """
    logger.info(
        f"Processing recommendation for product={product_id}, "
        f"sentiment={sentiment_score:.2f}"
    )

    try:
        engine = RecommendationEngine()
        request = RecommendationRequest(
            client_id=client_id,
            product_id=product_id,
            sentiment_score=sentiment_score,
            product_type=ProductType(product_type),
            top_k=top_k,
        )

        session = get_sync_session()
        try:
            result = engine.recommend_sync(request, session)
            return result.model_dump()
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Recommendation processing failed: {e}")
        raise self.retry(exc=e)


@celery_app.task(bind=True, base=BaseTask, name="process_full_workflow")
def process_full_workflow_task(
    self,
    product_id: str,
    client_id: str,
    commentaire: str,
    product_type: str,
    top_k: int = 10,
) -> Dict[str, Any]:
    """
    Complete workflow: sentiment analysis + recommendation.

    Args:
        product_id: Product identifier
        client_id: Client identifier
        commentaire: Comment text
        product_type: Type of product
        top_k: Number of recommendations

    Returns:
        Dict with full workflow results
    """
    logger.info(f"Starting full workflow for product={product_id}")

    try:
        # Step 1: Sentiment analysis
        analyzer = SentimentAnalyzer()
        sentiment_input = SentimentInput(
            product_id=product_id,
            client_id=client_id,
            commentaire=commentaire,
            product_type=product_type,
        )
        sentiment_result = analyzer.analyze(sentiment_input)

        # Step 2: Recommendation
        engine = RecommendationEngine()
        rec_request = RecommendationRequest(
            client_id=client_id,
            product_id=product_id,
            sentiment_score=sentiment_result.sentiment_score,
            product_type=ProductType(product_type),
            top_k=top_k,
        )

        session = get_sync_session()
        try:
            rec_result = engine.recommend_sync(rec_request, session)
        finally:
            session.close()

        return {
            "sentiment": {
                "score": sentiment_result.sentiment_score,
                "label": sentiment_result.sentiment_label,
                "confidence": sentiment_result.confidence,
            },
            "recommendations": rec_result.model_dump(),
        }

    except Exception as e:
        logger.error(f"Full workflow failed: {e}")
        raise self.retry(exc=e)


@celery_app.task(bind=True, base=BaseTask, name="vectorize_products")
def vectorize_products_task(
    self,
    product_type: str,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """
    Task to vectorize all products of a given type.

    Args:
        product_type: Type of products to vectorize
        batch_size: Number of products per batch

    Returns:
        Dict with vectorization results
    """
    from src.modules.module2_recommendation import (
        EmbeddingService,
        VectorStore,
    )
    from src.database.repositories import vehicle_repository

    logger.info(f"Starting vectorization for {product_type}")

    try:
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        pt = ProductType(product_type)

        # Create collection
        vector_store.create_collection_sync(pt, recreate=True)

        session = get_sync_session()
        try:
            # Get all products
            products = vehicle_repository.get_all_sync(session)
            items = [
                {
                    "real_product_id": str(p.vehicle_id),
                    "vector": embedding_service.encode_for_qdrant(
                        p.to_description()
                    ),
                    "metadata": {
                        "brand": p.brand,
                        "model": p.model,
                        "disponible": p.disponible,
                    },
                }
                for p in products
            ]

            # Batch insert
            total_inserted = 0
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                count = vector_store.upsert_vectors_batch(pt, batch)
                total_inserted += count
                logger.info(
                    f"Vectorized batch {i // batch_size + 1}: {count} items"
                )

            return {
                "product_type": product_type,
                "total_products": len(products),
                "total_vectors": total_inserted,
                "status": "completed",
            }

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Vectorization failed: {e}")
        raise self.retry(exc=e)


@celery_app.task(name="health_check")
def health_check_task() -> Dict[str, Any]:
    """
    Periodic health check task.

    Returns:
        Dict with health status of all services
    """
    from src.modules.module2_recommendation import (
        get_cache_manager,
        get_embedding_service,
        get_vector_store,
    )

    results = {
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "services": {},
    }

    # Check cache
    try:
        cache = get_cache_manager()
        import asyncio
        results["services"]["redis"] = asyncio.run(cache.health_check())
    except Exception as e:
        results["services"]["redis"] = False
        logger.error(f"Redis health check failed: {e}")

    # Check embeddings
    try:
        embeddings = get_embedding_service()
        results["services"]["embeddings"] = embeddings.health_check()
    except Exception as e:
        results["services"]["embeddings"] = False
        logger.error(f"Embeddings health check failed: {e}")

    # Check vector store
    try:
        vectors = get_vector_store()
        results["services"]["qdrant"] = vectors.health_check()
    except Exception as e:
        results["services"]["qdrant"] = False
        logger.error(f"Qdrant health check failed: {e}")

    results["healthy"] = all(results["services"].values())
    return results
