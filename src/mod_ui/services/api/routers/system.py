"""
System Router

Handles system-related endpoints for the MOD UI API including health checks,
system information, and preferences.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["system"])

# Import settings with fallbacks
try:
    from mod import safe_json_load

    from mod_ui.utils.mod_legacy.settings import IMAGE_VERSION, PREFERENCES_JSON_FILE

    MOD_SETTINGS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"MOD settings not available for system router: {e}")
    MOD_SETTINGS_AVAILABLE = False
    IMAGE_VERSION = "1.0.0"
    PREFERENCES_JSON_FILE = "/app/data/preferences.json"

    def safe_json_load(filepath, default_type):
        try:
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    return json.load(f)
        except:
            pass
        return default_type()


@router.get("/system/info")
async def get_system_info():
    """
    Get system information and status

    Returns basic system information including version, hardware type,
    uptime, and migration status.
    """
    return JSONResponse(
        {
            "success": True,
            "data": {
                "version": IMAGE_VERSION or "1.0.0",
                "hardware": "MOD Duo",
                "uptime": 3600,  # TODO: Get actual uptime
                "framework": "FastAPI",
                "migration_status": "in_progress",
            },
        }
    )


@router.get("/ping")
async def ping():
    """
    Health check endpoint

    Simple health check that returns success status and timestamp.
    Used by monitoring systems and load balancers.
    Compatible with legacy JavaScript client expectations.
    """
    return JSONResponse(
        {
            "success": True,
            "ihm_online": True,
            "ihm_time": 1,
            "timestamp": datetime.now().isoformat(),
        }
    )


@router.get("/hello")
async def hello():
    """
    Remote monitoring endpoint

    Returns basic system status for remote monitoring.
    Shows if WebSocket connections are active.
    """
    # Import manager here to avoid circular imports
    try:
        from ..websocket.connection_manager import manager

        active_connections = len(manager.active_connections)
    except ImportError:
        active_connections = 0

    return JSONResponse(
        {
            "online": active_connections > 0,
            "version": IMAGE_VERSION or "1.0.0",
            "framework": "FastAPI",
        }
    )


@router.get("/websocket/health")
async def websocket_health():
    """
    WebSocket health check endpoint

    Returns WebSocket service status and connection count.
    """
    # Import manager and session status here to avoid circular imports
    try:
        from ..websocket.connection_manager import manager

        active_connections = len(manager.active_connections)
    except ImportError:
        active_connections = 0

    try:
        from mod_ui.utils.mod_legacy.session import SESSION

        session_available = SESSION is not None
    except ImportError:
        session_available = False

    return JSONResponse(
        {
            "websocket_endpoint": "/websocket",
            "active_connections": active_connections,
            "session_available": session_available,
            "status": "ready",
        }
    )


@router.get("/system/prefs")
async def get_system_preferences():
    """
    Get system preferences

    Returns system preferences including file-based flags and service states.
    Matches the original SystemPreferences handler.
    """
    try:
        # Implement system preferences logic matching original
        ret = {}

        # Bluetooth name
        bluetooth_path = "/data/bluetooth/name"
        if os.path.exists(bluetooth_path):
            try:
                with open(bluetooth_path, "r") as f:
                    ret["bluetooth_name"] = f.read().strip()
            except:
                ret["bluetooth_name"] = None
        else:
            ret["bluetooth_name"] = None

        # File-based flags
        ret["jack_mono_copy"] = os.path.exists("/data/jack-mono-copy")
        ret["jack_sync_mode"] = os.path.exists("/data/jack-sync-mode")
        ret["jack_256_frames"] = os.path.exists("/data/using-256-frames")
        ret["separate_spdif_outs"] = os.path.exists("/data/separate-spdif-outs")

        # Services
        ret["service_mod_peakmeter"] = not os.path.exists("/data/disable-mod-peakmeter")
        ret["service_mod_sdk"] = os.path.exists("/data/enable-mod-sdk")
        ret["service_netmanager"] = not os.path.exists("/data/disable-netmanager")

        # Workarounds
        ret["autorestart_hmi"] = os.path.exists("/data/autorestart-hmi")

        return JSONResponse(ret)
    except Exception as e:
        logger.error(f"Error getting system preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/prefs")
async def set_system_preferences(preferences: dict):
    """
    Set system preferences

    Updates system-wide preferences and saves them to the preferences file.
    """
    try:
        preferences_file = os.environ.get(
            "MOD_PREFERENCES_FILE", "/app/data/preferences.json"
        )

        # Ensure data directory exists
        os.makedirs(os.path.dirname(preferences_file), exist_ok=True)

        # Save preferences
        with open(preferences_file, "w") as f:
            json.dump(preferences, f, indent=2)

        return JSONResponse(
            {"success": True, "message": "Preferences saved successfully"}
        )
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))
