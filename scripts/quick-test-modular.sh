#!/bin/bash

# Quick test runner for the modular FastAPI architecture
# This script runs the modular architecture directly without full Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Quick Test: MOD UI Modular FastAPI Architecture${NC}"

# Check if Python venv is available
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating Python virtual environment${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}🔄 Activating virtual environment${NC}"
source venv/bin/activate

# Install dependencies if needed
echo -e "${YELLOW}📦 Installing dependencies${NC}"
pip install -q -r requirements.txt

# Build C++ utils if needed
if [ ! -f "utils/libmod_utils.so" ]; then
    echo -e "${YELLOW}🔨 Building C++ utilities${NC}"
    cd utils && make && cd ..
fi

# Copy library to modtools if needed
if [ ! -f "modtools/libmod_utils.so" ]; then
    echo -e "${YELLOW}📋 Copying library to modtools${NC}"
    cp utils/libmod_utils.so modtools/
fi

# Set environment variables
export PYTHONPATH="$(pwd)"
export LD_LIBRARY_PATH="$(pwd)/utils:$(pwd)/modtools:$LD_LIBRARY_PATH"
export MOD_HTML_DIR="$(pwd)/html"
export MOD_DATA_DIR="$(pwd)/data"
export MOD_LOG=1
export MOD_DEBUG=1
export MOD_PORT=8888

# Create data directory if needed
mkdir -p data

echo -e "${BLUE}🎯 Testing modular architecture...${NC}"

# Test import first
python3 -c "
import sys
sys.path.append('.')
try:
    from src.mod_ui.services.api.main import app
    print('✅ Modular app imported successfully')
    routes = [route.path for route in app.routes]
    print(f'📍 Found {len(routes)} routes')
    print('Sample routes:', routes[:5])
except Exception as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Modular architecture is working!${NC}"
    echo -e "${BLUE}🚀 You can now run:${NC}"
    echo -e "   ${YELLOW}uvicorn src.mod_ui.services.api.main:app --host 0.0.0.0 --port 8888 --reload${NC}"
    echo -e "${BLUE}📍 Or test with Docker when build completes${NC}"
else
    echo -e "${RED}❌ Modular architecture test failed${NC}"
    exit 1
fi