"""Phase 2: mocked ElevenLabs, Grok, and Google Maps pipeline."""

from unittest.mock import patch

from app.services import audio_analysis, grok_service, pipeline
from app.services import elevenlabs_service
from tests.conftest import BLANK_MP3, VARIED_MP3


def test_blank_audio_is_discarded_before_llm(app):
    with app.app_context():
        with (
            patch("app.services.pipeline.elevenlabs_service.transcribe_mp3") as stt,
            patch("app.services.pipeline.grok_service.analyze_transcript") as grok,
        ):
            result = pipeline.process_clip(BLANK_MP3, start_time=0, end_time=5)
            assert result["status"] == "discarded_blank_audio"
            stt.assert_not_called()
            grok.assert_not_called()
            assert result["incident"] is None


def test_process_clip_parses_grok_and_geocodes(app):
    grok_payload = {
        "is_relevant": True,
        "relevance_category": "violent_crime",
        "severity": "Severe",
        "description": "Car crash with 2 casualties",
        "confidence": 0.83,
        "location": "Peachtree Street",
        "location_confidence": 0.9,
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
    assert incident["category"] == "violent_crime"
    assert incident["type"][0]["confidence"] == 0.83
    assert incident["location"][0]["latitude"] == 33.759
    assert incident["location"][0]["longitude"] == -84.388
    assert incident["recordings"][0]


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
    request_body = mocked.call_args.kwargs["json"]
    response_format = request_body["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "radio_incident"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["additionalProperties"] is False
    assert parsed["severity"] == "Moderate"
    assert parsed["location"] == "Five Points"
    assert parsed["confidence"] == 0.7


def test_m4a_pipeline_passes_m4a_filename_to_transcription(app):
    with app.app_context():
        with patch(
            "app.services.pipeline.elevenlabs_service.transcribe_mp3",
            return_value="m4a transcript",
        ) as stt, patch(
            "app.services.pipeline.grok_service.analyze_transcript",
            return_value={
                "is_relevant": True,
                "relevance_category": "property_crime",
                "severity": "Minor",
                "description": "Test call",
                "confidence": 0.8,
                "location": "Peachtree Street",
                "location_confidence": 0.8,
            },
        ), patch(
            "app.services.pipeline.geocode_service.geocode_location",
            return_value={
                "google_maps": "Peachtree Street, Atlanta, GA",
                "latitude": 33.75,
                "longitude": -84.39,
            },
        ):
            result = pipeline.process_clip(VARIED_MP3, 0, 5, filename="clip.m4a")

    assert result["status"] == "processed"
    stt.assert_called_once_with(VARIED_MP3, filename="clip.m4a")


def test_irrelevant_clip_is_discarded_before_storage(app):
    with app.app_context():
        with (
            patch(
                "app.services.pipeline.elevenlabs_service.transcribe_mp3",
                return_value="routine unit acknowledgement",
            ),
            patch(
                "app.services.pipeline.grok_service.analyze_transcript",
                return_value={
                    "is_relevant": False,
                    "relevance_category": "routine_radio",
                    "severity": "Minor",
                    "description": "Routine traffic",
                    "confidence": 0.9,
                    "location": "",
                    "location_confidence": 0.0,
                },
            ),
            patch("app.services.pipeline.clip_service.create_clip") as create_clip,
        ):
            result = pipeline.process_clip(VARIED_MP3, 0, 5)

    assert result["status"] == "discarded_irrelevant"
    assert result["incident"] is None
    create_clip.assert_not_called()


def test_is_blank_audio_detects_uniform_payload():
    assert audio_analysis.is_blank_audio(BLANK_MP3) is True
    assert audio_analysis.is_blank_audio(VARIED_MP3) is False


def test_elevenlabs_options_are_multipart_fields():
    response = type("Response", (), {"ok": True, "json": lambda self: {"text": "test transcript"}})()
    with patch("app.services.elevenlabs_service.requests.post", return_value=response) as post:
        with patch.object(elevenlabs_service.Config, "ELEVENLABS_API_KEY", "test-key"):
            result = elevenlabs_service.transcribe_mp3(VARIED_MP3, filename="clip.m4a")

    assert result == "test transcript"
    request_kwargs = post.call_args.kwargs
    assert request_kwargs["data"]["language_code"] == "en"
    assert request_kwargs["data"]["keyterms"] == elevenlabs_service.keyterms
    assert "language_code" not in request_kwargs
    assert "keyterms" not in request_kwargs
