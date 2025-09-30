#!/bin/bash
# Start all consolidated MOD UI services

set -e

# Configuration
REDIS_PORT=6379
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

# Check if Redis is running
check_redis() {
    log "Checking Redis availability..."
    if ! command -v redis-cli &> /dev/null; then
        error "redis-cli not found. Please install Redis."
        exit 1
    fi
    
    if ! redis-cli -p $REDIS_PORT ping &> /dev/null; then
        warn "Redis not running on port $REDIS_PORT"
        log "Starting Redis server..."
        redis-server --daemonize yes --port $REDIS_PORT
        sleep 2
        
        if ! redis-cli -p $REDIS_PORT ping &> /dev/null; then
            error "Failed to start Redis server"
            exit 1
        fi
    fi
    
    success "Redis is available on port $REDIS_PORT"
}

# Function to start a service
start_service() {
    local service_name=$1
    local service_dir=$2
    local port=$3
    
    log "Starting $service_name service on port $port..."
    
    cd "$BASE_DIR/$service_dir"
    
    # Create log directory
    mkdir -p "$BASE_DIR/logs"
    
    # Start service in background
    nohup ./start.sh > "$BASE_DIR/logs/${service_name}.log" 2>&1 &
    local pid=$!
    
    # Wait a moment for startup
    sleep 3
    
    # Check if service is still running
    if kill -0 $pid 2>/dev/null; then
        success "$service_name started successfully (PID: $pid)"
        echo $pid > "$BASE_DIR/logs/${service_name}.pid"
    else
        error "Failed to start $service_name"
        return 1
    fi
    
    cd "$BASE_DIR"
}

# Function to check service health
check_service_health() {
    local service_name=$1
    local port=$2
    
    log "Checking $service_name health..."
    
    # Wait for service to be ready
    for i in {1..30}; do
        if curl -s "http://localhost:$port/health" &> /dev/null; then
            success "$service_name is healthy"
            return 0
        fi
        sleep 1
    done
    
    warn "$service_name health check failed after 30 seconds"
    return 1
}

# Main startup sequence
main() {
    log "Starting MOD UI Consolidated Services"
    
    # Check prerequisites
    check_redis
    
    # Create necessary directories
    mkdir -p data/pedalboards data/keys data/pedalboard-tmp-data logs
    
    # Start services in dependency order
    log "Starting consolidated services..."
    
    # 1. System & Resource Management (foundational)
    start_service "system_resource_management" "src/mod_ui/services/system_resource_management" 8081
    
    # 2. Audio Processing (core functionality)
    start_service "audio_processing" "src/mod_ui/services/audio_processing" 8082
    
    # 3. Hardware Interface (physical controls)
    start_service "hardware_interface" "src/mod_ui/services/hardware_interface" 8083
    
    # 4. Client Interface (web UI - depends on others)
    start_service "client_interface" "src/mod_ui/services/client_interface" 8080
    
    log "Waiting for services to fully initialize..."
    sleep 5
    
    # Health checks
    log "Performing health checks..."
    check_service_health "system_resource_management" 8081
    check_service_health "audio_processing" 8082
    check_service_health "hardware_interface" 8083
    check_service_health "client_interface" 8080
    
    # Show status
    log "Service Status:"
    echo "=================================="
    echo "🌐 Client Interface:      http://localhost:8080"
    echo "🖥️  System Management:    http://localhost:8081"
    echo "🎵 Audio Processing:      http://localhost:8082"
    echo "🎛️  Hardware Interface:   http://localhost:8083"
    echo "📊 Redis:                 localhost:6379"
    echo "=================================="
    echo ""
    
    success "All MOD UI consolidated services started successfully!"
    
    log "Main UI available at: http://localhost:8080"
    log "Service logs are in: $BASE_DIR/logs/"
    log ""
    log "To stop all services, run: ./stop-consolidated.sh"
}

# Trap to cleanup on exit
cleanup() {
    log "Cleaning up..."
    # This will be handled by the stop script
}

trap cleanup EXIT

# Run main function
main "$@"