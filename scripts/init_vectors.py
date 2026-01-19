#!/usr/bin/env python3
"""
Vector Initialization Script
Vectorizes all products in PostgreSQL and stores them in Qdrant.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.config.constants import ProductType
from src.database.connection import get_sync_session
from src.database.repositories import vehicle_repository
from src.modules.module2_recommendation import (
    EmbeddingService,
    VectorStore,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def vectorize_vehicles(
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    batch_size: int = 50,
) -> int:
    """
    Vectorize all vehicles.

    Args:
        embedding_service: Embedding service instance
        vector_store: Vector store instance
        batch_size: Number of items per batch

    Returns:
        Number of vehicles vectorized
    """
    logger.info("Starting vehicle vectorization...")

    session = get_sync_session()
    try:
        # Get all vehicles
        vehicles = vehicle_repository.get_all_sync(session)
        logger.info(f"Found {len(vehicles)} vehicles to vectorize")

        if not vehicles:
            logger.warning("No vehicles found in database")
            return 0

        # Create collection
        vector_store.create_collection_sync(ProductType.VEHICLE, recreate=True)

        # Prepare items for vectorization
        items = []
        for vehicle in vehicles:
            description = vehicle.to_description()
            vector = embedding_service.encode_for_qdrant(description)

            items.append({
                "real_product_id": str(vehicle.vehicle_id),
                "vector": vector,
                "metadata": {
                    "brand": vehicle.brand,
                    "model": vehicle.model,
                    "year": vehicle.year,
                    "vehicle_type": vehicle.vehicle_type,
                    "disponible": vehicle.disponible,
                    "localisation": vehicle.localisation,
                    "prix_journalier": vehicle.prix_journalier,
                    "note_moyenne": vehicle.note_moyenne,
                },
            })

        # Batch insert
        total = 0
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            count = vector_store.upsert_vectors_batch(ProductType.VEHICLE, batch)
            total += count
            logger.info(f"Vectorized batch {i // batch_size + 1}: {count} vehicles")

        logger.info(f"Vehicle vectorization complete: {total} vectors created")
        return total

    finally:
        session.close()


def main():
    """Main entry point for vectorization script."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize vector database")
    parser.add_argument(
        "--type",
        choices=["vehicles", "all"],
        default="all",
        help="Type of products to vectorize",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for vectorization",
    )
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Vector Database Initialization")
    logger.info("=" * 50)

    # Initialize services
    logger.info("Loading embedding model...")
    embedding_service = EmbeddingService()

    logger.info("Connecting to Qdrant...")
    vector_store = VectorStore()

    results = {}

    if args.type in ["vehicles", "all"]:
        results["vehicles"] = vectorize_vehicles(
            embedding_service, vector_store, args.batch_size
        )

    # Print summary
    logger.info("=" * 50)
    logger.info("Vectorization Summary")
    logger.info("=" * 50)
    for product_type, count in results.items():
        logger.info(f"  {product_type}: {count} vectors")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
