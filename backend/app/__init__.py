from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.routes.audio import bp as audio_bp
from app.routes.health import bp as health_bp
from app.routes.incidents import bp as incidents_bp
from app.routes.pipeline import bp as pipeline_bp
from app.routes.radio import bp as radio_bp
from app.services.mongo import init_mongo


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

    return app
