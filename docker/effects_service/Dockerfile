# Effects Service - Pure Redis pub/sub service for managing effects/plugins
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libjack-jackd2-dev \
    liblilv-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY mod/ mod/
COPY modtools/ modtools/
COPY utils/ utils/

# Copy and install ServiceBus package
COPY libraries/ libraries/
RUN pip install -e ./libraries/servicebus/

# Compile C++ utilities
RUN cd utils && make

# Set environment variables
ENV PYTHONPATH=/app/src:/app
ENV PYTHONUNBUFFERED=1

# Service runs as Redis pub/sub consumer (no HTTP port)
EXPOSE 0

# Create data directory
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import redis, os; redis.Redis(host=os.getenv('REDIS_HOST', 'redis')).ping()"

# Run the effects service
CMD ["python", "-m", "src.mod_ui.services.effects_service.main"]