from flask import Blueprint, current_app, jsonify, request

from app.services import pipeline

bp = Blueprint("pipeline", __name__)


@bp.post("/api/pipeline/process")
def process_clip():
    uploaded = request.files.get("file") or request.files.get("audio")
    if uploaded is None:
        return jsonify({"error": "multipart field 'file' is required"}), 400
    data = uploaded.read()
    if not data:
        return jsonify({"error": "empty file"}), 400

    try:
        start_time = float(request.form.get("start_time", 0))
        end_time = float(request.form.get("end_time", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "start_time and end_time must be numbers"}), 400

    async_mode = request.form.get("async", "false").lower() in {"1", "true", "yes"}
    filename = uploaded.filename or "clip.mp3"

    if async_mode:
        pipeline.submit_clip_async(current_app._get_current_object(), data, start_time, end_time, filename)
        return jsonify({"status": "queued"}), 202

    try:
        result = pipeline.process_clip(data, start_time, end_time, filename=filename)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify(result), 200
