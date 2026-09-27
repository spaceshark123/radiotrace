"""Persist newly discovered Broadcastify clips in MongoDB and GridFS."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from flask import current_app

from app.services import broadcastify_service, clip_service, pipeline

logger = logging.getLogger(__name__)

_rejected_source_keys: set[str] = set()
_inflight_source_keys: set[str] = set()
_source_keys_lock = threading.Lock()


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
    app = current_app._get_current_object()
    stored_count = 0
    total_count = 0
    # Read stored keys once, then run each independent download and analysis in
    # parallel. Bound workers to the round size to avoid unbounded API fan-out.
    stored_keys = {
        str(item.get("source_key"))
        for item in clip_service.list_clips(1000)
        if item.get("source_key")
    }
    candidates: list[tuple[dict[str, Any], str, str]] = []
    for clip in payload.get("calls", []):
        total_count += 1
        if not all((clip.get("hash"), clip.get("systemId"), clip.get("filename"))):
            continue

        encoding = str(clip.get("enc", "mp3")).lower()
        if encoding not in {"mp3", "m4a"}:
            continue
        key = source_key(clip)
        with _source_keys_lock:
            if key in _rejected_source_keys or key in stored_keys or key in _inflight_source_keys:
                continue
            _inflight_source_keys.add(key)
        candidates.append((clip, encoding, key))
        if limit > 0 and len(candidates) >= limit:
            break

    def process_candidate(item: tuple[dict[str, Any], str, str]) -> tuple[str, str | None]:
        clip, encoding, key = item
        try:
            with app.app_context():
                audio = broadcastify_service.client.get_clip(
                    str(clip["hash"]), str(clip["systemId"]), str(clip["filename"]), encoding
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
                    run_llm=True,
                )
            status = result.get("status", "")
            return key, status
        except Exception:
            logger.exception("Failed to ingest radio clip %s", key)
            return key, None
        finally:
            with _source_keys_lock:
                _inflight_source_keys.discard(key)

    if candidates:
        with ThreadPoolExecutor(
            max_workers=min(len(candidates), max(1, limit)),
            thread_name_prefix="radiotrace-radio-clip",
        ) as executor:
            futures = [executor.submit(process_candidate, item) for item in candidates]
            for future in as_completed(futures):
                key, status = future.result()
                if status is None:
                    continue
                if status.startswith("discarded"):
                    with _source_keys_lock:
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
