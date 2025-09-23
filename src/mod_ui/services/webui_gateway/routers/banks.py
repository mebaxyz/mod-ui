"""
Bank API Router

Handles pedalboard bank management for the WebSocket Gateway.
"""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank", tags=["banks"])

# Mock bank storage - in production this would connect to the actual bank system
MOCK_BANKS = [
    {
        "name": "My Banks",
        "pedalboards": [
            {
                "bundle": "/usr/lib/lv2/default.pedalboard",
                "title": "Default",
                "broken": False,
            }
        ],
    }
]


@router.get("/load")
async def load_banks() -> list:
    """Load all pedalboard banks"""
    try:
        # In production, this would load banks from the file system
        return MOCK_BANKS
    except Exception as e:
        logger.error(f"Failed to load banks: {e}")
        raise HTTPException(status_code=500, detail="Failed to load banks")


@router.post("/save")
async def save_banks(banks: list) -> Dict[str, Any]:
    """Save the pedalboard banks"""
    try:
        # In production, this would save banks to the file system
        global MOCK_BANKS
        MOCK_BANKS = banks
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to save banks: {e}")
        raise HTTPException(status_code=500, detail="Failed to save banks")
