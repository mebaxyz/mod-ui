"""
WebSocket Router

Handles WebSocket endpoint for real-time communication.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .connection_manager import (
    handle_websocket_command,
    manager,
    send_websocket_initialization,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["websocket"])


@router.websocket("/websocket")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication

    Handles the main WebSocket connection that the MOD UI frontend
    uses for real-time parameter updates, plugin management, and
    transport control.
    """
    logger.info(f"WebSocket connection attempt from {websocket.client}")

    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        await manager.connect(websocket)

        # Send initialization sequence that frontend expects
        await send_websocket_initialization(websocket)

    except Exception as e:
        logger.error(f"Error accepting WebSocket connection: {e}")
        await websocket.close(code=1000, reason="Connection error")
        return

    # Check for session availability
    session = None
    try:
        # Try to get session instance (may not be available during development)
        from mod.session import SESSION

        session = SESSION if SESSION else None
        if session:
            logger.debug("WebSocket connected, SESSION available")
    except ImportError:
        logger.debug("SESSION module not available")
    except Exception as e:
        logger.error(f"Error accessing SESSION: {e}")

    try:
        while True:
            message = await websocket.receive_text()
            logger.debug(f"WebSocket received: {message}")

            # Handle pong messages (keepalive)
            if message == "pong":
                continue

            # Parse command and data
            if " " in message:
                cmd, data = message.split(" ", 1)
            else:
                cmd = message
                data = ""

            # Process WebSocket commands
            await handle_websocket_command(websocket, cmd, data, session)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket connection closed")
        # Notify session about WebSocket disconnection if available
        if session:
            try:
                logger.debug("WebSocket disconnected, SESSION available")
            except Exception as e:
                logger.error(f"Error notifying SESSION about WebSocket disconnect: {e}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
