from flask import Blueprint, Response, jsonify, request

from app.services import gridfs_service
from app.services.gridfs_service import AudioNotFoundError

bp = Blueprint("audio", __name__)


@bp.post("/api/audio")
def upload_audio():
    uploaded = request.files.get("file") or request.files.get("audio")
    if uploaded is None:
        return jsonify({"error": "multipart field 'file' is required"}), 400
    data = uploaded.read()
    if not data:
        return jsonify({"error": "empty file"}), 400
    filename = uploaded.filename or "clip.mp3"
    file_id = gridfs_service.upload_mp3(data, filename=filename)
    return jsonify({"id": file_id, "filename": filename}), 201


@bp.get("/api/audio/<file_id>")
def stream_audio(file_id: str):
    try:
        download_stream = gridfs_service.open_mp3_stream(file_id)
    except AudioNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404

    def generate():
        try:
            while True:
                chunk = download_stream.read(8192)
                if not chunk:
                    break
                yield chunk
        finally:
            download_stream.close()

    return Response(
        generate(),
        mimetype=download_stream.metadata.get("contentType", "audio/mpeg"),
        headers={"Content-Disposition": f'inline; filename="{download_stream.filename}"'},
    )
