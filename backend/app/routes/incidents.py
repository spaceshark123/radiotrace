from flask import Blueprint, jsonify, request

from app.services import incident_service, seed

bp = Blueprint("incidents", __name__)


@bp.get("/api/config")
def public_config():
    return jsonify(seed.city_config())


@bp.post("/api/incidents/seed")
def seed_incidents():
    incidents = seed.seed_if_empty()
    return jsonify({"incidents": incidents})


@bp.get("/api/incidents")
def list_incidents():
    return jsonify({"incidents": incident_service.list_incidents()})


@bp.get("/api/incidents/<int:incident_id>")
def get_incident(incident_id: int):
    incident = incident_service.get_incident(incident_id)
    if incident is None:
        return jsonify({"error": "incident not found"}), 404
    return jsonify(incident)


@bp.post("/api/incidents")
def create_incident():
    payload = request.get_json(silent=True) or {}
    incident = incident_service.create_incident(
        recordings=payload.get("recordings") or [],
        location=payload.get("location") or [],
        incident_type=payload.get("type") or [],
    )
    return jsonify(incident), 201
