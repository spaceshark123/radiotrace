"""Incident persistence. Collection shape matches schemas/Incident.json."""

from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

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
        "recordings": doc.get("recordings", []),
        "location": doc.get("location", []),
        "type": doc.get("type", []),
    }


def create_incident(
    recordings: list[dict],
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


def append_recording(incident_id: int, recording: dict) -> dict[str, Any] | None:
    result = _collection().find_one_and_update(
        {"id": incident_id},
        {"$push": {"recordings": recording}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    return serialize(result) if result else None
