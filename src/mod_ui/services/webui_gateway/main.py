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

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from mod_ui.common import ServiceClient
from src.mod_ui.services.webui_gateway.models import (
    ClientConnection,
    EventSubscription,
    GatewayStats,
)

# Import API routers
from src.mod_ui.services.webui_gateway.routers import (  # banks,; effects,; favorites,; lv2,; pedalboard,; snapshots,; updates,; utilities
    broadcast,
    connections,
    health,
    legacy,
    system,
)
from src.mod_ui.services.webui_gateway.services.connection_manager import (
    ConnectionManager,
)
from src.mod_ui.services.webui_gateway.services.event_router import EventRouter
from src.mod_ui.services.webui_gateway.services.redis_subscriber import (
    RedisEventSubscriber,
)
from src.mod_ui.services.webui_gateway.utils.event_types import EventType

# Global service instances
connection_manager: Optional[ConnectionManager] = None
event_router: Optional[EventRouter] = None
redis_subscriber: Optional[RedisEventSubscriber] = None
service_client: Optional[ServiceClient] = None


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
