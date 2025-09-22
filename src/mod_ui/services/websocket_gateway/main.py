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

from src.mod_ui.services.websocket_gateway.models import (
    ClientConnection,
    EventSubscription,
    GatewayStats,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown"""
    global connection_manager, event_router, redis_subscriber

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

        # Store services in app state for access from endpoints
        app.state.connection_manager = connection_manager
        app.state.event_router = event_router
        app.state.redis_subscriber = redis_subscriber

        # Start services in background after HTTP server is ready
        def start_background_services():
            asyncio.create_task(event_router.start())
            asyncio.create_task(redis_subscriber.start())
            logger.info("Background services started")

        # Schedule services to start after yield
        asyncio.get_event_loop().call_soon(start_background_services)

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


# Create FastAPI application
app = FastAPI(
    title="MOD UI WebSocket Gateway Service",
    description="Dedicated real-time communication hub for all MOD UI services",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return {"status": "ok", "service": "websocket-gateway"}


@app.get("/status")
async def status():
    """Detailed service status"""
    global connection_manager, event_router, redis_subscriber

    status_info = {
        "service": "websocket-gateway",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }

    if connection_manager:
        stats = await connection_manager.get_stats()
        status_info.update(
            {
                "total_connections": stats.total_connections,
                "active_connections": stats.active_connections,
                "total_messages_sent": stats.total_messages_sent,
                "total_messages_received": stats.total_messages_received,
            }
        )

    if event_router:
        router_stats = await event_router.get_stats()
        status_info.update(
            {
                "events_processed": router_stats.events_processed,
                "active_subscriptions": router_stats.active_subscriptions,
            }
        )

    if redis_subscriber:
        status_info["redis_connected"] = redis_subscriber.is_connected()

    return status_info


@app.get("/connections")
async def list_connections():
    """List all active WebSocket connections"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    connections = await connection_manager.get_connection_info()
    return {
        "success": True,
        "connections": connections,
        "count": len(connections),
    }


@app.post("/broadcast")
async def broadcast_message(message: Dict[str, Any]):
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


@app.post("/broadcast/{event_type}")
async def broadcast_to_subscribers(event_type: str, message: Dict[str, Any]):
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


# Legacy message endpoints


@app.post("/legacy/stats")
async def send_stats(stats_data: Dict[str, Any]):
    """Send legacy stats message"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        cpu_load = float(stats_data.get("cpu_load", 0.0))
        xruns = int(stats_data.get("xruns", 0))

        count = await connection_manager.send_stats_message(cpu_load, xruns)

        return {
            "success": True,
            "message": "Stats sent",
            "clients_reached": count,
        }
    except Exception as e:
        return {"error": f"Failed to send stats: {str(e)}"}


@app.post("/legacy/sys_stats")
async def send_sys_stats(sys_stats_data: Dict[str, Any]):
    """Send legacy system stats message"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        mem_load = float(sys_stats_data.get("mem_load", 0.0))
        cpu_freq = str(sys_stats_data.get("cpu_freq", "0"))
        cpu_temp = str(sys_stats_data.get("cpu_temp", "0"))

        count = await connection_manager.send_sys_stats_message(
            mem_load, cpu_freq, cpu_temp
        )

        return {
            "success": True,
            "message": "System stats sent",
            "clients_reached": count,
        }
    except Exception as e:
        return {"error": f"Failed to send system stats: {str(e)}"}


@app.post("/legacy/transport")
async def send_transport(transport_data: Dict[str, Any]):
    """Send legacy transport message"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        rolling = bool(transport_data.get("rolling", False))
        bpb = float(transport_data.get("bpb", 4.0))
        bpm = float(transport_data.get("bpm", 120.0))
        sync = str(transport_data.get("sync", "none"))

        count = await connection_manager.send_transport_message(rolling, bpb, bpm, sync)

        return {
            "success": True,
            "message": "Transport sent",
            "clients_reached": count,
        }
    except Exception as e:
        return {"error": f"Failed to send transport: {str(e)}"}


@app.post("/legacy/loading_start")
async def send_loading_start(loading_data: Dict[str, Any]):
    """Send legacy loading start message"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        empty = bool(loading_data.get("empty", True))
        modified = bool(loading_data.get("modified", False))

        count = await connection_manager.send_loading_start_message(empty, modified)

        return {
            "success": True,
            "message": "Loading start sent",
            "clients_reached": count,
        }
    except Exception as e:
        return {"error": f"Failed to send loading start: {str(e)}"}


@app.post("/legacy/loading_end")
async def send_loading_end(loading_data: Dict[str, Any]):
    """Send legacy loading end message"""
    global connection_manager

    if not connection_manager:
        return {"error": "Connection manager not available"}

    try:
        snapshot_id = int(loading_data.get("snapshot_id", 0))

        count = await connection_manager.send_loading_end_message(snapshot_id)

        return {
            "success": True,
            "message": "Loading end sent",
            "clients_reached": count,
        }
    except Exception as e:
        return {"error": f"Failed to send loading end: {str(e)}"}


# Health and monitoring endpoints


@app.get("/health")
async def health_check():
    """Check health of WebSocket gateway services"""
    global connection_manager, event_router, redis_subscriber

    try:
        health_info = {
            "success": True,
            "health": "healthy",
            "services": {},
            "timestamp": datetime.now().isoformat(),
        }

        if connection_manager:
            stats = await connection_manager.get_stats()
            health_info["services"]["connection_manager"] = "healthy"
            health_info["connected_clients"] = stats.active_connections
        else:
            health_info["services"]["connection_manager"] = "unavailable"

        if event_router:
            health_info["services"]["event_router"] = "healthy"
        else:
            health_info["services"]["event_router"] = "unavailable"

        if redis_subscriber:
            health_info["services"]["redis_subscriber"] = (
                "healthy" if redis_subscriber.is_connected() else "disconnected"
            )
        else:
            health_info["services"]["redis_subscriber"] = "unavailable"

        return health_info

    except Exception as e:
        return {
            "success": False,
            "health": "unhealthy",
            "error": str(e),
            "services": {
                "connection_manager": "unknown",
                "event_router": "unknown",
                "redis_subscriber": "unknown",
            },
        }


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
