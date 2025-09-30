#!/bin/bash
# Start Hardware Interface Service

# Set service configuration
export HARDWARE_INTERFACE_PORT=8083
export REDIS_URL="redis://localhost:6379"
export SIMULATE_HARDWARE=true  # Set to false for real hardware

# Set Python path
export PYTHONPATH="$(pwd)"

# Start the service
echo "Starting Hardware Interface Service on port $HARDWARE_INTERFACE_PORT..."
cd src/mod_ui/services/hardware_interface
python main.py