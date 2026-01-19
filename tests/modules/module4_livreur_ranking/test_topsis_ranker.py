"""Tests for TOPSIS Ranker (Module 4 - Phase 3)."""

import pytest
import numpy as np

from src.modules.module4_livreur_ranking.topsis_ranker import TOPSISRanker
from src.modules.module4_livreur_ranking.schemas import (
    LivreurCandidatSchema,
    PointSchema,
)
from src.modules.module4_livreur_ranking.constants import TypeVehicule


class TestTOPSISRanker:
    """Test suite for TOPSIS Ranker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.ranker = TOPSISRanker()

    def create_livreur(
        self,
        livreur_id: str,
        reputation: float,
        capacite: float,
        vehicle_type: TypeVehicule
    ):
        """Helper to create a test livreur."""
        return LivreurCandidatSchema(
            livreur_id=livreur_id,
            nom_commercial=f"Livreur {livreur_id}",
            position_actuelle=PointSchema(latitude=48.8566, longitude=2.3522),
            reputation=reputation,
            nombre_livraisons=100,
            taux_reussite=0.95,
            type_vehicule=vehicle_type,
            capacite_max_kg=capacite
        )

    def test_build_decision_matrix(self):
        """Test building decision matrix from livreur data."""
        livreurs = [
            self.create_livreur("L1", 8.0, 50.0, TypeVehicule.MOTO),
            self.create_livreur("L2", 9.0, 100.0, TypeVehicule.VOITURE),
            self.create_livreur("L3", 7.5, 30.0, TypeVehicule.VELO),
        ]

        distances = {"L1": 5.0, "L2": 3.0, "L3": 8.0}

        matrix, livreur_ids = self.ranker.build_decision_matrix(livreurs, distances)

        # Check shape
        assert matrix.shape == (3, 4)  # 3 livreurs, 4 criteria

        # Check livreur IDs
        assert livreur_ids == ["L1", "L2", "L3"]

        # Check distance column (column 0)
        assert matrix[0, 0] == 5.0  # L1
        assert matrix[1, 0] == 3.0  # L2
        assert matrix[2, 0] == 8.0  # L3

        # Check reputation column (column 1)
        assert matrix[0, 1] == 8.0  # L1
        assert matrix[1, 1] == 9.0  # L2
        assert matrix[2, 1] == 7.5  # L3

        # Check capacity column (column 2)
        assert matrix[0, 2] == 50.0  # L1
        assert matrix[1, 2] == 100.0  # L2
        assert matrix[2, 2] == 30.0  # L3

    def test_normalize_matrix(self):
        """Test vector normalization."""
        # Simple test matrix
        matrix = np.array([
            [3.0, 4.0],
            [4.0, 3.0],
        ])

        normalized = self.ranker.normalize_matrix(matrix)

        # Check that column norms are 1
        for j in range(normalized.shape[1]):
            column_norm = np.sqrt(np.sum(normalized[:, j] ** 2))
            assert np.isclose(column_norm, 1.0)

    def test_apply_weights(self):
        """Test applying criteria weights."""
        normalized_matrix = np.array([
            [0.6, 0.8],
            [0.8, 0.6],
        ])

        weights = {
            "proximite_geographique": 0.7,
            "reputation": 0.15,
            "capacite": 0.10,
            "type_vehicule": 0.05,
        }

        # Expand to 4 columns for test
        normalized_matrix = np.array([
            [0.6, 0.8, 0.5, 0.3],
            [0.8, 0.6, 0.7, 0.4],
        ])

        weighted = self.ranker.apply_weights(normalized_matrix, weights)

        # Check shape preserved
        assert weighted.shape == normalized_matrix.shape

        # Check that weights were applied correctly
        assert np.isclose(weighted[0, 0], 0.6 * 0.7)
        assert np.isclose(weighted[0, 1], 0.8 * 0.15)

    def test_calculate_ideal_solutions(self):
        """Test calculation of ideal positive and negative solutions."""
        # Test matrix
        weighted_matrix = np.array([
            [0.5, 0.8, 0.6, 0.7],
            [0.3, 0.9, 0.7, 0.8],
            [0.7, 0.7, 0.5, 0.6],
        ])

        A_positive, A_negative = self.ranker.calculate_ideal_solutions(weighted_matrix)

        # Check length
        assert len(A_positive) == 4
        assert len(A_negative) == 4

        # For proximity (cost criterion): A+ = min, A- = max
        assert A_positive[0] == np.min(weighted_matrix[:, 0])
        assert A_negative[0] == np.max(weighted_matrix[:, 0])

        # For reputation (benefit criterion): A+ = max, A- = min
        assert A_positive[1] == np.max(weighted_matrix[:, 1])
        assert A_negative[1] == np.min(weighted_matrix[:, 1])

    def test_calculate_distances(self):
        """Test Euclidean distance calculation."""
        weighted_matrix = np.array([
            [0.5, 0.8],
            [0.3, 0.9],
        ])

        A_positive = np.array([0.3, 0.9])
        A_negative = np.array([0.5, 0.8])

        d_positive, d_negative = self.ranker.calculate_distances(
            weighted_matrix, A_positive, A_negative
        )

        # Check lengths
        assert len(d_positive) == 2
        assert len(d_negative) == 2

        # All distances should be non-negative
        assert all(d >= 0 for d in d_positive)
        assert all(d >= 0 for d in d_negative)

        # First alternative is exactly at A-
        assert np.isclose(d_negative[0], 0.0)

        # Second alternative is exactly at A+
        assert np.isclose(d_positive[1], 0.0)

    def test_calculate_similarity_scores(self):
        """Test similarity score calculation."""
        # Alternative at A+ should have score 1
        d_positive = np.array([0.0, 1.0])
        d_negative = np.array([1.0, 0.0])

        scores = self.ranker.calculate_similarity_scores(d_positive, d_negative)

        # Check range [0, 1]
        assert all(0 <= s <= 1 for s in scores)

        # First alternative at A+ should have score 1
        assert np.isclose(scores[0], 1.0)

        # Second alternative at A- should have score 0
        assert np.isclose(scores[1], 0.0)

    def test_rank_simple_case(self):
        """Test complete ranking with simple case."""
        # Create livreurs with clear best choice
        livreurs = [
            # L1: Close, good reputation, good capacity, good vehicle
            self.create_livreur("L1", 9.0, 100.0, TypeVehicule.VOITURE),
            # L2: Far, poor reputation, low capacity, poor vehicle
            self.create_livreur("L2", 5.0, 20.0, TypeVehicule.VELO),
        ]

        distances = {"L1": 2.0, "L2": 10.0}

        weights = {
            "proximite_geographique": 0.5,
            "reputation": 0.3,
            "capacite": 0.15,
            "type_vehicule": 0.05,
        }

        results = self.ranker.rank(livreurs, distances, weights)

        # Check results structure
        assert len(results) == 2
        assert results[0]["livreur_id"] == "L1"  # L1 should be first
        assert results[1]["livreur_id"] == "L2"  # L2 should be second

        # Check scores are in descending order
        assert results[0]["score_final"] > results[1]["score_final"]

        # Check all required fields
        for result in results:
            assert "livreur_id" in result
            assert "score_final" in result
            assert "distance_A_positive" in result
            assert "distance_A_negative" in result
            assert "criteres_valeurs" in result
            assert "criteres_normalises" in result
            assert "criteres_ponderes" in result

    def test_rank_all_equal(self):
        """Test ranking when all alternatives are equal."""
        livreurs = [
            self.create_livreur("L1", 8.0, 50.0, TypeVehicule.MOTO),
            self.create_livreur("L2", 8.0, 50.0, TypeVehicule.MOTO),
            self.create_livreur("L3", 8.0, 50.0, TypeVehicule.MOTO),
        ]

        distances = {"L1": 5.0, "L2": 5.0, "L3": 5.0}

        weights = {
            "proximite_geographique": 0.5,
            "reputation": 0.3,
            "capacite": 0.15,
            "type_vehicule": 0.05,
        }

        results = self.ranker.rank(livreurs, distances, weights)

        # All scores should be equal (or very close)
        scores = [r["score_final"] for r in results]
        assert all(np.isclose(scores[0], s) for s in scores)

    def test_rank_scores_in_range(self):
        """Test that all scores are in valid range [0, 1]."""
        livreurs = [
            self.create_livreur("L1", 9.0, 100.0, TypeVehicule.CAMION),
            self.create_livreur("L2", 7.0, 50.0, TypeVehicule.VOITURE),
            self.create_livreur("L3", 5.0, 20.0, TypeVehicule.VELO),
        ]

        distances = {"L1": 2.0, "L2": 5.0, "L3": 10.0}

        weights = {
            "proximite_geographique": 0.4,
            "reputation": 0.3,
            "capacite": 0.2,
            "type_vehicule": 0.1,
        }

        results = self.ranker.rank(livreurs, distances, weights)

        # All scores should be in [0, 1]
        for result in results:
            assert 0 <= result["score_final"] <= 1
