"""
Ranking Service for final recommendation scoring.
Implements weighted scoring based on similarity, availability, and reputation.
"""

import logging
from typing import Dict, List, Any, Optional

from src.config import settings
from src.config.constants import ProductType
from .schemas import SimilarProduct, RankedProduct, ProductDetails

logger = logging.getLogger(__name__)


class RankingService:
    """
    Service for ranking similar products based on multiple criteria.

    Scoring factors:
    - Semantic similarity (from vector search)
    - Product availability
    - Product reputation/rating

    Weights are configurable via settings.
    """

    def __init__(
        self,
        similarity_weight: Optional[float] = None,
        availability_weight: Optional[float] = None,
        reputation_weight: Optional[float] = None,
    ):
        """
        Initialize ranking service with configurable weights.

        Args:
            similarity_weight: Weight for semantic similarity (default: 0.6)
            availability_weight: Weight for availability (default: 0.25)
            reputation_weight: Weight for reputation (default: 0.15)
        """
        self.similarity_weight = similarity_weight or settings.similarity_weight
        self.availability_weight = availability_weight or settings.availability_weight
        self.reputation_weight = reputation_weight or settings.reputation_weight

        # Normalize weights
        total = self.similarity_weight + self.availability_weight + self.reputation_weight
        if total != 1.0:
            self.similarity_weight /= total
            self.availability_weight /= total
            self.reputation_weight /= total

        logger.info(
            f"RankingService initialized with weights: "
            f"similarity={self.similarity_weight:.2f}, "
            f"availability={self.availability_weight:.2f}, "
            f"reputation={self.reputation_weight:.2f}"
        )

    def compute_final_score(
        self,
        similarity_score: float,
        availability: bool,
        reputation: float,
    ) -> float:
        """
        Compute weighted final score for a product.

        Args:
            similarity_score: Semantic similarity (0-1)
            availability: Product availability (True/False)
            reputation: Product reputation/rating (0-5 normalized to 0-1)

        Returns:
            Final weighted score (0-1)
        """
        availability_score = 1.0 if availability else 0.0
        reputation_normalized = min(reputation / 5.0, 1.0) if reputation else 0.0

        final_score = (
            self.similarity_weight * similarity_score
            + self.availability_weight * availability_score
            + self.reputation_weight * reputation_normalized
        )

        return round(final_score, 4)

    def rank_products(
        self,
        similar_products: List[SimilarProduct],
        product_details: Dict[str, ProductDetails],
        product_type: ProductType,
    ) -> List[RankedProduct]:
        """
        Rank similar products based on computed scores.

        Args:
            similar_products: List of similar products from vector search
            product_details: Dict mapping product_id to ProductDetails
            product_type: Type of products being ranked

        Returns:
            Sorted list of RankedProduct objects
        """
        ranked_products = []

        for similar in similar_products:
            details = product_details.get(similar.product_id)

            if details is None:
                logger.warning(f"No details found for product {similar.product_id}")
                continue

            # Get reputation from details
            reputation = details.reputation or 0.0

            # Compute final score
            final_score = self.compute_final_score(
                similarity_score=similar.similarity_score,
                availability=details.disponible,
                reputation=reputation,
            )

            ranked_product = RankedProduct(
                product_id=similar.product_id,
                product_type=product_type,
                similarity_score=round(similar.similarity_score, 4),
                availability_score=1.0 if details.disponible else 0.0,
                reputation_score=round(reputation / 5.0, 4) if reputation else 0.0,
                final_score=final_score,
                rank=0,  # Will be set after sorting
                metadata=details.metadata,
            )
            ranked_products.append(ranked_product)

        # Sort by final score (descending)
        ranked_products.sort(key=lambda x: x.final_score, reverse=True)

        # Assign ranks (1-based)
        for i, product in enumerate(ranked_products):
            product.rank = i + 1

        logger.info(f"Ranked {len(ranked_products)} products")
        return ranked_products

    def apply_availability_boost(
        self, products: List[RankedProduct], boost_factor: float = 0.1
    ) -> List[RankedProduct]:
        """
        Apply additional boost to available products.

        Args:
            products: List of ranked products
            boost_factor: Additional score boost for available products

        Returns:
            Re-ranked products with availability boost
        """
        for product in products:
            if product.availability_score == 1.0:
                product.final_score = min(
                    product.final_score + boost_factor, 1.0
                )

        # Re-sort and re-rank
        products.sort(key=lambda x: x.final_score, reverse=True)
        for i, product in enumerate(products):
            product.rank = i + 1

        return products

    def filter_by_minimum_score(
        self, products: List[RankedProduct], min_score: float = 0.3
    ) -> List[RankedProduct]:
        """
        Filter out products below minimum score threshold.

        Args:
            products: List of ranked products
            min_score: Minimum acceptable final score

        Returns:
            Filtered list of products
        """
        filtered = [p for p in products if p.final_score >= min_score]

        # Re-rank after filtering
        for i, product in enumerate(filtered):
            product.rank = i + 1

        logger.info(
            f"Filtered from {len(products)} to {len(filtered)} products "
            f"(min_score={min_score})"
        )
        return filtered


# Singleton instance
_ranking_service: Optional[RankingService] = None


def get_ranking_service() -> RankingService:
    """Get or create singleton ranking service instance."""
    global _ranking_service
    if _ranking_service is None:
        _ranking_service = RankingService()
    return _ranking_service
