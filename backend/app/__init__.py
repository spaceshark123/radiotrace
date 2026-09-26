import os

from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    mongo_client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongo:27017"))
    mongo_database = mongo_client[os.getenv("MONGO_DATABASE", "radiotrace")]

    @app.get("/api/health")
    def health_check():
        try:
            mongo_client.admin.command("ping")
        except Exception:
            return jsonify({"status": "degraded", "database": "unavailable"}), 503

        return jsonify({"status": "ok", "database": mongo_database.name})

    return app