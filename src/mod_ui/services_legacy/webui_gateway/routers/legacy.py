"""
Legacy Message API Router

Handles legacy message endpoints for backward compatibility with existing MOD UI clients.
These endpoints send specific message types that older clients expect.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["legacy"])

# Import global service instances (will be injected at runtime)
connection_manager = None


def inject_services(cm):
    """Inject service instances for router use"""
    global connection_manager
    connection_manager = cm


@router.post("/stats")
async def send_stats(stats_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send legacy stats message"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        cpu_load = float(stats_data.get("cpu_load", 0.0))
        xruns = int(stats_data.get("xruns", 0))

        count = await connection_manager.send_stats_message(cpu_load, xruns)

        return {
            "success": True,
            "message": "Stats sent",
            "clients_reached": count,
        }
    except Exception as e:
        return {"error": f"Failed to send stats: {str(e)}"}


@router.post("/sys_stats")
async def send_sys_stats(sys_stats_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send legacy system stats message"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        mem_load = float(sys_stats_data.get("mem_load", 0.0))
        cpu_freq = str(sys_stats_data.get("cpu_freq", "0"))
        cpu_temp = str(sys_stats_data.get("cpu_temp", "0"))

        count = await connection_manager.send_sys_stats_message(
            mem_load, cpu_freq, cpu_temp
        )

        return {
            "success": True,
            "message": "System stats sent",
            "clients_reached": count,
        }
    except Exception as e:
        return {"error": f"Failed to send system stats: {str(e)}"}


@router.post("/transport")
async def send_transport(transport_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send legacy transport message"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        rolling = bool(transport_data.get("rolling", False))
        bpb = float(transport_data.get("bpb", 4.0))
        bpm = float(transport_data.get("bpm", 120.0))
        sync = str(transport_data.get("sync", "none"))

        count = await connection_manager.send_transport_message(rolling, bpb, bpm, sync)

        return {
            "success": True,
            "message": "Transport sent",
            "clients_reached": count,
        }
    except Exception as e:
        return {"error": f"Failed to send transport: {str(e)}"}


@router.post("/loading_start")
async def send_loading_start(loading_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send legacy loading start message"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        empty = bool(loading_data.get("empty", True))
        modified = bool(loading_data.get("modified", False))

        count = await connection_manager.send_loading_start_message(empty, modified)

        return {
            "success": True,
            "message": "Loading start sent",
            "clients_reached": count,
        }
    except Exception as e:
        return {"error": f"Failed to send loading start: {str(e)}"}


@router.post("/loading_end")
async def send_loading_end(loading_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send legacy loading end message"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        snapshot_id = int(loading_data.get("snapshot_id", 0))

        count = await connection_manager.send_loading_end_message(snapshot_id)

        return {
            "success": True,
            "message": "Loading end sent",
            "clients_reached": count,
        }
    except Exception as e:
        return {"error": f"Failed to send loading end: {str(e)}"}
