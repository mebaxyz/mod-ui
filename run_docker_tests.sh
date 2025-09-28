#!/bin/bash
set -e

echo "🚀 MOD UI Docker Test Suite Runner"
echo "=================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if containers are running
echo "📋 Checking Docker containers..."
cd "$(dirname "$0")"

if ! docker compose -f docker/docker-compose.dev.yml ps --services | head -1 > /dev/null 2>&1; then
    echo "⚠️  Docker containers may not be running. Starting them..."
    docker compose -f docker/docker-compose.dev.yml up -d
    echo "⏳ Waiting for services to start..."
    sleep 15
fi

echo "✅ Docker environment ready"
echo ""

# Run the comprehensive test suite
echo "🧪 Running comprehensive Docker functionality tests..."
echo ""

# Install test dependencies if needed
if ! python -c "import requests, redis" > /dev/null 2>&1; then
    echo "📦 Installing test dependencies..."
    pip install -r requirements-testing.txt
fi

# Run the tests
echo "🏃‍♂️ Executing test suite..."
echo ""

# Run with different levels of verbosity based on argument
if [[ "$1" == "--verbose" || "$1" == "-v" ]]; then
    python test_docker_functionality.py -v
elif [[ "$1" == "--summary" || "$1" == "-s" ]]; then
    pytest test_docker_functionality.py::test_comprehensive_functionality_summary -v -s
else
    python test_docker_functionality.py
fi

echo ""
echo "🎯 Test Results:"
echo "   - All curl-equivalent HTTP tests included"  
echo "   - Redis connectivity and pub/sub verified"
echo "   - ServiceBus communication tested"
echo "   - Project reorganization validated"
echo ""
echo "✨ MOD UI Docker environment testing complete!"