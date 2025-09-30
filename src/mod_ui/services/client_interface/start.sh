#!/bin/bash
# Start Client Interface Service

# Set service configuration
export CLIENT_INTERFACE_PORT=8080
export REDIS_URL="redis://localhost:6379"

# Set Python path
export PYTHONPATH="$(pwd)"

# Start the service
echo "Starting Client Interface Service on port $CLIENT_INTERFACE_PORT..."
cd src/mod_ui/services/client_interface
python main.py