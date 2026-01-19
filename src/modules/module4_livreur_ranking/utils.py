"""
Utility functions for Module 4 - Livreur Ranking System
"""

import math
from typing import Tuple

from .constants import EARTH_RADIUS_KM


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    radius: float = EARTH_RADIUS_KM
) -> float:
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula.

    Formula:
        d = 2R × arcsin(√(sin²((φ₂-φ₁)/2) + cos(φ₁)cos(φ₂)sin²((λ₂-λ₁)/2)))

    Args:
        lat1: Latitude of point 1 in degrees
        lon1: Longitude of point 1 in degrees
        lat2: Latitude of point 2 in degrees
        lon2: Longitude of point 2 in degrees
        radius: Earth radius in km (default: 6371.0)

    Returns:
        Distance in kilometers

    Example:
        >>> haversine_distance(48.8566, 2.3522, 51.5074, -0.1278)
        343.56  # Paris to London in km
    """
    # Convert degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    lambda1 = math.radians(lon1)
    lambda2 = math.radians(lon2)

    # Differences
    delta_phi = phi2 - phi1
    delta_lambda = lambda2 - lambda1

    # Haversine formula
    a = (
        math.sin(delta_phi / 2) ** 2 +
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))

    distance = radius * c

    return distance


def calculate_total_distance(
    livreur_lat: float,
    livreur_lon: float,
    pickup_lat: float,
    pickup_lon: float,
    delivery_lat: float,
    delivery_lon: float
) -> Tuple[float, float, float]:
    """
    Calculate total delivery distance for a delivery person.

    Distance = d(Livreur, Pickup) + d(Pickup, Delivery)

    Args:
        livreur_lat: Livreur latitude
        livreur_lon: Livreur longitude
        pickup_lat: Pickup point latitude
        pickup_lon: Pickup point longitude
        delivery_lat: Delivery point latitude
        delivery_lon: Delivery point longitude

    Returns:
        Tuple of (distance_to_pickup, pickup_to_delivery, total_distance) in km
    """
    dist_to_pickup = haversine_distance(
        livreur_lat, livreur_lon,
        pickup_lat, pickup_lon
    )

    dist_pickup_to_delivery = haversine_distance(
        pickup_lat, pickup_lon,
        delivery_lat, delivery_lon
    )

    total_distance = dist_to_pickup + dist_pickup_to_delivery

    return dist_to_pickup, dist_pickup_to_delivery, total_distance


def calculate_ellipse_dmax(
    f1_lat: float,
    f1_lon: float,
    f2_lat: float,
    f2_lon: float,
    tolerance_km: float
) -> float:
    """
    Calculate Dmax for ellipse spatial filtering.

    Dmax = d(F1, F2) + 2 × tolerance

    where F1 is pickup point and F2 is delivery point.

    Args:
        f1_lat: Pickup latitude
        f1_lon: Pickup longitude
        f2_lat: Delivery latitude
        f2_lon: Delivery longitude
        tolerance_km: Spatial tolerance in km

    Returns:
        Dmax in kilometers
    """
    direct_distance = haversine_distance(f1_lat, f1_lon, f2_lat, f2_lon)
    dmax = direct_distance + (2 * tolerance_km)
    return dmax


def degrees_to_radians(degrees: float) -> float:
    """Convert degrees to radians."""
    return degrees * (math.pi / 180)


def radians_to_degrees(radians: float) -> float:
    """Convert radians to degrees."""
    return radians * (180 / math.pi)
