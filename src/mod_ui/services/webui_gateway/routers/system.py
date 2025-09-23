"""
System API Router

Handles system-level operations for the WebSocket Gateway.
"""

import json
import logging
import os
import subprocess
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from mod_ui.common import RequestType, ServiceClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

# Service dependencies
_service_client: Optional[ServiceClient] = None


def inject_services(service_client: ServiceClient):
    """Inject service dependencies"""
    global _service_client
    _service_client = service_client


@router.get("/info")
async def get_system_info() -> Dict[str, Any]:
    """Get system hardware and software information"""
    global _service_client

    if not _service_client:
        # Fallback to mock data if service client not available
        logger.warning("Service client not available, using mock system info")
        return {
            "hwname": "MOD Duo",
            "architecture": "armv7l",
            "cpu": "ARM Cortex-A7",
            "platform": "modduo",
            "bin_compat": "arm-linux-gnueabihf",
            "model": "modduo",
            "sysdate": "2024-01-01",
            "python": {"version": "3.11.2"},
            "uname": {
                "machine": "armv7l",
                "release": "5.10.0",
                "sysname": "Linux",
                "version": "#1 SMP PREEMPT",
            },
        }

    try:
        # Make request to system stats service
        response = await _service_client.make_request(
            request_type=RequestType.GET_SYSTEM_INFO,
            data={},
            service_name="system-stats-service",
            timeout=5.0,
        )

        if response.status == "success":
            return response.data
        else:
            logger.error(
                f"Failed to get system info from service: {response.error_message}"
            )
            raise HTTPException(
                status_code=500, detail=f"Service error: {response.error_message}"
            )

    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system info")


@router.get("/stats")
async def get_system_stats() -> Dict[str, Any]:
    """Get current system statistics"""
    global _service_client

    if not _service_client:
        # Fallback to mock data if service client not available
        logger.warning("Service client not available, using mock system stats")
        return {
            "cpu_load": 25.5,
            "mem_usage": 45.2,
            "cpu_frequency": "1000000000",
            "cpu_temperature": "45000",
            "uptime": "12345",
            "disk_usage": 35.8,
            "timestamp": "2024-01-01T00:00:00",
        }

    try:
        # Make request to system stats service
        response = await _service_client.make_request(
            request_type="get_system_stats",
            data={},
            service_name="system-stats-service",
            timeout=5.0,
        )

        if response.status == "success":
            return response.data
        else:
            logger.error(
                f"Failed to get system stats from service: {response.error_message}"
            )
            raise HTTPException(
                status_code=500, detail=f"Service error: {response.error_message}"
            )

    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system stats")


@router.get("/preferences")
async def get_system_preferences() -> Dict[str, Any]:
    """Get system preferences"""
    try:
        # Mock preferences - in production this would load from preferences file
        return {
            "bluetooth_name": "MOD",
            "jack_mono_copy": False,
            "jack_sync_mode": False,
            "jack_256_frames": False,
            "separate_spdif_outs": False,
            "service_mod_peakmeter": True,
            "service_mod_sdk": False,
            "service_netmanager": False,
            "autorestart_hmi": False,
        }
    except Exception as e:
        logger.error(f"Failed to get system preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system preferences")


@router.post("/exe")
async def execute_system_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a system-level command"""
    try:
        command_type = data.get("type")
        command_data = data.get("cmd", "")

        if command_type == "command":
            if command_data == "reboot":
                # In production, this would trigger a system reboot
                return {"ok": True}
            elif command_data == "restore":
                # In production, this would trigger system restore
                return {"ok": True}
            elif command_data.startswith("backup-export"):
                # In production, this would create a backup
                return {"ok": True, "error": ""}
            elif command_data.startswith("backup-import"):
                # In production, this would restore from backup
                return {"ok": True, "error": ""}

        elif command_type == "filecreate":
            # In production, this would create system files
            return {"ok": True}

        elif command_type == "filewrite":
            # In production, this would write system files
            return {"ok": True}

        elif command_type == "service":
            # In production, this would manage system services
            return {"ok": True}

        return {"ok": False}
    except Exception as e:
        logger.error(f"Failed to execute system command: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute system command")


@router.post("/cleanup")
async def cleanup_system(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean up user data"""
    try:
        # In production, this would clean up the specified data types
        return {"ok": True, "error": ""}
    except Exception as e:
        logger.error(f"Failed to cleanup system: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup system")
