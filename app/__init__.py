from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_cors import CORS
import os
import logging

logging.basicConfig(level=logging.DEBUG)

db = SQLAlchemy()
migrate = Migrate()

socketio = SocketIO(
    async_mode="threading",  # eventlet mandatory for Gunicorn + SocketIO
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25
)


def create_app():
    app = Flask(__name__, static_folder=None)

    # --------------------------------------
    # Load Config.py ALWAYS (Render + Local)
    # --------------------------------------
    from app.config import Config

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True
    )

    # Blueprints
    from .routes.auth import auth_bp
    from .routes.channels import channels_bp
    from .routes.health import health_bp
    try:
        from .routes.messages import messages_bp
    except:
        messages_bp = None

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(channels_bp, url_prefix='/api/channels')
    if messages_bp:
        app.register_blueprint(messages_bp, url_prefix='/api/channels')
    app.register_blueprint(health_bp, url_prefix='/')

    # Socket.IO
    socketio.init_app(app, cors_allowed_origins="*")

    # Socket handlers
    try:
        from . import socketio_events
    except Exception as e:
        logging.warning(f"SocketIO events import failed: {e}")

    return app
