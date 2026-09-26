"""Incident API and health checks."""

import time

from app import delete_old_incidents
from app.services import incident_service


def test_health_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["city"] == "Atlanta"


def test_create_and_list_incidents(client):
    payload = {
        "recordings": [{"start_time": 1, "end_time": 2, "audio": "abc"}],
        "location": [
            {
                "google_maps": "Centennial Olympic Park, Atlanta, GA",
                "latitude": 33.760,
                "longitude": -84.393,
                "confidence": 0.9,
            }
        ],
        "type": [
            {
                "severity": "Minor",
                "description": "Disturbance reported",
                "confidence": 0.6,
            }
        ],
    }
    created = client.post("/api/incidents", json=payload)
    assert created.status_code == 201
    incident_id = created.get_json()["id"]

    listed = client.get("/api/incidents")
    assert listed.status_code == 200
    incidents = listed.get_json()["incidents"]
    assert any(item["id"] == incident_id for item in incidents)


def test_pipeline_endpoint_blank_skips_llm(client):
    response = client.post(
        "/api/pipeline/process",
        data={
            "file": (b"\xff\xfb" + b"\x00" * 400, "blank.mp3"),
            "start_time": "0",
            "end_time": "3",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "skipped_blank_audio"


def test_delete_old_incidents_removes_only_stale_latest_recording(app):
    now = time.time()
    with app.app_context():
        incident_service.create_incident(
            recordings=[{"start_time": now - 4000, "end_time": now - 3900, "audio": "old"}],
            location=[],
            incident_type=[],
            incident_id=1001,
        )
        incident_service.create_incident(
            recordings=[{"start_time": now - 1200, "end_time": now - 1100, "audio": "recent"}],
            location=[],
            incident_type=[],
            incident_id=1002,
        )

        deleted = delete_old_incidents(now_timestamp=now)
        assert deleted == 1

        remaining_ids = {incident["id"] for incident in incident_service.list_incidents()}
        assert remaining_ids == {1002}


def test_append_recording_keeps_latest_entry_at_first_index(app):
    with app.app_context():
        incident_service.create_incident(
            recordings=[{"start_time": 1, "end_time": 2, "audio": "first"}],
            location=[],
            incident_type=[],
            incident_id=2001,
        )

        updated = incident_service.append_recording(
            2001, {"start_time": 3, "end_time": 4, "audio": "newest"}
        )
        assert updated is not None
        assert updated["recordings"][0]["audio"] == "newest"
