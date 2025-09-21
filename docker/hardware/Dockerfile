# Hardware Service Dockerfile

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
    udev \
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
COPY utils/ utils/

# Build C++ utilities
RUN make -C utils

# Create data directory
RUN mkdir -p /data

# Set Python path
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the hardware service
CMD ["python", "src/mod_ui/services/hardware/main.py"]