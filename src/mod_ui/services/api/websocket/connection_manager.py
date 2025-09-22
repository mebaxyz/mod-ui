"""
WebSocket Manager

Handles WebSocket connections and real-time communication for the MOD UI.
"""

import logging
from typing import List

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        # Note: websocket.accept() should be called before this method
        self.active_connections.append(websocket)
        logger.info(
            f"WebSocket connected, {len(self.active_connections)} total connections"
        )

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            f"WebSocket disconnected, {len(self.active_connections)} total connections"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                # Remove broken connection
                self.disconnect(connection)


# Global connection manager instance
manager = ConnectionManager()


async def send_websocket_initialization(websocket: WebSocket):
    """
    Send initialization sequence that frontend expects

    This sends the loading_start and loading_end messages
    that the MOD UI frontend requires to properly initialize.
    """
    try:
        # Send loading_start with default parameters (empty=0, modified=0)
        # This tells the frontend to start the loading process
        await websocket.send_text("loading_start 0 0")
        logger.debug("Sent loading_start")

        # Send loading_end with snapshot ID 0 (default/empty pedalboard)
        # This tells the frontend the loading is complete
        await websocket.send_text("loading_end 0")
        logger.debug("Sent loading_end")

    except Exception as e:
        logger.error(f"Error sending WebSocket initialization: {e}")


async def handle_websocket_command(
    websocket: WebSocket, cmd: str, data: str, session=None
):
    """
    Handle WebSocket commands from the frontend

    Processes various commands sent by the MOD UI frontend including
    parameter changes, plugin positioning, transport controls, etc.
    """
    try:
        if cmd == "data_ready":
            # Handle data ready acknowledgment
            counter = int(data) if data else 0
            if session:
                session.ws_data_ready(counter)
            logger.debug(f"Data ready: {counter}")

        elif cmd == "param_set":
            # Handle parameter changes: param_set port value
            parts = data.split(" ", 2)
            if len(parts) >= 2:
                port = parts[0]
                value = float(parts[1])
                if session:
                    session.ws_parameter_set(port, value, websocket)
                logger.debug(f"Parameter set: {port} = {value}")

        elif cmd == "patch_get":
            # Handle patch get request: patch_get instance uri
            parts = data.split(" ", 2)
            if len(parts) >= 2:
                inst = parts[0]
                uri = parts[1]
                if session:
                    session.ws_patch_get(inst, uri, websocket)
                logger.debug(f"Patch get: {inst} {uri}")

        elif cmd == "patch_set":
            # Handle patch set: patch_set instance uri type value
            parts = data.split(" ", 3)
            if len(parts) >= 4:
                inst = parts[0]
                uri = parts[1]
                vtype = parts[2]
                value = parts[3]
                if session:
                    session.ws_patch_set(inst, uri, vtype, value, websocket)
                logger.debug(f"Patch set: {inst} {uri} {vtype} {value}")

        elif cmd == "plugin_pos":
            # Handle plugin position: plugin_pos instance x y
            parts = data.split(" ", 3)
            if len(parts) >= 3:
                inst = parts[0]
                x = float(parts[1])
                y = float(parts[2])
                if session:
                    session.ws_plugin_position(inst, x, y, websocket)
                logger.debug(f"Plugin position: {inst} ({x}, {y})")

        elif cmd == "pb_size":
            # Handle pedalboard size: pb_size width height
            parts = data.split(" ", 2)
            if len(parts) >= 2:
                width = int(float(parts[0]))
                height = int(float(parts[1]))
                if session:
                    session.ws_pedalboard_size(width, height)
                logger.debug(f"Pedalboard size: {width}x{height}")

        elif cmd == "transport-bpm":
            # Handle transport BPM changes
            bpm = float(data) if data else 120.0
            if session:
                # Note: Original uses gen.Task, we'll need to adapt this
                logger.debug(f"Transport BPM: {bpm}")
            else:
                logger.debug(f"Transport BPM: {bpm} (SESSION not available)")

        elif cmd == "transport-rolling":
            # Handle transport start/stop
            rolling = bool(int(data)) if data else False
            if session:
                logger.debug(f"Transport rolling: {rolling}")
            else:
                logger.debug(f"Transport rolling: {rolling} (SESSION not available)")

        else:
            logger.warning(f"Unknown WebSocket command: {cmd} {data}")
            # Echo back for unknown commands during development
            await websocket.send_text(f"Unknown command: {cmd}")

    except ValueError as e:
        logger.error(f"Error parsing WebSocket command '{cmd} {data}': {e}")
        await websocket.send_text(f"Error: Invalid command format")
    except Exception as e:
        logger.error(f"Error handling WebSocket command '{cmd} {data}': {e}")
        await websocket.send_text(f"Error: {str(e)}")
