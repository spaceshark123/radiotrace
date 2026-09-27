"""Gunicorn settings so Flask logs reach Docker and one worker owns the ingest thread."""

bind = "0.0.0.0:5000"
workers = 1
worker_class = "gthread"
threads = 4
timeout = 120
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
capture_output = True
loglevel = "info"
