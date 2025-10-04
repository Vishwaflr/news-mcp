# Base stage for common dependencies
FROM python:3.12-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage with hot-reload support
FROM base AS development

# Copy application code
COPY . .

# Keep running as root for development (easier file permissions)
EXPOSE 8000

# Development command (will be overridden by docker-compose.dev.yml)
CMD ["uvicorn", "app.web.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage with security hardening
FROM base AS production

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start command
CMD ["uvicorn", "app.web.main:app", "--host", "0.0.0.0", "--port", "8000"]