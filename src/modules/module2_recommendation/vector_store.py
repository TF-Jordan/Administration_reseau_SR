"""
Qdrant Vector Store for semantic search.
Implements HNSW-based similarity search.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from uuid import  uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
    SearchParams,
    HnswConfigDiff,
)

from src.config import settings
from src.config.constants import ProductType
from src.utils.context import get_correlation_id
from .schemas import SimilarProduct

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Qdrant vector store for vehicle embeddings.

    Supports:
    - Vehicle collection for rental platform
    - HNSW-based similarity search
    - Metadata storage with real_product_id mapping
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """
        Initialize vector store connection.

        Args:
            host: Qdrant host
            port: Qdrant port
        """
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self._client: Optional[QdrantClient] = None
        self.dimension = settings.embedding_dimension
        self.collections = {
            ProductType.VEHICLE: settings.qdrant_collection_vehicles,
        }

    def connect(self) -> None:
        """Establish Qdrant connection."""
        if self._client is None:
            self._client = QdrantClient(host=self.host, port=self.port)
            logger.info(f"Qdrant connection established: {self.host}:{self.port}")

    @property
    def client(self) -> QdrantClient:
        """Get Qdrant client."""
        if self._client is None:
            self.connect()
        return self._client

    def _get_collection_name(self, product_type: ProductType) -> str:
        """Get collection name for product type."""
        return self.collections.get(product_type, "products")

    async def create_collection(
        self, product_type: ProductType, recreate: bool = False
    ) -> bool:
        """
        Create or recreate a collection.

        Args:
            product_type: Type of products for this collection
            recreate: If True, delete existing collection first

        Returns:
            True if created successfully
        """
        self.connect()
        collection_name = self._get_collection_name(product_type)

        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)

            if exists and recreate:
                self.client.delete_collection(collection_name)
                logger.info(f"Deleted existing collection: {collection_name}")
                exists = False

            if not exists:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE,
                    ),
                    hnsw_config=HnswConfigDiff(
                        m=16,
                        ef_construct=100,
                        full_scan_threshold=10000,
                    ),
                )
                logger.info(f"Created collection: {collection_name}")

            return True

        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {e}")
            return False

    def create_collection_sync(
        self, product_type: ProductType, recreate: bool = False
    ) -> bool:
        """Synchronous version of create_collection."""
        self.connect()
        collection_name = self._get_collection_name(product_type)

        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)

            if exists and recreate:
                self.client.delete_collection(collection_name)
                exists = False

            if not exists:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE,
                    ),
                    hnsw_config=HnswConfigDiff(
                        m=16,
                        ef_construct=100,
                        full_scan_threshold=10000,
                    ),
                )
                logger.info(f"Created collection: {collection_name}")

            return True

        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return False

    def upsert_vector(
        self,
        product_type: ProductType,
        real_product_id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Insert or update a single vector.

        Args:
            product_type: Type of product
            real_product_id: PostgreSQL product ID
            vector: Embedding vector
            metadata: Additional metadata

        Returns:
            Vector UUID in Qdrant
        """
        self.connect()
        collection_name = self._get_collection_name(product_type)
        vector_id = str(uuid4())

        payload = {
            "real_product_id": real_product_id,
            **(metadata or {}),
        }

        self.client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=vector_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

        logger.debug(f"Upserted vector {vector_id} for product {real_product_id}")
        return vector_id

    def upsert_vectors_batch(
        self,
        product_type: ProductType,
        items: List[Dict[str, Any]],
    ) -> int:
        """
        Batch insert vectors.

        Args:
            product_type: Type of products
            items: List of dicts with 'real_product_id', 'vector', and optional 'metadata'

        Returns:
            Number of vectors inserted
        """
        self.connect()
        collection_name = self._get_collection_name(product_type)

        points = []
        for item in items:
            vector_id = str(uuid4())
            payload = {
                "real_product_id": item["real_product_id"],
                **(item.get("metadata", {})),
            }
            points.append(
                PointStruct(
                    id=vector_id,
                    vector=item["vector"],
                    payload=payload,
                )
            )

        if points:
            self.client.upsert(
                collection_name=collection_name,
                points=points,
                wait=True,
            )
            logger.info(f"Batch upserted {len(points)} vectors to {collection_name}")

        return len(points)

    def search(
        self,
        product_type: ProductType,
        query_vector: List[float],
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> List[SimilarProduct]:
        """
        Search for similar products.

        Args:
            product_type: Type of products to search
            query_vector: Query embedding vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            List of SimilarProduct objects
        """
        start_time = time.time()
        self.connect()
        collection_name = self._get_collection_name(product_type)

        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                search_params=SearchParams(
                    hnsw_ef=128,
                    exact=False,
                ),
            )

            similar_products = []
            scores = []
            for result in results:
                similar_products.append(
                    SimilarProduct(
                        product_id=result.payload.get("real_product_id", ""),
                        similarity_score=result.score,
                        vector_id=str(result.id),
                    )
                )
                scores.append(result.score)

            duration_ms = (time.time() - start_time) * 1000

            # Log vector search metrics
            logger.info(
                f"Vector search completed: {len(similar_products)} results",
                extra={
                    "event": "vector_search",
                    "metric_type": "vector_search",
                    "operation": "search",
                    "collection": collection_name,
                    "product_type": product_type.value,
                    "query_limit": top_k,
                    "results_count": len(similar_products),
                    "score_threshold": score_threshold,
                    "duration_ms": round(duration_ms, 2),
                    "avg_score": round(sum(scores) / len(scores), 3) if scores else 0,
                    "max_score": round(max(scores), 3) if scores else 0,
                    "min_score": round(min(scores), 3) if scores else 0,
                    "vector_dim": len(query_vector),
                    "hnsw_ef": 128,
                    "correlation_id": get_correlation_id(),
                }
            )

            return similar_products

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Vector search error: {e}",
                extra={
                    "event": "vector_search_error",
                    "metric_type": "vector_search",
                    "operation": "search",
                    "collection": collection_name,
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": get_correlation_id(),
                }
            )
            return []

    def delete_by_product_id(
        self, product_type: ProductType, real_product_id: str
    ) -> bool:
        """
        Delete vectors for a specific product.

        Args:
            product_type: Type of product
            real_product_id: PostgreSQL product ID

        Returns:
            True if deleted successfully
        """
        self.connect()
        collection_name = self._get_collection_name(product_type)

        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="real_product_id",
                                match=qdrant_models.MatchValue(value=real_product_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Deleted vectors for product {real_product_id}")
            return True

        except Exception as e:
            logger.error(f"Delete error: {e}")
            return False

    def get_collection_info(self, product_type: ProductType) -> Dict[str, Any]:
        """Get collection statistics."""
        self.connect()
        collection_name = self._get_collection_name(product_type)

        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.points_count,
                "points_count": info.points_count,
                "status": info.status,
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {"error": str(e)}

    def health_check(self) -> bool:
        """Check Qdrant connection health."""
        try:
            self.connect()
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create singleton vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
