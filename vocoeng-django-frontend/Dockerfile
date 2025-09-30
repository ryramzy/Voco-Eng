# Use Python 3.11 slim image for minimal size and security
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including PostgreSQL client
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
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

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port (Cloud Run will override this)
EXPOSE 8080

# Use Gunicorn for production WSGI server
# Configured for Django application with multiple workers
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--worker-class", "sync", "--timeout", "120", "--max-requests", "1000", "--access-logfile", "-", "--error-logfile", "-", "vocoeng_django.wsgi:application"]
