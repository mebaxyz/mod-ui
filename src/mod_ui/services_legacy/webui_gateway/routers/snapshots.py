"""
Snapshots API Router

Handles pedalboard snapshot management for the WebSocket Gateway.
"""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

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
async def save_snapshot_as(title: str, request: Request) -> Dict[str, Any]:
    """Save the current state as a new snapshot"""
    try:
        # In production, this would create a new snapshot
        new_id = max(MOCK_SNAPSHOTS.keys()) + 1
        MOCK_SNAPSHOTS[new_id] = {"name": title, "id": new_id}

        result = {"ok": True, "id": new_id, "title": title}

        # Broadcast snapshot save via WebSocket
        if result.get("ok"):
            await _notify_snapshot_save(request, new_id, title)

        return result
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
async def load_snapshot(id: int, request: Request) -> Dict[str, Any]:
    """Load a specific snapshot"""
    try:
        if id not in MOCK_SNAPSHOTS:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        snapshot = MOCK_SNAPSHOTS[id]

        # In production, this would load the snapshot
        result = {"ok": True}

        # Broadcast snapshot load via WebSocket
        if result.get("ok"):
            await _notify_snapshot_load(request, id, snapshot["name"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load snapshot {id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load snapshot")


async def _notify_snapshot_load(request: Request, snapshot_id: int, snapshot_name: str):
    """Notify webui-gateway to broadcast snapshot load WebSocket message via ServiceBus"""
    try:
        # WebSocket message format expected by frontend: "pedal_snapshot {index} {name}"
        websocket_message = f"pedal_snapshot {snapshot_id} {snapshot_name}"

        # Get service instance from app state
        service = request.app.state.service

        # Publish ServiceBus event for WebSocket broadcasting
        await service.publish_event(
            "websocket_broadcast",
            {
                "type": "legacy_websocket",
                "content": websocket_message,
                "message_type": "snapshot_load",
                "snapshot_id": snapshot_id,
                "snapshot_name": snapshot_name,
            },
        )

        logger.info(f"Published snapshot load event: {snapshot_id}/{snapshot_name}")

    except Exception as e:
        logger.error(f"Error publishing snapshot load event: {e}")
        # Don't re-raise - WebSocket notification failure shouldn't break the main operation


async def _notify_snapshot_save(request: Request, snapshot_id: int, snapshot_name: str):
    """Notify webui-gateway to broadcast snapshot save WebSocket message via ServiceBus"""
    try:
        # Custom WebSocket message format for snapshot save notification
        websocket_message = f"snapshot_saved {snapshot_id} {snapshot_name}"

        # Get service instance from app state
        service = request.app.state.service

        # Publish ServiceBus event for WebSocket broadcasting
        await service.publish_event(
            "websocket_broadcast",
            {
                "type": "legacy_websocket",
                "content": websocket_message,
                "message_type": "snapshot_save",
                "snapshot_id": snapshot_id,
                "snapshot_name": snapshot_name,
            },
        )

        logger.info(f"Published snapshot save event: {snapshot_id}/{snapshot_name}")

    except Exception as e:
        logger.error(f"Error publishing snapshot save event: {e}")
        # Don't re-raise - WebSocket notification failure shouldn't break the main operation
