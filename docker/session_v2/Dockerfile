FROM python:3.11-slim

LABEL maintainer="MOD Audio Platform"
LABEL description="MOD UI Session Service v2 - Pure Redis pub/sub session management"

# Install system dependencies  
RUN apt-get update && apt-get install -y \
    libasound2-dev \
    libjack-jackd2-dev \
    pkg-config \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Additional dependencies for session service v2
RUN pip install --no-cache-dir \
    pydantic>=2.5.0 \
    redis>=5.0.0 \
    aiofiles>=23.0.0

# Copy application code
COPY src/ /app/src/
COPY mod/ /app/mod/
COPY modtools/ /app/modtools/

# Copy and install ServiceBus package
COPY libraries/ /app/libraries/
RUN pip install -e /app/libraries/servicebus/

# Set Python path
ENV PYTHONPATH=/app/src:/app

# Create directories for data persistence
RUN mkdir -p /app/data/pedalboards /app/data/sessions /app/data/snapshots

# Health check using Redis connectivity
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import redis; redis.Redis(host=os.getenv('REDIS_HOST', 'redis')).ping()" || exit 1

# Default command to run session service v2
CMD ["python", "-m", "src.mod_ui.services.session_v2.main"]