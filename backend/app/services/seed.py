"""Seed a few Atlanta demo incidents so the map is usable without live radio."""

from app.config import Config
from app.services import incident_service


DEMO_INCIDENTS = [
    {
        "recordings": [
            {"start_time": 1_714_000_000, "end_time": 1_714_000_045, "audio": ""}
        ],
        "location": [
            {
                "google_maps": "Centennial Olympic Park, Atlanta, GA",
                "latitude": 33.7603,
                "longitude": -84.3935,
                "confidence": 0.91,
            }
        ],
        "type": [
            {
                "severity": "Minor",
                "description": "Large crowd and traffic congestion near the park",
                "confidence": 0.78,
            }
        ],
    },
    {
        "recordings": [
            {"start_time": 1_714_000_100, "end_time": 1_714_000_160, "audio": ""}
        ],
        "location": [
            {
                "google_maps": "Five Points Station, Atlanta, GA",
                "latitude": 33.7537,
                "longitude": -84.3915,
                "confidence": 0.86,
            }
        ],
        "type": [
            {
                "severity": "Moderate",
                "description": "Theft in progress reported on MARTA property",
                "confidence": 0.72,
            }
        ],
    },
    {
        "recordings": [
            {"start_time": 1_714_000_200, "end_time": 1_714_000_280, "audio": ""}
        ],
        "location": [
            {
                "google_maps": "Grady Memorial Hospital, Atlanta, GA",
                "latitude": 33.752,
                "longitude": -84.382,
                "confidence": 0.88,
            }
        ],
        "type": [
            {
                "severity": "Severe",
                "description": "Multi-vehicle crash with injuries, EMS requested",
                "confidence": 0.83,
            }
        ],
    },
]


def seed_if_empty() -> list:
    existing = incident_service.list_incidents()
    if existing:
        return existing
    created = []
    for item in DEMO_INCIDENTS:
        created.append(
            incident_service.create_incident(
                recordings=item["recordings"],
                location=item["location"],
                incident_type=item["type"],
            )
        )
    return created


def city_config() -> dict:
    return {
        "city": Config.CITY,
        "state": Config.CITY_STATE,
        "center": {"lat": Config.CITY_CENTER_LAT, "lng": Config.CITY_CENTER_LNG},
    }
