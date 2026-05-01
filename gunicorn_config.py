# Gunicorn configuration file for Resume Studio
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# Worker processes
workers = 2  # Good for small to medium traffic
worker_class = "sync"
threads = 2

# Timeout settings (CRITICAL for email sending)
timeout = 120  # 2 minutes - prevents worker timeout during email send
graceful_timeout = 120
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True

# Process naming
proc_name = "resume_studio"

# Performance
preload_app = True
max_requests = 1000
max_requests_jitter = 50

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190