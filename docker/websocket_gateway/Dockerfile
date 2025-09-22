# WebSocket Gateway Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for WebSocket Gateway
RUN pip install \
    redis \
    websockets

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 modui && chown -R modui:modui /app
USER modui

# Expose port
EXPOSE 8081

# Health check using Python instead of curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/ping', timeout=5)" || exit 1

# Start command (using working version with enhanced functionality)
CMD ["python", "src/mod_ui/services/websocket_gateway/simple_main.py"]