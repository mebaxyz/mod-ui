#!/usr/bin/env python3
"""
Multi-Service Example

This shows how to run multiple services in one application using ServiceRegistry.
"""

import asyncio
import logging
from datetime import datetime

from mod_ui.common import ServiceRegistry, RequestType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create registry and services
registry = ServiceRegistry()

# System service
system_service = registry.create_service("system-service")

@system_service.enum_handler(RequestType.GET_SYSTEM_INFO)
async def get_system_info(request):
    return {"service": "system", "status": "running"}

@system_service.enum_handler(RequestType.GET_SYSTEM_STATS)
async def get_system_stats(request):
    return {"cpu": 25.0, "memory": 60.0}


# Session service
session_service = registry.create_service("session-service")

@session_service.enum_handler(RequestType.GET_SESSION_STATE)
async def get_session_state(request):
    return {"session_id": "12345", "active": True}


# Audio service
audio_service = registry.create_service("audio-service")

@audio_service.enum_handler(RequestType.GET_AUDIO_STATUS)
async def get_audio_status(request):
    return {"sample_rate": 48000, "buffer_size": 256}

@audio_service.enum_handler(RequestType.CONTROL_TRANSPORT)
async def control_transport(request):
    action = request.data.get("action", "unknown")
    return {"transport_action": action, "status": "executed"}


async def main():
    """Run all services"""
    logger.info("Starting multi-service application...")
    
    # Show all registered services
    services_info = registry.list_services()
    for service_name, handlers in services_info.items():
        logger.info(f"Service '{service_name}': {list(handlers.keys())}")
    
    try:
        # Start all services
        await registry.start_all()
        
        # Keep running
        logger.info("All services running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down all services...")
        await registry.stop_all()
    except Exception as e:
        logger.error(f"Error in multi-service app: {e}")
        await registry.stop_all()
        raise


if __name__ == "__main__":
    asyncio.run(main())