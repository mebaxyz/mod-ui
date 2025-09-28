FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including C++ compiler for building packages and ALSA
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    libasound2-dev \
    libasound2 \
    libjack-jackd2-dev \
    libjack-jackd2-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY docker/audio_engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/mod_ui/services/audio_engine ./src/mod_ui/services/audio_engine
COPY src/mod_ui_original/modtools ./src/mod_ui_original/modtools
COPY libraries/servicebus ./libraries/servicebus

# Create symbolic link for modtools compatibility
RUN mkdir -p ./mod_ui/utils && ln -s /app/src/mod_ui_original/modtools ./mod_ui/utils/modtools

# Install servicebus library
RUN pip install -e ./libraries/servicebus

# Set Python path
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8003

# Run the audio engine service
CMD ["python", "-m", "src.mod_ui.services.audio_engine.main"]