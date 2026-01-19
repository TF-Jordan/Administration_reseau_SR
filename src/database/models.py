"""
SQLAlchemy models for Vehicle and Livreur entities.
Based on the UML diagrams provided.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .connection import Base


class Personne(Base):
    """
    Person/Client model.
    Represents users of the platform.
    """

    __tablename__ = "personnes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    id_client: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    telephone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    cni: Mapped[Optional[str]] = mapped_column(String(100))
    carte_photo: Mapped[Optional[str]] = mapped_column(Text)
    extrait_du_cassier: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Personne(id_client={self.id_client}, nom={self.nom})>"


class Vehicle(Base):
    """
    Vehicle model for the rental platform.
    Based on the detailed UML diagram provided.
    """

    __tablename__ = "vehicles"

    # Primary key
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign keys (simplified - storing as strings for flexibility)
    vehicle_make_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    vehicle_model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    transmission_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    manufacturer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    vehicle_size_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    vehicle_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    fuel_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Vehicle identification
    vehicle_serial_number: Mapped[Optional[str]] = mapped_column(Text)
    vehicle_serial_photo: Mapped[Optional[str]] = mapped_column(Text)
    registration_number: Mapped[Optional[str]] = mapped_column(
        Text, index=True
    )
    registration_photo: Mapped[Optional[str]] = mapped_column(Text)
    registration_expiry_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime
    )

    # Vehicle specifications
    tank_capacity: Mapped[Optional[float]] = mapped_column(Float)
    luggage_max_capacity: Mapped[Optional[float]] = mapped_column(Float)
    total_seat_number: Mapped[Optional[int]] = mapped_column(Integer)

    # Performance metrics
    average_fuel_consumption_per_km: Mapped[Optional[float]] = mapped_column(
        Float
    )
    mileage_at_start: Mapped[Optional[float]] = mapped_column(Float)
    mileage_since_commissioning: Mapped[Optional[float]] = mapped_column(Float)
    vehicle_age_at_start: Mapped[Optional[float]] = mapped_column(Float)

    # Additional info
    brand: Mapped[Optional[str]] = mapped_column(Text, index=True)
    model: Mapped[Optional[str]] = mapped_column(Text)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    color: Mapped[Optional[str]] = mapped_column(String(100))
    transmission_type: Mapped[Optional[str]] = mapped_column(String(50))
    fuel_type: Mapped[Optional[str]] = mapped_column(String(50))
    vehicle_type: Mapped[Optional[str]] = mapped_column(String(100))

    # Availability and pricing
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    localisation: Mapped[Optional[str]] = mapped_column(String(255))
    prix_journalier: Mapped[Optional[float]] = mapped_column(Float)

    # Ratings
    note_moyenne: Mapped[float] = mapped_column(Float, default=0.0)
    nombre_locations: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Vehicle(id={self.vehicle_id}, brand={self.brand}, model={self.model})>"

    def to_description(self) -> str:
        """
        Generate textual description for embedding.
        Used for vectorization in Qdrant.
        """
        parts = []

        # Brand and model
        if self.brand:
            parts.append(f"Véhicule {self.brand}")
            if self.model:
                parts.append(self.model)

        # Year
        if self.year:
            parts.append(f"année {self.year}")

        # Type
        if self.vehicle_type:
            parts.append(f"de type {self.vehicle_type}")

        # Specifications
        specs = []
        if self.total_seat_number:
            specs.append(f"{self.total_seat_number} places")
        if self.transmission_type:
            specs.append(f"boîte {self.transmission_type}")
        if self.fuel_type:
            specs.append(f"carburant {self.fuel_type}")

        if specs:
            parts.append("avec " + ", ".join(specs))

        # Capacity
        if self.luggage_max_capacity:
            parts.append(
                f"capacité bagages {self.luggage_max_capacity}L"
            )

        # Location
        if self.localisation:
            parts.append(f"situé à {self.localisation}")

        # Availability
        if self.disponible:
            parts.append("disponible à la location")
        else:
            parts.append("actuellement indisponible")

        # Rating
        if self.note_moyenne > 0:
            parts.append(f"noté {self.note_moyenne:.1f}/5")

        return " ".join(parts)


class Comment(Base):
    """
    Comment/Review model for storing user feedback.
    Links to both vehicles and livreurs.
    """

    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[str] = mapped_column(String(100), index=True)
    product_id: Mapped[str] = mapped_column(String(100), index=True)
    product_type: Mapped[str] = mapped_column(String(50), index=True)
    commentaire: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, product_id={self.product_id}, score={self.sentiment_score})>"
