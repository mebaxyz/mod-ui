#!/usr/bin/env python3
"""
Example System Service Implementation

This demonstrates how to use ServiceServer to create a service that responds
to requests from other services using the common package.
"""

import asyncio
import logging
import platform
import sys
from datetime import datetime

from mod_ui.common import ServiceServer, ServiceRequest, RequestType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_get_system_info(request: ServiceRequest) -> dict:
    """Handle GET_SYSTEM_INFO requests"""
    logger.info(f"Handling system info request from {request.source_service}")
    
    # Gather actual system information
    uname = platform.uname()
    
    return {
        "hwname": "MOD Device",
        "architecture": uname.machine,
        "cpu": platform.processor() or "Unknown",
        "platform": "mod-platform",
        "bin_compat": f"{uname.machine}-linux-gnu",
        "model": "mod-device",
        "sysdate": datetime.now().strftime("%Y-%m-%d"),
        "python": {"version": platform.python_version()},
        "uname": {
            "machine": uname.machine,
            "release": uname.release,
            "sysname": uname.system,
            "version": uname.version,
        },
        "uptime": "System uptime would go here",
        "load_average": "Load average would go here",
    }


async def handle_get_system_stats(request: ServiceRequest) -> dict:
    """Handle GET_SYSTEM_STATS requests"""
    logger.info(f"Handling system stats request from {request.source_service}")
    
    # Mock system stats - in production this would gather real metrics
    return {
        "cpu_usage": 25.5,
        "memory": {
            "total": 1024 * 1024 * 1024,  # 1GB
            "available": 512 * 1024 * 1024,  # 512MB
            "used": 512 * 1024 * 1024,  # 512MB
            "percent": 50.0
        },
        "disk": {
            "total": 8 * 1024 * 1024 * 1024,  # 8GB
            "available": 4 * 1024 * 1024 * 1024,  # 4GB
            "used": 4 * 1024 * 1024 * 1024,  # 4GB
            "percent": 50.0
        },
        "network": {
            "bytes_sent": 1024 * 1024,  # 1MB
            "bytes_recv": 2 * 1024 * 1024,  # 2MB
            "packets_sent": 1000,
            "packets_recv": 2000
        },
        "timestamp": datetime.now().isoformat()
    }


async def handle_get_hardware_status(request: ServiceRequest) -> dict:
    """Handle GET_HARDWARE_STATUS requests"""
    logger.info(f"Handling hardware status request from {request.source_service}")
    
    return {
        "audio_interface": {
            "status": "connected",
            "sample_rate": 48000,
            "buffer_size": 256,
            "inputs": 2,
            "outputs": 2
        },
        "midi": {
            "ports": [
                {"name": "MIDI In", "type": "input", "connected": True},
                {"name": "MIDI Out", "type": "output", "connected": True}
            ]
        },
        "usb": {
            "ports": 4,
            "devices_connected": 1
        },
        "temperature": {
            "cpu": 45.2,
            "case": 42.1,
            "unit": "celsius"
        }
    }


async def main():
    """Main service function"""
    logger.info("Starting Example System Service...")
    
    # Create service server
    server = ServiceServer(service_name="system-service")
    
    # Register request handlers
    server.register_handler(RequestType.GET_SYSTEM_INFO, handle_get_system_info)
    server.register_handler(RequestType.GET_SYSTEM_STATS, handle_get_system_stats)
    server.register_handler(RequestType.GET_HARDWARE_STATUS, handle_get_hardware_status)
    
    try:
        async with server:
            logger.info("System service is running. Press Ctrl+C to stop.")
            
            # Keep the service running
            while True:
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Service error: {e}")
        return 1
    
    logger.info("System service stopped")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))