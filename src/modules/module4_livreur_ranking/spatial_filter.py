"""
Spatial Filter - Phase 1 of Module 4

Implements spherical ellipse filtering to select geographically relevant
delivery persons.
"""

import logging
from typing import List, Tuple, Dict, Any

from .schemas import LivreurCandidatSchema, PointSchema
from .utils import calculate_total_distance, calculate_ellipse_dmax
from .constants import EARTH_RADIUS_KM

logger = logging.getLogger(__name__)


class SpatialFilter:
    """
    Filters delivery persons using spherical ellipse method.

    A delivery person P is eligible if:
        d(P, F1) + d(P, F2) ≤ Dmax

    where:
    - F1 = pickup point
    - F2 = delivery point
    - Dmax = d(F1, F2) + 2 × tolerance
    """

    def __init__(self, earth_radius_km: float = EARTH_RADIUS_KM):
        """
        Initialize spatial filter.

        Args:
            earth_radius_km: Earth radius in kilometers (default: 6371.0)
        """
        self.earth_radius = earth_radius_km

    def filter_by_ellipse(
        self,
        livreurs: List[LivreurCandidatSchema],
        point_ramassage: PointSchema,
        point_livraison: PointSchema,
        tolerance_km: float
    ) -> Tuple[List[LivreurCandidatSchema], List[Dict[str, Any]]]:
        """
        Filter delivery persons using spherical ellipse.

        Args:
            livreurs: List of candidate delivery persons
            point_ramassage: Pickup point
            point_livraison: Delivery point
            tolerance_km: Spatial tolerance in km

        Returns:
            Tuple of:
            - List of eligible delivery persons
            - List of rejected delivery persons with reasons
        """
        logger.info(
            f"Filtering {len(livreurs)} candidates with tolerance {tolerance_km} km"
        )

        # Calculate Dmax
        dmax = calculate_ellipse_dmax(
            point_ramassage.latitude,
            point_ramassage.longitude,
            point_livraison.latitude,
            point_livraison.longitude,
            tolerance_km
        )

        logger.info(f"Calculated Dmax: {dmax:.2f} km")

        eligible = []
        rejected = []

        for livreur in livreurs:
            # Calculate total distance for this livreur
            dist_to_pickup, dist_pickup_delivery, total_dist = calculate_total_distance(
                livreur.position_actuelle.latitude,
                livreur.position_actuelle.longitude,
                point_ramassage.latitude,
                point_ramassage.longitude,
                point_livraison.latitude,
                point_livraison.longitude
            )

            # Check if within ellipse
            if total_dist <= dmax:
                eligible.append(livreur)
                logger.debug(
                    f"Livreur {livreur.livreur_id} ELIGIBLE: "
                    f"total_dist={total_dist:.2f} km ≤ Dmax={dmax:.2f} km"
                )
            else:
                rejected.append({
                    "livreur_id": livreur.livreur_id,
                    "nom_commercial": livreur.nom_commercial,
                    "raison": "hors_zone_ellipse",
                    "distance_totale_km": round(total_dist, 2),
                    "distance_max_km": round(dmax, 2),
                    "distance_ramassage_km": round(dist_to_pickup, 2),
                })
                logger.debug(
                    f"Livreur {livreur.livreur_id} REJECTED: "
                    f"total_dist={total_dist:.2f} km > Dmax={dmax:.2f} km"
                )

        logger.info(
            f"Spatial filtering complete: {len(eligible)} eligible, "
            f"{len(rejected)} rejected"
        )

        return eligible, rejected

    def calculate_distances(
        self,
        livreur: LivreurCandidatSchema,
        point_ramassage: PointSchema,
        point_livraison: PointSchema
    ) -> Dict[str, float]:
        """
        Calculate all distances for a delivery person.

        Args:
            livreur: Delivery person
            point_ramassage: Pickup point
            point_livraison: Delivery point

        Returns:
            Dict with distance_ramassage_km, distance_livraison_km, distance_totale_km
        """
        dist_to_pickup, _, total_dist = calculate_total_distance(
            livreur.position_actuelle.latitude,
            livreur.position_actuelle.longitude,
            point_ramassage.latitude,
            point_ramassage.longitude,
            point_livraison.latitude,
            point_livraison.longitude
        )

        # Also calculate direct distance to delivery point (for completeness)
        from .utils import haversine_distance
        dist_to_delivery = haversine_distance(
            livreur.position_actuelle.latitude,
            livreur.position_actuelle.longitude,
            point_livraison.latitude,
            point_livraison.longitude
        )

        return {
            "distance_ramassage_km": round(dist_to_pickup, 2),
            "distance_livraison_km": round(dist_to_delivery, 2),
            "distance_totale_km": round(total_dist, 2),
        }

    def calculate_distances_for_livreurs(
        self,
        livreurs: List[LivreurCandidatSchema],
        point_ramassage: PointSchema,
        point_livraison: PointSchema
    ) -> Dict[str, float]:
        """
        Calculate total distances for multiple delivery persons.

        This is used for TOPSIS ranking - we need the total distance
        (livreur -> pickup -> delivery) for each livreur as a criterion.

        Args:
            livreurs: List of delivery persons
            point_ramassage: Pickup point
            point_livraison: Delivery point

        Returns:
            Dict mapping livreur_id to total distance in km
        """
        distances = {}

        for livreur in livreurs:
            _, _, total_dist = calculate_total_distance(
                livreur.position_actuelle.latitude,
                livreur.position_actuelle.longitude,
                point_ramassage.latitude,
                point_ramassage.longitude,
                point_livraison.latitude,
                point_livraison.longitude
            )
            distances[livreur.livreur_id] = total_dist

        return distances
