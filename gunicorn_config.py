"""Gunicorn configuration for production deployment."""
import os
import multiprocessing

# Server socket
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:8000')
backlog = 2048

# Worker processes (use 1 for WebSocket, or 2-4 with message queue)
workers = int(os.getenv('GUNICORN_WORKERS', '1'))
worker_class = 'eventlet'
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'deeref-chat'

# Environment
preload_app = False
daemon = False
