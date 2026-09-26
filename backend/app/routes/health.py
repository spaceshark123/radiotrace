from flask import Blueprint, jsonify

from app.config import Config
from app.services.mongo import ping_database

bp = Blueprint("health", __name__)


@bp.get("/api/health")
def health_check():
    if not ping_database():
        return jsonify({"status": "degraded", "database": "unavailable"}), 503
    return jsonify(
        {
            "status": "ok",
            "database": Config.MONGO_DATABASE,
            "city": Config.CITY,
        }
    )
