"""
Schemas for the recommendation module.
Defines data structures for recommendations workflow.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.config.constants import ProductType


class RecommendationRequest(BaseModel):
    """Input schema for recommendation request from Module 1."""

    client_id: str = Field(..., description="Client identifier")
    product_id: str = Field(..., description="Product identifier (reference product)")
    sentiment_score: float = Field(
        ..., ge=-1.0, le=1.0, description="Sentiment score from analysis"
    )
    product_type: ProductType = Field(
        ..., description="Type of product: vehicle or livreur"
    )
    top_k: Optional[int] = Field(
        default=10, ge=1, le=100, description="Number of recommendations to return"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client_123",
                "product_id": "vehicle_456",
                "sentiment_score": 0.85,
                "product_type": "vehicle",
                "top_k": 10,
            }
        }


class SimilarProduct(BaseModel):
    """Intermediate structure for similar products from vector search."""

    product_id: str = Field(..., description="Product identifier from PostgreSQL")
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Cosine similarity score"
    )
    vector_id: Optional[str] = Field(None, description="Vector ID in Qdrant")


class ProductDetails(BaseModel):
    """Product details retrieved from PostgreSQL."""

    product_id: str
    product_type: ProductType
    description: str
    disponible: bool
    reputation: Optional[float] = None
    localisation: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RankedProduct(BaseModel):
    """Final ranked product in recommendation result."""

    product_id: str = Field(..., description="Product identifier")
    product_type: ProductType = Field(..., description="Product type")
    similarity_score: float = Field(..., description="Semantic similarity score")
    availability_score: float = Field(..., description="Availability score (0 or 1)")
    reputation_score: float = Field(
        default=0.0, description="Reputation/rating score"
    )
    final_score: float = Field(..., description="Weighted final score")
    rank: int = Field(..., description="Position in ranking (1-based)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional product info"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "vehicle_789",
                "product_type": "vehicle",
                "similarity_score": 0.92,
                "availability_score": 1.0,
                "reputation_score": 0.85,
                "final_score": 0.91,
                "rank": 1,
                "metadata": {"brand": "Toyota", "model": "Corolla"},
            }
        }


class IntermediateResult(BaseModel):
    """Intermediate dictionary structure as specified in requirements."""

    client_id: str
    similarity_score: float


class RecommendationResult(BaseModel):
    """Final output schema from recommendation engine."""

    client_id: str = Field(..., description="Client who requested recommendations")
    reference_product_id: str = Field(
        ..., description="Original product used as reference"
    )
    sentiment_score: float = Field(
        ..., description="Sentiment score from the original analysis"
    )
    product_type: ProductType = Field(..., description="Type of recommended products")
    recommendations: List[RankedProduct] = Field(
        ..., description="Ranked list of recommendations"
    )
    total_results: int = Field(..., description="Total number of results")
    cached: bool = Field(default=False, description="Whether result was from cache")
    cache_key: Optional[str] = Field(None, description="Cache key if cached")
    processed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Processing timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client_123",
                "reference_product_id": "vehicle_456",
                "sentiment_score": 0.85,
                "product_type": "vehicle",
                "recommendations": [
                    {
                        "product_id": "vehicle_789",
                        "product_type": "vehicle",
                        "similarity_score": 0.92,
                        "availability_score": 1.0,
                        "reputation_score": 0.85,
                        "final_score": 0.91,
                        "rank": 1,
                        "metadata": {},
                    }
                ],
                "total_results": 10,
                "cached": False,
                "processed_at": "2024-01-15T10:30:00Z",
            }
        }


class CacheEntry(BaseModel):
    """Schema for cached recommendation entry."""

    key: str
    result: RecommendationResult
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    sentiment_score_range: tuple[float, float]
