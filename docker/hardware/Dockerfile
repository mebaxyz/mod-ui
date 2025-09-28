# Hardware Service Dockerfile
# Handles MOD device hardware interfaces with privileged access

FROM python:3.11-slim

# Install system dependencies for hardware access
RUN apt-get update && apt-get install -y \
    # Audio system dependencies
    libjack-jackd2-dev \
    libjack-jackd2-0 \
    jackd2 \
    libasound2-dev \
    libasound2 \
    alsa-utils \
    # LV2 and audio plugin support  
    liblilv-dev \
    liblilv-0-0 \
    libserd-dev \
    libsord-dev \
    libsratom-dev \
    lv2-dev \
    # Serial communication and hardware access
    udev \
    # System utilities
    curl \
    procps \
    # Build tools
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy minimal requirements for hardware service
COPY requirements-hardware.txt .
RUN pip install --no-cache-dir -r requirements-hardware.txt

# Copy source code
COPY src/ ./src/
COPY src/mod_ui_original ./mod
COPY config ./config
COPY utils/ ./utils/

# Build C++ utilities for JACK integration
RUN make -C utils

# Create hardware user with audio/dialout groups for device access
RUN groupadd -r hardware && useradd -r -g hardware -G audio,dialout hardware

# Set up proper permissions for hardware access
RUN chown -R hardware:hardware /app

# Expose hardware service port
EXPOSE 8003

# Switch to hardware user (will be overridden by privileged mode when needed)
USER hardware

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Set Python path
ENV PYTHONPATH=/app

# Run the hardware service
CMD ["python", "-m", "mod_ui.services.hardware.main"]