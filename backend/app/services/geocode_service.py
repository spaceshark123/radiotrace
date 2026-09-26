"""Google Maps Geocoding: turn a place name into lat/lng, biased to Atlanta."""

from __future__ import annotations

import logging

import requests

from app.config import Config

logger = logging.getLogger(__name__)


class GeocodeError(RuntimeError):
    """Raised when Google Geocoding fails or returns no result."""


def geocode_location(place: str) -> dict:
    """Convert a location string into Google Maps coordinates."""
    if not Config.GOOGLE_MAPS_API_KEY:
        raise GeocodeError("GOOGLE_MAPS_API_KEY is not configured")
    if not place.strip():
        raise GeocodeError("Cannot geocode an empty location")

    query = place
    city_hint = f"{Config.CITY}, {Config.CITY_STATE}"
    if Config.CITY.lower() not in place.lower():
        query = f"{place}, {city_hint}"

    try:
        response = requests.get(
            Config.GOOGLE_GEOCODE_BASE,
            params={
                "address": query,
                "key": Config.GOOGLE_MAPS_API_KEY,
                "region": "us",
                "bounds": "33.65,-84.55|33.89,-84.28",
            },
            timeout=Config.HTTP_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise GeocodeError("Google Geocoding timed out") from exc
    except requests.RequestException as exc:
        raise GeocodeError(f"Google Geocoding request failed: {exc}") from exc

    if not response.ok:
        raise GeocodeError(f"Geocoding returned {response.status_code}")

    payload = response.json()
    status = payload.get("status")
    results = payload.get("results") or []
    if status != "OK" or not results:
        raise GeocodeError(f"No geocode result for '{query}' (status={status})")

    first = results[0]
    loc = first["geometry"]["location"]
    formatted = first.get("formatted_address", query)
    return {
        "google_maps": formatted,
        "latitude": float(loc["lat"]),
        "longitude": float(loc["lng"]),
    }
