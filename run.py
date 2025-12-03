from app import create_app, socketio, db
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

# Auto-create tables if they don't exist
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    host = os.environ.get('HOST', '127.0.0.1')
    logger.info(f"Starting server on {host}:{port}")
    try:
        # Use threading mode for better Windows compatibility
        socketio.run(
            app,
            host=host,
            port=port,
            debug=True,
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        raise
