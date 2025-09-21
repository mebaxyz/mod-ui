#!/bin/bash

# FastAPI Migration Development Setup Script
# This script sets up the development environment for the MOD UI FastAPI migration

set -e

echo "🚀 Setting up MOD UI FastAPI Migration Development Environment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [[ ! -f "requirements.txt" || ! -d "mod" ]]; then
    print_error "Please run this script from the MOD UI project root directory"
    exit 1
fi

# Check for Python 3.8+
print_status "Checking Python version..."
if ! python3 --version | grep -E "Python 3\.(8|9|10|11|12)" > /dev/null; then
    print_error "Python 3.8+ is required. Please install a compatible Python version."
    exit 1
fi
print_success "Python version OK"

# Check for Docker
print_status "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_warning "Docker not found. Please install Docker for containerized development."
else
    print_success "Docker found"
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_warning "Docker Compose not found. Please install Docker Compose."
else
    print_success "Docker Compose found"
fi

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Install additional FastAPI dependencies
print_status "Installing FastAPI dependencies..."
pip install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    websockets==12.0 \
    python-multipart==0.0.6 \
    aiofiles==23.2.1 \
    psutil==5.9.6

print_success "Python dependencies installed"

# Build C++ utilities
print_status "Building C++ utilities..."
if [[ -d "utils" && -f "utils/Makefile" ]]; then
    cd utils
    make clean
    make
    cd ..
    print_success "C++ utilities built"
else
    print_warning "C++ utilities directory not found or no Makefile"
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs
mkdir -p data
mkdir -p tmp
print_success "Directories created"

# Set up environment variables
print_status "Setting up environment variables..."
if [[ ! -f ".env" ]]; then
    cat > .env << EOF
# MOD UI FastAPI Migration Environment Variables

# Development mode
MOD_DEV=1
MOD_LOG_LEVEL=DEBUG

# Data directories
MOD_DATA_DIR=./data
MOD_LOG_DIR=./logs

# Server configuration
MOD_DEVICE_WEBSERVER_PORT=8888
MOD_SESSION_PORT=5555
MOD_HARDWARE_PORT=5556

# Database (future use)
MOD_DATABASE_URL=sqlite:///./data/mod_ui.db

# JACK Audio (development)
JACK_DEFAULT_SERVER=default

# Hardware simulation (for development without MOD device)
MOD_SIMULATE_HARDWARE=1
EOF
    print_success "Environment file created"
else
    print_status "Environment file already exists"
fi

# Create VS Code configuration for debugging
print_status "Setting up VS Code debugging configuration..."
mkdir -p .vscode

cat > .vscode/launch.json << EOF
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI API Service",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "src.mod_ui.services.api.main:app",
                "--host", "0.0.0.0",
                "--port", "8888",
                "--reload"
            ],
            "console": "integratedTerminal",
            "envFile": "\${workspaceFolder}/.env",
            "cwd": "\${workspaceFolder}"
        },
        {
            "name": "Session Service",
            "type": "python",
            "request": "launch",
            "program": "src/mod_ui/services/session/main.py",
            "console": "integratedTerminal",
            "envFile": "\${workspaceFolder}/.env",
            "cwd": "\${workspaceFolder}"
        },
        {
            "name": "Hardware Service",
            "type": "python",
            "request": "launch",
            "program": "src/mod_ui/services/hardware/main.py",
            "console": "integratedTerminal",
            "envFile": "\${workspaceFolder}/.env",
            "cwd": "\${workspaceFolder}"
        },
        {
            "name": "Legacy Tornado Server",
            "type": "python",
            "request": "launch",
            "program": "server.py",
            "console": "integratedTerminal",
            "envFile": "\${workspaceFolder}/.env",
            "cwd": "\${workspaceFolder}"
        }
    ]
}
EOF

cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/venv": true,
        "**/node_modules": true
    }
}
EOF

print_success "VS Code configuration created"

# Create development scripts
print_status "Creating development scripts..."

cat > scripts/dev-api.sh << 'EOF'
#!/bin/bash
# Start the FastAPI development server

source venv/bin/activate
export PYTHONPATH=$PWD

