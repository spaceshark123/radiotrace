"""Offline clip pipeline: GridFS -> blank check -> ElevenLabs -> Grok -> geocode -> incident."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.config import Config
from app.services import (
    audio_analysis,
    elevenlabs_service,
    geocode_service,
    gridfs_service,
    grok_service,
    incident_service,
)

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="radiotrace-pipeline")


def process_clip(
    audio: bytes,
    start_time: float,
    end_time: float,
    filename: str = "clip.mp3",
    run_llm: bool = True,
) -> dict[str, Any]:
    """
    Persist audio immediately, then optionally run STT + LLM + geocode.

    LLM steps are skipped for blank audio so we do not spend tokens on dead air.
    Processing is designed for prerecorded clips, not a live transcription loop.
    """
    audio_id = gridfs_service.upload_mp3(
        audio,
        filename=filename,
        metadata={"start_time": start_time, "end_time": end_time},
    )
    recording = {
        "start_time": start_time,
        "end_time": end_time,
        "audio": audio_id,
    }

    if audio_analysis.is_blank_audio(
        audio,
        min_bytes=Config.BLANK_AUDIO_MIN_BYTES,
        min_unique_bytes=Config.BLANK_AUDIO_MIN_UNIQUE_BYTES,
    ):
        incident = incident_service.create_incident(
            recordings=[recording],
            location=[],
            incident_type=[],
        )
        return {
            "status": "skipped_blank_audio",
            "incident": incident,
            "transcript": "",
        }

    if not run_llm:
        incident = incident_service.create_incident(
            recordings=[recording],
            location=[],
            incident_type=[],
        )
        return {"status": "stored", "incident": incident, "transcript": ""}

    transcript = elevenlabs_service.transcribe_mp3(audio, filename=filename)
    if not transcript:
        incident = incident_service.create_incident(
            recordings=[recording],
            location=[],
            incident_type=[],
        )
        return {
            "status": "skipped_empty_transcript",
            "incident": incident,
            "transcript": "",
        }

    analysis = grok_service.analyze_transcript(transcript)
    locations: list[dict] = []
    place = analysis.get("location") or ""
    if place:
        try:
            geo = geocode_service.geocode_location(place)
            locations.append(
                {
                    "google_maps": geo["google_maps"],
                    "latitude": geo["latitude"],
                    "longitude": geo["longitude"],
                    "confidence": analysis["confidence"],
                }
            )
        except geocode_service.GeocodeError as exc:
            logger.warning("Geocode failed, storing Atlanta fallback: %s", exc)
            locations.append(
                {
                    "google_maps": place or f"{Config.CITY}, {Config.CITY_STATE}",
                    "latitude": Config.CITY_CENTER_LAT,
                    "longitude": Config.CITY_CENTER_LNG,
                    "confidence": max(0.0, analysis["confidence"] * 0.4),
                }
            )

    incident_type = [
        {
            "severity": analysis["severity"],
            "description": analysis["description"],
            "confidence": analysis["confidence"],
        }
    ]
    incident = incident_service.create_incident(
        recordings=[recording],
        location=locations,
        incident_type=incident_type,
    )
    return {
        "status": "processed",
        "incident": incident,
        "transcript": transcript,
    }


def submit_clip_async(app, audio: bytes, start_time: float, end_time: float, filename: str) -> None:
    """Queue clip analysis on a background thread so the request path stays fast."""

    def _job() -> None:
        with app.app_context():
            try:
                process_clip(audio, start_time, end_time, filename=filename)
            except Exception:
                logger.exception("Background clip processing failed")

    _executor.submit(_job)
