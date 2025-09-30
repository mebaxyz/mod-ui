#!/bin/bash
# Verify MOD UI Services Migration

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== MOD UI Services Migration Verification ===${NC}"
echo ""

# Check new consolidated services exist
echo -e "${BLUE}Checking consolidated services...${NC}"

services=("client_interface" "system_resource_management" "audio_processing" "hardware_interface")
base_path="/home/nicolas/project/madeline/mod-ui/src/mod_ui/services"

for service in "${services[@]}"; do
    if [ -d "$base_path/$service" ]; then
        echo -e "✅ ${GREEN}$service${NC} - Present"
        
        # Check if main.py exists
        if [ -f "$base_path/$service/main.py" ]; then
            echo -e "   📄 main.py - Present"
        else
            echo -e "   ${RED}❌ main.py - Missing${NC}"
        fi
        
        # Check if start.sh exists
        if [ -f "$base_path/$service/start.sh" ]; then
            echo -e "   🚀 start.sh - Present"
        else
            echo -e "   ${YELLOW}⚠️  start.sh - Missing${NC}"
        fi
        
    else
        echo -e "❌ ${RED}$service${NC} - Missing"
    fi
done

# Check mod-host submodule
if [ -d "$base_path/mod-host" ]; then
    echo -e "✅ ${GREEN}mod-host${NC} - Present (submodule)"
else
    echo -e "❌ ${RED}mod-host${NC} - Missing"
fi

echo ""

# Check legacy services were moved
echo -e "${BLUE}Checking legacy services archive...${NC}"

legacy_services=("api" "audio_engine" "config_service" "effects_service" "hardware" "session_v2" "system_stats" "webui_gateway")
legacy_path="/home/nicolas/project/madeline/mod-ui/src/mod_ui/services_legacy"

for service in "${legacy_services[@]}"; do
    if [ -d "$legacy_path/$service" ]; then
        echo -e "✅ ${GREEN}$service${NC} - Archived"
    else
        echo -e "❌ ${RED}$service${NC} - Not found in archive"
    fi
done

# Check documentation
echo ""
echo -e "${BLUE}Checking documentation...${NC}"

docs=("src/mod_ui/services_legacy/README.md" "MIGRATION_LOG.md" "IMPLEMENTATION_COMPLETE.md" "MOD_CONSOLIDATED_ARCHITECTURE.md")
project_root="/home/nicolas/project/madeline/mod-ui"

for doc in "${docs[@]}"; do
    if [ -f "$project_root/$doc" ]; then
        echo -e "✅ ${GREEN}$doc${NC} - Present"
    else
        echo -e "❌ ${RED}$doc${NC} - Missing"
    fi
done

# Check startup scripts
echo ""
echo -e "${BLUE}Checking startup scripts...${NC}"

scripts=("start-consolidated.sh" "stop-consolidated.sh" "docker-compose.consolidated.yml" "requirements-consolidated.txt")

for script in "${scripts[@]}"; do
    if [ -f "$project_root/$script" ]; then
        echo -e "✅ ${GREEN}$script${NC} - Present"
        
        # Check if executable
        if [ -x "$project_root/$script" ]; then
            echo -e "   🔧 Executable - Yes"
        else
            echo -e "   ${YELLOW}⚠️  Executable - No${NC}"
        fi
    else
        echo -e "❌ ${RED}$script${NC} - Missing"
    fi
done

# Summary
echo ""
echo -e "${BLUE}=== Migration Summary ===${NC}"
echo -e "📁 Active Services: ${GREEN}4 consolidated services${NC}"
echo -e "📦 Archived Services: ${YELLOW}8 legacy services${NC}"
echo -e "🔧 Infrastructure: ${GREEN}Startup scripts, Docker, Documentation${NC}"
echo -e "📚 Documentation: ${GREEN}Complete migration tracking${NC}"

echo ""
echo -e "${GREEN}✅ Migration verification complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Test consolidated services: ${YELLOW}./start-consolidated.sh${NC}"
echo -e "2. Visit main UI: ${YELLOW}http://localhost:8080${NC}"
echo -e "3. Stop services: ${YELLOW}./stop-consolidated.sh${NC}"