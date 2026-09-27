"""Offline clip pipeline: GridFS -> blank check -> ElevenLabs -> Grok -> geocode -> spatial incident matching/creation."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

from app.config import Config
from app.services import (
    audio_analysis,
    clip_service,
    elevenlabs_service,
    geocode_service,
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
    clip_id: str | None = None,
) -> dict[str, Any]:
    """
    Persist audio immediately, then optionally run STT + LLM + geocode.
    Applies spatial coordinate matching followed by Grok semantic matching.
    """
    if clip_id is None:
        clip = clip_service.create_clip(
            audio,
            filename=filename,
            source_key=f"manual:{uuid4()}",
            metadata={"start_time": start_time, "end_time": end_time},
        )
        clip_id = clip["id"]
    recording = clip_id

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

    if clip_id:
        clip_service.update_metadata(clip_id, {"transcript": transcript})

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

    # --- TWO-TIER SPATIAL MATCHING PIPELINE ---
    incident = None
    status = "processed"

    candidate_incidents = []
    # Ensure we successfully geocoded valid coordinates to filter by
    if locations and "latitude" in locations[0] and "longitude" in locations[0]:
        target_lat = locations[0]["latitude"]
        target_lon = locations[0]["longitude"]

        # Step 1: Broad Filter (Find recent candidates within a ~500m radius and 1 hour window)
        candidate_incidents = incident_service.find_matching_incidents_by_coordinates(
            lat=target_lat,
            lon=target_lon,
            max_distance_deg=0.005,  # Radius threshold (~500 meters)
            max_age_minutes=60
        )

    # Step 2: Fine-Grained Match (Use Grok to decide if transcript belongs to any spatially close candidate)
    matched_id = None
    if candidate_incidents and transcript:
        matched_id = grok_service.match_incident(transcript, candidate_incidents)

    # Step 3: Branch based on Grok's matching result
    if matched_id is not None:
        incident = incident_service.append_recording(
            incident_id=matched_id,
            recording=recording,
            severity=analysis["severity"]
        )
        status = "matched_and_updated"
    else:
        incident = incident_service.create_incident(
            recordings=[recording],
            location=locations,
            incident_type=incident_type,
            severity=analysis["severity"],
            confidence=analysis["confidence"],
        )
        status = "processed"

    return {
        "status": status,
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