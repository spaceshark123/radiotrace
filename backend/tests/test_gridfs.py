"""Phase 1: verify MP3 upload and retrieval through GridFSBucket."""

from app.services import gridfs_service
from tests.conftest import VARIED_MP3


def test_gridfs_upload_and_download_roundtrip(app):
    with app.app_context():
        file_id = gridfs_service.upload_mp3(VARIED_MP3, filename="unit.mp3")
        assert file_id
        restored = gridfs_service.download_mp3(file_id)
        assert restored == VARIED_MP3


def test_audio_http_upload_and_stream(client):
    response = client.post(
        "/api/audio",
        data={"file": (VARIED_MP3, "clip.mp3")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    file_id = response.get_json()["id"]

    streamed = client.get(f"/api/audio/{file_id}")
    assert streamed.status_code == 200
    assert streamed.mimetype == "audio/mpeg"
    assert streamed.data == VARIED_MP3


def test_m4a_upload_and_stream_preserves_audio_type(client):
    response = client.post(
        "/api/audio",
        data={"file": (VARIED_MP3, "clip.m4a")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    file_id = response.get_json()["id"]

    streamed = client.get(f"/api/audio/{file_id}")
    assert streamed.status_code == 200
    assert streamed.mimetype == "audio/mp4"
    assert streamed.data == VARIED_MP3


def test_missing_audio_returns_404(client):
    response = client.get("/api/audio/64b64b64b64b64b64b64b64b")
    assert response.status_code == 404
