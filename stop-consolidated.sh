#!/bin/bash
# Stop all consolidated MOD UI services

set -e

# Configuration
BASE_DIR="$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="$BASE_DIR/logs/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        
        if kill -0 $pid 2>/dev/null; then
            log "Stopping $service_name (PID: $pid)..."
            kill $pid
            
            # Wait for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 $pid 2>/dev/null; then
                    success "$service_name stopped"
                    rm -f "$pid_file"
                    return 0
                fi
                sleep 1
            done
            
            # Force kill if needed
            warn "Force killing $service_name..."
            kill -9 $pid 2>/dev/null || true
            rm -f "$pid_file"
            success "$service_name force stopped"
        else
            warn "$service_name was not running"
            rm -f "$pid_file"
        fi
    else
        warn "No PID file found for $service_name"
    fi
}

# Function to stop services by port
stop_by_port() {
    local port=$1
    local service_name=$2
    
    log "Checking for processes on port $port..."
    
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            log "Stopping process $pid on port $port ($service_name)..."
            kill $pid 2>/dev/null || true
            sleep 1
            kill -9 $pid 2>/dev/null || true
        done
        success "Stopped processes on port $port"
    fi
}

# Main stop sequence
main() {
    log "Stopping MOD UI Consolidated Services"
    
    # Stop services in reverse dependency order
    log "Stopping consolidated services..."
    
    # 1. Client Interface (web UI)
    stop_service "client_interface"
    stop_by_port 8080 "client_interface"
    
    # 2. Hardware Interface
    stop_service "hardware_interface"
    stop_by_port 8083 "hardware_interface"
    
    # 3. Audio Processing
    stop_service "audio_processing"
    stop_by_port 8082 "audio_processing"
    stop_by_port 5555 "mod-host"  # mod-host port
    
    # 4. System & Resource Management
    stop_service "system_resource_management"
    stop_by_port 8081 "system_resource_management"
    
    # Stop any remaining Python processes for our services
    log "Cleaning up any remaining service processes..."
    pkill -f "src.mod_ui.services" 2>/dev/null || true
    
    # Optional: Stop Redis if it was started by us
    if [ "$1" = "--stop-redis" ]; then
        log "Stopping Redis server..."
        redis-cli shutdown 2>/dev/null || true
        success "Redis stopped"
    fi
    
    # Clean up log files if requested
    if [ "$1" = "--clean" ] || [ "$2" = "--clean" ]; then
        log "Cleaning up log files..."
        rm -rf logs/*.pid
        rm -rf logs/*.log
        success "Log files cleaned"
    fi
    
    success "All MOD UI consolidated services stopped!"
}

# Show usage
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --stop-redis    Also stop the Redis server"
    echo "  --clean         Remove log files"
    echo "  --help, -h      Show this help message"
    echo ""
    exit 0
fi

# Run main function
main "$@"