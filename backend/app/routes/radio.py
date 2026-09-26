from flask import Blueprint, Response, jsonify, request

from app.config import Config
from app.services import broadcastify_service
from app.services.broadcastify_service import BroadcastifyError, client as BroadcastifyClient

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
        payload = BroadcastifyClient.get_clips()
        calls = payload.get("calls", [])
        return jsonify(
            [
                {
                    "filename": call["filename"],
                    "hash": call["hash"],
                    "system_id": str(call["systemId"]),
                    "encoding": call.get("enc", "mp3"),
                }
                for call in calls
                if call.get("filename") and call.get("hash") and call.get("systemId")
            ]
        )
    except BroadcastifyError as exc:
        return jsonify({"error": str(exc), "city": Config.CITY}), 502


@bp.get("/api/radio/clips/file")
def radio_clip():
    clip_hash = request.args.get("hash", "")
    system_id = request.args.get("system_id", "")
    filename = request.args.get("filename", "")
    encoding = request.args.get("encoding", "mp3").lower()
    if not all((clip_hash, system_id, filename)) or encoding not in {"mp3", "m4a"}:
        return jsonify({"error": "hash, system_id, filename, and a valid encoding are required"}), 400

    try:
        clip = BroadcastifyClient.get_clip(clip_hash, system_id, filename, encoding)
        return Response(
            clip,
            mimetype="audio/mp4" if encoding == "m4a" else "audio/mpeg",
        )
    except BroadcastifyError as exc:
        return jsonify({"error": str(exc), "city": Config.CITY}), 502