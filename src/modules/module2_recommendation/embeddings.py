"""
Embedding Service using sentence-transformers.
Model: paraphrase-multilingual-mpnet-base-v2
"""

import logging
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from src.config import settings
from src.utils.context import get_correlation_id

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings.

    Uses paraphrase-multilingual-mpnet-base-v2 model as specified
    for multilingual support (French).
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            model_name: Model name to use. Defaults to configured model.
        """
        self.model_name = model_name or settings.embedding_model_name
        self._model = None
        self.dimension = settings.embedding_dimension

        # Définir le chemin du modèle local
        self.model_path = Path(__file__).parent / "models"

        # Déterminer le device (CPU ou GPU)
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _load_model(self) -> None:
        """Lazy load the paraphrase-multilingual-mpnet model."""
        if self._model is not None:
            return

        model_path = self.model_path

        if model_path.exists() and (model_path / "config.json").exists():
            logger.info(f"Loading paraphrase-multilingual-mpnet from: {model_path}")

            try:
                # Charger le modèle depuis le dossier local
                self._model = SentenceTransformer(
                    str(model_path),
                    device=str(self._device)
                )

                # Vérifier la dimension
                test_embedding = self._model.encode("test")
                self.dimension = len(test_embedding)

                logger.info(f"Model loaded successfully (dimension: {self.dimension})")
                logger.info("Paraphrase-multilingual-mpnet model loaded successfully")

            except Exception as e:
                logger.error(f"Error loading local model: {e}")
                self._load_fallback_model()
        else:
            logger.warning(f"Model not found at {model_path}")
            self._load_fallback_model()

    def _load_fallback_model(self) -> None:
        """Load fallback model from Hugging Face Hub."""
        try:
            logger.info("Loading fallback model from Hugging Face Hub...")
            self._model = SentenceTransformer(
                'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
                device=str(self._device)
            )

            # Vérifier la dimension
            test_embedding = self._model.encode("test")
            self.dimension = len(test_embedding)

            logger.info(f"Fallback model loaded successfully (dimension: {self.dimension})")
        except Exception as e:
            logger.error(f"Failed to load fallback model: {e}")
            raise RuntimeError("Could not load embedding model") from e

    @property
    def model(self) -> SentenceTransformer:
        """Get the loaded model."""
        self._load_model()
        return self._model

    def encode(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text to encode

        Returns:
            Numpy array of shape (dimension,)
        """
        if self._model is None:
            self._load_model()

        try:
            embedding = self._model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,
                device=str(self._device)
            )
            return embedding
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            raise

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to encode

        Returns:
            Numpy array of shape (n_texts, dimension)
        """
        start_time = time.time()
        batch_size = len(texts)
        avg_text_length = sum(len(t) for t in texts) / batch_size if batch_size > 0 else 0

        if self._model is None:
            self._load_model()

        try:
            embeddings = self._model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 10,
                batch_size=32,
                device=str(self._device)
            )

            duration_ms = (time.time() - start_time) * 1000

            # Log embedding generation metrics
            logger.info(
                f"Embeddings generated for {batch_size} texts",
                extra={
                    "event": "embedding_generation",
                    "metric_type": "ml_inference",
                    "model": "paraphrase-multilingual-mpnet-base-v2",
                    "operation": "embedding_generation",
                    "batch_size": batch_size,
                    "avg_text_length": round(avg_text_length, 0),
                    "embedding_dim": embeddings.shape[1] if embeddings.ndim > 1 else len(embeddings),
                    "duration_ms": round(duration_ms, 2),
                    "texts_per_second": round(batch_size / (duration_ms / 1000), 2),
                    "device": str(self._device),
                    "correlation_id": get_correlation_id(),
                }
            )

            return embeddings
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Error encoding batch: {e}",
                extra={
                    "event": "embedding_generation_error",
                    "metric_type": "ml_inference",
                    "model": "paraphrase-multilingual-mpnet-base-v2",
                    "operation": "embedding_generation",
                    "error": str(e),
                    "batch_size": batch_size,
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": get_correlation_id(),
                }
            )
            raise

    def encode_for_qdrant(self, text: str) -> List[float]:
        """
        Generate embedding in format suitable for Qdrant.

        Args:
            text: Text to encode

        Returns:
            List of floats (embedding vector)
        """
        embedding = self.encode(text)
        return embedding.tolist()

    def encode_batch_for_qdrant(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in Qdrant format.

        Args:
            texts: List of texts to encode

        Returns:
            List of embedding vectors
        """
        embeddings = self.encode_batch(texts)
        return [e.tolist() for e in embeddings]

    def compute_similarity(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Since embeddings are normalized, dot product equals cosine similarity.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between 0 and 1
        """
        # Embeddings are normalized, so dot product = cosine similarity
        similarity = np.dot(embedding1, embedding2)
        return float(similarity)

    def health_check(self) -> bool:
        """Check if embedding service is functional."""
        try:
            if self._model is None:
                self._load_model()
            test_embedding = self.encode("test")
            return len(test_embedding) == self.dimension
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return False


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create singleton embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service