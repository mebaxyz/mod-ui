"""
LV2/Cloud API Router

Handles LV2 plugin and cloud operations for the WebSocket Gateway.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lv2", tags=["lv2"])

# Mock LV2 data - in production this would connect to the actual LV2 system
MOCK_BUNDLES = {
    "bundle123": {
        "name": "Test Bundle",
        "plugins": [
            {
                "uri": "http://lv2plug.in/plugins/eg-amp",
                "name": "Simple Amplifier",
                "brand": "LV2",
            }
        ],
    }
}

MOCK_PLUGINS = [
    {
        "uri": "http://lv2plug.in/plugins/eg-amp",
        "name": "Simple Amplifier",
        "brand": "LV2",
        "bundle_id": "bundle123",
    }
]


@router.get("/bundles/{bundle_id}")
async def get_bundle(bundle_id: str) -> Dict[str, Any]:
    """Get bundle information from the cloud"""
    try:
        bundle = MOCK_BUNDLES.get(bundle_id)
        if not bundle:
            raise HTTPException(status_code=404, detail="Bundle not found")

        return bundle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bundle {bundle_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get bundle")


@router.get("/plugins")
async def get_plugins(
    uri: str = None, image_version: str = None
) -> List[Dict[str, Any]]:
    """Get plugin information from the cloud"""
    try:
        if uri:
            # Filter by specific URI
            plugins = [p for p in MOCK_PLUGINS if p["uri"] == uri]
        else:
            plugins = MOCK_PLUGINS

        return plugins
    except Exception as e:
        logger.error(f"Failed to get plugins: {e}")
        raise HTTPException(status_code=500, detail="Failed to get plugins")
