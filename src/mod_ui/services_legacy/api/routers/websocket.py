"""
WebSocket Router

Handles WebSocket connections for the MOD UI API.
This provides backward compatibility for the original WebSocket protocol.
"""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["websocket"])

# Store active connections
active_connections: Dict[str, WebSocket] = {}


@router.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for MOD UI communication

    Handles the original WebSocket protocol for backward compatibility
    with the existing web client JavaScript code.
    """
    await websocket.accept()
    connection_id = f"ws_{id(websocket)}"
    active_connections[connection_id] = websocket

    logger.info(f"WebSocket connected: {connection_id}")

    try:
        # Send initial connection acknowledgment
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection_ack",
                    "data": {"connected": True, "connection_id": connection_id},
                }
            )
        )

        while True:
            # Wait for messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                logger.debug(f"WebSocket message received: {message}")

                # Handle different message types
                await handle_websocket_message(websocket, message)

            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON received: {e}")
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "data": {"message": "Invalid JSON format"}}
                    )
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up connection
        if connection_id in active_connections:
            del active_connections[connection_id]


async def handle_websocket_message(websocket: WebSocket, message: Dict[str, Any]):
    """Handle incoming WebSocket messages"""

    message_type = message.get("type", "unknown")
    data = message.get("data", {})

    if message_type == "ping":
        # Respond to ping with pong
        await websocket.send_text(
            json.dumps(
                {"type": "pong", "data": {"timestamp": data.get("timestamp", 0)}}
            )
        )

    elif message_type == "pedalboard_request":
        # Handle pedalboard data requests
        await websocket.send_text(
            json.dumps(
                {
                    "type": "pedalboard_data",
                    "data": {
                        "pedalboard": {
                            "title": "Empty Pedalboard",
                            "size": [0, 0],
                            "plugins": [],
                            "connections": [],
                        }
                    },
                }
            )
        )

    elif message_type == "system_info_request":
        # Handle system info requests
        await websocket.send_text(
            json.dumps(
                {
                    "type": "system_info",
                    "data": {
                        "version": "1.0.0",
                        "hardware": "MOD Duo",
                        "jack_sample_rate": 48000,
                        "jack_buffer_size": 256,
                    },
                }
            )
        )

    else:
        # Handle unknown message types
        logger.warning(f"Unknown WebSocket message type: {message_type}")
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "data": {"message": f"Unknown message type: {message_type}"},
                }
            )
        )


async def broadcast_to_all(message: Dict[str, Any]):
    """Broadcast a message to all connected WebSocket clients"""
    if not active_connections:
        return

    message_text = json.dumps(message)
    disconnected = []

    for connection_id, websocket in active_connections.items():
        try:
            await websocket.send_text(message_text)
        except Exception as e:
            logger.warning(f"Failed to send to {connection_id}: {e}")
            disconnected.append(connection_id)

    # Clean up disconnected clients
    for connection_id in disconnected:
        active_connections.pop(connection_id, None)


async def send_to_connection(connection_id: str, message: Dict[str, Any]):
    """Send a message to a specific WebSocket connection"""
    websocket = active_connections.get(connection_id)
    if websocket:
        try:
            await websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.warning(f"Failed to send to {connection_id}: {e}")
            active_connections.pop(connection_id, None)
    return False
