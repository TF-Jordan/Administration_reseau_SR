"""
Redis Cache Manager for recommendation results.
Implements cache verification with sentiment score tolerance.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import redis.asyncio as redis

from src.config import settings, SENTIMENT_SCORE_TOLERANCE, CACHE_TTL_SECONDS
from src.config.constants import CacheKeyPrefix
from src.utils.context import get_correlation_id
from .schemas import RecommendationRequest, RecommendationResult

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis cache manager for recommendation results.

    Implements:
    1. Exact match lookup by product_id, client_id, and sentiment_score
    2. Fuzzy match with sentiment score tolerance
    3. Cache storage with configurable TTL
    """

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache manager with Redis connection."""
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None
        self.ttl_seconds = CACHE_TTL_SECONDS
        self.sentiment_tolerance = SENTIMENT_SCORE_TOLERANCE

    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Redis cache connection established")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis cache connection closed")

    @property
    def client(self) -> redis.Redis:
        """Get Redis client, ensuring connection."""
        if self._client is None:
            raise RuntimeError("Cache not connected. Call connect() first.")
        return self._client

    def _generate_cache_key(
        self,
        product_id: str,
        client_id: str,
        sentiment_score: float,
        product_type: str,
    ) -> str:
        """
        Generate cache key from request parameters.

        Uses sentiment score interval for fuzzy matching.
        """
        # Round sentiment score to nearest tolerance interval
        score_bucket = round(sentiment_score / self.sentiment_tolerance) * self.sentiment_tolerance

        key_data = f"{product_type}:{product_id}:{client_id}:{score_bucket:.2f}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]

        return f"{CacheKeyPrefix.RECOMMENDATION.value}:{product_type}:{key_hash}"

    def _generate_product_key(self, product_id: str, product_type: str) -> str:
        """Generate key for product-only lookup."""
        return f"{CacheKeyPrefix.PRODUCT.value}:{product_type}:{product_id}"

    async def get_cached_result(
        self, request: RecommendationRequest
    ) -> Optional[RecommendationResult]:
        """
        Check cache for existing recommendation result.

        First checks exact match, then checks for similar sentiment scores.

        Args:
            request: The recommendation request

        Returns:
            Cached result if found, None otherwise
        """
        start_time = time.time()
        await self.connect()

        cache_hit = False
        cache_hit_type = None
        result = None

        try:
            # Try exact match first
            cache_key = self._generate_cache_key(
                request.product_id,
                request.client_id,
                request.sentiment_score,
                request.product_type.value,
            )

            cached_data = await self.client.get(cache_key)
            if cached_data:
                cache_hit = True
                cache_hit_type = "exact"
                logger.info(f"Cache hit (exact): {cache_key}")
                result = RecommendationResult.model_validate_json(cached_data)
                result.cached = True
                result.cache_key = cache_key

                # Log cache metrics
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "Cache operation completed",
                    extra={
                        "event": "cache_get",
                        "metric_type": "cache_operation",
                        "operation": "get",
                        "cache_hit": True,
                        "cache_hit_type": "exact",
                        "duration_ms": round(duration_ms, 2),
                        "product_id": request.product_id,
                        "product_type": request.product_type.value,
                        "correlation_id": get_correlation_id(),
                    }
                )
                return result

            # Try fuzzy match with nearby sentiment scores
            for delta in [-self.sentiment_tolerance, self.sentiment_tolerance]:
                nearby_score = request.sentiment_score + delta
                if -1.0 <= nearby_score <= 1.0:
                    fuzzy_key = self._generate_cache_key(
                        request.product_id,
                        request.client_id,
                        nearby_score,
                        request.product_type.value,
                    )
                    cached_data = await self.client.get(fuzzy_key)
                    if cached_data:
                        cache_hit = True
                        cache_hit_type = "fuzzy"
                        logger.info(f"Cache hit (fuzzy): {fuzzy_key}")
                        result = RecommendationResult.model_validate_json(cached_data)
                        result.cached = True
                        result.cache_key = fuzzy_key

                        # Log cache metrics
                        duration_ms = (time.time() - start_time) * 1000
                        logger.info(
                            "Cache operation completed",
                            extra={
                                "event": "cache_get",
                                "metric_type": "cache_operation",
                                "operation": "get",
                                "cache_hit": True,
                                "cache_hit_type": "fuzzy",
                                "duration_ms": round(duration_ms, 2),
                                "product_id": request.product_id,
                                "product_type": request.product_type.value,
                                "sentiment_delta": delta,
                                "correlation_id": get_correlation_id(),
                            }
                        )
                        return result

            # Check product-only cache (same product, any client)
            product_key = self._generate_product_key(
                request.product_id, request.product_type.value
            )
            product_cache = await self.client.get(product_key)
            if product_cache:
                # Verify sentiment score is within tolerance
                cached_result = RecommendationResult.model_validate_json(product_cache)
                if abs(cached_result.sentiment_score - request.sentiment_score) <= self.sentiment_tolerance:
                    cache_hit = True
                    cache_hit_type = "product"
                    logger.info(f"Cache hit (product): {product_key}")
                    cached_result.cached = True
                    cached_result.cache_key = product_key

                    # Log cache metrics
                    duration_ms = (time.time() - start_time) * 1000
                    logger.info(
                        "Cache operation completed",
                        extra={
                            "event": "cache_get",
                            "metric_type": "cache_operation",
                            "operation": "get",
                            "cache_hit": True,
                            "cache_hit_type": "product",
                            "duration_ms": round(duration_ms, 2),
                            "product_id": request.product_id,
                            "product_type": request.product_type.value,
                            "correlation_id": get_correlation_id(),
                        }
                    )
                    return cached_result

            # Cache miss
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Cache miss",
                extra={
                    "event": "cache_get",
                    "metric_type": "cache_operation",
                    "operation": "get",
                    "cache_hit": False,
                    "cache_hit_type": None,
                    "duration_ms": round(duration_ms, 2),
                    "product_id": request.product_id,
                    "product_type": request.product_type.value,
                    "correlation_id": get_correlation_id(),
                }
            )
            return None

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Cache lookup error: {e}",
                extra={
                    "event": "cache_error",
                    "metric_type": "cache_operation",
                    "operation": "get",
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": get_correlation_id(),
                }
            )
            return None

    async def store_result(
        self,
        request: RecommendationRequest,
        result: RecommendationResult,
    ) -> bool:
        """
        Store recommendation result in cache.

        Args:
            request: Original request
            result: Recommendation result to cache

        Returns:
            True if stored successfully
        """
        start_time = time.time()
        await self.connect()

        try:
            # Store with full key (includes client_id)
            cache_key = self._generate_cache_key(
                request.product_id,
                request.client_id,
                request.sentiment_score,
                request.product_type.value,
            )

            result_json = result.model_dump_json()
            data_size_bytes = len(result_json.encode('utf-8'))

            # Set with TTL
            await self.client.setex(
                cache_key,
                self.ttl_seconds,
                result_json,
            )

            # Also store product-level cache
            product_key = self._generate_product_key(
                request.product_id, request.product_type.value
            )
            await self.client.setex(
                product_key,
                self.ttl_seconds,
                result_json,
            )

            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Cache store completed: {cache_key}",
                extra={
                    "event": "cache_set",
                    "metric_type": "cache_operation",
                    "operation": "set",
                    "duration_ms": round(duration_ms, 2),
                    "data_size_bytes": data_size_bytes,
                    "ttl_seconds": self.ttl_seconds,
                    "product_id": request.product_id,
                    "product_type": request.product_type.value,
                    "correlation_id": get_correlation_id(),
                }
            )
            return True

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Cache store error: {e}",
                extra={
                    "event": "cache_error",
                    "metric_type": "cache_operation",
                    "operation": "set",
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": get_correlation_id(),
                }
            )
            return False

    async def invalidate(
        self,
        product_id: str,
        product_type: str,
        client_id: Optional[str] = None,
    ) -> int:
        """
        Invalidate cache entries for a product.

        Args:
            product_id: Product to invalidate
            product_type: Type of product
            client_id: Optional specific client to invalidate

        Returns:
            Number of keys deleted
        """
        await self.connect()

        try:
            pattern = f"{CacheKeyPrefix.RECOMMENDATION.value}:{product_type}:*"
            keys_deleted = 0

            async for key in self.client.scan_iter(match=pattern):
                await self.client.delete(key)
                keys_deleted += 1

            # Also invalidate product key
            product_key = self._generate_product_key(product_id, product_type)
            await self.client.delete(product_key)
            keys_deleted += 1

            logger.info(f"Invalidated {keys_deleted} cache entries")
            return keys_deleted

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            await self.connect()
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create singleton cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