echo "🚀 Starting FastAPI API Service..."
uvicorn src.mod_ui.services.api.main:app \
    --host 0.0.0.0 \
    --port 8888 \
    --reload \
    --reload-dir src/ \
    --log-level debug
EOF

cat > scripts/dev-session.sh << 'EOF'
#!/bin/bash
# Start the Session Service

source venv/bin/activate
export PYTHONPATH=$PWD

echo "🔧 Starting Session Service..."
python src/mod_ui/services/session/main.py
EOF

cat > scripts/dev-hardware.sh << 'EOF'
#!/bin/bash
# Start the Hardware Service

source venv/bin/activate
export PYTHONPATH=$PWD

echo "🔌 Starting Hardware Service..."
python src/mod_ui/services/hardware/main.py
EOF

cat > scripts/dev-all.sh << 'EOF'
#!/bin/bash
# Start all services using Docker Compose

echo "🐳 Starting all services with Docker Compose..."
docker-compose -f docker/docker-compose.dev.yml up --build
EOF

cat > scripts/dev-legacy.sh << 'EOF'
#!/bin/bash
# Start the legacy Tornado server for comparison

source venv/bin/activate
export PYTHONPATH=$PWD

echo "⚡ Starting Legacy Tornado Server..."
python server.py
EOF

# Make scripts executable
chmod +x scripts/*.sh

print_success "Development scripts created"

# Create README for migration
print_status "Creating migration documentation..."

cat > MIGRATION.md << 'EOF'
# MOD UI FastAPI Migration

This document describes the migration from the legacy Tornado monolithic application to a modern FastAPI microservices architecture.

## Architecture Overview

### Legacy Architecture (Tornado)
- Single monolithic application (`server.py`)
- 2500+ lines in `mod/webserver.py`
- Synchronous request handling
- Tightly coupled components

### New Architecture (FastAPI)
- Microservices architecture
- Async/await throughout
- Type hints and validation
- Automatic API documentation
- Docker containerization

## Services

### API Service (`src/mod_ui/services/api/main.py`)
- FastAPI web application
- REST API endpoints
- WebSocket communication
- Replaces `mod/webserver.py`

### Session Service (`src/mod_ui/services/session/main.py`)
- Session state management
- Coordinates between services
- Replaces parts of `mod/session.py`

### Hardware Service (`src/mod_ui/services/hardware/main.py`)
- MOD device communication
- HMI protocol handling
- Control Chain management
- Replaces hardware parts of legacy code

## Development

### Running Services Individually

```bash
# API Service
./scripts/dev-api.sh

# Session Service
./scripts/dev-session.sh

# Hardware Service
./scripts/dev-hardware.sh

# Legacy server (for comparison)
./scripts/dev-legacy.sh
```

### Running All Services
```bash
# Docker Compose
./scripts/dev-all.sh
```

### VS Code Debugging

Use the provided launch configurations to debug individual services.

## Migration Progress

- [x] Project structure setup
- [x] FastAPI application skeleton
- [x] Pydantic models
- [x] Docker configuration
- [x] Session service
- [x] Hardware service
- [ ] Complete endpoint migration
- [ ] WebSocket implementation
- [ ] Testing
- [ ] Documentation

## Testing

The migration maintains backward compatibility during development. You can run both the legacy and new systems side by side for comparison.

## Deployment

The new architecture supports:
- Docker containerization
- Kubernetes deployment
- Load balancing
- Horizontal scaling
EOF

print_success "Migration documentation created"

# Print final status
echo ""
print_success "🎉 MOD UI FastAPI Migration development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Start the FastAPI API service: ./scripts/dev-api.sh"
echo "  3. Open another terminal and start the session service: ./scripts/dev-session.sh"
echo "  4. Open VS Code and use the debugging configurations"
echo "  5. Read MIGRATION.md for detailed information"
echo ""
echo "Services will be available at:"
echo "  - FastAPI API: http://localhost:8888"
echo "  - FastAPI Docs: http://localhost:8888/docs"
echo "  - Legacy server: http://localhost:8888 (when running)"
echo ""
print_status "Happy coding! 🚀"