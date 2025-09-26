"""
Broadcast and Event Management API Router

Handles message broadcasting and event management endpoints for the WebSocket Gateway.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["broadcast"])

# Import global service instances (will be injected at runtime)
connection_manager = None
event_router = None

from src.mod_ui.services.webui_gateway.utils.event_types import EventType


def inject_services(cm, er):
    """Inject service instances for router use"""
    global connection_manager, event_router
    connection_manager = cm
    event_router = er


@router.post("/broadcast")
async def broadcast_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Broadcast a message to all connected clients"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    count = await connection_manager.broadcast_to_all(message)
    return {
        "success": True,
        "message": "Message broadcast",
        "clients_reached": count,
    }


@router.post("/broadcast/{event_type}")
async def broadcast_to_subscribers(
    event_type: str, message: Dict[str, Any]
) -> Dict[str, Any]:
    """Broadcast a message to clients subscribed to specific event type"""
    global event_router

    if not event_router:
        return {"error": "Event router not available"}

    try:
        event_type_enum = EventType(event_type)
        count = await event_router.broadcast_to_subscribers(event_type_enum, message)
        return {
            "success": True,
            "message": f"Message broadcast to {event_type} subscribers",
            "clients_reached": count,
        }
    except ValueError:
        return {"error": f"Invalid event type: {event_type}"}


@router.get("/events/types")
async def list_event_types() -> Dict[str, Any]:
    """List all available event types"""
    try:
        event_types = [event_type.value for event_type in EventType]

        return {"success": True, "event_types": event_types, "count": len(event_types)}
    except Exception as e:
        return {"error": f"Failed to list event types: {str(e)}"}


@router.post("/events/publish")
async def publish_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Publish an event through the gateway"""
    global event_router

    if not event_router:
        return {"error": "Event router not available"}

    try:
        event_type = event_data.get("event_type")
        data = event_data.get("data", {})

        if not event_type:
            return {"error": "event_type is required"}

        event_type_enum = EventType(event_type)
        await event_router.broadcast_to_subscribers(
            event_type_enum,
            {
                "type": "event",
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            },
        )

        return {
            "success": True,
            "event_type": event_type,
            "message": "Event published",
        }
    except ValueError:
        return {"error": f"Invalid event type: {event_type}"}
    except Exception as e:
        return {"error": f"Failed to publish event: {str(e)}"}
