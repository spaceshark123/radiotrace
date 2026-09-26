"""Persistence helpers for radio clip metadata and GridFS audio."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from gridfs.errors import NoFile
from pymongo import ReturnDocument

from app.services.mongo import get_database, get_gridfs_bucket


CLIPS = "clips"


def _collection():
    collection = get_database()[CLIPS]
    collection.create_index("source_key", unique=True)
    return collection


def serialize(document: dict[str, Any]) -> dict[str, Any]:
    result = {key: value for key, value in document.items() if key != "_id"}
    result["id"] = str(document["_id"])
    return result


def create_clip(
    audio: bytes,
    filename: str,
    metadata: dict[str, Any],
    source_key: str,
) -> dict[str, Any]:
    bucket = get_gridfs_bucket()
    content_type = "audio/mp4" if filename.lower().endswith(".m4a") else "audio/mpeg"
    audio_id = bucket.upload_from_stream(
        filename,
        io.BytesIO(audio),
        metadata={"contentType": content_type, "clipSourceKey": source_key},
    )
    document = {
        "hash": metadata.get("hash", ""),
        "systemId": str(metadata.get("systemId", "")),
        "encoding": metadata.get("encoding", "mp3"),
        "filename": filename,
        "metadata": {
            "start_time": metadata.get("start_time", 0),
            "end_time": metadata.get("end_time", 0),
            "transcript": metadata.get("transcript", ""),
        },
        "source_key": source_key,
        "audio_id": str(audio_id),
        "stored_at": datetime.now(timezone.utc),
    }
    result = _collection().insert_one(document)
    document["_id"] = result.inserted_id
    return serialize(document)


def update_metadata(clip_id: str, metadata: dict[str, Any]) -> dict[str, Any] | None:
    document = _collection().find_one_and_update(
        {"_id": ObjectId(clip_id)},
        {"$set": {f"metadata.{key}": value for key, value in metadata.items()}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 1, "hash": 1, "systemId": 1, "encoding": 1, "filename": 1, "metadata": 1, "source_key": 1, "audio_id": 1, "stored_at": 1},
    )
    return serialize(document) if document else None


def list_clips(limit: int = 100) -> list[dict[str, Any]]:
    documents = _collection().find({}, {"_id": 1, "hash": 1, "systemId": 1, "encoding": 1, "filename": 1, "metadata": 1, "source_key": 1, "audio_id": 1, "stored_at": 1}).sort("stored_at", -1).limit(limit)
    return [serialize(document) for document in documents]


def get_clip(clip_id: str) -> dict[str, Any] | None:
    try:
        object_id = ObjectId(clip_id)
    except (InvalidId, TypeError):
        return None
    document = _collection().find_one({"_id": object_id}, {"_id": 1, "hash": 1, "systemId": 1, "encoding": 1, "filename": 1, "metadata": 1, "source_key": 1, "audio_id": 1, "stored_at": 1})
    return serialize(document) if document else None


def open_audio_stream(clip: dict[str, Any]):
    try:
        return get_gridfs_bucket().open_download_stream(ObjectId(clip["audio_id"]))
    except (InvalidId, NoFile, TypeError) as exc:
        raise LookupError(f"Audio not found for clip {clip.get('id', '')}") from exc
