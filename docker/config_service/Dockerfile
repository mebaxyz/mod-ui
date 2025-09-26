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

# Install additional dependencies for Configuration Service
RUN pip install \
    fastapi \
    uvicorn[standard]

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 modui && chown -R modui:modui /app
USER modui

# Expose port
EXPOSE 8083

# Health check using curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8083/health || exit 1

# Start command
CMD ["python", "-m", "src.mod_ui.services.config_service.main"]