#!/usr/bin/env python3
"""
Auto-Registration Example

This shows how to use decorators and auto-registration for even cleaner code.
"""

import asyncio
import logging
from datetime import datetime

from mod_ui.common import SimpleService, service_handler, auto_register_handlers, RequestType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define handlers using standalone decorators
@service_handler("get_system_info")
async def handle_system_info(request):
    """System info handler"""
    return {
        "hwname": "MOD Device",
        "version": "2.0",
        "timestamp": datetime.now().isoformat()
    }


@service_handler("get_health")
async def handle_health(request):
    """Health check handler"""
    return {"status": "healthy", "uptime": "5 days"}


@service_handler("custom_command")
async def handle_custom_command(request):
    """Custom command handler"""
    command = request.data.get("command", "ping")
    return {"command": command, "result": "executed"}


# You can even define handlers in other modules and import them
def create_more_handlers():
    @service_handler("get_version")
    def get_version(request):
        return {"version": "1.2.3"}
    
    @service_handler("get_uptime")
    def get_uptime(request):
        return "48 hours"
    
    return locals()  # Return all local functions


async def main():
    """Create service and auto-register all handlers"""
    logger.info("Creating service with auto-registration...")
    
    # Create service
    service = SimpleService("auto-service")
    
    # Auto-register handlers from current module
    current_module = globals()
    count1 = auto_register_handlers(service, current_module)
    logger.info(f"Auto-registered {count1} handlers from current module")
    
    # Auto-register handlers from other functions
    more_handlers = create_more_handlers()
    count2 = auto_register_handlers(service, more_handlers)
    logger.info(f"Auto-registered {count2} handlers from other functions")
    
    # Show all handlers
    logger.info(f"Total handlers: {service.list_handlers()}")
    
    # Run the service
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())