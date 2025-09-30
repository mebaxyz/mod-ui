#!/bin/bash
# Start Audio Processing Service

# Set service configuration
export AUDIO_PROCESSING_PORT=8082
export REDIS_URL="redis://localhost:6379"
export JACK_SAMPLE_RATE=48000
export JACK_BUFFER_SIZE=256

# Set Python path
export PYTHONPATH="$(pwd)"

# Build mod-host if needed
if [ ! -f "src/mod_ui/services/mod-host/mod-host" ]; then
    echo "Building mod-host..."
    cd src/mod_ui/services/mod-host
    make
    cd ../../../../
fi

# Start the service
echo "Starting Audio Processing Service on port $AUDIO_PROCESSING_PORT..."
cd src/mod_ui/services/audio_processing
python main.py