"""
Connections and Client Management API Router

Handles WebSocket connection and client management endpoints for the WebSocket Gateway.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["connections"])

# Import global service instances (will be injected at runtime)
connection_manager = None


def inject_services(cm):
    """Inject service instances for router use"""
    global connection_manager
    connection_manager = cm


@router.get("/connections")
async def list_connections() -> Dict[str, Any]:
    """List all active WebSocket connections"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    connections = connection_manager.get_connection_info()
    return {
        "success": True,
        "connections": connections,
        "count": len(connections),
    }


@router.get("/clients")
async def list_connected_clients() -> Dict[str, Any]:
    """List all connected WebSocket clients"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        connections = connection_manager.get_connection_info()
        clients = [
            {
                "client_id": conn["client_id"],
                "connected_at": conn["connected_at"],
                "last_activity": conn["last_activity"],
                "messages_sent": conn["messages_sent"],
                "messages_received": conn["messages_received"],
                "subscription_count": len(conn.get("subscriptions", [])),
            }
            for conn in connections
        ]

        return {
            "success": True,
            "connections": clients,
            "count": len(clients),
        }
    except Exception as e:
        return {"error": f"Failed to list connections: {str(e)}"}


@router.get("/clients/{client_id}")
async def get_client_info(client_id: str) -> Dict[str, Any]:
    """Get information about a specific client"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        connections = connection_manager.get_connection_info()
        client_info = next(
            (conn for conn in connections if conn["client_id"] == client_id), None
        )

        if client_info is None:
            return {"error": "Client not found", "status_code": 404}

        return {
            "success": True,
            "client": {
                "client_id": client_id,
                "connected_at": datetime.fromtimestamp(
                    client_info["connected_at"]
                ).isoformat(),
                "last_activity": datetime.fromtimestamp(
                    client_info["last_activity"]
                ).isoformat(),
                "messages_sent": client_info["messages_sent"],
                "messages_received": client_info["messages_received"],
                "subscriptions": client_info.get("subscriptions", []),
            },
        }
    except Exception as e:
        return {"error": f"Failed to get client info: {str(e)}"}


@router.post("/clients/{client_id}/disconnect")
async def disconnect_client(client_id: str) -> Dict[str, Any]:
    """Disconnect a specific client"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        success = await connection_manager.remove_connection(client_id)

        if not success:
            return {"error": "Client not found", "status_code": 404}

        return {
            "success": True,
            "client_id": client_id,
            "message": "Client disconnected",
        }
    except Exception as e:
        return {"error": f"Failed to disconnect client: {str(e)}"}


@router.post("/clients/{client_id}/send")
async def send_message_to_client(
    client_id: str, message: Dict[str, Any]
) -> Dict[str, Any]:
    """Send a message to a specific client"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        message_data = {
            "type": "direct_message",
            "data": message,
            "timestamp": datetime.now().isoformat(),
        }

        success = await connection_manager.send_to_client(client_id, message_data)

        if not success:
            return {"error": "Client not found or not connected", "status_code": 404}

        return {"success": True, "client_id": client_id, "message": "Message sent"}
    except Exception as e:
        return {"error": f"Failed to send message: {str(e)}"}
