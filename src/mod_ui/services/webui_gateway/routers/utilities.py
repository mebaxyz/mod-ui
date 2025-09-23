"""
Utility API Router

Handles utility endpoints for the WebSocket Gateway.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(tags=["utilities"])


@router.get("/ping")
async def ping() -> Dict[str, Any]:
    """Ping the server to check for liveness"""
    return {"status": "ok", "service": "websocket-gateway"}


@router.get("/hello")
async def hello() -> Dict[str, Any]:
    """Check if the WebSocket server is online"""
    return {"online": True, "version": "1.0.0"}


@router.get("/truebypass/{channel}/{state}")
async def set_truebypass(channel: str, state: str) -> Dict[str, Any]:
    """Set the true bypass state for an audio channel"""
    try:
        # In production, this would set the true bypass state
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to set true bypass for {channel} to {state}: {e}")
        raise HTTPException(status_code=500, detail="Failed to set true bypass")


@router.post("/buffersize/{size}")
async def set_buffer_size(size: int) -> Dict[str, Any]:
    """Set the JACK buffer size"""
    try:
        # In production, this would set the JACK buffer size
        return {"ok": True, "size": size}
    except Exception as e:
        logger.error(f"Failed to set buffer size to {size}: {e}")
        raise HTTPException(status_code=500, detail="Failed to set buffer size")


@router.post("/xruns/reset")
async def reset_xruns() -> Dict[str, Any]:
    """Reset the x-run counter"""
    try:
        # In production, this would reset the x-run counter
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to reset xruns: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset xruns")


@router.post("/cpu/freq/switch")
async def switch_cpu_frequency() -> Dict[str, Any]:
    """Switch the CPU frequency"""
    try:
        # In production, this would switch CPU frequency
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to switch CPU frequency: {e}")
        raise HTTPException(status_code=500, detail="Failed to switch CPU frequency")


@router.post("/config/save")
async def save_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """Save a single configuration value"""
    try:
        key = data.get("key")
        value = data.get("value")

        if not key:
            raise HTTPException(status_code=400, detail="Key is required")

        # In production, this would save the configuration
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save config {key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save config")


@router.post("/user/save")
async def save_user(data: Dict[str, Any]) -> Dict[str, Any]:
    """Save the user's ID (name and email)"""
    try:
        name = data.get("name")
        email = data.get("email")

        # In production, this would save user information
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to save user: {e}")
        raise HTTPException(status_code=500, detail="Failed to save user")


@router.get("/dashboard/clean")
async def clean_dashboard() -> Dict[str, Any]:
    """Clear the dashboard (reset the current pedalboard)"""
    try:
        # In production, this would reset the current pedalboard
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to clean dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to clean dashboard")
