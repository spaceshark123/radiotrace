from flask import Blueprint, Response, jsonify, stream_with_context

import requests

from app.config import Config
from app.services import broadcastify_service
from app.services.broadcastify_service import BroadcastifyError

bp = Blueprint("radio", __name__)


@bp.get("/api/radio/status")
def radio_status():
    try:
        return jsonify(broadcastify_service.get_feed_status())
    except BroadcastifyError as exc:
        return jsonify({"error": str(exc), "city": Config.CITY}), 502


@bp.get("/api/radio/stream")
def radio_stream():
    url = broadcastify_service.get_stream_url()
    try:
        upstream = requests.get(url, stream=True, timeout=(5, 60))
    except requests.Timeout:
        return jsonify({"error": "Broadcastify stream timed out"}), 504
    except requests.RequestException as exc:
        return jsonify({"error": f"Unable to reach Broadcastify: {exc}"}), 502

    if not upstream.ok:
        return jsonify({"error": "Broadcastify stream unavailable"}), 502

    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return Response(
        stream_with_context(generate()),
        mimetype=upstream.headers.get("Content-Type", "audio/mpeg"),
    )
