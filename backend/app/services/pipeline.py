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
    source_key: str | None = None,
    clip_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Analyze and filter audio before persisting it, then run geocoding and
    spatial coordinate matching followed by Grok semantic matching.
    """
    if audio_analysis.is_blank_audio(
        audio,
        min_bytes=Config.BLANK_AUDIO_MIN_BYTES,
        min_unique_bytes=Config.BLANK_AUDIO_MIN_UNIQUE_BYTES,
    ):
        return {
            "status": "discarded_blank_audio",
            "incident": None,
            "transcript": "",
        }

    if not run_llm:
        clip = clip_service.create_clip(
            audio,
            filename=filename,
            source_key=source_key or f"manual:{uuid4()}",
            metadata={
                "start_time": start_time,
                "end_time": end_time,
                **(clip_metadata or {}),
            },
        )
        incident = incident_service.create_incident(
            recordings=[clip["id"]], location=[], incident_type=[]
        )
        return {"status": "stored", "incident": incident, "transcript": ""}

    transcript = elevenlabs_service.transcribe_mp3(audio, filename=filename)
    if not transcript:
        return {
            "status": "discarded_empty_transcript",
            "incident": None,
            "transcript": "",
        }

    analysis = grok_service.analyze_transcript(transcript)
    allowed_categories = {
        "violent_crime",
        "traffic_collision",
        "fire",
        "medical_emergency",
        "missing_person",
        "public_safety_threat",
        "property_crime",
        "other_crime",
    }
    if (
        not analysis["is_relevant"]
        or analysis["relevance_category"] not in allowed_categories
        or analysis["confidence"] < Config.MIN_RELEVANCE_CONFIDENCE
    ):
        return {
            "status": "discarded_irrelevant",
            "incident": None,
            "transcript": transcript,
        }

    locations: list[dict] = []
    place = analysis.get("location") or ""
    if place and analysis["location_confidence"] >= Config.MIN_LOCATION_CONFIDENCE:
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
            logger.warning("Geocode failed, rejecting clip: %s", exc)

    incident_type = [
        {
            "severity": analysis["severity"],
            "description": analysis["description"],
            "confidence": analysis["confidence"],
            "category": analysis["relevance_category"],
        }
    ]

    # --- TWO-TIER SPATIAL MATCHING PIPELINE ---
    candidate_incidents: list[dict] = []
    # Ensure we successfully geocoded valid coordinates to filter by
    if locations and "latitude" in locations[0] and "longitude" in locations[0]:
        target_lat = locations[0]["latitude"]
        target_lon = locations[0]["longitude"]

        # Step 1: Broad Filter (Find recent candidates within a ~300m radius)
        candidate_incidents = incident_service.find_matching_incidents(
            lat=target_lat,
            lon=target_lon,
            max_distance_deg=0.003  # Radius threshold (~300 meters)
        )
    else:
        # A follow-up transmission may omit the location; let semantic matching
        # reuse the location already attached to a recent incident.
        candidate_incidents = incident_service.list_recent_incidents()

    # Step 2: Fine-Grained Match (Use Grok to decide if transcript belongs to any spatially close candidate)
    matched_id = None
    if candidate_incidents and transcript:
        matched_id = grok_service.match_incident(transcript, candidate_incidents)

    if matched_id is None and not locations:
        return {
            "status": "discarded_no_location",
            "incident": None,
            "transcript": transcript,
        }

    if clip_id is None:
        clip = clip_service.create_clip(
            audio,
            filename=filename,
            source_key=source_key or f"manual:{uuid4()}",
            metadata={
                "start_time": start_time,
                "end_time": end_time,
                "transcript": transcript,
                **(clip_metadata or {}),
            },
        )
        recording = clip["id"]
    else:
        recording = clip_id
        clip_service.update_metadata(clip_id, {"transcript": transcript})

    # Step 3: Branch based on Grok's matching result
    if matched_id is not None:
        incident = incident_service.append_recording(
            incident_id=matched_id,
            recording=recording,
            severity=analysis["severity"],
            category=analysis["relevance_category"],
        )
        status = "matched_and_updated" if incident else "processed"
    else:
        incident = incident_service.create_incident(
            recordings=[recording],
            location=locations,
            incident_type=incident_type,
            severity=analysis["severity"],
            category=analysis["relevance_category"],
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