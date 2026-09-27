import threading
import uuid
from unittest.mock import patch

from flask import Flask

from app import run_radio_ingestion_poll
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
            patch(
                "app.services.radio_ingestion.clip_service.list_clips",
                side_effect=[[], [{"source_key": "clip-hash:6204:1790455000-10020:m4a"}]],
            ),
        ):
            get_clips.return_value = {"calls": [clip]}

            assert radio_ingestion.ingest_new_clips() == 1
            assert radio_ingestion.ingest_new_clips() == 0

        get_clip.assert_called_once_with("clip-hash", "6204", "1790455000-10020", "m4a")
        process_clip.assert_called_once()


def test_run_radio_ingestion_poll_prints_completion(app, capsys):
    with app.app_context():
        with patch("app.services.radio_ingestion.ingest_new_clips", return_value=2):
            assert run_radio_ingestion_poll(app) == 2

    captured = capsys.readouterr()
    assert "[radio-ingestion] poll starting" in captured.out
    assert "poll complete stored=2" in captured.out


def test_ingest_new_clips_processes_clips_concurrently():
    batch = uuid.uuid4().hex
    clips = [
        {
            "filename": f"{batch}-{index}",
            "hash": f"{batch}-{index}",
            "systemId": 6204,
            "enc": "mp3",
        }
        for index in range(3)
    ]
    all_workers_started = threading.Barrier(3, timeout=5)

    def process(*args, **kwargs):
        all_workers_started.wait()
        return {"status": "processed"}

    with Flask(__name__).app_context():
        with (
            patch(
                "app.services.radio_ingestion.broadcastify_service.client.get_clips",
                return_value={"calls": clips},
            ),
            patch(
                "app.services.radio_ingestion.broadcastify_service.client.get_clip",
                return_value=VARIED_MP3,
            ),
            patch("app.services.radio_ingestion.pipeline.process_clip", side_effect=process),
            patch("app.services.radio_ingestion.clip_service.list_clips", return_value=[]),
        ):
            assert radio_ingestion.ingest_new_clips(limit=3) == 3
