"""Tests for AHP Calculator (Module 4 - Phase 2)."""

import pytest
import numpy as np

from src.modules.module4_livreur_ranking.ahp_calculator import AHPCalculator
from src.modules.module4_livreur_ranking.constants import (
    TypeLivraison,
    AHP_CONSISTENCY_THRESHOLD,
)


class TestAHPCalculator:
    """Test suite for AHP Calculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = AHPCalculator()

    def test_build_comparison_matrix_standard(self):
        """Test building comparison matrix for standard delivery."""
        matrix = self.calculator.build_comparison_matrix(TypeLivraison.STANDARD)

        # Check matrix shape
        assert matrix.shape == (4, 4)

        # Check diagonal is all 1s
        assert np.allclose(np.diag(matrix), np.ones(4))

        # Check reciprocal property: A[i,j] = 1 / A[j,i]
        for i in range(4):
            for j in range(4):
                assert np.isclose(matrix[i, j], 1.0 / matrix[j, i])

        # Check symmetry property
        assert np.allclose(matrix @ matrix.T, matrix.T @ matrix)

    def test_build_comparison_matrix_express(self):
        """Test building comparison matrix for express delivery."""
        matrix = self.calculator.build_comparison_matrix(TypeLivraison.EXPRESS)

        assert matrix.shape == (4, 4)
        assert np.allclose(np.diag(matrix), np.ones(4))

    def test_build_comparison_matrix_sameday(self):
        """Test building comparison matrix for sameday delivery."""
        matrix = self.calculator.build_comparison_matrix(TypeLivraison.SAMEDAY)

        assert matrix.shape == (4, 4)
        assert np.allclose(np.diag(matrix), np.ones(4))

    def test_calculate_weights(self):
        """Test weight calculation using column averaging."""
        # Simple test matrix (all equal importance)
        matrix = np.ones((4, 4))
        weights = self.calculator.calculate_weights(matrix)

        # All weights should be equal (0.25 each)
        assert np.allclose(weights, np.array([0.25, 0.25, 0.25, 0.25]))

        # Weights should sum to 1
        assert np.isclose(np.sum(weights), 1.0)

    def test_calculate_weights_sum_to_one(self):
        """Test that weights always sum to 1."""
        for delivery_type in TypeLivraison:
            matrix = self.calculator.build_comparison_matrix(delivery_type)
            weights = self.calculator.calculate_weights(matrix)
            assert np.isclose(np.sum(weights), 1.0)

    def test_check_consistency(self):
        """Test consistency checking."""
        # Perfectly consistent matrix (all equal)
        matrix = np.ones((4, 4))
        weights = self.calculator.calculate_weights(matrix)
        cr, is_consistent = self.calculator.check_consistency(matrix, weights)

        # Should be perfectly consistent (CR ≈ 0)
        assert cr < AHP_CONSISTENCY_THRESHOLD
        assert is_consistent is True

    def test_calculate_criteria_weights_standard(self):
        """Test complete AHP process for standard delivery."""
        weights_dict, consistency_info = self.calculator.calculate_criteria_weights(
            TypeLivraison.STANDARD
        )

        # Check all criteria are present
        assert "proximite_geographique" in weights_dict
        assert "reputation" in weights_dict
        assert "capacite" in weights_dict
        assert "type_vehicule" in weights_dict

        # Check weights sum to 1
        total_weight = sum(weights_dict.values())
        assert np.isclose(total_weight, 1.0)

        # Check all weights are positive
        assert all(w > 0 for w in weights_dict.values())

        # Check consistency info
        assert "CR" in consistency_info
        assert "est_coherent" in consistency_info
        assert "seuil" in consistency_info
        assert consistency_info["seuil"] == AHP_CONSISTENCY_THRESHOLD

    def test_calculate_criteria_weights_express(self):
        """Test complete AHP process for express delivery."""
        weights_dict, consistency_info = self.calculator.calculate_criteria_weights(
            TypeLivraison.EXPRESS
        )

        # Express should prioritize proximity more than standard
        assert weights_dict["proximite_geographique"] > 0.5

        # Check weights sum to 1
        total_weight = sum(weights_dict.values())
        assert np.isclose(total_weight, 1.0)

    def test_calculate_criteria_weights_sameday(self):
        """Test complete AHP process for sameday delivery."""
        weights_dict, consistency_info = self.calculator.calculate_criteria_weights(
            TypeLivraison.SAMEDAY
        )

        # Sameday should prioritize proximity most
        assert weights_dict["proximite_geographique"] > 0.6

        # Check weights sum to 1
        total_weight = sum(weights_dict.values())
        assert np.isclose(total_weight, 1.0)

    def test_proximity_weight_increases_by_urgency(self):
        """Test that proximity weight increases with delivery urgency."""
        weights_standard, _ = self.calculator.calculate_criteria_weights(
            TypeLivraison.STANDARD
        )
        weights_express, _ = self.calculator.calculate_criteria_weights(
            TypeLivraison.EXPRESS
        )
        weights_sameday, _ = self.calculator.calculate_criteria_weights(
            TypeLivraison.SAMEDAY
        )

        # Proximity should increase: standard < express < sameday
        assert (
            weights_standard["proximite_geographique"]
            < weights_express["proximite_geographique"]
            < weights_sameday["proximite_geographique"]
        )
