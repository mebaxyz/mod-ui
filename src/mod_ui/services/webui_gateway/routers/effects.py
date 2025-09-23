"""
Effects/Plugins API Router

Handles all plugin-related API endpoints for the WebSocket Gateway.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/effect", tags=["effects"])

# Mock data for development - in production this would connect to the actual plugin system
MOCK_PLUGINS = [
    {
        "uri": "http://lv2plug.in/plugins/eg-amp",
        "name": "Simple Amplifier",
        "brand": "LV2",
        "label": "Simple Amp",
        "category": ["Utility"],
        "ports": {
            "control": {
                "input": [
                    {
                        "name": "Gain",
                        "symbol": "gain",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.5,
                    }
                ]
            },
            "audio": {
                "input": [{"name": "Input", "symbol": "input"}],
                "output": [{"name": "Output", "symbol": "output"}],
            },
        },
    }
]


@router.get("/list")
async def list_effects() -> Dict[str, Any]:
    """Get all available plugins"""
    try:
        # In production, this would query the actual plugin system
        return {"effects": MOCK_PLUGINS}
    except Exception as e:
        logger.error(f"Failed to list effects: {e}")
        raise HTTPException(status_code=500, detail="Failed to list effects")


@router.get("/get")
async def get_effect(uri: str) -> Dict[str, Any]:
    """Get detailed information for a specific plugin"""
    try:
        # In production, this would query the actual plugin system
        effect = next((p for p in MOCK_PLUGINS if p["uri"] == uri), None)
        if not effect:
            raise HTTPException(status_code=404, detail="Plugin not found")
        return effect
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get effect {uri}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get effect")


@router.post("/install")
async def install_effect(data: Dict[str, Any]) -> Dict[str, Any]:
    """Install a new plugin"""
    try:
        # In production, this would trigger plugin installation
        uri = data.get("uri")
        if not uri:
            raise HTTPException(status_code=400, detail="URI is required")

        # Mock installation response
        return {"ok": True, "installed": [uri], "removed": []}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to install effect: {e}")
        raise HTTPException(status_code=500, detail="Failed to install effect")


@router.get("/add/{instance}")
async def add_effect(
    instance: str, uri: str, x: float = 0.0, y: float = 0.0
) -> Dict[str, Any]:
    """Add a plugin instance to the pedalboard"""
    try:
        # In production, this would add the plugin to the current pedalboard
        effect = next((p for p in MOCK_PLUGINS if p["uri"] == uri), None)
        if not effect:
            raise HTTPException(status_code=404, detail="Plugin not found")

        return {"instance": instance, "uri": uri, "x": x, "y": y, **effect}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add effect {instance}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add effect")


@router.get("/remove/{instance}")
async def remove_effect(instance: str) -> Dict[str, Any]:
    """Remove a plugin instance from the pedalboard"""
    try:
        # In production, this would remove the plugin from the current pedalboard
        return {"ok": True, "instance": instance}
    except Exception as e:
        logger.error(f"Failed to remove effect {instance}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove effect")


@router.get("/connect/{port_from}/{port_to}")
async def connect_effects(port_from: str, port_to: str) -> Dict[str, Any]:
    """Connect two plugin ports"""
    try:
        # In production, this would create a connection between ports
        return {"ok": True, "from": port_from, "to": port_to}
    except Exception as e:
        logger.error(f"Failed to connect {port_from} to {port_to}: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect ports")


@router.get("/disconnect/{port_from}/{port_to}")
async def disconnect_effects(port_from: str, port_to: str) -> Dict[str, Any]:
    """Disconnect two plugin ports"""
    try:
        # In production, this would remove a connection between ports
        return {"ok": True, "from": port_from, "to": port_to}
    except Exception as e:
        logger.error(f"Failed to disconnect {port_from} to {port_to}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect ports")


@router.post("/preset/load/{instance}")
async def load_preset(instance: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Load a preset for a plugin instance"""
    try:
        uri = data.get("uri")
        if not uri:
            raise HTTPException(status_code=400, detail="URI is required")

        # In production, this would load the preset
        return {"ok": True, "instance": instance, "uri": uri}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load preset for {instance}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load preset")


@router.get("/preset/save_new/{instance}")
async def save_new_preset(instance: str, name: str) -> Dict[str, Any]:
    """Save a new preset for a plugin instance"""
    try:
        # In production, this would save a new preset
        return {"ok": True, "instance": instance, "name": name}
    except Exception as e:
        logger.error(f"Failed to save new preset for {instance}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save preset")


@router.get("/preset/save_replace/{instance}")
async def save_replace_preset(
    instance: str, uri: str, bundle: str, name: str
) -> Dict[str, Any]:
    """Replace an existing preset"""
    try:
        # In production, this would replace an existing preset
        return {"ok": True, "instance": instance, "uri": uri, "name": name}
    except Exception as e:
        logger.error(f"Failed to replace preset for {instance}: {e}")
        raise HTTPException(status_code=500, detail="Failed to replace preset")


@router.get("/preset/delete/{instance}")
async def delete_preset(instance: str, uri: str, bundle: str) -> Dict[str, Any]:
    """Delete a preset"""
    try:
        # In production, this would delete a preset
        return {"ok": True, "instance": instance, "uri": uri}
    except Exception as e:
        logger.error(f"Failed to delete preset for {instance}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete preset")


# Additional endpoints from webserver.py that aren't used by frontend but might be useful
@router.get("/get_non_cached")
async def get_effect_non_cached(uri: str) -> Dict[str, Any]:
    """Get non-cached information for a specific plugin"""
    # This is identical to /get in functionality for now
    return await get_effect(uri)


@router.post("/parameter/address/{port}")
async def address_parameter(port: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Address a parameter to a hardware control"""
    try:
        # In production, this would set up parameter addressing
        return {"ok": True, "port": port}
    except Exception as e:
        logger.error(f"Failed to address parameter {port}: {e}")
        raise HTTPException(status_code=500, detail="Failed to address parameter")


@router.post("/parameter/set")
async def set_parameter(data: Dict[str, Any]) -> Dict[str, Any]:
    """Set a parameter value (alternative to WebSocket)"""
    try:
        symbol = data.get("symbol")
        instance = data.get("instance")
        portsymbol = data.get("portsymbol")
        value = data.get("value")

        if not all([symbol, instance, portsymbol, value is not None]):
            raise HTTPException(status_code=400, detail="Missing required parameters")

        # In production, this would set the parameter value
        return {"ok": True, "instance": instance, "symbol": portsymbol, "value": value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set parameter: {e}")
        raise HTTPException(status_code=500, detail="Failed to set parameter")


@router.get("/resource/{path:path}")
async def get_effect_resource(path: str) -> Dict[str, Any]:
    """Get a resource file for a plugin"""
    try:
        # In production, this would serve plugin resources
        raise HTTPException(status_code=404, detail="Resource not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resource {path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get resource")


@router.get("/image/{image}")
async def get_effect_image(image: str, uri: str) -> Dict[str, Any]:
    """Get an image file (thumbnail, screenshot) for a plugin"""
    try:
        # In production, this would serve plugin images
        raise HTTPException(status_code=404, detail="Image not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get image {image} for {uri}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get image")


@router.get("/file/{prop}")
async def get_effect_file(prop: str, uri: str) -> Dict[str, Any]:
    """Get a file (stylesheet, javascript, etc.) for a plugin"""
    try:
        # In production, this would serve plugin files
        raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file {prop} for {uri}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file")
