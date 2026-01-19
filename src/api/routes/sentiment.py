"""
Sentiment Analysis API endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from src.api.schemas import SentimentOnlyRequest, SentimentResponse, AsyncTaskResponse
from src.modules.module1_sentiment import SentimentAnalyzer, SentimentInput
from src.modules.module3_orchestration.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/analyze",
    response_model=SentimentResponse,
    summary="Analyze sentiment",
    description="Analyze sentiment of a comment using the fine-tuned model.",
)
async def analyze_sentiment(request: SentimentOnlyRequest):
    """
    Analyze sentiment of a single comment.

    Uses the fine-tuned distil-camembert model for French text analysis.
    """
    logger.info(f"Sentiment analysis request for product={request.product_id}")

    try:
        analyzer = SentimentAnalyzer()
        input_data = SentimentInput(
            product_id=request.product_id,
            client_id=request.client_id,
            commentaire=request.commentaire,
            product_type=request.product_type,
        )

        result = analyzer.analyze(input_data)

        return SentimentResponse(
            client_id=result.client_id,
            product_id=result.product_id,
            sentiment_score=result.sentiment_score,
            sentiment_label=result.sentiment_label or "unknown",
            confidence=result.confidence,
        )

    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/analyze/async",
    response_model=AsyncTaskResponse,
    summary="Analyze sentiment asynchronously",
    description="Submit sentiment analysis for async processing via Celery.",
)
async def analyze_sentiment_async(request: SentimentOnlyRequest):
    """
    Submit sentiment analysis for async processing.

    Returns a task ID that can be used to check status.
    """
    logger.info(f"Async sentiment request for product={request.product_id}")

    try:
        orchestrator = get_orchestrator()
        task_id = orchestrator.process_sentiment_only(
            product_id=request.product_id,
            client_id=request.client_id,
            commentaire=request.commentaire,
            product_type=request.product_type or "unknown",
        )

        return AsyncTaskResponse(
            task_id=task_id,
            status="pending",
            message="Sentiment analysis task submitted",
        )

    except Exception as e:
        logger.error(f"Async sentiment submission error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/batch",
    summary="Analyze sentiment for multiple comments",
    description="Batch sentiment analysis for multiple comments.",
)
async def analyze_sentiment_batch(requests: list[SentimentOnlyRequest]):
    """
    Analyze sentiment for multiple comments in batch.

    Returns list of sentiment results.
    """
    logger.info(f"Batch sentiment request: {len(requests)} items")

    try:
        analyzer = SentimentAnalyzer()
        inputs = [
            SentimentInput(
                product_id=req.product_id,
                client_id=req.client_id,
                commentaire=req.commentaire,
                product_type=req.product_type,
            )
            for req in requests
        ]

        results = analyzer.analyze_batch(inputs)

        return [
            SentimentResponse(
                client_id=r.client_id,
                product_id=r.product_id,
                sentiment_score=r.sentiment_score,
                sentiment_label=r.sentiment_label or "unknown",
                confidence=r.confidence,
            )
            for r in results
        ]

    except Exception as e:
        logger.error(f"Batch sentiment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
