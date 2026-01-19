"""Tests for Spatial Filter (Module 4 - Phase 1)."""

import pytest
from src.modules.module4_livreur_ranking.spatial_filter import SpatialFilter
from src.modules.module4_livreur_ranking.schemas import (
    LivreurCandidatSchema,
    PointSchema,
)
from src.modules.module4_livreur_ranking.constants import TypeVehicule


class TestSpatialFilter:
    """Test suite for Spatial Filter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.filter = SpatialFilter()

        # Test points (Paris area)
        self.pickup = PointSchema(
            latitude=48.8566,
            longitude=2.3522,
            adresse="Paris, France"
        )

        self.delivery = PointSchema(
            latitude=48.8606,
            longitude=2.3376,
            adresse="Arc de Triomphe, Paris"
        )

    def create_livreur(self, livreur_id: str, lat: float, lon: float):
        """Helper to create a test livreur."""
        return LivreurCandidatSchema(
            livreur_id=livreur_id,
            nom_commercial=f"Livreur {livreur_id}",
            position_actuelle=PointSchema(latitude=lat, longitude=lon),
            reputation=8.5,
            nombre_livraisons=100,
            taux_reussite=0.95,
            type_vehicule=TypeVehicule.MOTO,
            capacite_max_kg=50.0
        )

    def test_filter_by_ellipse_all_eligible(self):
        """Test filtering when all livreurs are within ellipse."""
        # Create livreurs very close to pickup/delivery
        livreurs = [
            self.create_livreur("L1", 48.8570, 2.3500),  # Very close
            self.create_livreur("L2", 48.8590, 2.3400),  # Very close
        ]

        eligible, rejected = self.filter.filter_by_ellipse(
            livreurs=livreurs,
            point_ramassage=self.pickup,
            point_livraison=self.delivery,
            tolerance_km=5.0
        )

        assert len(eligible) == 2
        assert len(rejected) == 0

    def test_filter_by_ellipse_all_rejected(self):
        """Test filtering when all livreurs are outside ellipse."""
        # Create livreurs far away
        livreurs = [
            self.create_livreur("L1", 48.9000, 2.5000),  # Far away
            self.create_livreur("L2", 48.7000, 2.2000),  # Far away
        ]

        eligible, rejected = self.filter.filter_by_ellipse(
            livreurs=livreurs,
            point_ramassage=self.pickup,
            point_livraison=self.delivery,
            tolerance_km=0.5  # Very small tolerance
        )

        assert len(eligible) == 0
        assert len(rejected) == 2

    def test_filter_by_ellipse_mixed(self):
        """Test filtering with mixed results."""
        livreurs = [
            self.create_livreur("L1", 48.8570, 2.3500),  # Close
            self.create_livreur("L2", 48.9000, 2.5000),  # Far
            self.create_livreur("L3", 48.8590, 2.3400),  # Close
        ]

        eligible, rejected = self.filter.filter_by_ellipse(
            livreurs=livreurs,
            point_ramassage=self.pickup,
            point_livraison=self.delivery,
            tolerance_km=2.0
        )

        assert len(eligible) > 0
        assert len(rejected) > 0
        assert len(eligible) + len(rejected) == 3

    def test_rejected_info_structure(self):
        """Test that rejected livreurs have proper info."""
        livreurs = [
            self.create_livreur("L1", 48.9000, 2.5000),  # Far away
        ]

        eligible, rejected = self.filter.filter_by_ellipse(
            livreurs=livreurs,
            point_ramassage=self.pickup,
            point_livraison=self.delivery,
            tolerance_km=1.0
        )

        assert len(rejected) == 1
        rejected_info = rejected[0]

        # Check structure
        assert "livreur_id" in rejected_info
        assert "nom_commercial" in rejected_info
        assert "raison" in rejected_info
        assert "distance_totale_km" in rejected_info
        assert "distance_max_km" in rejected_info

        assert rejected_info["raison"] == "hors_zone_ellipse"

    def test_calculate_distances(self):
        """Test distance calculation for a single livreur."""
        livreur = self.create_livreur("L1", 48.8570, 2.3500)

        distances = self.filter.calculate_distances(
            livreur=livreur,
            point_ramassage=self.pickup,
            point_livraison=self.delivery
        )

        # Check structure
        assert "distance_ramassage_km" in distances
        assert "distance_livraison_km" in distances
        assert "distance_totale_km" in distances

        # All distances should be positive
        assert distances["distance_ramassage_km"] >= 0
        assert distances["distance_livraison_km"] >= 0
        assert distances["distance_totale_km"] >= 0

    def test_calculate_distances_for_livreurs(self):
        """Test distance calculation for multiple livreurs."""
        livreurs = [
            self.create_livreur("L1", 48.8570, 2.3500),
            self.create_livreur("L2", 48.8590, 2.3400),
            self.create_livreur("L3", 48.8600, 2.3450),
        ]

        distances = self.filter.calculate_distances_for_livreurs(
            livreurs=livreurs,
            point_ramassage=self.pickup,
            point_livraison=self.delivery
        )

        # Check all livreurs have distances
        assert len(distances) == 3
        assert "L1" in distances
        assert "L2" in distances
        assert "L3" in distances

        # All distances should be positive
        assert all(d > 0 for d in distances.values())

    def test_tolerance_effect(self):
        """Test that larger tolerance accepts more candidates."""
        livreurs = [
            self.create_livreur("L1", 48.8700, 2.3600),
            self.create_livreur("L2", 48.8750, 2.3700),
            self.create_livreur("L3", 48.8800, 2.3800),
        ]

        # Small tolerance
        eligible_small, _ = self.filter.filter_by_ellipse(
            livreurs=livreurs,
            point_ramassage=self.pickup,
            point_livraison=self.delivery,
            tolerance_km=1.0
        )

        # Large tolerance
        eligible_large, _ = self.filter.filter_by_ellipse(
            livreurs=livreurs,
            point_ramassage=self.pickup,
            point_livraison=self.delivery,
            tolerance_km=5.0
        )

        # Larger tolerance should accept same or more candidates
        assert len(eligible_large) >= len(eligible_small)
