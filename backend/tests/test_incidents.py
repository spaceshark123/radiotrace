"""Incident API and health checks."""

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
