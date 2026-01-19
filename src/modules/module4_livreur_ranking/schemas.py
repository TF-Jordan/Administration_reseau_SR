"""
Pydantic schemas for Module 4 - Livreur Ranking System
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator

from .constants import TypeLivraison, TypeVehicule


class PointSchema(BaseModel):
    """Geographic point with coordinates."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude en degrés décimaux")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude en degrés décimaux")
    adresse: Optional[str] = Field(None, description="Adresse textuelle (optionnel)")


class AnnonceSchema(BaseModel):
    """Annonce de livraison."""
    annonce_id: str = Field(..., description="Identifiant unique de l'annonce")
    point_ramassage: PointSchema = Field(..., description="Point de collecte du colis")
    point_livraison: PointSchema = Field(..., description="Point de livraison du colis")
    type_livraison: TypeLivraison = Field(..., description="Type de livraison (standard/express/sameday)")
    description: Optional[str] = Field(None, description="Description de la livraison")


class LivreurCandidatSchema(BaseModel):
    """Livreur candidat pour une livraison."""
    livreur_id: str = Field(..., description="Identifiant unique du livreur")
    nom_commercial: str = Field(..., description="Nom commercial du livreur")
    position_actuelle: PointSchema = Field(..., description="Position actuelle du livreur")
    reputation: float = Field(..., ge=0, le=10, description="Réputation du livreur sur 10")
    nombre_livraisons: int = Field(..., ge=0, description="Nombre total de livraisons effectuées")
    taux_reussite: float = Field(..., ge=0, le=1, description="Taux de réussite (0-1)")
    type_vehicule: TypeVehicule = Field(..., description="Type de véhicule")
    capacite_max_kg: float = Field(..., gt=0, description="Capacité maximale en kilogrammes")
    rayon_action_km: Optional[float] = Field(None, gt=0, description="Rayon d'action en km")


class OptionsClassementSchema(BaseModel):
    """Options pour le classement."""
    top_k: int = Field(
        default=None,
        ge=1,
        le=100,
        description="Nombre de résultats souhaités (None = tous)"
    )
    tolerance_spatiale_km: Optional[float] = Field(
        None,
        gt=0,
        description="Tolérance spatiale en km (None = auto selon type_livraison)"
    )


class RankingRequestSchema(BaseModel):
    """Requête de classement de livreurs."""
    annonce: AnnonceSchema
    livreurs_candidats: List[LivreurCandidatSchema] = Field(..., min_items=1)
    options: Optional[OptionsClassementSchema] = None

    @validator('livreurs_candidats')
    def validate_candidats(cls, v):
        """Valide qu'il y a au moins un candidat."""
        if len(v) < 1:
            raise ValueError("Au moins un livreur candidat est requis")
        return v


class DetailScoresProximiteSchema(BaseModel):
    """Détails du score de proximité."""
    distance_ramassage_km: float = Field(..., description="Distance au point de ramassage")
    distance_livraison_km: float = Field(..., description="Distance au point de livraison")
    distance_totale_km: float = Field(..., description="Distance totale")
    score_normalise: float = Field(..., description="Score normalisé")


class DetailScoresReputationSchema(BaseModel):
    """Détails du score de réputation."""
    valeur: float = Field(..., description="Réputation brute")
    score_normalise: float = Field(..., description="Score normalisé")


class DetailScoresCapaciteSchema(BaseModel):
    """Détails du score de capacité."""
    capacite_kg: float = Field(..., description="Capacité en kg")
    score_normalise: float = Field(..., description="Score normalisé")


class DetailScoresTypeVehiculeSchema(BaseModel):
    """Détails du score du type de véhicule."""
    type: str = Field(..., description="Type de véhicule")
    score_numerique: float = Field(..., description="Score numérique (0-1)")
    score_normalise: float = Field(..., description="Score normalisé")


class DetailScoresSchema(BaseModel):
    """Détails des scores par critère."""
    proximite: DetailScoresProximiteSchema
    reputation: DetailScoresReputationSchema
    capacite: DetailScoresCapaciteSchema
    type_vehicule: DetailScoresTypeVehiculeSchema


class DistancesTOPSISSchema(BaseModel):
    """Distances TOPSIS."""
    distance_ideale_positive: float = Field(..., description="Distance à la solution idéale positive")
    distance_ideale_negative: float = Field(..., description="Distance à la solution idéale négative")


class LivreurClasseSchema(BaseModel):
    """Livreur classé avec son score."""
    rang: int = Field(..., ge=1, description="Rang du livreur")
    livreur_id: str = Field(..., description="Identifiant du livreur")
    score_final: float = Field(..., ge=0, le=1, description="Score final TOPSIS (0-1)")
    details_scores: Optional[DetailScoresSchema] = Field(None, description="Détails des scores")
    distances_topsis: Optional[DistancesTOPSISSchema] = Field(None, description="Distances TOPSIS")


class PoidsAHPSchema(BaseModel):
    """Poids des critères calculés par AHP."""
    proximite_geographique: float = Field(..., description="Poids de la proximité")
    reputation: float = Field(..., description="Poids de la réputation")
    capacite: float = Field(..., description="Poids de la capacité")
    type_vehicule: float = Field(..., description="Poids du type de véhicule")
    CR: float = Field(..., description="Ratio de cohérence (Consistency Ratio)")
    est_coherent: bool = Field(..., description="True si CR < 0.1 (AHP cohérent)")


# Alias for backward compatibility
PoidsCriteresSchema = PoidsAHPSchema


class StatistiquesFiltrageSchema(BaseModel):
    """Statistiques du filtrage spatial."""
    total_candidats: int = Field(..., description="Nombre total de candidats initiaux")
    candidats_eligibles: int = Field(..., description="Nombre de candidats éligibles après filtrage")
    candidats_rejetes: int = Field(..., description="Nombre de candidats rejetés")
    livreurs_rejetes: List[str] = Field(default_factory=list, description="IDs des livreurs rejetés")


class MethodeUtiliseeSchema(BaseModel):
    """Méthodes utilisées pour le classement."""
    filtrage: str = Field(default="ellipse_spherique", description="Méthode de filtrage")
    ponderation: str = Field(default="AHP", description="Méthode de pondération")
    classement: str = Field(default="TOPSIS", description="Méthode de classement")


class MetadataSchema(BaseModel):
    """Métadonnées du classement."""
    type_livraison: TypeLivraison = Field(..., description="Type de livraison")
    tolerance_spatiale_km: float = Field(..., description="Tolérance spatiale utilisée en km")
    statistiques_filtrage: StatistiquesFiltrageSchema = Field(..., description="Statistiques du filtrage")
    poids_ahp: PoidsAHPSchema = Field(..., description="Poids des critères calculés par AHP")
    duree_traitement_ms: float = Field(..., description="Durée totale du traitement en millisecondes")


class RankingResponseSchema(BaseModel):
    """Réponse du classement de livreurs."""
    status: str = Field(default="success", description="Statut de la requête")
    annonce_id: str = Field(..., description="ID de l'annonce")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp de la réponse")
    livreurs_classes: List[LivreurClasseSchema] = Field(..., description="Liste des livreurs classés")
    metadata: MetadataSchema = Field(..., description="Métadonnées du classement")
    warnings: Optional[List[str]] = Field(None, description="Avertissements éventuels")


class ErrorResponseSchema(BaseModel):
    """Réponse d'erreur."""
    status: str = Field(default="error")
    annonce_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
