"""
Application constants and enumerations.
"""

from enum import Enum

# Product Types
PRODUCT_TYPE_VEHICLE = "vehicle"

# Cache Settings
CACHE_TTL_SECONDS = 3600
SENTIMENT_SCORE_TOLERANCE = 0.1
DEFAULT_TOP_K = 10

# Ranking Weights (default values)
DEFAULT_SIMILARITY_WEIGHT = 0.6
DEFAULT_AVAILABILITY_WEIGHT = 0.25
DEFAULT_REPUTATION_WEIGHT = 0.15


class ProductType(str, Enum):
    """Enumeration of supported product types."""
    VEHICLE = "vehicle"


class SentimentLabel(str, Enum):
    """Sentiment classification labels."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class TaskStatus(str, Enum):
    """Celery task status values."""
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"


class CacheKeyPrefix(str, Enum):
    """Redis cache key prefixes."""
    RECOMMENDATION = "rec"
    SENTIMENT = "sent"
    PRODUCT = "prod"
    EMBEDDING = "emb"


# Vehicle-specific constants
VEHICLE_FUEL_TYPES = [
    "essence",
    "diesel",
    "electrique",
    "hybride",
    "gpl",
]

VEHICLE_TRANSMISSION_TYPES = [
    "manuelle",
    "automatique",
    "semi-automatique",
]
