"""Application configuration loaded from environment variables."""

import os


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


class Config:
    """Runtime settings for RadioTrace (Atlanta-focused)."""

    CITY = _env("CITY", "Atlanta")
    CITY_STATE = _env("CITY_STATE", "GA")
    CITY_CENTER_LAT = float(_env("CITY_CENTER_LAT", "33.7490"))
    CITY_CENTER_LNG = float(_env("CITY_CENTER_LNG", "-84.3880"))

    MONGO_URI = _env("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DATABASE = _env("MONGO_DATABASE", "radiotrace")
    GRIDFS_BUCKET = _env("GRIDFS_BUCKET", "audio")

    ELEVENLABS_API_KEY = _env("ELEVENLABS_API_KEY")
    ELEVENLABS_API_BASE = _env("ELEVENLABS_API_BASE", "https://api.elevenlabs.io")
    ELEVENLABS_STT_MODEL = _env("ELEVENLABS_STT_MODEL", "scribe_v1")

    # SpaceX AI / xAI Grok (either key name is accepted)
    XAI_API_KEY = _env("XAI_API_KEY") or _env("SPACEX_AI_API_KEY")
    XAI_API_BASE = _env("XAI_API_BASE") or _env("SPACEX_AI_API_BASE", "https://api.x.ai/v1")
    GROK_MODEL = _env("GROK_MODEL", "grok-3-mini")

    GOOGLE_MAPS_API_KEY = _env("GOOGLE_MAPS_API_KEY")
    GOOGLE_GEOCODE_BASE = _env(
        "GOOGLE_GEOCODE_BASE", "https://maps.googleapis.com/maps/api/geocode/json"
    )

    BROADCASTIFY_API_KEY = _env("BROADCASTIFY_API_KEY")
    BROADCASTIFY_API_BASE = _env("BROADCASTIFY_API_BASE", "https://api.broadcastify.com")
    BROADCASTIFY_FEED_ID = _env("BROADCASTIFY_FEED_ID", "394")
    BROADCASTIFY_STREAM_URL = _env("BROADCASTIFY_STREAM_URL")

    HTTP_TIMEOUT_SECONDS = float(_env("HTTP_TIMEOUT_SECONDS", "20"))
    BLANK_AUDIO_MIN_BYTES = int(_env("BLANK_AUDIO_MIN_BYTES", "2048"))
    BLANK_AUDIO_MIN_UNIQUE_BYTES = int(_env("BLANK_AUDIO_MIN_UNIQUE_BYTES", "8"))
