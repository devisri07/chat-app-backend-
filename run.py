from app import create_app, socketio
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

# -----------------------------------------
# ONLY create tables in local development
# NEVER in Render (Gunicorn)
# -----------------------------------------
if os.environ.get("RENDER") != "true":
    from app import db
    with app.app_context():
        db.create_all()
        logger.info("Local: Database tables created.")
else:
    logger.info("Render: Skipping db.create_all().")

# -----------------------------------------
# Local dev server (Werkzeug)
# -----------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")

    logger.info(f"Running local server on {host}:{port}")
    socketio.run(
        app,
        host=host,
        port=port,
        debug=True,
        allow_unsafe_werkzeug=True
    )
