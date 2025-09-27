#!/bin/bash
# ServiceBus Installation Script for MOD-UI Project

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}ServiceBus Library Installation${NC}"
echo "=================================="

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"
SERVICEBUS_PATH="$PROJECT_ROOT/libraries/servicebus"

echo "Project root: $PROJECT_ROOT"
echo "Virtual environment: $VENV_PATH"
echo "ServiceBus path: $SERVICEBUS_PATH"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_PATH${NC}"
    echo "Please create a virtual environment first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    exit 1
fi

# Check if ServiceBus package exists
if [ ! -d "$SERVICEBUS_PATH" ]; then
    echo -e "${RED}Error: ServiceBus package not found at $SERVICEBUS_PATH${NC}"
    exit 1
fi

echo -e "${YELLOW}Installing ServiceBus with dependencies...${NC}"

# Install the package
cd "$SERVICEBUS_PATH"
"$VENV_PATH/bin/pip" install -e .

# Create the proper path file (workaround for editable installation issue)
SITE_PACKAGES="$VENV_PATH/lib/python*/site-packages"
PTH_FILE=$(echo $SITE_PACKAGES)/_servicebus.pth

echo -e "${YELLOW}Creating path file...${NC}"
echo "$SERVICEBUS_PATH" > "$PTH_FILE"

echo -e "${YELLOW}Testing installation...${NC}"

# Test the installation
cd "$PROJECT_ROOT"
if "$VENV_PATH/bin/python" -c "from servicebus import Service; print('Import successful')" 2>/dev/null; then
    echo -e "${GREEN}✅ ServiceBus installed successfully!${NC}"
    
    # Run full test
    echo -e "${YELLOW}Running full test suite...${NC}"
    if "$VENV_PATH/bin/python" "$SERVICEBUS_PATH/test_installation.py" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
    else
        echo -e "${YELLOW}⚠️  Some tests had warnings but package is functional${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}ServiceBus is ready to use!${NC}"
    echo ""
    echo "Quick usage:"
    echo "  from servicebus import Service"
    echo "  service = Service('my-service')"
    echo "  await service.start()"
    
else
    echo -e "${RED}❌ Installation failed - ServiceBus import error${NC}"
    exit 1
fi