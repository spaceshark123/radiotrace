"""Persist newly discovered Broadcastify clips in MongoDB and GridFS."""

from __future__ import annotations

import logging
from typing import Any

from app.services import broadcastify_service, clip_service, pipeline

logger = logging.getLogger(__name__)

_rejected_source_keys: set[str] = set()


def source_key(clip: dict[str, Any]) -> str:
    return ":".join(
        (
            str(clip["hash"]),
            str(clip["systemId"]),
            str(clip["filename"]),
            str(clip.get("enc", "mp3")),
        )
    )


def list_clips(limit: int = 100) -> list[dict[str, Any]]:
    return clip_service.list_clips(limit)


def get_clip(clip_id: str) -> dict[str, Any] | None:
    return clip_service.get_clip(clip_id)


def ingest_new_clips(limit: int = 5) -> int:
    # get the latest clips
    logger.info("fetching all current Broadcastify clips")
    payload = broadcastify_service.client.get_clips()
    logger.info("Broadcastify returned %s current clips", len(payload.get("calls", [])))
    stored_count = 0
    total_count = 0
    for clip in payload.get("calls", []):
        total_count += 1
        if not all((clip.get("hash"), clip.get("systemId"), clip.get("filename"))):
            continue

        encoding = str(clip.get("enc", "mp3")).lower()
        if encoding not in {"mp3", "m4a"}:
            continue
        key = source_key(clip)
        if key in _rejected_source_keys:
            continue
        if any(item.get("source_key") == key for item in clip_service.list_clips(1000)):
            continue

        # fetch the audio for each new clip
        audio = broadcastify_service.client.get_clip(
            str(clip["hash"]),
            str(clip["systemId"]),
            str(clip["filename"]),
            encoding,
        )
        result = pipeline.process_clip(
            audio,
            clip.get("meta_starttime", 0),
            clip.get("meta_endtime", 0),
            filename=f"{clip['filename']}.{encoding}",
            source_key=key,
            clip_metadata={
                "hash": clip["hash"],
                "systemId": clip["systemId"],
                "encoding": encoding,
            },
            run_llm=True
        )
        if result.get("status", "").startswith("discarded"):
            _rejected_source_keys.add(key)
        else:
            stored_count += 1
    logger.info("Newly stored clips: %s", stored_count)
    logger.info("Rejected clips: %s", total_count - stored_count)
    print(
        f"[radio-ingestion] stored={stored_count} rejected={total_count - stored_count}",
        flush=True,
    )
    return stored_count