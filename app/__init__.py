
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

# Windows-safe socket.io mode
socketio = SocketIO(
    async_mode="threading",
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25
)


def create_app(config_object=None):
    app = Flask(__name__, static_folder=None)

    # Load config
    if config_object:
        app.config.from_object(config_object)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///dev.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'dev-secret')
        app.config['JWT_ALGORITHM'] = os.environ.get('JWT_ALGORITHM', 'HS256')
        app.config['ACCESS_TOKEN_EXPIRE_MINUTES'] = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '15'))
        app.config['REFRESH_TOKEN_EXPIRE_DAYS'] = int(os.environ.get('REFRESH_TOKEN_EXPIRE_DAYS', '30'))

    db.init_app(app)
    migrate.init_app(app, db)

    # FULL FIXED CORS (WORKS WITH VITE FRONTEND)
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True
    )

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.channels import channels_bp
    try:
        from .routes.messages import messages_bp
    except Exception:
        messages_bp = None
    from .routes.health import health_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(channels_bp, url_prefix='/api/channels')
    if messages_bp:
        app.register_blueprint(messages_bp, url_prefix='/api/channels')
    app.register_blueprint(health_bp, url_prefix='/')

    # Initialize socket.io
    socketio.init_app(app)

    # Load socket handlers
    try:
        from . import socketio_events  # noqa
    except Exception as e:
        logging.warning(f"SocketIO events import failed: {e}")

    return app
