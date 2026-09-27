"""Persist newly discovered Broadcastify clips in MongoDB and GridFS."""

from __future__ import annotations

from typing import Any

from app.services import broadcastify_service, clip_service, pipeline


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
    payload = broadcastify_service.client.get_clips()
    stored_count = 0
    for clip in payload.get("calls", [])[:limit]:
        if not all((clip.get("hash"), clip.get("systemId"), clip.get("filename"))):
            continue

        encoding = str(clip.get("enc", "mp3")).lower()
        if encoding not in {"mp3", "m4a"}:
            continue
        key = source_key(clip)
        if any(item.get("source_key") == key for item in clip_service.list_clips(1000)):
            continue

        # fetch the audio for each new clip
        audio = broadcastify_service.client.get_clip(
            str(clip["hash"]),
            str(clip["systemId"]),
            str(clip["filename"]),
            encoding,
        )
        document = clip_service.create_clip(
            audio,
            filename=f"{clip['filename']}.{encoding}",
            source_key=key,
            metadata={
                "hash": clip["hash"],
                "systemId": clip["systemId"],
                "encoding": encoding,
                "start_time": clip.get("meta_starttime"),
                "end_time": clip.get("meta_endtime")
            },
        )
        stored_count += 1
        pipeline.process_clip(
            audio,
            0,
            0,
            filename=document["filename"],
            clip_id=document["id"],
            run_llm=True,
        )
    return stored_count