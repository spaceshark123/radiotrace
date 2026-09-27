from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.routes.audio import bp as audio_bp
from app.routes.health import bp as health_bp
from app.routes.incidents import bp as incidents_bp
from app.routes.pipeline import bp as pipeline_bp
from app.routes.radio import bp as radio_bp
from app.services import radio_ingestion
from app.services import incident_service
from app.services.mongo import init_mongo
import threading
import time


def delete_old_incidents(now_timestamp: float | None = None) -> int:
    """Delete incidents whose latest recording (recordings[0]) is over retention age."""
    now = now_timestamp if now_timestamp is not None else time.time()
    cutoff = now - (Config.INCIDENT_RETENTION_MINUTES * 60)
    return incident_service.delete_incidents_with_latest_recording_before(cutoff)


def _start_incident_cleanup_scheduler(app: Flask) -> None:
    if app.config.get("TESTING") or not app.config.get("ENABLE_INCIDENT_CLEANUP", True):
        return
    interval_seconds = int(app.config["INCIDENT_CLEANUP_INTERVAL_MINUTES"]) * 60
    if interval_seconds <= 0:
        raise ValueError("INCIDENT_CLEANUP_INTERVAL_MINUTES must be greater than 0")

    def _cleanup_loop() -> None:
        while True:
            time.sleep(interval_seconds)
            with app.app_context():
                deleted_count = delete_old_incidents()
                app.logger.info("incident cleanup removed %s incidents", deleted_count)

    worker = threading.Thread(
        target=_cleanup_loop,
        name="incident-cleanup-scheduler",
        daemon=True,
    )
    worker.start()


def _start_radio_ingestion_scheduler(app: Flask) -> None:
    if app.config.get("TESTING") or not app.config.get("ENABLE_RADIO_INGESTION", True):
        return
    interval_seconds = float(app.config.get("RADIO_INGEST_INTERVAL_SECONDS", 10))
    if interval_seconds <= 0:
        raise ValueError("RADIO_INGEST_INTERVAL_SECONDS must be greater than 0")

    def _ingestion_loop() -> None:
        while True:
            with app.app_context():
                try:
                    print("[radio-ingestion] poll starting", flush=True)
                    app.logger.info("radio ingestion poll starting")
                    stored_count = radio_ingestion.ingest_new_clips(
                        limit=int(app.config.get("RADIO_INGEST_LIMIT", 5))
                    )
                    app.logger.info("radio ingestion stored %s new clips", stored_count)
                except Exception:
                    app.logger.exception("radio ingestion failed")
            time.sleep(interval_seconds)

    worker = threading.Thread(
        target=_ingestion_loop,
        name="radio-ingestion-scheduler",
        daemon=True,
    )
    worker.start()
    print(
        f"[radio-ingestion] scheduler started; interval={interval_seconds}s",
        flush=True,
    )
    app.logger.info("radio ingestion scheduler started with %.1fs interval", interval_seconds)


def create_app(test_config: dict | None = None, mongo_client=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    CORS(app)
    init_mongo(app, client=mongo_client)

    app.register_blueprint(health_bp)
    app.register_blueprint(audio_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(radio_bp)
    _start_incident_cleanup_scheduler(app)
    _start_radio_ingestion_scheduler(app)

    return app
