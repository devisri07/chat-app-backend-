import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
worker_class = "sync"

timeout = 120
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"

preload_app = False
daemon = False
 

