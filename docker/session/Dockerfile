# Session Service Dockerfile

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libjack-jackd2-dev \
    liblilv-dev \
    libserd-dev \
    libsord-dev \
    libsratom-dev \
    lv2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY mod/ mod/
COPY modtools/ modtools/
COPY utils/ utils/

# Build C++ utilities
RUN make -C utils

# Create data directory
RUN mkdir -p /data

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5555

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.connect(('localhost', 5555)); s.close()" || exit 1

# Run the session service
CMD ["python", "src/mod_ui/services/session/main.py"]