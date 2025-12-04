# Use Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for pymysql, MySQL, socketio)
RUN apt-get update && apt-get install -y \
    build-essential \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything
COPY . .

# Expose the port that Render requires
EXPOSE 5000

# Start Flask + SocketIO with Gunicorn
CMD ["sh", "-c", "gunicorn -k eventlet -w 1 -b 0.0.0.0:$PORT 'app:create_app()'"]


