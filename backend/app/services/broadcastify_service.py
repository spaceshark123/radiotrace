"""Broadcastify live Atlanta police radio metadata and stream URL resolution."""

from __future__ import annotations

import logging

import requests

from app.config import Config

logger = logging.getLogger(__name__)


class BroadcastifyError(RuntimeError):
    """Raised when Broadcastify metadata cannot be fetched."""


def get_stream_url() -> str:
    if Config.BROADCASTIFY_STREAM_URL:
        return Config.BROADCASTIFY_STREAM_URL
    feed_id = Config.BROADCASTIFY_FEED_ID
    return f"https://broadcastify.cdnstream1.com/{feed_id}"


def get_feed_status() -> dict:
    """
    Fetch feed metadata when an API key is present.

    Broadcastify's owner API is optional; without a key we still return the
    public stream URL so the live player can attempt playback.
    """
    info = {
        "city": Config.CITY,
        "feed_id": Config.BROADCASTIFY_FEED_ID,
        "stream_url": get_stream_url(),
        "live": True,
        "source": "broadcastify",
    }
    if not Config.BROADCASTIFY_API_KEY:
        info["authenticated"] = False
        return info

    url = f"{Config.BROADCASTIFY_API_BASE.rstrip('/')}/owner"
    try:
        response = requests.get(
            url,
            params={"a": "feeds", "key": Config.BROADCASTIFY_API_KEY},
            timeout=Config.HTTP_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise BroadcastifyError("Broadcastify API timed out") from exc
    except requests.RequestException as exc:
        raise BroadcastifyError(f"Broadcastify request failed: {exc}") from exc

    info["authenticated"] = True
    if response.ok:
        info["raw_status"] = response.status_code
    else:
        logger.warning("Broadcastify API status %s", response.status_code)
        info["authenticated"] = False
        info["error"] = f"status {response.status_code}"
    return info
