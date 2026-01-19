"""
Schemas for sentiment analysis module.
Defines input/output data structures.
"""

from pydantic import BaseModel, Field
from typing import Optional


class SentimentInput(BaseModel):
    """Input schema for sentiment analysis."""

    product_id: str = Field(..., description="Product identifier (vehicle or livreur)")
    client_id: str = Field(..., description="Client identifier")
    commentaire: str = Field(..., description="Comment text to analyze")
    product_type: Optional[str] = Field(
        None, description="Type of product: 'vehicle' or 'livreur'"
    )


class SentimentResult(BaseModel):
    """Output schema from sentiment analysis."""

    client_id: str = Field(..., description="Client identifier")
    product_id: str = Field(..., description="Product identifier")
    sentiment_score: float = Field(
        ..., ge=-1.0, le=1.0, description="Sentiment score from -1 (negative) to 1 (positive)"
    )
    sentiment_label: Optional[str] = Field(
        None, description="Sentiment label: positive, negative, or neutral"
    )
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score of the prediction"
    )
    product_type: Optional[str] = Field(
        None, description="Type of product: 'vehicle' or 'livreur'"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client_123",
                "product_id": "vehicle_456",
                "sentiment_score": 0.85,
                "sentiment_label": "positive",
                "confidence": 0.92,
                "product_type": "vehicle",
            }
        }
