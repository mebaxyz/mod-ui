"""
Session Management API Router for WebUI Gateway

This router handles all session-related HTTP requests and communicates with
the Session S        response = await session_service_client.call(
            target_service="session",
            request_type="control_transport",
            data={"action": action},
        )

        if response is not None:
            return {
                "ok": True,
                "transport_state": response.get("transport_state"),
                "message": response.get(
                    "message", f"Transport {action} successful"
                ),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to {action} transport",
            ) pub/sub for managing MOD device sessions.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from servicebus import ServiceClient

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
        response = await session_service_client.call(
            target_service="session",
            request_type="get_session_state",
            data={},
        )

        if response is not None:
            session_data = response.get("session", response)

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
        response = await session_service_client.call(
            target_service="session",
            request_type="get_session_state",
            data={},
        )

        if response is not None:
            session_data = response.get("session", response)
            return {
                "ok": True,
                "tempo_bpm": session_data.get("tempo_bpm", 120.0),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to get tempo",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tempo/{bpm}")
async def set_tempo(bpm: float) -> Dict[str, Any]:
    """Set session tempo"""
    if not session_service_client:
        raise HTTPException(status_code=500, detail="Session service not available")

    try:
        response = await session_service_client.call(
            target_service="session",
            request_type="set_session_tempo",
            data={"bpm": bpm},
        )

        if response is not None:
            return {
                "ok": True,
                "tempo_bpm": response.get("tempo_bpm", bpm),
                "message": response.get("message", "Tempo set successfully"),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to set tempo",
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
        response = await session_service_client.call(
            target_service="session",
            request_type="control_transport",
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
        response = await session_service_client.call(
            target_service="session",
            request_type="get_session_stats",
            data={},
        )

        if response is not None:
            return {
                "ok": True,
                **response.get("stats", response if isinstance(response, dict) else {}),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to get stats",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
