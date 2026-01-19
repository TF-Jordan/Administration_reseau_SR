"""
Constants for Module 4 - Livreur Ranking System
"""

from enum import Enum
from typing import Dict

# Earth radius in kilometers (for Haversine calculations)
EARTH_RADIUS_KM = 6371.0

# Delivery types
class TypeLivraison(str, Enum):
    """Types de livraison supportés."""
    STANDARD = "standard"
    EXPRESS = "express"
    SAMEDAY = "sameday"

# Vehicle types
class TypeVehicule(str, Enum):
    """Types de véhicule."""
    VELO = "velo"
    MOTO = "moto"
    VOITURE = "voiture"
    CAMION = "camion"

# Vehicle type scores (for TOPSIS normalization)
VEHICLE_TYPE_SCORES: Dict[str, float] = {
    TypeVehicule.VELO: 0.1,
    TypeVehicule.MOTO: 0.3,
    TypeVehicule.VOITURE: 0.8,
    TypeVehicule.CAMION: 1.0,
}

# Saaty Scale for AHP (1-9 scale)
SAATY_SCALE = {
    1: "Également important",
    2: "Entre également et modérément important",
    3: "Modérément plus important",
    4: "Entre modérément et fortement important",
    5: "Fortement plus important",
    6: "Entre fortement et très fortement important",
    7: "Très fortement plus important",
    8: "Entre très fortement et extrêmement important",
    9: "Extrêmement plus important",
}

# Random Index (RI) for AHP consistency check
# n: number of criteria
RANDOM_INDEX = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}

# AHP Consistency Ratio threshold
AHP_CONSISTENCY_THRESHOLD = 0.1  # CR < 0.1 is acceptable

# Predefined AHP comparison matrices for each delivery type
# Format: [proximite_vs_others, reputation_vs_others, capacite_vs_others]
# Each value represents importance on Saaty scale (1-9)

# STANDARD delivery: balanced approach
AHP_MATRIX_STANDARD = {
    # Proximité comparisons
    "proximite_vs_reputation": 2,      # proximité légèrement plus important
    "proximite_vs_capacite": 3,        # proximité moyennement plus important
    "proximite_vs_type_vehicule": 5,   # proximité fortement plus important
    # Réputation comparisons
    "reputation_vs_capacite": 2,
    "reputation_vs_type_vehicule": 3,
    # Capacité comparisons
    "capacite_vs_type_vehicule": 2,
}

# EXPRESS delivery: emphasis on proximity
AHP_MATRIX_EXPRESS = {
    "proximite_vs_reputation": 4,      # proximité fortement plus important
    "proximite_vs_capacite": 5,
    "proximite_vs_type_vehicule": 6,
    "reputation_vs_capacite": 2,
    "reputation_vs_type_vehicule": 3,
    "capacite_vs_type_vehicule": 2,
}

# SAMEDAY delivery: maximum emphasis on proximity
AHP_MATRIX_SAMEDAY = {
    "proximite_vs_reputation": 6,      # proximité très fortement plus important
    "proximite_vs_capacite": 7,
    "proximite_vs_type_vehicule": 7,
    "reputation_vs_capacite": 2,
    "reputation_vs_type_vehicule": 2,
    "capacite_vs_type_vehicule": 1,    # également important
}

# Mapping delivery type to AHP matrix
AHP_MATRICES = {
    TypeLivraison.STANDARD: AHP_MATRIX_STANDARD,
    TypeLivraison.EXPRESS: AHP_MATRIX_EXPRESS,
    TypeLivraison.SAMEDAY: AHP_MATRIX_SAMEDAY,
}

# Default spatial tolerance (km) by delivery type
SPATIAL_TOLERANCE_KM = {
    TypeLivraison.STANDARD: 2.5,  # Large zone
    TypeLivraison.EXPRESS: 1.5,   # Medium zone
    TypeLivraison.SAMEDAY: 1.0,   # Restricted zone
}

# Default top_k results
DEFAULT_TOP_K = 5

# Criteria names (for TOPSIS)
CRITERIA_NAMES = [
    "proximite",      # Distance (cost criterion - to minimize)
    "reputation",     # Reputation (benefit criterion - to maximize)
    "capacite",       # Capacity (benefit criterion - to maximize)
    "type_vehicule",  # Vehicle type (benefit criterion - to maximize)
]

# Criteria types (True = benefit, False = cost)
CRITERIA_TYPES = {
    "proximite": False,       # Cost - minimize distance
    "reputation": True,       # Benefit - maximize reputation
    "capacite": True,         # Benefit - maximize capacity
    "type_vehicule": True,    # Benefit - maximize vehicle capability
}
