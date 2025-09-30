"""
Hardware Ports Router

Provides REST endpoints for hardware port information and management.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from servicebus import ServiceClient

from src.mod_ui.services.webui_gateway.services.connection_manager import (
    ConnectionManager,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency injection
_connection_manager: ConnectionManager = None
_service_client: ServiceClient = None


def inject_services(
    connection_manager: ConnectionManager, service_client: ServiceClient
):
    """Inject dependencies into the router"""
    global _connection_manager, _service_client
    _connection_manager = connection_manager
    _service_client = service_client


@router.get("/hardware/ports")
async def get_hardware_ports() -> Dict[str, Any]:
    """Get current hardware ports state"""
    if not _connection_manager:
        raise HTTPException(status_code=503, detail="Connection manager not available")

    return {
        "success": True,
        "ports": _connection_manager.hardware_ports,
        "port_count": len(_connection_manager.hardware_ports),
    }


@router.post("/hardware/ports/refresh")
async def refresh_hardware_ports() -> Dict[str, Any]:
    """Refresh hardware ports from audio engine"""
    if not _connection_manager:
        raise HTTPException(status_code=503, detail="Connection manager not available")

    try:
        await _connection_manager.request_hardware_ports_from_audio_engine()
        return {
            "success": True,
            "message": "Hardware ports refreshed",
            "port_count": len(_connection_manager.hardware_ports),
        }
    except Exception as e:
        logger.error(f"Failed to refresh hardware ports: {e}")
        raise HTTPException(status_code=500, detail=str(e))
