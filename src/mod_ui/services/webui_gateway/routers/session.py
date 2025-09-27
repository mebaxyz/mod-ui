"""
Session Management Router for WebUI Gateway

This router provides session management endpoints that interact
with the Session Service and broadcast events to connected WebSocket clients.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.mod_ui.common import RequestType, ServiceClient

from ..services.connection_manager import ConnectionManager
from ..utils.event_types import EventType

logger = logging.getLogger(__name__)
router = APIRouter()


# Request models
class StartSessionRequest(BaseModel):
    pedalboard_path: Optional[str] = None
    auto_save: bool = True


class SetTempoRequest(BaseModel):
    bpm: float


class TransportRequest(BaseModel):
    action: str  # "play", "pause", "stop", "rewind"


class ConfigRequest(BaseModel):
    sample_rate: Optional[int] = None
    buffer_size: Optional[int] = None
    audio_driver: Optional[str] = None


# Dependencies
async def get_service_client(request: Request) -> ServiceClient:
    """Get service client from app state"""
    service_client = getattr(request.app.state, "service_client", None)
    if not service_client:
        raise HTTPException(status_code=503, detail="Service client not available")
    return service_client


async def get_connection_manager(request: Request) -> ConnectionManager:
    """Get connection manager from app state"""
    connection_manager = getattr(request.app.state, "connection_manager", None)
    if not connection_manager:
        raise HTTPException(status_code=503, detail="Connection manager not available")
    return connection_manager


@router.get("/info")
async def get_session_info(request: Request):
    """Get current session information"""
    try:
        service_client = await get_service_client(request)

        # Call session service using Redis pub/sub
        response = await service_client.make_request(
            request_type=RequestType.GET_SESSION_STATUS,
            data={},
            service_name="session",
            timeout=5.0,
        )

        if response.status == "success" and response.data.get("success"):
            session_data = response.data.get("session", {})

            return {
                "ok": True,
                "session_id": "current",  # Legacy format compatibility
                "transport": {
                    "rolling": session_data.get("transport_state") == "playing",
                    "bpm": session_data.get("tempo_bpm", 120.0),
                },
                "audio": {
                    "sample_rate": session_data.get("sample_rate", 48000),
                    "buffer_size": session_data.get("buffer_size", 256),
                    "driver": session_data.get("audio_driver", "jack"),
                },
                "performance": {
                    "cpu_load": session_data.get("cpu_load", 0.0),
                    "xruns": session_data.get("xrun_count", 0),
                    "uptime": session_data.get("uptime_seconds", 0),
                },
            }
        else:
            logger.error(f"Session service error: {response}")
            return {"ok": False, "error": "Failed to get session status"}

    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_session(request_data: StartSessionRequest, request: Request):
    """Start a new session"""
    try:

        connection_manager = await get_connection_manager(request)

        # Reset current session first
        await session_request(
            service="session", endpoint="/api/session/reset", method="POST"
        )

        # Load pedalboard if specified
        if request_data.pedalboard_path:
            pedalboard_response = await session_request(
                service="session",
                endpoint="/api/pedalboard/load",
                method="POST",
                data={"bundle_path": request_data.pedalboard_path},
            )

            if not pedalboard_response or not pedalboard_response.get("success"):
                return {
                    "ok": False,
                    "error": f"Failed to load pedalboard: {request_data.pedalboard_path}",
                }

        # Get session status
        status_response = await session_request(
            service="session", endpoint="/api/session/status", method="GET"
        )

        if status_response and status_response.get("success"):
            # Broadcast session started event
            await connection_manager.broadcast_message(
                {
                    "type": "event",
                    "event_type": EventType.SESSION_STARTED,
                    "data": {
                        "session_id": "current",
                        "pedalboard_path": request_data.pedalboard_path,
                        "timestamp": status_response["session"]["created_at"],
                    },
                }
            )

            return {
                "ok": True,
                "message": "Session started successfully",
                "session_id": "current",
            }
        else:
            return {"ok": False, "error": "Failed to start session"}

    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_session(request: Request):
    """Stop current session"""
    try:

        connection_manager = await get_connection_manager(request)

        # Stop transport first
        await session_request(
            service="session", endpoint="/api/session/transport/stop", method="POST"
        )

        # Reset session
        response = await session_request(
            service="session", endpoint="/api/session/reset", method="POST"
        )

        if response and response.get("success"):
            # Broadcast session stopped event
            await connection_manager.broadcast_message(
                {
                    "type": "event",
                    "event_type": EventType.SESSION_STOPPED,
                    "data": {
                        "session_id": "current",
                        "timestamp": response.get("timestamp"),
                    },
                }
            )

            return {"ok": True, "message": "Session stopped successfully"}
        else:
            return {"ok": False, "error": "Failed to stop session"}

    except Exception as e:
        logger.error(f"Error stopping session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transport")
async def transport_control(transport_req: TransportRequest, request: Request):
    """Control transport (play/pause/stop/rewind)"""
    try:

        connection_manager = await get_connection_manager(request)

        action = transport_req.action.lower()

        # Map actions to endpoints
        endpoint_map = {
            "play": "/api/session/transport/play",
            "pause": "/api/session/transport/pause",
            "stop": "/api/session/transport/stop",
            "rewind": "/api/session/transport/rewind",
        }

        if action not in endpoint_map:
            raise HTTPException(
                status_code=400, detail=f"Invalid transport action: {action}"
            )

        # Call session service
        response = await session_request(
            service="session", endpoint=endpoint_map[action], method="POST"
        )

        if response and response.get("success"):
            # Broadcast transport change event
            await connection_manager.broadcast_message(
                {
                    "type": "event",
                    "event_type": EventType.SESSION_TRANSPORT_CHANGED,
                    "data": {
                        "transport_state": response.get("transport_state"),
                        "action": action,
                        "timestamp": None,
                    },
                }
            )

            return {
                "ok": True,
                "transport_state": response.get("transport_state"),
                "message": response.get("message", f"Transport {action} successful"),
            }
        else:
            return {"ok": False, "error": f"Failed to {action} transport"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling transport: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tempo")
async def set_tempo(tempo_req: SetTempoRequest, request: Request):
    """Set session tempo"""
    try:

        connection_manager = await get_connection_manager(request)

        # Validate tempo
        if not 30.0 <= tempo_req.bpm <= 300.0:
            raise HTTPException(
                status_code=400, detail="BPM must be between 30 and 300"
            )

        # Call session service
        response = await session_request(
            service="session",
            endpoint="/api/session/tempo",
            method="POST",
            data={"bpm": tempo_req.bpm},
        )

        if response and response.get("success"):
            # Broadcast tempo change event
            await connection_manager.broadcast_message(
                {
                    "type": "event",
                    "event_type": EventType.SESSION_CONFIG_CHANGED,
                    "data": {"tempo_bpm": tempo_req.bpm, "config_type": "tempo"},
                }
            )

            return {
                "ok": True,
                "tempo_bpm": tempo_req.bpm,
                "message": f"Tempo set to {tempo_req.bpm} BPM",
            }
        else:
            return {"ok": False, "error": "Failed to set tempo"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting tempo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tempo")
async def get_tempo(request: Request):
    """Get current session tempo"""
    try:

        response = await session_request(
            service="session", endpoint="/api/session/tempo", method="GET"
        )

        if response and response.get("success"):
            return {"ok": True, "tempo_bpm": response.get("tempo_bpm")}
        else:
            return {"ok": False, "error": "Failed to get tempo"}

    except Exception as e:
        logger.error(f"Error getting tempo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def set_system_config(config_req: ConfigRequest, request: Request):
    """Update system audio configuration"""
    try:

        connection_manager = await get_connection_manager(request)

        # Build config data
        config_data = {}
        if config_req.sample_rate is not None:
            config_data["sample_rate"] = config_req.sample_rate
        if config_req.buffer_size is not None:
            config_data["buffer_size"] = config_req.buffer_size
        if config_req.audio_driver is not None:
            config_data["audio_driver"] = config_req.audio_driver

        if not config_data:
            raise HTTPException(status_code=400, detail="No configuration provided")

        # Call session service
        response = await session_request(
            service="session",
            endpoint="/api/session/config",
            method="POST",
            data=config_data,
        )

        if response and response.get("success"):
            # Broadcast config change event
            await connection_manager.broadcast_message(
                {
                    "type": "event",
                    "event_type": EventType.SESSION_CONFIG_CHANGED,
                    "data": {
                        "config": response.get("config", {}),
                        "config_type": "audio",
                    },
                }
            )

            return {
                "ok": True,
                "config": response.get("config"),
                "message": response.get("message", "Configuration updated"),
            }
        else:
            return {"ok": False, "error": "Failed to update configuration"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_session_stats(request: Request):
    """Get session performance statistics"""
    try:

        response = await session_request(
            service="session", endpoint="/api/session/stats", method="GET"
        )

        if response and response.get("success"):
            stats = response.get("stats", {})

            return {
                "ok": True,
                "stats": {
                    "cpu_load": stats.get("cpu_load", 0.0),
                    "xrun_count": stats.get("xrun_count", 0),
                    "uptime_seconds": stats.get("uptime_seconds", 0),
                    "sample_rate": stats.get("sample_rate", 48000),
                    "buffer_size": stats.get("buffer_size", 256),
                    "transport_state": stats.get("transport_state", "stopped"),
                },
            }
        else:
            return {"ok": False, "error": "Failed to get statistics"}

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats/reset")
async def reset_session_stats(request: Request):
    """Reset session performance counters"""
    try:

        connection_manager = await get_connection_manager(request)

        response = await session_request(
            service="session", endpoint="/api/session/stats/reset", method="POST"
        )

        if response and response.get("success"):
            # Broadcast stats reset event
            await connection_manager.broadcast_message(
                {
                    "type": "event",
                    "event_type": EventType.SESSION_STATS_UPDATED,
                    "data": {"action": "reset", "stats": response.get("stats", {})},
                }
            )

            return {"ok": True, "message": "Statistics reset successfully"}
        else:
            return {"ok": False, "error": "Failed to reset statistics"}

    except Exception as e:
        logger.error(f"Error resetting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Legacy endpoints for compatibility
@router.get("")
async def session_root(request: Request):
    """Legacy session root endpoint"""
    return await get_session_info(request)


@router.post("/load_pedalboard")
async def load_pedalboard_legacy(request: Request):
    """Legacy pedalboard loading endpoint"""
    try:
        # This would typically come from form data
        # For now, redirect to pedalboard service
        return {"ok": False, "error": "Use /api/pedalboard/load endpoint instead"}
    except Exception as e:
        logger.error(f"Error in legacy pedalboard load: {e}")
        raise HTTPException(status_code=500, detail=str(e))
