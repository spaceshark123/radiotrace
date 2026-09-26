"""Phase 2: mocked ElevenLabs, Grok, and Google Maps pipeline."""

from unittest.mock import patch

from app.services import audio_analysis, grok_service, pipeline
from tests.conftest import BLANK_MP3, VARIED_MP3


def test_blank_audio_skips_llm(app):
    with app.app_context():
        with (
            patch("app.services.pipeline.elevenlabs_service.transcribe_mp3") as stt,
            patch("app.services.pipeline.grok_service.analyze_transcript") as grok,
        ):
            result = pipeline.process_clip(BLANK_MP3, start_time=0, end_time=5)
            assert result["status"] == "skipped_blank_audio"
            stt.assert_not_called()
            grok.assert_not_called()
            assert result["incident"]["recordings"][0]["audio"]


def test_process_clip_parses_grok_and_geocodes(app):
    grok_payload = {
        "severity": "Severe",
        "description": "Car crash with 2 casualties",
        "confidence": 0.83,
        "location": "Peachtree Street",
    }
    geo_payload = {
        "google_maps": "Peachtree St NE, Atlanta, GA",
        "latitude": 33.759,
        "longitude": -84.388,
    }

    with app.app_context():
        with (
            patch(
                "app.services.pipeline.elevenlabs_service.transcribe_mp3",
                return_value="engine 12 on scene peachtree street two injured",
            ),
            patch(
                "app.services.pipeline.grok_service.analyze_transcript",
                return_value=grok_payload,
            ),
            patch(
                "app.services.pipeline.geocode_service.geocode_location",
                return_value=geo_payload,
            ),
        ):
            result = pipeline.process_clip(VARIED_MP3, start_time=10, end_time=40)

    assert result["status"] == "processed"
    incident = result["incident"]
    assert incident["type"][0]["severity"] == "Severe"
    assert incident["type"][0]["description"] == "Car crash with 2 casualties"
    assert incident["type"][0]["confidence"] == 0.83
    assert incident["location"][0]["latitude"] == 33.759
    assert incident["location"][0]["longitude"] == -84.388
    assert incident["recordings"][0]["start_time"] == 10


def test_grok_json_extraction():
    sample = {
        "choices": [
            {
                "message": {
                    "content": '```json\n{"severity":"Moderate","description":"Theft in progress","confidence":0.7,"location":"Five Points"}\n```'
                }
            }
        ]
    }
    with patch("app.services.grok_service.requests.post") as mocked:
        mocked.return_value.ok = True
        mocked.return_value.json.return_value = sample
        with patch.object(grok_service.Config, "XAI_API_KEY", "test-key"):
            parsed = grok_service.analyze_transcript("units on scene at five points")
    assert parsed["severity"] == "Moderate"
    assert parsed["location"] == "Five Points"
    assert parsed["confidence"] == 0.7


def test_is_blank_audio_detects_uniform_payload():
    assert audio_analysis.is_blank_audio(BLANK_MP3) is True
    assert audio_analysis.is_blank_audio(VARIED_MP3) is False
