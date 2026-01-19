"""
TOPSIS Ranker - Phase 3 of Module 4

Implements TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution)
for multi-criteria ranking of delivery persons.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple

from .schemas import LivreurCandidatSchema
from .constants import VEHICLE_TYPE_SCORES, TypeVehicule

logger = logging.getLogger(__name__)


class TOPSISRanker:
    """
    Implements TOPSIS algorithm for multi-criteria decision making.

    Steps:
    1. Build decision matrix from livreur data
    2. Normalize matrix (vector normalization)
    3. Apply criteria weights
    4. Calculate ideal solutions (A+ and A-)
    5. Calculate Euclidean distances to ideal solutions
    6. Calculate similarity scores (Ci)
    7. Rank alternatives by Ci (descending)
    """

    def __init__(self):
        """Initialize TOPSIS ranker."""
        self.criteria_names = [
            "proximite_geographique",
            "reputation",
            "capacite",
            "type_vehicule"
        ]

        # Define criterion optimization direction
        # True = maximize (benefit), False = minimize (cost)
        self.is_benefit = {
            "proximite_geographique": False,  # Lower distance is better
            "reputation": True,               # Higher reputation is better
            "capacite": True,                 # Higher capacity is better
            "type_vehicule": True,            # Better vehicle type is better
        }

    def build_decision_matrix(
        self,
        livreurs: List[LivreurCandidatSchema],
        distances: Dict[str, float]
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Build the decision matrix from livreur data.

        Matrix structure (m x n):
        - m = number of livreurs (alternatives)
        - n = 4 criteria (proximite, reputation, capacite, type_vehicule)

        Args:
            livreurs: List of candidate delivery persons
            distances: Dict mapping livreur_id to total distance

        Returns:
            Tuple of (decision_matrix, livreur_ids)
            - decision_matrix: numpy array of shape (m, 4)
            - livreur_ids: list of livreur IDs in same order as matrix rows
        """
        m = len(livreurs)
        n = 4  # Number of criteria

        matrix = np.zeros((m, n))
        livreur_ids = []

        for i, livreur in enumerate(livreurs):
            livreur_ids.append(livreur.livreur_id)

            # Column 0: Proximité géographique (total distance in km)
            matrix[i, 0] = distances[livreur.livreur_id]

            # Column 1: Réputation (0-10)
            matrix[i, 1] = livreur.reputation

            # Column 2: Capacité (kg)
            matrix[i, 2] = livreur.capacite_max_kg

            # Column 3: Type véhicule (score 0-1)
            matrix[i, 3] = VEHICLE_TYPE_SCORES[livreur.type_vehicule]

        logger.debug(f"Decision matrix shape: {matrix.shape}")
        logger.debug(f"Decision matrix:\n{matrix}")

        return matrix, livreur_ids

    def normalize_matrix(self, matrix: np.ndarray) -> np.ndarray:
        """
        Normalize the decision matrix using vector normalization.

        Formula: v_ij = x_ij / sqrt(sum(x_ij^2)) for each column j

        Args:
            matrix: Decision matrix (m x n)

        Returns:
            Normalized matrix (m x n)
        """
        # Calculate column-wise norms (sqrt of sum of squares)
        column_norms = np.sqrt(np.sum(matrix ** 2, axis=0))

        # Avoid division by zero
        column_norms = np.where(column_norms == 0, 1, column_norms)

        # Normalize each column
        normalized = matrix / column_norms

        logger.debug(f"Normalized matrix:\n{normalized}")

        return normalized

    def apply_weights(
        self,
        normalized_matrix: np.ndarray,
        weights: Dict[str, float]
    ) -> np.ndarray:
        """
        Apply criteria weights to normalized matrix.

        Formula: r_ij = w_j * v_ij

        Args:
            normalized_matrix: Normalized decision matrix (m x n)
            weights: Dict mapping criterion name to weight

        Returns:
            Weighted normalized matrix (m x n)
        """
        # Create weight vector in correct order
        weight_vector = np.array([
            weights["proximite_geographique"],
            weights["reputation"],
            weights["capacite"],
            weights["type_vehicule"]
        ])

        # Multiply each column by its weight
        weighted = normalized_matrix * weight_vector

        logger.debug(f"Weight vector: {weight_vector}")
        logger.debug(f"Weighted matrix:\n{weighted}")

        return weighted

    def calculate_ideal_solutions(
        self,
        weighted_matrix: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate ideal positive (A+) and ideal negative (A-) solutions.

        For benefit criteria: A+ = max, A- = min
        For cost criteria: A+ = min, A- = max

        Args:
            weighted_matrix: Weighted normalized matrix (m x n)

        Returns:
            Tuple of (A_positive, A_negative)
            Both are arrays of length n (one value per criterion)
        """
        n_criteria = weighted_matrix.shape[1]
        A_positive = np.zeros(n_criteria)
        A_negative = np.zeros(n_criteria)

        for j, criterion in enumerate(self.criteria_names):
            column = weighted_matrix[:, j]

            if self.is_benefit[criterion]:
                # Benefit criterion: maximize
                A_positive[j] = np.max(column)
                A_negative[j] = np.min(column)
            else:
                # Cost criterion: minimize
                A_positive[j] = np.min(column)
                A_negative[j] = np.max(column)

        logger.debug(f"A+ (ideal positive): {A_positive}")
        logger.debug(f"A- (ideal negative): {A_negative}")

        return A_positive, A_negative

    def calculate_distances(
        self,
        weighted_matrix: np.ndarray,
        A_positive: np.ndarray,
        A_negative: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate Euclidean distances to ideal solutions.

        Formula:
        - d+ = sqrt(sum((r_ij - A+_j)^2))
        - d- = sqrt(sum((r_ij - A-_j)^2))

        Args:
            weighted_matrix: Weighted normalized matrix (m x n)
            A_positive: Ideal positive solution (length n)
            A_negative: Ideal negative solution (length n)

        Returns:
            Tuple of (distances_positive, distances_negative)
            Both are arrays of length m (one distance per alternative)
        """
        # Calculate squared differences
        diff_positive = weighted_matrix - A_positive
        diff_negative = weighted_matrix - A_negative

        # Calculate Euclidean distances (sqrt of sum of squared differences)
        distances_positive = np.sqrt(np.sum(diff_positive ** 2, axis=1))
        distances_negative = np.sqrt(np.sum(diff_negative ** 2, axis=1))

        logger.debug(f"Distances to A+: {distances_positive}")
        logger.debug(f"Distances to A-: {distances_negative}")

        return distances_positive, distances_negative

    def calculate_similarity_scores(
        self,
        distances_positive: np.ndarray,
        distances_negative: np.ndarray
    ) -> np.ndarray:
        """
        Calculate similarity scores (relative closeness to ideal solution).

        Formula: C_i = d- / (d+ + d-)

        Values range from 0 to 1:
        - C_i = 1: Alternative is at ideal positive solution
        - C_i = 0: Alternative is at ideal negative solution

        Args:
            distances_positive: Distances to A+ (length m)
            distances_negative: Distances to A- (length m)

        Returns:
            Similarity scores (length m)
        """
        # Avoid division by zero
        total_distance = distances_positive + distances_negative
        total_distance = np.where(total_distance == 0, 1e-10, total_distance)

        # Calculate similarity scores
        scores = distances_negative / total_distance

        logger.debug(f"Similarity scores (C_i): {scores}")

        return scores

    def rank(
        self,
        livreurs: List[LivreurCandidatSchema],
        distances: Dict[str, float],
        weights: Dict[str, float]
    ) -> List[Dict]:
        """
        Complete TOPSIS ranking process.

        Args:
            livreurs: List of candidate delivery persons
            distances: Dict mapping livreur_id to total distance
            weights: Dict mapping criterion name to weight (from AHP)

        Returns:
            List of dicts with ranking results, sorted by score (descending)
            Each dict contains:
            - livreur_id: str
            - score_final: float (0-1)
            - distance_A_positive: float
            - distance_A_negative: float
            - criteres_valeurs: dict (original criterion values)
            - criteres_normalises: dict (normalized values)
            - criteres_ponderes: dict (weighted values)
        """
        logger.info(f"Starting TOPSIS ranking for {len(livreurs)} livreurs")

        # Step 1: Build decision matrix
        decision_matrix, livreur_ids = self.build_decision_matrix(livreurs, distances)

        # Step 2: Normalize matrix
        normalized_matrix = self.normalize_matrix(decision_matrix)

        # Step 3: Apply weights
        weighted_matrix = self.apply_weights(normalized_matrix, weights)

        # Step 4: Calculate ideal solutions
        A_positive, A_negative = self.calculate_ideal_solutions(weighted_matrix)

        # Step 5: Calculate distances
        distances_positive, distances_negative = self.calculate_distances(
            weighted_matrix, A_positive, A_negative
        )

        # Step 6: Calculate similarity scores
        scores = self.calculate_similarity_scores(distances_positive, distances_negative)

        # Step 7: Build results with detailed information
        results = []
        for i, livreur_id in enumerate(livreur_ids):
            result = {
                "livreur_id": livreur_id,
                "score_final": float(scores[i]),
                "distance_A_positive": float(distances_positive[i]),
                "distance_A_negative": float(distances_negative[i]),
                "criteres_valeurs": {
                    "proximite_geographique": float(decision_matrix[i, 0]),
                    "reputation": float(decision_matrix[i, 1]),
                    "capacite": float(decision_matrix[i, 2]),
                    "type_vehicule": float(decision_matrix[i, 3]),
                },
                "criteres_normalises": {
                    "proximite_geographique": float(normalized_matrix[i, 0]),
                    "reputation": float(normalized_matrix[i, 1]),
                    "capacite": float(normalized_matrix[i, 2]),
                    "type_vehicule": float(normalized_matrix[i, 3]),
                },
                "criteres_ponderes": {
                    "proximite_geographique": float(weighted_matrix[i, 0]),
                    "reputation": float(weighted_matrix[i, 1]),
                    "capacite": float(weighted_matrix[i, 2]),
                    "type_vehicule": float(weighted_matrix[i, 3]),
                },
            }
            results.append(result)

        # Step 8: Sort by score (descending)
        results.sort(key=lambda x: x["score_final"], reverse=True)

        logger.info(
            f"TOPSIS ranking complete. Top score: {results[0]['score_final']:.4f}, "
            f"Lowest score: {results[-1]['score_final']:.4f}"
        )

        return results
