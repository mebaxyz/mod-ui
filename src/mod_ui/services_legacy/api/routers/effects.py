"""
Effects Router

Handles plugin/effect-related endpoints for the MOD UI API.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/effect", tags=["effects"])

# Import MOD utilities with fallbacks
try:
    from mod_ui.utils.modtools.utils import get_all_plugins, get_plugin_info

    MOD_UTILS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"MOD utilities not available for effects router: {e}")
    MOD_UTILS_AVAILABLE = False

    def get_all_plugins():
        """Fallback for plugin list"""
        return []

    def get_plugin_info(uri):
        """Fallback for plugin info"""
        return {"uri": uri, "name": "Plugin", "version": "1.0.0"}


@router.get("/list")
async def get_plugin_list_endpoint():
    """
    List all available plugins

    Matches the original EffectList handler functionality.
    Returns a list of all LV2 plugins available on the system.
    """
    try:
        # Use get_all_plugins() to get plugin objects with proper structure
        # This matches the original Tornado EffectList handler
        plugins = get_all_plugins()
        return JSONResponse(plugins)
    except Exception as e:
        logger.error(f"Error getting plugin list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get")
async def get_plugin_info_endpoint(uri: str):
    """
    Get information about a specific plugin

    Args:
        uri: The LV2 URI of the plugin to get info for

    Returns:
        Plugin information including name, version, ports, etc.
    """
    try:
        plugin_data = get_plugin_info(uri)
        return JSONResponse({"success": True, "data": plugin_data})
    except Exception as e:
        logger.error(f"Error getting plugin info for {uri}: {e}")
        raise HTTPException(status_code=404, detail=f"Plugin not found: {uri}")
