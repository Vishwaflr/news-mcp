# Base stage for common dependencies
FROM python:3.12-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage with hot-reload support
FROM base AS development

# Copy application code
COPY . .

# Keep running as root for development (easier file permissions)
# Development command
CMD ["python", "-B", "app/worker/analysis_worker.py", "--verbose"]

# Production stage with security hardening
FROM base AS production

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser && \
    chown -R appuser:appuser /app

USER appuser

# Start command
CMD ["python", "-B", "app/worker/analysis_worker.py", "--verbose"]