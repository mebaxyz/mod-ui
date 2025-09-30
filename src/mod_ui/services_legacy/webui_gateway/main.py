"""
MOD UI WebUI Gateway - Enhanced with Auto-Reconnecting ServiceBus

This provides exactly what you wanted:
1. Define connection once ✅
2. Define topics and handlers ✅
3. Everything else automatic ✅
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

# Import ServiceBus components
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from redis.exceptions import ConnectionError, RedisError, TimeoutError
from servicebus import Service, ServiceEvent, get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResilientServiceBus:
    """
    Auto-reconnecting ServiceBus that handles all the boring stuff automatically

    Usage:
        bus = ResilientServiceBus("my_service")
        bus.on_event("websocket_broadcast", my_handler)
        await bus.start()  # That's it! Everything else is automatic
    """

    def __init__(self, service_name: str, redis_url: Optional[str] = None):
        self.service_name = service_name
        self.config = get_config()
        self._redis_url = redis_url or self.config.redis_url

        # State management
        self._is_running = False
        self._should_stop = False
        self._current_service: Optional[Service] = None
        self._redis_client: Optional[redis.Redis] = None

        # Event handlers
        self._event_handlers: Dict[str, Callable[[ServiceEvent], Awaitable[None]]] = {}

        # Reconnection settings
        self._reconnect_delay = 1.0  # Start with 1 second
        self._max_reconnect_delay = 60.0  # Max 1 minute between attempts
        self._reconnect_backoff = 1.5  # Exponential backoff multiplier
        self._last_connection_time = 0
        self._connection_failures = 0

        # Background tasks
        self._health_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None

        logger.info(f"ResilientServiceBus created for service '{service_name}'")

    def on_event(
        self, event_type: str, handler: Callable[[ServiceEvent], Awaitable[None]]
    ) -> None:
        """Register an event handler - SIMPLE INTERFACE"""
        self._event_handlers[event_type] = handler
        logger.info(f"Registered handler for event type '{event_type}'")

        # If already running, subscribe immediately
        if self._current_service and self._is_running:
            try:
                self._current_service.subscribe_to_event(event_type, handler)
                logger.info(
                    f"Immediately subscribed to '{event_type}' (service already running)"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to immediately subscribe to '{event_type}': {e}"
                )

    async def start(self) -> None:
        """Start the resilient ServiceBus - SIMPLE INTERFACE"""
        if self._is_running:
            logger.warning(
                f"ResilientServiceBus for '{self.service_name}' is already running"
            )
            return

        logger.info(f"Starting ResilientServiceBus for '{self.service_name}'...")
        self._should_stop = False

        # Start the connection management
        await self._ensure_connection()

        # Start background health monitoring
        self._health_task = asyncio.create_task(self._health_monitoring_loop())

        self._is_running = True
        logger.info(
            f"ResilientServiceBus for '{self.service_name}' started successfully"
        )

    async def stop(self) -> None:
        """Stop the resilient ServiceBus"""
        if not self._is_running:
            return

        logger.info(f"Stopping ResilientServiceBus for '{self.service_name}'...")
        self._should_stop = True
        self._is_running = False

        # Cancel background tasks
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        # Clean shutdown of current service
        await self._disconnect()

        logger.info(f"ResilientServiceBus for '{self.service_name}' stopped")

    async def publish_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Publish an event - handles connection issues automatically"""
        if not self._current_service:
            logger.warning(
                f"Cannot publish event '{event_type}' - no active connection"
            )
            return False

        try:
            await self._current_service.publish_event(event_type, data)
            return True
        except Exception as e:
            logger.error(f"Failed to publish event '{event_type}': {e}")
            # Trigger reconnection
            asyncio.create_task(self._handle_connection_failure())
            return False

    async def call_service(
        self, service_name: str, method: str, *args, **kwargs
    ) -> Any:
        """Call another service - handles connection issues automatically"""
        if not self._current_service:
            raise RuntimeError("No active ServiceBus connection")

        try:
            client = self._current_service._client
            return await client.call_service(
                service_name, method, {"args": args, "kwargs": kwargs}
            )
        except Exception as e:
            logger.error(f"Failed to call {service_name}.{method}: {e}")
            # Trigger reconnection for next time
            asyncio.create_task(self._handle_connection_failure())
            raise

    @property
    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self._current_service is not None and self._is_running

    @property
    def connection_info(self) -> Dict[str, Any]:
        """Get connection status info"""
        return {
            "service_name": self.service_name,
            "is_connected": self.is_connected,
            "is_running": self._is_running,
            "connection_failures": self._connection_failures,
            "last_connection_time": self._last_connection_time,
            "registered_events": list(self._event_handlers.keys()),
        }

    # Private methods - all the "boring stuff" happens here

    async def _ensure_connection(self) -> bool:
        """Ensure we have a working ServiceBus connection"""
        if self._current_service:
            # Test existing connection
            if await self._test_connection():
                return True
            else:
                # Connection is dead, clean it up
                await self._disconnect()

        # Create new connection
        return await self._create_connection()

    async def _create_connection(self) -> bool:
        """Create a new ServiceBus connection"""
        try:
            logger.info(
                f"Creating new ServiceBus connection for '{self.service_name}'..."
            )

            # Create Redis client
            self._redis_client = redis.Redis.from_url(
                self._redis_url,
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test Redis connection
            await self._redis_client.ping()

            # Create ServiceBus service
            self._current_service = Service(
                self.service_name,
                redis_client=self._redis_client,
                enable_discovery=True,
                enable_events=True,
                enable_metrics=True,
            )

            # Start the service
            await self._current_service.start()

            # Subscribe to all registered events
            for event_type, handler in self._event_handlers.items():
                self._current_service.subscribe_to_event(event_type, handler)
                logger.info(f"Subscribed to event '{event_type}'")

            # Update connection state
            self._last_connection_time = time.time()
            self._connection_failures = 0
            self._reconnect_delay = 1.0  # Reset backoff

            logger.info(f"ServiceBus connection established for '{self.service_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create ServiceBus connection: {e}")
            self._connection_failures += 1
            await self._disconnect()
            return False

    async def _disconnect(self) -> None:
        """Clean up current connection"""
        if self._current_service:
            try:
                await self._current_service.stop()
            except Exception as e:
                logger.warning(f"Error stopping service: {e}")
            finally:
                self._current_service = None

        if self._redis_client:
            try:
                await self._redis_client.close()
            except Exception as e:
                logger.warning(f"Error closing Redis client: {e}")
            finally:
                self._redis_client = None

    async def _test_connection(self) -> bool:
        """Test if current connection is healthy"""
        if not self._current_service or not self._redis_client:
            return False

        try:
            # Test Redis connection
            await self._redis_client.ping()

            # Test ServiceBus by calling ping
            client = self._current_service._client
            await client.call_service(self.service_name, "ping")

            return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            return False

    async def _handle_connection_failure(self) -> None:
        """Handle connection failure - trigger reconnection"""
        if self._should_stop:
            return

        logger.warning(f"Connection failure detected for '{self.service_name}'")

        # Cancel any existing reconnect task
        if self._reconnect_task and not self._reconnect_task.done():
            return  # Already reconnecting

        # Start reconnection task
        self._reconnect_task = asyncio.create_task(self._reconnection_loop())

    async def _reconnection_loop(self) -> None:
        """Background reconnection loop"""
        while not self._should_stop and not await self._ensure_connection():
            # Calculate delay with exponential backoff
            delay = min(self._reconnect_delay, self._max_reconnect_delay)
            logger.info(f"Reconnection failed, retrying in {delay:.1f}s...")

            await asyncio.sleep(delay)
            self._reconnect_delay *= self._reconnect_backoff

        if not self._should_stop:
            logger.info(f"Reconnection successful for '{self.service_name}'")

    async def _health_monitoring_loop(self) -> None:
        """Background health monitoring"""
        while not self._should_stop:
            try:
                if not await self._test_connection():
                    logger.warning(f"Health check failed for '{self.service_name}'")
                    await self._handle_connection_failure()
                else:
                    # Connection is healthy
                    pass

                # Check every 30 seconds
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(10)


# ENHANCED GLOBALS - Just what we need
resilient_bus: Optional[ResilientServiceBus] = None
connection_manager: Optional["ConnectionManager"] = None


class ConnectionManager:
    """Simple WebSocket connection manager"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.logger = logging.getLogger(f"{__name__}.ConnectionManager")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.logger.info(
                f"WebSocket disconnected. Total: {len(self.active_connections)}"
            )

    async def broadcast_event(self, event_type: str, data: dict):
        if not self.active_connections:
            return

        message = {
            "event_type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time(),
        }

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                self.logger.error(f"WebSocket send error: {e}")
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)

        if self.active_connections:
            self.logger.info(
                f"Broadcasted {event_type} to {len(self.active_connections)} clients"
            )


# Create connection manager
connection_manager = ConnectionManager()


# SUPER SIMPLE EVENT HANDLER - This is all you need to define!
async def handle_websocket_broadcast(event):
    """Handle websocket_broadcast events - SUPER SIMPLE!"""
    try:
        logger.info(f"📡 Received: {event.event_type}")

        # Extract data
        event_data = event.data
        message = event_data.get("content", "")
        message_type = event_data.get("message_type", "unknown")

        # Broadcast to WebSocket clients
        if connection_manager and message:
            await connection_manager.broadcast_event("websocket_message", event_data)
            logger.info(f"✅ Broadcasted {message_type}: {message}")

    except Exception as e:
        logger.error(f"❌ Error handling websocket broadcast: {e}")


async def initialize_enhanced_servicebus():
    """ENHANCED ServiceBus initialization - This is ALL you need!"""
    global resilient_bus

    try:
        logger.info("🚀 Initializing ENHANCED ServiceBus with auto-reconnection...")

        # 1️⃣ DEFINE CONNECTION ONCE
        resilient_bus = ResilientServiceBus("webui_gateway")

        # 2️⃣ DEFINE TOPICS AND HANDLERS
        resilient_bus.on_event("websocket_broadcast", handle_websocket_broadcast)

        # 3️⃣ START - EVERYTHING ELSE IS AUTOMATIC!
        await resilient_bus.start()

        # Store in app state for endpoints
        app.state.resilient_bus = resilient_bus

        logger.info("🎉 ENHANCED ServiceBus ready! Auto-reconnection active!")

    except Exception as e:
        logger.error(f"❌ ServiceBus initialization failed: {e}")
        import traceback

        traceback.print_exc()
        resilient_bus = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """MINIMAL lifespan - no complex stuff!"""
    logger.info("🌟 Starting WebUI Gateway with ENHANCED ServiceBus...")

    # Schedule enhanced initialization
    asyncio.create_task(initialize_enhanced_servicebus())

    yield

    # Simple cleanup
    if resilient_bus:
        await resilient_bus.stop()
        logger.info("🛑 ENHANCED ServiceBus stopped")


# FastAPI app
app = FastAPI(
    title="MOD UI WebUI Gateway - ENHANCED",
    description="WebUI Gateway with auto-reconnecting ServiceBus (integrated)",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = "/app/html"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def read_root():
    return {
        "message": "MOD UI WebUI Gateway - ENHANCED with auto-reconnecting ServiceBus"
    }


@app.get("/test")
async def test_endpoint():
    return {"status": "ok", "message": "HTTP server working with ENHANCED ServiceBus!"}


@app.get("/health")
async def health_check():
    """Health check with ResilientServiceBus info"""
    servicebus_info = {"status": "disconnected"}

    if resilient_bus:
        info = resilient_bus.connection_info
        servicebus_info = {
            "status": "connected" if info["is_connected"] else "disconnected",
            "connection_failures": info["connection_failures"],
            "registered_events": info["registered_events"],
            "auto_reconnection": "enabled ✅",
            "last_connection": info["last_connection_time"],
            "version": "enhanced_integrated",
        }

    return {
        "status": "healthy",
        "servicebus": servicebus_info,
        "websocket_connections": len(connection_manager.active_connections),
        "version": "ENHANCED",
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint"""
    await connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"📨 WebSocket message: {data}")
            await connection_manager.broadcast_event(
                "echo", {"message": f"Echo: {data}"}
            )
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)


@app.post("/api/broadcast")
async def broadcast_message(message_data: dict):
    """Broadcast messages - SUPER SIMPLE!"""
    try:
        # Local broadcast
        await connection_manager.broadcast_event("broadcast_message", message_data)

        # ServiceBus broadcast - ENHANCED CALL!
        if resilient_bus:
            success = await resilient_bus.publish_event(
                "websocket_broadcast", message_data
            )
            status = "✅ sent" if success else "⚠️ failed (will auto-retry)"
        else:
            status = "❌ no connection"

        return {
            "success": True,
            "message": "Message broadcasted",
            "servicebus_status": status,
        }

    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/service/{service_name}/call")
async def call_service(service_name: str, request_data: dict):
    """Call other services - SUPER SIMPLE!"""
    if not resilient_bus:
        raise HTTPException(status_code=503, detail="ServiceBus not available")

    try:
        method = request_data.get("method")
        args = request_data.get("args", [])
        kwargs = request_data.get("kwargs", {})

        if not method:
            raise HTTPException(status_code=400, detail="Method required")

        # ENHANCED SERVICE CALL!
        result = await resilient_bus.call_service(service_name, method, *args, **kwargs)
        return {"success": True, "result": result}

    except Exception as e:
        logger.error(f"Service call error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
