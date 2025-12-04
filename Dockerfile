# Backend Dockerfile for Deeref (Flask + Flask-SocketIO)
# Build context: backend/

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for some Python packages (e.g. psycopg2)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libpq-dev \
       gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . /app

# Expose default Flask port
EXPOSE 5000

# Recommended production command: use gunicorn with eventlet worker for Socket.IO support
# Ensure run:app is valid (this file should create the Flask/SocketIO `app` object)
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "run:app"]
