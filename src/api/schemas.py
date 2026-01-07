"""
API schemas for request/response validation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.config.constants import ProductType


# Request schemas
class RecommendationRequestSchema(BaseModel):
    """Schema for recommendation request."""

    product_id: str = Field(..., description="Product identifier")
    client_id: str = Field(..., description="Client identifier")
    commentaire: str = Field(..., description="Comment text to analyze")
    product_type: ProductType = Field(..., description="Type: vehicle or livreur")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results")
    async_processing: bool = Field(
        default=False, description="Process asynchronously via Celery"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "client_id": "client_123",
                "commentaire": "Excellent service, très professionnel!",
                "product_type": "vehicle",
                "top_k": 10,
                "async_processing": False,
            }
        }


class SentimentOnlyRequest(BaseModel):
    """Schema for sentiment-only analysis."""

    product_id: str = Field(..., description="Product identifier")
    client_id: str = Field(..., description="Client identifier")
    commentaire: str = Field(..., description="Comment text")
    product_type: Optional[str] = Field(None, description="Product type")

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "client_id": "client_123",
                "commentaire": "Service rapide et efficace",
            }
        }


class RecommendationOnlyRequest(BaseModel):
    """Schema for recommendation with pre-computed sentiment."""

    product_id: str = Field(..., description="Reference product ID")
    client_id: str = Field(..., description="Client identifier")
    sentiment_score: float = Field(
        ..., ge=-1.0, le=1.0, description="Pre-computed sentiment score"
    )
    product_type: ProductType = Field(..., description="Product type")
    top_k: int = Field(default=10, ge=1, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440000",
                "client_id": "client_123",
                "sentiment_score": 0.75,
                "product_type": "vehicle",
                "top_k": 10,
            }
        }


class VectorizationRequest(BaseModel):
    """Schema for triggering vectorization."""

    product_type: ProductType = Field(..., description="Product type to vectorize")
    batch_size: int = Field(default=100, ge=10, le=1000)


# Response schemas
class SentimentResponse(BaseModel):
    """Response schema for sentiment analysis."""

    client_id: str
    product_id: str
    sentiment_score: float
    sentiment_label: str
    confidence: Optional[float] = None


class RankedProductResponse(BaseModel):
    """Response schema for a ranked product."""

    product_id: str
    product_type: str
    similarity_score: float
    availability_score: float
    reputation_score: float
    final_score: float
    rank: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    """Response schema for recommendations."""

    client_id: str
    reference_product_id: str
    sentiment_score: float
    product_type: str
    recommendations: List[RankedProductResponse]
    total_results: int
    cached: bool
    processing_time_seconds: Optional[float] = None
    processed_at: datetime


class FullWorkflowResponse(BaseModel):
    """Response schema for complete workflow."""

    status: str
    processing_time_seconds: float
    sentiment: SentimentResponse
    recommendations: RecommendationResponse


class AsyncTaskResponse(BaseModel):
    """Response for async task submission."""

    task_id: str
    status: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc123-def456",
                "status": "pending",
                "message": "Task submitted successfully",
            }
        }


class TaskStatusResponse(BaseModel):
    """Response for task status query."""

    task_id: str
    status: str
    ready: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response for health check."""

    status: str
    timestamp: datetime
    services: Dict[str, bool]
    version: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    status_code: int
