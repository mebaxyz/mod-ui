#!/bin/bash
# Start System & Resource Management Service

# Set service configuration
export SYSTEM_RESOURCE_PORT=8081
export REDIS_URL="redis://localhost:6379"

# Set Python path
export PYTHONPATH="$(pwd)"

# Start the service
echo "Starting System & Resource Management Service on port $SYSTEM_RESOURCE_PORT..."
cd src/mod_ui/services/system_resource_management
python main.py