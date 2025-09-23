"""
WebSocket Gateway Service

Dedicated microservice for managing WebSocket connections and real-time communication.
This service acts as a central hub for all real-time events from multiple MOD UI services.
"""

import asyncio
import json
import logging
import os
import signal
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from mod_ui.common import ServiceClient
from src.mod_ui.services.websocket_gateway.models import (
    ClientConnection,
    EventSubscription,
    GatewayStats,
)

# Import API routers
from src.mod_ui.services.websocket_gateway.routers import (
    banks,
    broadcast,
    connections,
    effects,
    favorites,
    health,
    legacy,
    lv2,
    pedalboard,
    snapshots,
    system,
    updates,
    utilities,
)
from src.mod_ui.services.websocket_gateway.services.connection_manager import (
    ConnectionManager,
)
from src.mod_ui.services.websocket_gateway.services.event_router import EventRouter
from src.mod_ui.services.websocket_gateway.services.redis_subscriber import (
    RedisEventSubscriber,
)
from src.mod_ui.services.websocket_gateway.utils.event_types import EventType

# Global service instances
connection_manager: Optional[ConnectionManager] = None
event_router: Optional[EventRouter] = None
redis_subscriber: Optional[RedisEventSubscriber] = None
service_client: Optional[ServiceClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown"""
    global connection_manager, event_router, redis_subscriber, service_client

    logger = logging.getLogger(__name__)
    logger.info("Starting WebSocket Gateway Service...")

    try:
        # Initialize connection manager (lightweight, no async operations)
        connection_manager = ConnectionManager()
        logger.info("Connection manager initialized")

        # Initialize event router (lightweight, creates task but doesn't block)
        event_router = EventRouter(connection_manager)

        # Initialize Redis event subscriber
        redis_subscriber = RedisEventSubscriber(event_router)

        # Initialize service client for backend communication
        service_client = ServiceClient()
        logger.info("Service client initialized")

        # Store services in app state for access from endpoints
        app.state.connection_manager = connection_manager
        app.state.event_router = event_router
        app.state.redis_subscriber = redis_subscriber
        app.state.service_client = service_client

        # Inject services into routers
        health.inject_services(connection_manager, event_router, redis_subscriber)
        connections.inject_services(connection_manager)
        broadcast.inject_services(connection_manager, event_router)
        legacy.inject_services(connection_manager)
        system.inject_services(service_client)

        # Start services synchronously before yielding
        await event_router.start()
        await redis_subscriber.start()

        logger.info("WebSocket Gateway Service startup complete")

        yield

    except Exception as e:
        logger.error(f"Failed to start WebSocket Gateway Service: {e}")
        raise

    finally:
        logger.info("Shutting down WebSocket Gateway Service...")

        # Close Redis subscriber
        if redis_subscriber:
            try:
                await redis_subscriber.stop()
            except Exception as e:
                logger.error(f"Error stopping Redis subscriber: {e}")

        # Close event router
        if event_router:
            try:
                await event_router.stop()
            except Exception as e:
                logger.error(f"Error stopping event router: {e}")

        logger.info("WebSocket Gateway Service shutdown complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown"""
    global connection_manager, event_router, service_client

    logger = logging.getLogger(__name__)
    logger.info("Starting WebSocket Gateway Service...")

    try:
        # Initialize connection manager (lightweight, no async operations)
        connection_manager = ConnectionManager()
        logger.info("Connection manager initialized")

        # Initialize event router (lightweight, creates task but doesn't block)
        event_router = EventRouter(connection_manager)

        # Initialize service client for backend communication
        service_client = ServiceClient()
        logger.info("Service client initialized")

        # Store services in app state for access from endpoints
        app.state.connection_manager = connection_manager
        app.state.event_router = event_router
        app.state.service_client = service_client

        # Inject services into routers
        health.inject_services(
            connection_manager, event_router, None
        )  # No redis subscriber yet
        connections.inject_services(connection_manager)
        broadcast.inject_services(connection_manager, event_router)
        legacy.inject_services(connection_manager)
        system.inject_services(service_client)

        logger.info("WebSocket Gateway Service startup complete")

    except Exception as e:
        logger.error(f"Failed to start WebSocket Gateway Service: {e}")
        raise

    yield

    logger.info("Shutting down WebSocket Gateway Service...")


# Create FastAPI application
app = FastAPI(
    title="Madeline Web UI Gateway",
    description="Dedicated real-time communication hub for all MOD UI services",
    version="1.0.0",
    lifespan=lifespan,
)

# Include API routers
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(connections.router, prefix="/api/connections", tags=["connections"])
app.include_router(broadcast.router, prefix="/api/broadcast", tags=["broadcast"])
app.include_router(legacy.router, prefix="/api/legacy", tags=["legacy"])


@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return {"status": "ok", "service": "websocket-gateway"}


@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return {"status": "ok", "service": "websocket-gateway"}


# Client management endpoints (from Session Service v2 realtime.py)


@app.get("/clients")
async def list_connected_clients():
    """List all connected WebSocket clients"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        connections = await connection_manager.get_connection_info()
        clients = [
            {
                "client_id": conn["client_id"],
                "connected_at": datetime.fromtimestamp(
                    conn["connected_at"]
                ).isoformat(),
                "last_activity": datetime.fromtimestamp(
                    conn["last_activity"]
                ).isoformat(),
                "messages_sent": conn["messages_sent"],
                "messages_received": conn["messages_received"],
                "subscription_count": len(conn.get("subscriptions", [])),
            }
            for conn in connections
        ]

        return {
            "success": True,
            "clients": clients,
            "count": len(clients),
        }
    except Exception as e:
        return {"error": f"Failed to list clients: {str(e)}"}


@app.get("/clients/{client_id}")
async def get_client_info(client_id: str):
    """Get information about a specific client"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        connections = await connection_manager.get_connection_info()
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


@app.post("/clients/{client_id}/disconnect")
async def disconnect_client(client_id: str):
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


@app.post("/clients/{client_id}/send")
async def send_message_to_client(client_id: str, message: Dict[str, Any]):
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


# Event management endpoints


@app.get("/events/types")
async def list_event_types():
    """List all available event types"""
    try:
        event_types = [event_type.value for event_type in EventType]

        return {"success": True, "event_types": event_types, "count": len(event_types)}
    except Exception as e:
        return {"error": f"Failed to list event types: {str(e)}"}


@app.post("/events/publish")
async def publish_event(event_data: Dict[str, Any]):
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for client connections"""
    global connection_manager, event_router

    logger = logging.getLogger(__name__)

    if not connection_manager or not event_router:
        await websocket.close(code=1011, reason="Gateway services not available")
        return

    client_id = None

    try:
        await websocket.accept()

        # Register connection
        client_id = await connection_manager.add_connection(websocket)
        logger.info(f"WebSocket client connected: {client_id}")

        # Send initial welcome message
        await connection_manager.send_to_client(
            client_id,
            {
                "type": "welcome",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat(),
                "gateway_version": "1.0.0",
            },
        )

        # Send initial status from all services
        await event_router.send_initial_status(client_id)

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                await event_router.handle_client_message(client_id, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                await connection_manager.send_to_client(
                    client_id,
                    {
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat(),
                    },
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {client_id or 'unknown'}")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        if client_id and connection_manager:
            await connection_manager.remove_connection(client_id)


# Development server entry point
async def main():
    """Main entry point for development server"""
    import uvicorn

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, _frame):
        logger.info("Received signal %d, shutting down...", signum)
        asyncio.get_event_loop().stop()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.getenv("WEBSOCKET_GATEWAY_PORT", "8081")),
        log_level="info",
        access_log=True,
    )

    server = uvicorn.Server(config)

    try:
        logger.info("Starting WebSocket Gateway Service on http://0.0.0.0:8081")
        await server.serve()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
