# Configuration Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for Configuration Service v2 (Redis pub/sub)
RUN pip install --no-cache-dir \
    redis==5.0.1 \
    pydantic==2.5.0

# Copy application code
COPY src/ /app/src/
COPY mod/ /app/mod/

# Set Python path
ENV PYTHONPATH=/app/src:/app

# Create non-root user
RUN useradd -m -u 1000 modui && chown -R modui:modui /app
USER modui

# Expose port (not used for Redis-only service, but kept for compatibility)
EXPOSE 8083

# Health check using Redis connectivity instead of HTTP
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import redis; r=redis.Redis(host='redis', port=6379); r.ping()" || exit 1

# Start command
CMD ["python", "-m", "src.mod_ui.services.config_service.main"]