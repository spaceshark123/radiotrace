from flask import Blueprint, Response, jsonify

from app.config import Config
from app.services import broadcastify_service, clip_service, radio_ingestion
from app.services.broadcastify_service import BroadcastifyError

bp = Blueprint("radio", __name__)


@bp.get("/api/radio/status")
def radio_status():
    try:
        return jsonify(broadcastify_service.get_feed_status())
    except BroadcastifyError as exc:
        return jsonify({"error": str(exc), "city": Config.CITY}), 502


@bp.get("/api/radio/clips")
def radio_clips():
    try:
        return jsonify(radio_ingestion.list_clips())
    except Exception as exc:
        return jsonify({"error": str(exc), "city": Config.CITY}), 500


@bp.get("/api/radio/clips/file/<audio_id>")
def radio_clip(audio_id: str):
    try:
        stored_clip = clip_service.get_clip(audio_id)
        if stored_clip is None:
            return jsonify({"error": "radio clip not found"}), 404
        download_stream = clip_service.open_audio_stream(stored_clip)

        def generate():
            try:
                while chunk := download_stream.read(8192):
                    yield chunk
            finally:
                download_stream.close()

        return Response(
            generate(),
            mimetype="audio/mp4" if stored_clip["encoding"] == "m4a" else "audio/mpeg",
        )
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404


@bp.get("/api/radio/clips/<clip_id>")
def radio_clip_object(clip_id: str):
    clip = clip_service.get_clip(clip_id)
    if clip is None:
        return jsonify({"error": "radio clip not found"}), 404
    clip["audio_url"] = f"/api/radio/clips/file/{clip_id}"
    return jsonify(clip)