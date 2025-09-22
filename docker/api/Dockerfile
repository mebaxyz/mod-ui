# FastAPI API Service Dockerfile
FROM python:3.11-slim

# Install system dependencies for building the C++ library
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libasound2-dev \
    libasound2 \
    libjack-jackd2-dev \
    libjack-jackd2-0 \
    liblilv-dev \
    liblilv-0-0 \
    libserd-dev \
    libsord-dev \
    libsratom-dev \
    lv2-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install LV2 plugins for development/testing
RUN apt-get update && apt-get install -y \
    lv2-examples \
    swh-lv2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies including multipart support for forms
RUN pip install --no-cache-dir -r requirements.txt python-multipart

# Copy source code
COPY src/ src/
COPY mod/ mod/
COPY modtools/ modtools/
COPY utils/ utils/
COPY html/ html/
COPY default.pedalboard/ default.pedalboard/

# Build C++ utilities
RUN cd utils && make

# Copy the built library to modtools directory
RUN cp utils/libmod_utils.so modtools/

# Set library path for the compiled library
ENV LD_LIBRARY_PATH=/app/utils:/app/modtools:$LD_LIBRARY_PATH

# Create data directory
RUN mkdir -p /data

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/ping || exit 1

# Run the modular FastAPI application
CMD ["python", "-m", "uvicorn", "src.mod_ui.services.api.main:app", "--host", "0.0.0.0", "--port", "8888"]