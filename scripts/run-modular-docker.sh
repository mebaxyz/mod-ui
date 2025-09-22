#!/bin/bash

# Run MOD UI Development Environment with Docker
# This script sets up and runs the FastAPI development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Starting MOD UI Development Environment${NC}"

# Check if Docker and Docker Compose are available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed or not in PATH${NC}"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not available${NC}"
    exit 1
fi

# Create Docker network if it doesn't exist
if ! docker network ls | grep -q mod-network; then
    echo -e "${YELLOW}📡 Creating Docker network 'mod-network'${NC}"
    docker network create mod-network
fi

# Build the C++ utilities first (they need to be available for the Docker build)
echo -e "${YELLOW}🔨 Building C++ utilities${NC}"
cd utils && make clean && make && cd ..

# Stop any existing containers
echo -e "${YELLOW}🛑 Stopping existing containers${NC}"
docker compose -f docker/docker-compose.dev.yml down

# Build and start the modular architecture
echo -e "${YELLOW}🏗️  Building modular containers${NC}"
docker compose -f docker/docker-compose.dev.yml build --no-cache

echo -e "${YELLOW}🚀 Starting modular containers${NC}"
docker compose -f docker/docker-compose.dev.yml up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 10

# Check service health
echo -e "${BLUE}🩺 Checking service health${NC}"

# Check API service
if curl -f http://localhost:8888/ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API Service is healthy at http://localhost:8888${NC}"
else
    echo -e "${RED}❌ API Service is not responding${NC}"
fi

# Check Web UI
if curl -f http://localhost:8080 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Web UI is healthy at http://localhost:8080${NC}"
else
    echo -e "${RED}❌ Web UI is not responding${NC}"
fi

echo -e "${BLUE}📊 Container Status:${NC}"
docker compose -f docker/docker-compose.dev.yml ps

echo -e "${GREEN}🎉 MOD UI Development Environment is running!${NC}"
echo -e "${BLUE}📍 Available endpoints:${NC}"
echo -e "   • Web UI: ${YELLOW}http://localhost${NC} (port 80)"
echo -e "   • API: ${YELLOW}http://localhost:8888${NC}"
echo -e "   • API Health: ${YELLOW}http://localhost:8888/ping${NC}"
echo -e "   • API Docs: ${YELLOW}http://localhost:8888/docs${NC}"
echo -e "   • System Info: ${YELLOW}http://localhost:8888/system/info${NC}"
echo -e "   • Effect List: ${YELLOW}http://localhost:8888/effect/list${NC}"

echo -e "${BLUE}🔍 To view logs:${NC}"
echo -e "   docker compose -f docker/docker-compose.dev.yml logs -f"

echo -e "${BLUE}🛑 To stop:${NC}"  
echo -e "   docker compose -f docker/docker-compose.dev.yml down"