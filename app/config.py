import os

class Config:
    # Load PostgreSQL URL from Render
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dev.db")

    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT settings
    JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '15'))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '30'))

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

    # Socket Queue (optional)
    SOCKETIO_MESSAGE_QUEUE_URL = os.getenv('SOCKETIO_MESSAGE_QUEUE_URL')
