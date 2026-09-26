"""Incident persistence. Collection shape matches schemas/Incident.json."""

from __future__ import annotations

from typing import Any

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
    }


def create_incident(
    recordings: list[str],
    location: list[dict],
    incident_type: list[dict],
    incident_id: int | None = None,
) -> dict[str, Any]:
    assigned_id = incident_id if incident_id is not None else next_incident_id()
    document = {
        "id": assigned_id,
        "recordings": recordings,
        "location": location,
        "type": incident_type,
    }
    _collection().insert_one(document)
    return serialize(document)


def list_incidents() -> list[dict[str, Any]]:
    docs = _collection().find({}, {"_id": 0}).sort("id", -1)
    return [serialize(doc) for doc in docs]


def get_incident(incident_id: int) -> dict[str, Any] | None:
    doc = _collection().find_one({"id": incident_id}, {"_id": 0})
    return serialize(doc) if doc else None


def append_recording(incident_id: int, recording: str) -> dict[str, Any] | None:
    result = _collection().find_one_and_update(
        {"id": incident_id},
        {"$push": {"recordings": {"$each": [recording], "$position": 0}}},
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
