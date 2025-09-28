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
    libasound2-dev \
    libasound2 \
    libjack-jackd2-0 \
    liblilv-0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY src/mod_ui_original mod/
COPY src/mod_ui_original/modtools modtools/
COPY config config/
COPY utils/ utils/

# Build C++ utilities
RUN make -C utils

# Copy the built library to modtools directory
RUN cp utils/libmod_utils.so modtools/

# Set library path for the compiled library
ENV LD_LIBRARY_PATH=/app/utils:/app/modtools:$LD_LIBRARY_PATH

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