"""
Session Management API Router for WebUI Gateway

This router handles all session-related HTTP requests and communicates with
the Session Service v2 via Redis pub/sub for managing MOD device sessions.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from mod_ui.common import RequestType, ServiceClient

router = APIRouter()

# Service client for communicating with session service
session_service_client: Optional[ServiceClient] = None


def inject_service_client(client: ServiceClient):
    """Inject the service client for session communication"""
    global session_service_client
    session_service_client = client


@router.get("/info")
async def get_session_info() -> Dict[str, Any]:
    """Get current session information"""
    if not session_service_client:
        raise HTTPException(status_code=500, detail="Session service not available")

    try:
        response = await session_service_client.make_request(
            service_name="session",
            request_type=RequestType.GET_SESSION_STATE,
            data={},
        )

        if response.data.get("success"):
            session_data = response.data.get("session", {})

            # Transform the response to match expected format
            return {
                "ok": True,
                "session_id": "current",  # MOD uses single session
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
            raise HTTPException(
                status_code=500,
                detail=response.data.get("error", "Failed to get session"),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tempo")
async def get_tempo() -> Dict[str, Any]:
    """Get current tempo"""
    if not session_service_client:
        raise HTTPException(status_code=500, detail="Session service not available")

    try:
        response = await session_service_client.make_request(
            service_name="session",
            request_type=RequestType.GET_SESSION_STATE,
            data={},
        )

        if response.data.get("success"):
            session_data = response.data.get("session", {})
            return {
                "ok": True,
                "tempo_bpm": session_data.get("tempo_bpm", 120.0),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=response.data.get("error", "Failed to get tempo"),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tempo/{bpm}")
async def set_tempo(bpm: float) -> Dict[str, Any]:
    """Set session tempo"""
    if not session_service_client:
        raise HTTPException(status_code=500, detail="Session service not available")

    try:
        response = await session_service_client.make_request(
            service_name="session",
            request_type=RequestType.SET_SESSION_TEMPO,
            data={"bpm": bpm},
        )

        if response.data.get("success"):
            return {
                "ok": True,
                "tempo_bpm": response.data.get("tempo_bpm", bpm),
                "message": response.data.get("message", "Tempo set successfully"),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=response.data.get("error", "Failed to set tempo"),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transport/{action}")
async def transport_control(action: str) -> Dict[str, Any]:
    """Control transport (play, stop, pause)"""
    valid_actions = ["play", "stop", "pause"]
    if action not in valid_actions:
        raise HTTPException(
            status_code=400, detail=f"Invalid action. Must be one of: {valid_actions}"
        )

    if not session_service_client:
        raise HTTPException(status_code=500, detail="Session service not available")

    try:
        response = await session_service_client.make_request(
            service_name="session",
            request_type=RequestType.CONTROL_TRANSPORT,
            data={"action": action},
        )

        if response.data.get("success"):
            return {
                "ok": True,
                "transport_state": response.data.get("transport_state"),
                "message": response.data.get(
                    "message", f"Transport {action} successful"
                ),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=response.data.get("error", f"Failed to {action} transport"),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_session_stats() -> Dict[str, Any]:
    """Get session statistics"""
    if not session_service_client:
        raise HTTPException(status_code=500, detail="Session service not available")

    try:
        response = await session_service_client.make_request(
            service_name="session",
            request_type=RequestType.GET_SESSION_STATS,
            data={},
        )

        if response.data.get("success"):
            return {
                "ok": True,
                **response.data.get("stats", {}),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=response.data.get("error", "Failed to get stats"),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
