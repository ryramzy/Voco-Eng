# Use Python 3.11 slim image for minimal size and security
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port (Cloud Run will override this)
EXPOSE 8080

# Use Gunicorn for production WSGI server
# --bind 0.0.0.0:8080: Listen on all interfaces for Cloud Run
# --workers 1: Single worker for serverless (Cloud Run handles scaling)
# --worker-class sync: Synchronous workers suitable for I/O-bound Flask app
# --timeout 120: 2-minute timeout for long-running requests
# --max-requests 1000: Restart worker after 1000 requests to prevent memory leaks
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--worker-class", "sync", "--timeout", "120", "--max-requests", "1000", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
