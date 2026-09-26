"""ElevenLabs speech-to-text. Used asynchronously after a clip is stored, not live."""

from __future__ import annotations

import logging

import requests

from app.config import Config

logger = logging.getLogger(__name__)


class ElevenLabsError(RuntimeError):
    """Raised when transcription fails after defensive retries are exhausted."""


def transcribe_mp3(audio: bytes, filename: str = "clip.mp3") -> str:
    """Send MP3 bytes to ElevenLabs STT and return the transcript text."""
    if not Config.ELEVENLABS_API_KEY:
        raise ElevenLabsError("ELEVENLABS_API_KEY is not configured")

    url = f"{Config.ELEVENLABS_API_BASE.rstrip('/')}/v1/speech-to-text"
    try:
        response = requests.post(
            url,
            headers={"xi-api-key": Config.ELEVENLABS_API_KEY},
            data={"model_id": Config.ELEVENLABS_STT_MODEL},
            files={"file": (filename, audio, "audio/mpeg")},
            timeout=Config.HTTP_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise ElevenLabsError("ElevenLabs transcription timed out") from exc
    except requests.RequestException as exc:
        raise ElevenLabsError(f"ElevenLabs request failed: {exc}") from exc

    if not response.ok:
        raise ElevenLabsError(
            f"ElevenLabs returned {response.status_code}: {response.text[:300]}"
        )

    payload = response.json()
    text = payload.get("text") or payload.get("transcript") or ""
    if isinstance(text, dict):
        text = text.get("text", "")
    return str(text).strip()
