"""
Orchestrator - Main coordinator for Module 4

Coordinates the 3-phase livreur ranking process:
1. Phase 1: Spatial filtering (ellipse method)
2. Phase 2: AHP criteria weight calculation
3. Phase 3: TOPSIS multi-criteria ranking
"""

import logging
from datetime import datetime
from typing import List, Optional

from .schemas import (
    AnnonceSchema,
    LivreurCandidatSchema,
    RankingRequestSchema,
    RankingResponseSchema,
    LivreurClasseSchema,
    DetailScoresSchema,
    DistancesTOPSISSchema,
    MetadataSchema,
    StatistiquesFiltrageSchema,
    PoidsAHPSchema,
)
from .spatial_filter import SpatialFilter
from .ahp_calculator import AHPCalculator
from .topsis_ranker import TOPSISRanker
from .constants import SPATIAL_TOLERANCE_KM

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orchestrates the complete livreur ranking workflow.

    Workflow:
    1. Validate request
    2. Filter candidates by geographic proximity (ellipse method)
    3. Calculate criteria weights using AHP (based on delivery type)
    4. Rank eligible candidates using TOPSIS
    5. Format and return response
    """

    def __init__(self):
        """Initialize orchestrator with all required components."""
        self.spatial_filter = SpatialFilter()
        self.ahp_calculator = AHPCalculator()
        self.topsis_ranker = TOPSISRanker()

    def rank_livreurs(
        self,
        request: RankingRequestSchema,
        include_details: bool = False
    ) -> RankingResponseSchema:
        """
        Complete ranking workflow.

        Args:
            request: Ranking request containing annonce and candidates
            include_details: Whether to include detailed scores in response

        Returns:
            RankingResponseSchema with ranked livreurs
        """
        start_time = datetime.now()
        annonce = request.annonce
        livreurs = request.livreurs_candidats

        logger.info(
            f"Starting ranking for annonce {annonce.annonce_id} "
            f"with {len(livreurs)} candidates"
        )

        # ============================================================
        # PHASE 1: SPATIAL FILTERING
        # ============================================================
        logger.info("Phase 1: Spatial filtering")

        # Get tolerance based on delivery type
        tolerance_km = SPATIAL_TOLERANCE_KM[annonce.type_livraison]

        # Filter candidates
        eligible_livreurs, rejected_livreurs = self.spatial_filter.filter_by_ellipse(
            livreurs=livreurs,
            point_ramassage=annonce.point_ramassage,
            point_livraison=annonce.point_livraison,
            tolerance_km=tolerance_km
        )

        # Calculate distances for eligible livreurs
        distances = self.spatial_filter.calculate_distances_for_livreurs(
            livreurs=eligible_livreurs,
            point_ramassage=annonce.point_ramassage,
            point_livraison=annonce.point_livraison
        )

        logger.info(
            f"Phase 1 complete: {len(eligible_livreurs)} eligible, "
            f"{len(rejected_livreurs)} rejected"
        )

        # Handle case where no candidates are eligible
        if not eligible_livreurs:
            logger.warning("No eligible candidates after spatial filtering")
            return self._create_empty_response(
                annonce=annonce,
                total_candidats=len(livreurs),
                rejetes=rejected_livreurs,
                tolerance_km=tolerance_km,
                warning="Aucun livreur éligible après filtrage spatial"
            )

        # ============================================================
        # PHASE 2: AHP WEIGHT CALCULATION
        # ============================================================
        logger.info("Phase 2: AHP weight calculation")

        weights_dict, consistency_info = self.ahp_calculator.calculate_criteria_weights(
            type_livraison=annonce.type_livraison
        )

        logger.info(f"Phase 2 complete: weights = {weights_dict}")

        # ============================================================
        # PHASE 3: TOPSIS RANKING
        # ============================================================
        logger.info("Phase 3: TOPSIS ranking")

        # Rank eligible livreurs
        topsis_results = self.topsis_ranker.rank(
            livreurs=eligible_livreurs,
            distances=distances,
            weights=weights_dict
        )

        logger.info(
            f"Phase 3 complete: {len(topsis_results)} livreurs ranked"
        )

        # ============================================================
        # FORMAT RESPONSE
        # ============================================================
        livreurs_classes = self._format_ranked_livreurs(
            topsis_results=topsis_results,
            include_details=include_details
        )

        # Calculate processing time
        end_time = datetime.now()
        processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Build metadata
        metadata = MetadataSchema(
            type_livraison=annonce.type_livraison,
            tolerance_spatiale_km=tolerance_km,
            statistiques_filtrage=StatistiquesFiltrageSchema(
                total_candidats=len(livreurs),
                candidats_eligibles=len(eligible_livreurs),
                candidats_rejetes=len(rejected_livreurs),
                livreurs_rejetes=rejected_livreurs
            ),
            poids_ahp=PoidsAHPSchema(
                proximite_geographique=weights_dict["proximite_geographique"],
                reputation=weights_dict["reputation"],
                capacite=weights_dict["capacite"],
                type_vehicule=weights_dict["type_vehicule"],
                CR=consistency_info["CR"],
                est_coherent=consistency_info["est_coherent"]
            ),
            duree_traitement_ms=processing_time_ms
        )

        # Build final response
        response = RankingResponseSchema(
            status="success",
            annonce_id=annonce.annonce_id,
            timestamp=end_time,
            livreurs_classes=livreurs_classes,
            metadata=metadata,
            warnings=self._generate_warnings(consistency_info)
        )

        logger.info(
            f"Ranking complete for {annonce.annonce_id}: "
            f"{len(livreurs_classes)} livreurs ranked in {processing_time_ms}ms"
        )

        return response

    def _format_ranked_livreurs(
        self,
        topsis_results: List[dict],
        include_details: bool
    ) -> List[LivreurClasseSchema]:
        """
        Format TOPSIS results into response schema.

        Args:
            topsis_results: List of TOPSIS ranking results
            include_details: Whether to include detailed scores

        Returns:
            List of LivreurClasseSchema objects
        """
        livreurs_classes = []

        for rang, result in enumerate(topsis_results, start=1):
            # Build detail scores if requested
            details_scores = None
            distances_topsis = None

            if include_details:
                details_scores = DetailScoresSchema(
                    criteres_bruts=result["criteres_valeurs"],
                    criteres_normalises=result["criteres_normalises"],
                    criteres_ponderes=result["criteres_ponderes"]
                )

                distances_topsis = DistancesTOPSISSchema(
                    distance_ideal_positif=result["distance_A_positive"],
                    distance_ideal_negatif=result["distance_A_negative"]
                )

            livreur_classe = LivreurClasseSchema(
                rang=rang,
                livreur_id=result["livreur_id"],
                score_final=result["score_final"],
                details_scores=details_scores,
                distances_topsis=distances_topsis
            )

            livreurs_classes.append(livreur_classe)

        return livreurs_classes

    def _create_empty_response(
        self,
        annonce: AnnonceSchema,
        total_candidats: int,
        rejetes: List[dict],
        tolerance_km: float,
        warning: str
    ) -> RankingResponseSchema:
        """
        Create response when no candidates are eligible.

        Args:
            annonce: The delivery announcement
            total_candidats: Total number of candidates
            rejetes: List of rejected candidates
            tolerance_km: Spatial tolerance used
            warning: Warning message

        Returns:
            RankingResponseSchema with empty results
        """
        metadata = MetadataSchema(
            type_livraison=annonce.type_livraison,
            tolerance_spatiale_km=tolerance_km,
            statistiques_filtrage=StatistiquesFiltrageSchema(
                total_candidats=total_candidats,
                candidats_eligibles=0,
                candidats_rejetes=len(rejetes),
                livreurs_rejetes=rejetes
            ),
            poids_ahp=None,  # No AHP calculation needed
            duree_traitement_ms=0
        )

        return RankingResponseSchema(
            status="success",
            annonce_id=annonce.annonce_id,
            timestamp=datetime.now(),
            livreurs_classes=[],
            metadata=metadata,
            warnings=[warning]
        )

    def _generate_warnings(self, consistency_info: dict) -> Optional[List[str]]:
        """
        Generate warnings based on consistency check.

        Args:
            consistency_info: AHP consistency information

        Returns:
            List of warning messages, or None if no warnings
        """
        warnings = []

        if not consistency_info["est_coherent"]:
            warnings.append(
                f"La matrice AHP n'est pas parfaitement cohérente "
                f"(CR={consistency_info['CR']:.4f} > {consistency_info['seuil']}). "
                f"Les résultats peuvent être moins fiables."
            )

        return warnings if warnings else None


# ============================================================
# DEPENDENCY INJECTION / FACTORY
# ============================================================

_orchestrator_instance: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """
    Get singleton instance of Orchestrator.

    Used for dependency injection in FastAPI routes.

    Returns:
        Orchestrator instance
    """
    global _orchestrator_instance

    if _orchestrator_instance is None:
        _orchestrator_instance = Orchestrator()
        logger.info("Orchestrator instance created")

    return _orchestrator_instance
