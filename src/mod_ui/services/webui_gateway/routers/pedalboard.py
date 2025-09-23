"""
Pedalboard API Router

Handles pedalboard management for the WebSocket Gateway.
"""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pedalboard", tags=["pedalboard"])

# Mock pedalboard storage - in production this would connect to the actual pedalboard system
MOCK_PEDALBOARDS = [
    {
        "bundle": "/usr/lib/lv2/default.pedalboard",
        "title": "Default",
        "broken": False,
        "width": 800,
        "height": 600,
    }
]


@router.post("/save")
async def save_pedalboard(data: Dict[str, Any]) -> Dict[str, Any]:
    """Save the current pedalboard"""
    try:
        title = data.get("title", "Untitled")
        as_new = data.get("asNew", False)

        # In production, this would save the current pedalboard
        return {
            "ok": True,
            "bundlepath": f"/tmp/{title.lower()}.pedalboard",
            "title": title,
        }
    except Exception as e:
        logger.error(f"Failed to save pedalboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to save pedalboard")


@router.post("/load_bundle")
async def load_bundle(data: Dict[str, Any]) -> Dict[str, Any]:
    """Load a pedalboard from a bundle"""
    try:
        bundlepath = data.get("bundlepath")
        is_default = data.get("isDefault", False)

        if not bundlepath:
            raise HTTPException(status_code=400, detail="Bundle path is required")

        # In production, this would load the pedalboard
        return {"ok": True, "name": "Loaded Pedalboard"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load bundle {bundlepath}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load bundle")


@router.get("/remove")
async def remove_pedalboard(bundlepath: str) -> Dict[str, Any]:
    """Remove a pedalboard"""
    try:
        # In production, this would remove the pedalboard file
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to remove pedalboard {bundlepath}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove pedalboard")


@router.get("/info")
async def get_pedalboard_info(bundlepath: str) -> Dict[str, Any]:
    """Get information about a pedalboard"""
    try:
        # In production, this would read the pedalboard manifest
        return {
            "title": "Sample Pedalboard",
            "width": 800,
            "height": 600,
            "connections": [],
            "plugins": [],
            "hardware": {},
        }
    except Exception as e:
        logger.error(f"Failed to get pedalboard info for {bundlepath}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pedalboard info")


@router.get("/factory_copy")
async def factory_copy(bundlepath: str, title: str) -> Dict[str, Any]:
    """Create a user copy of a factory pedalboard"""
    try:
        # In production, this would copy the factory pedalboard to user directory
        return {
            "bundlepath": f"/tmp/{title.lower()}.pedalboard",
            "title": title,
            "width": 800,
            "height": 600,
            "connections": [],
            "plugins": [],
            "hardware": {},
        }
    except Exception as e:
        logger.error(f"Failed to copy factory pedalboard {bundlepath}: {e}")
        raise HTTPException(status_code=500, detail="Failed to copy factory pedalboard")


@router.get("/list")
async def list_pedalboards() -> list:
    """Get a list of all pedalboards"""
    try:
        # In production, this would scan the pedalboard directories
        return MOCK_PEDALBOARDS
    except Exception as e:
        logger.error(f"Failed to list pedalboards: {e}")
        raise HTTPException(status_code=500, detail="Failed to list pedalboards")


@router.get("/pack_bundle")
async def pack_bundle(bundlepath: str) -> Dict[str, Any]:
    """Pack a pedalboard into a downloadable bundle"""
    try:
        # In production, this would create a tar.gz file
        raise HTTPException(status_code=501, detail="Not implemented")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pack bundle {bundlepath}: {e}")
        raise HTTPException(status_code=500, detail="Failed to pack bundle")


@router.post("/load_remote/{pedalboard_id}")
async def load_remote_pedalboard(
    pedalboard_id: str, data: Dict[str, Any]
) -> Dict[str, Any]:
    """Load a remote pedalboard"""
    try:
        # In production, this would download and load a remote pedalboard
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to load remote pedalboard {pedalboard_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load remote pedalboard")


@router.post("/load_web")
async def load_web_pedalboard(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Load a pedalboard from a web upload"""
    try:
        # In production, this would process the uploaded file
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to load web pedalboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to load web pedalboard")


@router.get("/image/{image}")
async def get_pedalboard_image(image: str, bundlepath: str) -> Dict[str, Any]:
    """Get an image for a pedalboard"""
    try:
        # In production, this would serve pedalboard images
        raise HTTPException(status_code=404, detail="Image not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get image {image} for {bundlepath}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get image")


@router.get("/image/generate")
async def generate_pedalboard_image(bundlepath: str) -> Dict[str, Any]:
    """Generate a new image for a pedalboard"""
    try:
        # In production, this would trigger image generation
        return {"ok": True, "ctime": "1234567890.123"}
    except Exception as e:
        logger.error(f"Failed to generate image for {bundlepath}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate image")


@router.get("/image/check")
async def check_pedalboard_image(bundlepath: str) -> Dict[str, Any]:
    """Check the status of a pedalboard image generation"""
    try:
        # In production, this would check generation status
        return {"status": "ready", "ctime": "1234567890.123"}
    except Exception as e:
        logger.error(f"Failed to check image for {bundlepath}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check image")


@router.get("/image/wait")
async def wait_pedalboard_image(bundlepath: str) -> Dict[str, Any]:
    """Wait for a pedalboard image generation to complete"""
    try:
        # In production, this would wait for generation to complete
        return {"ok": True, "ctime": "1234567890.123"}
    except Exception as e:
        logger.error(f"Failed to wait for image generation for {bundlepath}: {e}")
        raise HTTPException(status_code=500, detail="Failed to wait for image")


@router.post("/cv_addressing/plugin_port/add")
async def add_cv_port(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a CV addressing port to a plugin"""
    try:
        uri = data.get("uri")
        name = data.get("name")

        if not uri or not name:
            raise HTTPException(status_code=400, detail="URI and name are required")

        # In production, this would add a CV port
        return {"ok": True, "operational_mode": "+"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add CV port: {e}")
        raise HTTPException(status_code=500, detail="Failed to add CV port")


@router.post("/cv_addressing/plugin_port/remove")
async def remove_cv_port(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove a CV addressing port from a plugin"""
    try:
        uri = data.get("uri")
        if not uri:
            raise HTTPException(status_code=400, detail="URI is required")

        # In production, this would remove a CV port
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove CV port: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove CV port")


@router.post("/transport/set_sync_mode/{mode}")
async def set_transport_sync_mode(mode: str) -> Dict[str, Any]:
    """Set the transport sync mode"""
    try:
        # In production, this would set the transport sync mode
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to set transport sync mode {mode}: {e}")
        raise HTTPException(status_code=500, detail="Failed to set transport sync mode")
