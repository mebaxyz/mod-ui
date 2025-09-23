"""
Snapshots API Router

Handles pedalboard snapshot management for the WebSocket Gateway.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/snapshot", tags=["snapshots"])

# Mock snapshot storage - in production this would connect to the actual snapshot system
MOCK_SNAPSHOTS = {
    0: {"name": "Default", "id": 0},
    1: {"name": "Clean", "id": 1},
    2: {"name": "Drive", "id": 2},
}


@router.get("/name")
async def get_snapshot_name(id: int) -> Dict[str, Any]:
    """Get the name of a specific snapshot"""
    try:
        snapshot = MOCK_SNAPSHOTS.get(id)
        if snapshot is None:
            return {"ok": False, "name": "Default"}

        return {"ok": True, "name": snapshot["name"]}
    except Exception as e:
        logger.error(f"Failed to get snapshot name for id {id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get snapshot name")


@router.post("/save")
async def save_snapshot() -> Dict[str, Any]:
    """Save the current state as a snapshot"""
    try:
        # In production, this would save the current pedalboard state
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}")
        raise HTTPException(status_code=500, detail="Failed to save snapshot")


@router.get("/saveas")
async def save_snapshot_as(title: str) -> Dict[str, Any]:
    """Save the current state as a new snapshot"""
    try:
        # In production, this would create a new snapshot
        new_id = max(MOCK_SNAPSHOTS.keys()) + 1
        MOCK_SNAPSHOTS[new_id] = {"name": title, "id": new_id}

        return {"ok": True, "id": new_id, "title": title}
    except Exception as e:
        logger.error(f"Failed to save snapshot as '{title}': {e}")
        raise HTTPException(status_code=500, detail="Failed to save snapshot")


@router.get("/rename")
async def rename_snapshot(id: int, title: str) -> Dict[str, Any]:
    """Rename a snapshot"""
    try:
        if id not in MOCK_SNAPSHOTS:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        MOCK_SNAPSHOTS[id]["name"] = title
        return {"ok": True, "title": title}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename snapshot {id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to rename snapshot")


@router.get("/remove")
async def remove_snapshot(id: int) -> Dict[str, Any]:
    """Remove a snapshot"""
    try:
        if id not in MOCK_SNAPSHOTS:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        del MOCK_SNAPSHOTS[id]
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove snapshot {id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove snapshot")


@router.get("/list")
async def list_snapshots() -> Any:
    """Get a list of all snapshots"""
    try:
        snapshots = {id: snapshot["name"] for id, snapshot in MOCK_SNAPSHOTS.items()}
        return snapshots
    except Exception as e:
        logger.error(f"Failed to list snapshots: {e}")
        raise HTTPException(status_code=500, detail="Failed to list snapshots")


@router.get("/load")
async def load_snapshot(id: int) -> Dict[str, Any]:
    """Load a specific snapshot"""
    try:
        if id not in MOCK_SNAPSHOTS:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        # In production, this would load the snapshot
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load snapshot {id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load snapshot")
