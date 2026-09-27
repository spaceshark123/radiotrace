"""Incident persistence. Collection shape matches schemas/Incident.json."""

from __future__ import annotations

from typing import Any
import time
from pymongo import ReturnDocument

from app.services import clip_service
from app.services.mongo import get_database


INCIDENTS = "incidents"
COUNTERS = "counters"


def _collection():
    return get_database()[INCIDENTS]


def next_incident_id() -> int:
    result = get_database()[COUNTERS].find_one_and_update(
        {"_id": "incidents"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(result["seq"])


def serialize(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": doc["id"],
        "recordings": [str(recording) for recording in doc.get("recordings", [])],
        "location": doc.get("location", []),
        "type": doc.get("type", []),
        "severity": doc.get("severity", "Unknown"),
        "category": doc.get("category", "unknown"),
        "confidence": doc.get("confidence", 0.0),
        "last_updated": doc.get("last_updated"),
    }

def find_matching_incidents(
    lat: float, 
    lon: float, 
    max_distance_deg: float = 0.005
) -> list[dict[str, Any]]:
    """
    Broad Filter: Finds recent incidents whose stored latitude and longitude 
    fall within a geographic bounding box threshold and time window.
    """
    
    # Define a bounding box around the target coordinates
    lat_min = lat - max_distance_deg
    lat_max = lat + max_distance_deg
    lon_min = lon - max_distance_deg
    lon_max = lon + max_distance_deg

    docs = _collection().find(
        {
            "location": {
                "$elemMatch": {
                    "latitude": {"$gte": lat_min, "$lte": lat_max},
                    "longitude": {"$gte": lon_min, "$lte": lon_max}
                }
            }
        },
        {"_id": 0}
    ).sort("id", -1)
    
    return [serialize(doc) for doc in docs]


def create_incident(
    recordings: list[str],
    location: list[dict],
    incident_type: list[dict],
    severity: str = "Unknown",
    category: str = "unknown",
    confidence: float = 0.0,
    incident_id: int | None = None,
) -> dict[str, Any]:
    assigned_id = incident_id if incident_id is not None else next_incident_id()
    now = int(time.time())
    
    document = {
        "id": assigned_id,
        "recordings": recordings,
        "location": location,
        "type": incident_type,
        "severity": severity,
        "category": category,
        "confidence": confidence,
        "last_updated": now,
    }
    _collection().insert_one(document)
    return serialize(document)


def list_incidents() -> list[dict[str, Any]]:
    docs = _collection().find({}, {"_id": 0}).sort("id", -1)
    return [serialize(doc) for doc in docs]


def list_recent_incidents(limit: int = 20) -> list[dict[str, Any]]:
    docs = (
        _collection()
        .find({}, {"_id": 0})
        .sort("last_updated", -1)
        .limit(limit)
    )
    return [serialize(doc) for doc in docs]


def get_incident(incident_id: int) -> dict[str, Any] | None:
    doc = _collection().find_one({"id": incident_id}, {"_id": 0})
    return serialize(doc) if doc else None


# def append_recording(incident_id: int, recording: str) -> dict[str, Any] | None:
#     result = _collection().find_one_and_update(
#         {"id": incident_id},
#         {"$push": {"recordings": {"$each": [recording], "$position": 0}}},
#         return_document=ReturnDocument.AFTER,
#         projection={"_id": 0},
#     )
#     return serialize(result) if result else None

def append_recording(
    incident_id: int,
    recording: str,
    severity: str | None = None,
    category: str | None = None,
) -> dict[str, Any] | None:
    """Appends a new recording clip to an existing incident and updates the timestamp."""
    update_ops: dict[str, Any] = {
        "$push": {"recordings": {"$each": [recording], "$position": 0}},
        "$set": {"last_updated": int(time.time())}
    }
    if severity:
        update_ops["$set"]["severity"] = severity
    if category:
        update_ops["$set"]["category"] = category

    result = _collection().find_one_and_update(
        {"id": incident_id},
        update_ops,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    return serialize(result) if result else None

def delete_incidents_with_latest_recording_before(cutoff_timestamp: float) -> int:
    """Delete incidents whose newest referenced clip is older than the cutoff."""
    deleted = 0
    for incident in _collection().find({}, {"_id": 1, "recordings": 1}):
        recordings = incident.get("recordings", [])
        if not recordings:
            continue
        latest = recordings[0]
        if isinstance(latest, dict):
            timestamp = latest.get("end_time", latest.get("start_time", 0))
            is_old = timestamp < cutoff_timestamp
        else:
            clip = clip_service.get_clip(str(latest))
            stored_at = clip.get("stored_at") if clip else None
            is_old = stored_at is not None and stored_at.timestamp() < cutoff_timestamp
        if is_old:
            _collection().delete_one({"_id": incident["_id"]})
            deleted += 1
    return deleted
