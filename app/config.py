import os

class Config:
    # --- FIX SSL ISSUE FROM RENDER ---
    raw_db_url = os.getenv("DATABASE_URL", "sqlite:///dev.db")

    # Remove ?ssl=true / ?ssl=require from Render MySQL URLs
    if raw_db_url.startswith("mysql"):
        # Strip everything after '?'
        raw_db_url = raw_db_url.split("?")[0]

    SQLALCHEMY_DATABASE_URI = raw_db_url

    # Disable SSL in SQLAlchemy for PyMySQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "ssl": {}
        }
    }

    # Other settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '15'))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '30'))
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    SOCKETIO_MESSAGE_QUEUE_URL = os.getenv('SOCKETIO_MESSAGE_QUEUE_URL')

