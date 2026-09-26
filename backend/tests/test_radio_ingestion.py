from unittest.mock import patch

from app.services import radio_ingestion
from tests.conftest import VARIED_MP3


def test_ingest_new_clips_stores_audio_and_deduplicates(app):
    clip = {
        "filename": "1790455000-10020",
        "hash": "clip-hash",
        "systemId": 6204,
        "enc": "m4a",
    }
    with app.app_context():
        with (
            patch("app.services.radio_ingestion.broadcastify_service.client.get_clips") as get_clips,
            patch(
                "app.services.radio_ingestion.broadcastify_service.client.get_clip",
                return_value=VARIED_MP3,
            ) as get_clip,
            patch(
                "app.services.radio_ingestion.pipeline.process_clip",
                return_value={"status": "processed"},
            ) as process_clip,
        ):
            get_clips.return_value = {"calls": [clip]}

            assert radio_ingestion.ingest_new_clips() == 1
            assert radio_ingestion.ingest_new_clips() == 0

        stored = radio_ingestion.list_clips()
        assert len(stored) == 1
        assert stored[0]["encoding"] == "m4a"
        assert stored[0]["audio_id"]
        get_clip.assert_called_once_with("clip-hash", "6204", "1790455000-10020", "m4a")
        process_clip.assert_called_once()