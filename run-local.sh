#!/bin/bash

# MOD UI Local Development Runner
# This script helps run MOD UI locally for development and testing

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
PORT=${MOD_PORT:-8888}
HOST=${MOD_HOST:-127.0.0.1}
DEBUG=${MOD_DEBUG:-0}
MODE="development"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system dependencies
check_dependencies() {
    print_info "Checking system dependencies..."

    local missing_deps=()

    if ! command_exists python3; then
        missing_deps+=("python3")
    fi

    if ! command_exists pip3; then
        missing_deps+=("python3-pip")
    fi

    if ! command_exists make; then
        missing_deps+=("make")
    fi

    if ! command_exists gcc; then
        missing_deps+=("gcc")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing system dependencies: ${missing_deps[*]}"
        print_info "Install with: sudo apt-get install ${missing_deps[*]}"
        exit 1
    fi

    print_success "System dependencies OK"
}

# Function to setup virtual environment
setup_venv() {
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    fi

    print_info "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"

    # Upgrade pip
    pip install --upgrade pip > /dev/null 2>&1
}

# Function to install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."

    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found!"
        exit 1
    fi

    pip install -r requirements.txt
    print_success "Python dependencies installed"
}

# Function to build C++ utilities
build_utils() {
    print_info "Building C++ utilities..."

    if [ ! -d "utils" ]; then
        print_error "utils/ directory not found!"
        exit 1
    fi

    cd utils
    make clean > /dev/null 2>&1 || true
    make

    if [ ! -f "libmod_utils.so" ]; then
        print_error "Failed to build libmod_utils.so"
        exit 1
    fi

    cd ..
    print_success "C++ utilities built"
}

# Function to install MOD UI
install_mod_ui() {
    print_info "Installing MOD UI..."

    if [ ! -f "setup.py" ]; then
        print_error "setup.py not found!"
        exit 1
    fi

    pip install -e .
    print_success "MOD UI installed"
}

# Function to check if MOD UI is installed
check_mod_ui() {
    if ! command_exists mod-ui; then
        print_warning "MOD UI not found in PATH, installing..."
        install_mod_ui
    fi
}

# Function to run MOD UI
run_mod_ui() {
    print_info "Starting MOD UI..."
    print_info "Mode: $MODE"
    print_info "Host: $HOST"
    print_info "Port: $PORT"
    print_info "Debug: $DEBUG"
    echo

    # Set environment variables
    export MOD_PORT=$PORT
    export MOD_HOST=$HOST
    export MOD_DEBUG=$DEBUG

    # Run MOD UI
    if [ "$DEBUG" = "1" ]; then
        print_info "Running in debug mode (with logging)..."
        mod-ui 2>&1
    else
        print_info "Running in normal mode..."
        mod-ui
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
MOD UI Local Development Runner

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    -p, --port PORT     Set the port number (default: 8888)
    -H, --host HOST     Set the host address (default: 127.0.0.1)
    -d, --debug         Enable debug mode with verbose logging
    --no-venv           Skip virtual environment setup
    --no-deps           Skip dependency installation
    --no-build          Skip C++ utilities build
    --production        Run in production mode (no debug)

EXAMPLES:
    $0                    # Run with default settings
    $0 --debug           # Run with debug logging
    $0 --port 8080       # Run on port 8080
    $0 --host 0.0.0.0    # Listen on all interfaces

ACCESS URLs:
    Web Interface: http://$HOST:$PORT
    API: http://$HOST:$PORT/api/v1/

EOF
}

# Parse command line arguments
SKIP_VENV=false
SKIP_DEPS=false
SKIP_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -H|--host)
            HOST="$2"
            shift 2
            ;;
        -d|--debug)
            DEBUG=1
            shift
            ;;
        --no-venv)
            SKIP_VENV=true
            shift
            ;;
        --no-deps)
            SKIP_DEPS=true
            shift
            ;;
        --no-build)
            SKIP_BUILD=true
            shift
            ;;
        --production)
            MODE="production"
            DEBUG=0
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo
    echo "========================================"
    echo "  MOD UI Local Development Runner"
    echo "========================================"
    echo

    # Check system dependencies
    check_dependencies

    # Setup virtual environment
    if [ "$SKIP_VENV" = false ]; then
        setup_venv
    else
        print_info "Skipping virtual environment setup"
    fi

    # Install dependencies
    if [ "$SKIP_DEPS" = false ]; then
        install_dependencies
    else
        print_info "Skipping dependency installation"
    fi

    # Build C++ utilities
    if [ "$SKIP_BUILD" = false ]; then
        build_utils
    else
        print_info "Skipping C++ utilities build"
    fi

    # Check/install MOD UI
    check_mod_ui

    # Run MOD UI
    echo
    echo "========================================"
    run_mod_ui
}

# Handle script interruption
trap 'echo -e "\n${YELLOW}Script interrupted by user${NC}"; exit 1' INT

# Run main function
main "$@"