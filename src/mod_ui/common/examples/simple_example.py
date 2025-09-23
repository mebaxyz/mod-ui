#!/usr/bin/env python3
"""
Simplified System Service Example

This demonstrates the new simplified API using decorators and SimpleService.
Compare this with example_server.py to see the difference!
"""

import asyncio
import logging
import platform
from datetime import datetime

from mod_ui.common import SimpleService, RequestType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create service with simple API
service = SimpleService("system-service")


@service.enum_handler(RequestType.GET_SYSTEM_INFO)
async def get_system_info(request):
    """Handle system info requests - much simpler!"""
    logger.info(f"System info requested by {request.source_service}")
    
    uname = platform.uname()
    return {
        "hwname": "MOD Device",
        "architecture": uname.machine,
        "cpu": platform.processor() or "Unknown",
        "platform": "mod-platform",
        "python": {"version": platform.python_version()},
        "uname": {
            "machine": uname.machine,
            "release": uname.release,
            "sysname": uname.system,
        },
        "timestamp": datetime.now().isoformat()
    }


@service.enum_handler(RequestType.GET_SYSTEM_STATS)
async def get_system_stats(request):
    """Handle system stats requests"""
    logger.info(f"System stats requested by {request.source_service}")
    
    return {
        "cpu_usage": 25.5,
        "memory_usage": 50.0,
        "disk_usage": 60.2,
        "uptime_hours": 24.5,
        "timestamp": datetime.now().isoformat()
    }


@service.handler("custom_action")  # Custom string-based handler
async def handle_custom(request):
    """Handle custom requests"""
    logger.info(f"Custom action requested: {request.data}")
    
    action = request.data.get("action", "unknown")
    return {
        "action_performed": action,
        "status": "completed",
        "timestamp": datetime.now().isoformat()
    }


# Even simpler - just return a value, not a dict
@service.handler("get_uptime")
def get_uptime(request):
    """Simple sync handler that returns a value"""
    return "24 hours 30 minutes"  # Will be wrapped as {"result": "24 hours 30 minutes"}


async def main():
    """Run the service - so simple!"""
    logger.info("Starting simplified system service...")
    logger.info(f"Registered handlers: {service.list_handlers()}")
    
    # Just run it!
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())