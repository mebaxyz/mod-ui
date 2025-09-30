FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libjack-jackd2-dev \
    jackd2 \
    libasound2-dev \
    liblilv-dev \
    libsndfile1-dev \
    lv2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY src/mod_ui/services/audio_processing/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy common modules
COPY src/mod_ui/common ./src/mod_ui/common/

# Copy service code
COPY src/mod_ui/services/audio_processing ./src/mod_ui/services/audio_processing/

# Copy mod-host submodule
COPY src/mod_ui/services/mod-host ./src/mod_ui/services/mod-host/

# Build mod-host
RUN cd src/mod_ui/services/mod-host && make

# Create necessary directories
RUN mkdir -p /app/data

# Expose ports
EXPOSE 8082 5555

# Set Python path
ENV PYTHONPATH=/app

# Run the service
CMD ["python", "-m", "src.mod_ui.services.audio_processing.main"]