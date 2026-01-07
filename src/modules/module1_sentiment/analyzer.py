"""
Sentiment Analysis Module (Module 1).
Integration layer for distil-camembert fine-tuned model.

This module provides an interface for sentiment analysis that:
1. Accepts product_id, client_id, and comment text
2. Analyzes sentiment using the fine-tuned distil-camembert model
3. Returns structured sentiment results for the recommendation engine
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

import torch
import torch.nn.functional as F
from transformers import (
    CamembertForSequenceClassification,
    CamembertTokenizer,
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

from .schemas import SentimentInput, SentimentResult

logger = logging.getLogger(__name__)

# Chemin par défaut vers le modèle fine-tuné (relatif au module)
DEFAULT_MODEL_PATH = Path(__file__).parent / "models"


class SentimentAnalyzer:
    """
    Sentiment analyzer using fine-tuned distil-camembert model.

    Le modèle est chargé depuis src/modules/module1_sentiment/models/
    qui contient:
    - config.json
    - model.safetensors
    - sentencepiece.bpe.model
    - special_tokens_map.json
    - tokenizer.json
    - tokenizer_config.json

    Attributes:
        model_path: Path to the fine-tuned model
        tokenizer: CamembertTokenizer for French text
        model: Fine-tuned distil-camembert classification model
    """

    # Labels du modèle (adapter selon votre fine-tuning)
    LABEL_MAPPING = {
        0: "negative",
        1: "neutral",
        2: "positive",
    }

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the sentiment analyzer.

        Args:
            model_path: Path to the fine-tuned model.
                       If None, uses the local models/ directory
        """
        if model_path:
            self.model_path = Path(model_path)
        else:
            self.model_path = DEFAULT_MODEL_PATH

        self._model = None
        self._tokenizer = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._num_labels = None

        logger.info(f"SentimentAnalyzer initialized (device: {self._device})")
        logger.info(f"Model path: {self.model_path}")

    def _load_model(self) -> None:
        """Lazy load the fine-tuned distil-camembert model and tokenizer."""
        if self._model is not None:
            return

        model_path = self.model_path

        if model_path.exists() and (model_path / "config.json").exists():
            logger.info(f"Loading distil-camembert from: {model_path}")

            try:
                # Charger le tokenizer CamemBERT
                self._tokenizer = CamembertTokenizer.from_pretrained(
                    str(model_path),
                    local_files_only=True,
                )

                # Charger le modèle fine-tuné (safetensors)
                self._model = CamembertForSequenceClassification.from_pretrained(
                    str(model_path),
                    local_files_only=True,
                )

                # Récupérer le nombre de labels depuis la config
                self._num_labels = self._model.config.num_labels
                logger.info(f"Model loaded with {self._num_labels} labels")

                # Mettre sur le bon device
                self._model.to(self._device)
                self._model.eval()

                logger.info("Distil-CamemBERT sentiment model loaded successfully")

            except Exception as e:
                logger.error(f"Error loading CamemBERT model: {e}")
                self._load_fallback_model()
        else:
            logger.warning(f"Model not found at {model_path}")
            self._load_fallback_model()

    def _load_fallback_model(self) -> None:
        """Load fallback model if local model is not available."""
        logger.warning("Loading fallback multilingual sentiment model")
        fallback_model = "nlptown/bert-base-multilingual-uncased-sentiment"

        self._tokenizer = AutoTokenizer.from_pretrained(fallback_model)
        self._model = AutoModelForSequenceClassification.from_pretrained(fallback_model)
        self._num_labels = 5  # nlptown uses 5 stars
        self._model.to(self._device)
        self._model.eval()

        logger.info("Fallback model loaded")

    def _predict(self, text: str) -> Dict[str, Any]:
        """
        Make prediction on a single text.

        Args:
            text: Input text to analyze

        Returns:
            Dict with logits, probabilities, predicted class and scores
        """
        self._load_model()

        # Tokenize
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )

        # Move to device
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        # Inference
        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits
            probabilities = F.softmax(logits, dim=-1)
            predicted_class = torch.argmax(probabilities, dim=-1).item()

        # Get scores for each class
        probs = probabilities[0].cpu().tolist()

        return {
            "logits": logits[0].cpu().tolist(),
            "probabilities": probs,
            "predicted_class": predicted_class,
            "confidence": max(probs),
        }

    def analyze(self, input_data: SentimentInput) -> SentimentResult:
        """
        Analyze sentiment of a comment.

        Args:
            input_data: SentimentInput containing product_id, client_id, and comment

        Returns:
            SentimentResult with sentiment score and label
        """
        try:
            # Get prediction from model
            prediction = self._predict(input_data.commentaire)

            # Convert to sentiment score and label
            sentiment_score, sentiment_label, confidence = self._compute_sentiment_score(
                prediction["probabilities"],
                prediction["predicted_class"],
            )

            return SentimentResult(
                client_id=input_data.client_id,
                product_id=input_data.product_id,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                confidence=confidence,
                product_type=input_data.product_type,
            )

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            # Return neutral sentiment on error
            return SentimentResult(
                client_id=input_data.client_id,
                product_id=input_data.product_id,
                sentiment_score=0.0,
                sentiment_label="neutral",
                confidence=0.0,
                product_type=input_data.product_type,
            )

    def _compute_sentiment_score(
        self,
        probabilities: list,
        predicted_class: int,
    ) -> tuple[float, str, float]:
        """
        Compute sentiment score from model probabilities.

        Adapte le calcul selon le nombre de classes du modèle.

        Args:
            probabilities: List of probabilities for each class
            predicted_class: Index of predicted class

        Returns:
            Tuple of (sentiment_score, sentiment_label, confidence)
        """
        num_classes = len(probabilities)
        confidence = max(probabilities)

        if num_classes == 2:
            # Binary: [negative, positive]
            neg_prob = probabilities[0]
            pos_prob = probabilities[1]
            sentiment_score = pos_prob - neg_prob  # Range: [-1, 1]

        elif num_classes == 3:
            # 3 classes: [negative, neutral, positive]
            neg_prob = probabilities[0]
            neu_prob = probabilities[1]
            pos_prob = probabilities[2]
            # Score pondéré: positif contribue positivement, négatif négativement
            sentiment_score = pos_prob - neg_prob  # Range: [-1, 1]

        elif num_classes == 5:
            # 5 étoiles: [1, 2, 3, 4, 5]
            weighted_sum = sum((i + 1) * p for i, p in enumerate(probabilities))
            sentiment_score = (weighted_sum - 3) / 2  # Normalize to [-1, 1]

        else:
            # Format inconnu - utiliser la classe prédite
            # Normaliser la classe à un score [-1, 1]
            sentiment_score = (predicted_class / (num_classes - 1)) * 2 - 1

        # Déterminer le label basé sur le score
        if sentiment_score > 0.2:
            sentiment_label = "positive"
        elif sentiment_score < -0.2:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        # Arrondir le score
        sentiment_score = round(sentiment_score, 4)

        return sentiment_score, sentiment_label, confidence

    def analyze_batch(
        self, inputs: list[SentimentInput]
    ) -> list[SentimentResult]:
        """
        Analyze sentiment for multiple comments.

        Args:
            inputs: List of SentimentInput objects

        Returns:
            List of SentimentResult objects
        """
        return [self.analyze(input_data) for input_data in inputs]

    def health_check(self) -> bool:
        """Check if the model is loaded and functional."""
        try:
            self._load_model()
            test_input = SentimentInput(
                product_id="test",
                client_id="test",
                commentaire="Test message",
            )
            result = self.analyze(test_input)
            return result.sentiment_score is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Singleton instance
_analyzer_instance: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or create singleton sentiment analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = SentimentAnalyzer()
    return _analyzer_instance
