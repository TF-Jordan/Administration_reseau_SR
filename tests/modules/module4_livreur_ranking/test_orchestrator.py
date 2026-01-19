"""Integration tests for Orchestrator (Module 4)."""

import pytest
from datetime import datetime

from src.modules.module4_livreur_ranking.orchestrator import Orchestrator
from src.modules.module4_livreur_ranking.schemas import (
    RankingRequestSchema,
    AnnonceSchema,
    LivreurCandidatSchema,
    PointSchema,
)
from src.modules.module4_livreur_ranking.constants import (
    TypeLivraison,
    TypeVehicule,
)


class TestOrchestrator:
    """Integration test suite for Orchestrator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.orchestrator = Orchestrator()

        # Test announcement
        self.annonce = AnnonceSchema(
            annonce_id="ANN-001",
            point_ramassage=PointSchema(
                latitude=48.8566,
                longitude=2.3522,
                adresse="Paris, France"
            ),
            point_livraison=PointSchema(
                latitude=48.8606,
                longitude=2.3376,
                adresse="Arc de Triomphe, Paris"
            ),
            type_livraison=TypeLivraison.STANDARD,
            description="Test delivery"
        )

    def create_livreur(
        self,
        livreur_id: str,
        lat: float,
        lon: float,
        reputation: float = 8.0,
        capacite: float = 50.0,
        vehicle: TypeVehicule = TypeVehicule.MOTO
    ):
        """Helper to create a test livreur."""
        return LivreurCandidatSchema(
            livreur_id=livreur_id,
            nom_commercial=f"Livreur {livreur_id}",
            position_actuelle=PointSchema(latitude=lat, longitude=lon),
            reputation=reputation,
            nombre_livraisons=100,
            taux_reussite=0.95,
            type_vehicule=vehicle,
            capacite_max_kg=capacite
        )

    def test_rank_livreurs_success(self):
        """Test successful complete ranking workflow."""
        livreurs = [
            self.create_livreur("L1", 48.8570, 2.3500, 9.0, 100.0, TypeVehicule.VOITURE),
            self.create_livreur("L2", 48.8590, 2.3400, 8.0, 50.0, TypeVehicule.MOTO),
            self.create_livreur("L3", 48.8600, 2.3450, 7.0, 30.0, TypeVehicule.VELO),
        ]

        request = RankingRequestSchema(
            annonce=self.annonce,
            livreurs_candidats=livreurs
        )

        response = self.orchestrator.rank_livreurs(request, include_details=False)

        # Check response structure
        assert response.status == "success"
        assert response.annonce_id == "ANN-001"
        assert isinstance(response.timestamp, datetime)
        assert len(response.livreurs_classes) > 0

        # Check metadata
        assert response.metadata is not None
        assert response.metadata.type_livraison == TypeLivraison.STANDARD
        assert response.metadata.statistiques_filtrage is not None
        assert response.metadata.poids_ahp is not None
        assert response.metadata.duree_traitement_ms >= 0

        # Check ranking is sorted by score (descending)
        scores = [lc.score_final for lc in response.livreurs_classes]
        assert scores == sorted(scores, reverse=True)

        # Check rank numbers are sequential
        for i, lc in enumerate(response.livreurs_classes, start=1):
            assert lc.rang == i

    def test_rank_livreurs_with_details(self):
        """Test ranking with detailed TOPSIS calculations."""
        livreurs = [
            self.create_livreur("L1", 48.8570, 2.3500),
            self.create_livreur("L2", 48.8590, 2.3400),
        ]

        request = RankingRequestSchema(
            annonce=self.annonce,
            livreurs_candidats=livreurs
        )

        response = self.orchestrator.rank_livreurs(request, include_details=True)

        # Check that details are included
        for lc in response.livreurs_classes:
            assert lc.details_scores is not None
            assert lc.distances_topsis is not None

            # Check detail structure
            assert lc.details_scores.criteres_bruts is not None
            assert lc.details_scores.criteres_normalises is not None
            assert lc.details_scores.criteres_ponderes is not None

            assert lc.distances_topsis.distance_ideal_positif >= 0
            assert lc.distances_topsis.distance_ideal_negatif >= 0

    def test_rank_livreurs_no_eligible(self):
        """Test ranking when no candidates are eligible."""
        # Create livreurs very far away
        livreurs = [
            self.create_livreur("L1", 49.0000, 3.0000),  # ~20km away
            self.create_livreur("L2", 48.7000, 2.0000),  # ~20km away
        ]

        request = RankingRequestSchema(
            annonce=self.annonce,
            livreurs_candidats=livreurs
        )

        response = self.orchestrator.rank_livreurs(request)

        # Should return empty results with warning
        assert response.status == "success"
        assert len(response.livreurs_classes) == 0
        assert response.warnings is not None
        assert len(response.warnings) > 0

        # Check that all candidates were rejected
        stats = response.metadata.statistiques_filtrage
        assert stats.candidats_eligibles == 0
        assert stats.candidats_rejetes == 2

    def test_rank_livreurs_express_delivery(self):
        """Test ranking with express delivery type."""
        annonce_express = AnnonceSchema(
            annonce_id="ANN-002",
            point_ramassage=self.annonce.point_ramassage,
            point_livraison=self.annonce.point_livraison,
            type_livraison=TypeLivraison.EXPRESS
        )

        livreurs = [
            self.create_livreur("L1", 48.8570, 2.3500),
            self.create_livreur("L2", 48.8590, 2.3400),
        ]

        request = RankingRequestSchema(
            annonce=annonce_express,
            livreurs_candidats=livreurs
        )

        response = self.orchestrator.rank_livreurs(request)

        # Check express delivery uses correct weights
        assert response.metadata.type_livraison == TypeLivraison.EXPRESS
        assert response.metadata.poids_ahp.proximite_geographique > 0.5

    def test_rank_livreurs_sameday_delivery(self):
        """Test ranking with sameday delivery type."""
        annonce_sameday = AnnonceSchema(
            annonce_id="ANN-003",
            point_ramassage=self.annonce.point_ramassage,
            point_livraison=self.annonce.point_livraison,
            type_livraison=TypeLivraison.SAMEDAY
        )

        livreurs = [
            self.create_livreur("L1", 48.8570, 2.3500),
            self.create_livreur("L2", 48.8590, 2.3400),
        ]

        request = RankingRequestSchema(
            annonce=annonce_sameday,
            livreurs_candidats=livreurs
        )

        response = self.orchestrator.rank_livreurs(request)

        # Sameday should prioritize proximity most
        assert response.metadata.type_livraison == TypeLivraison.SAMEDAY
        assert response.metadata.poids_ahp.proximite_geographique > 0.6

    def test_rank_livreurs_different_vehicles(self):
        """Test that vehicle type affects ranking."""
        livreurs = [
            # Same position and reputation, different vehicles
            self.create_livreur("L1", 48.8570, 2.3500, 8.0, 50.0, TypeVehicule.VELO),
            self.create_livreur("L2", 48.8570, 2.3500, 8.0, 50.0, TypeVehicule.MOTO),
            self.create_livreur("L3", 48.8570, 2.3500, 8.0, 50.0, TypeVehicule.VOITURE),
            self.create_livreur("L4", 48.8570, 2.3500, 8.0, 50.0, TypeVehicule.CAMION),
        ]

        request = RankingRequestSchema(
            annonce=self.annonce,
            livreurs_candidats=livreurs
        )

        response = self.orchestrator.rank_livreurs(request)

        # With all else equal, better vehicle should rank higher
        # CAMION (1.0) > VOITURE (0.8) > MOTO (0.3) > VELO (0.1)
        livreur_ids = [lc.livreur_id for lc in response.livreurs_classes]

        # L4 (CAMION) should rank higher than L1 (VELO)
        assert livreur_ids.index("L4") < livreur_ids.index("L1")

    def test_rank_livreurs_proximity_priority(self):
        """Test that proximity is a major factor in ranking."""
        livreurs = [
            # L1: Very close, average everything else
            self.create_livreur("L1", 48.8570, 2.3500, 7.0, 40.0, TypeVehicule.MOTO),
            # L2: Far, excellent everything else
            self.create_livreur("L2", 48.9000, 2.5000, 10.0, 200.0, TypeVehicule.CAMION),
        ]

        request = RankingRequestSchema(
            annonce=self.annonce,
            livreurs_candidats=livreurs
        )

        response = self.orchestrator.rank_livreurs(request)

        # Due to spatial filtering, L2 might be rejected
        # If both eligible, proximity should have major impact
        if len(response.livreurs_classes) == 2:
            # L1 should benefit from proximity
            assert response.metadata.poids_ahp.proximite_geographique > 0.3

    def test_metadata_completeness(self):
        """Test that metadata contains all required information."""
        livreurs = [
            self.create_livreur("L1", 48.8570, 2.3500),
        ]

        request = RankingRequestSchema(
            annonce=self.annonce,
            livreurs_candidats=livreurs
        )

        response = self.orchestrator.rank_livreurs(request)

        # Check metadata structure
        metadata = response.metadata
        assert metadata.type_livraison is not None
        assert metadata.tolerance_spatiale_km > 0

        # Check statistics
        stats = metadata.statistiques_filtrage
        assert stats.total_candidats == 1
        assert stats.candidats_eligibles + stats.candidats_rejetes == 1

        # Check AHP weights
        poids = metadata.poids_ahp
        assert poids.proximite_geographique > 0
        assert poids.reputation > 0
        assert poids.capacite > 0
        assert poids.type_vehicule > 0

        # Weights should sum to 1
        total_weight = (
            poids.proximite_geographique
            + poids.reputation
            + poids.capacite
            + poids.type_vehicule
        )
        assert abs(total_weight - 1.0) < 0.001

        # Check consistency
        assert poids.CR >= 0
        assert isinstance(poids.est_coherent, bool)
