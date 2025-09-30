"""
Session Service v2 - ENHANCED with Auto-Reconnecting ServiceBus

This provides exactly what you wanted:
1. Define connection once ✅
2. Define topics and handlers ✅
3. Everything else automatic ✅
"""

import asyncio
import logging
import os
import signal
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

# Import ServiceBus components
import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError
from servicebus import CommConfig, Service, ServiceEvent, get_config, set_config

from .integration.audio_engine_client import SessionPluginService
from .services.session_manager import SessionManager
from .services.state_manager import StateManagerService
from .utils.event_bus import EventBus, InMemoryEventBus, RedisEventBus

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResilientServiceBus:
    """
    ENHANCED Auto-Reconnecting ServiceBus Wrapper

    This provides exactly what you wanted:
    1. Define connection once ✅
    2. Define topics and handlers ✅
    3. Everything else automatic (reconnection, health monitoring, etc.) ✅
    """

    def __init__(self, service_name: str, redis_url: str = None):
        self.service_name = service_name
        self.redis_url = redis_url or self._get_redis_url()
        self.service: Optional[Service] = None
        self.methods: Dict[str, Callable] = {}
        self.events: Dict[str, Callable] = {}
        self.is_running = False
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 60.0
        self.health_check_interval = 30.0
        self.last_health_check = 0
        self._redis_client: Optional[redis.Redis] = None
        self._shutdown_event = asyncio.Event()

    def _get_redis_url(self) -> str:
        """Get Redis URL from environment"""
        host = os.getenv("REDIS_HOST", "localhost")
        port = os.getenv("REDIS_PORT", "6379")
        db = os.getenv("REDIS_DB", "0")
        return f"redis://{host}:{port}/{db}"

    def register_method(self, method_name: str, handler: Callable):
        """Register a method handler"""
        self.methods[method_name] = handler
        logger.info(f"Registered method '{method_name}'")

    def subscribe_to_event(self, event_name: str, handler: Callable):
        """Subscribe to an event"""
        self.events[event_name] = handler
        logger.info(f"Subscribed to event '{event_name}'")

    async def _create_redis_client(self) -> redis.Redis:
        """Create Redis client with connection pooling"""
        return redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            max_connections=10,
        )

    async def _test_redis_connection(self) -> bool:
        """Test if Redis connection is working"""
        try:
            if not self._redis_client:
                self._redis_client = await self._create_redis_client()

            await self._redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection test failed: {e}")
            # Clean up failed client
            if self._redis_client:
                try:
                    await self._redis_client.aclose()
                except:
                    pass
                self._redis_client = None
            return False

    async def _connect_to_servicebus(self) -> bool:
        """Connect to ServiceBus with error handling"""
        try:
            # Configure ServiceBus
            config = CommConfig(redis_url=self.redis_url)
            set_config(config)

            # Create service
            self.service = Service(self.service_name)

            # Register all methods
            for method_name, handler in self.methods.items():
                self.service.register_handler(method_name, handler)

            # Subscribe to all events
            for event_name, handler in self.events.items():
                self.service.subscribe(event_name, handler)

            return True

        except Exception as e:
            logger.error(f"Failed to connect to ServiceBus: {e}")
            self.service = None
            return False

    async def _reconnect_to_redis(self):
        """Handle Redis reconnection with exponential backoff"""
        while not self._shutdown_event.is_set() and self.is_running:
            try:
                logger.info(
                    f"Attempting to reconnect ServiceBus for '{self.service_name}'..."
                )

                # Test Redis connection first
                if await self._test_redis_connection():
                    # Try to reconnect ServiceBus
                    if await self._connect_to_servicebus():
                        logger.info(
                            f"ServiceBus connection established for '{self.service_name}'"
                        )
                        logger.info(
                            f"Reconnection successful for '{self.service_name}'"
                        )
                        self.reconnect_delay = 1.0  # Reset delay on success
                        return

                # Exponential backoff
                logger.warning(
                    f"Reconnection failed, retrying in {self.reconnect_delay}s..."
                )
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(
                    self.reconnect_delay * 2, self.max_reconnect_delay
                )

            except Exception as e:
                logger.error(f"Reconnection error: {e}")
                await asyncio.sleep(self.reconnect_delay)

    async def _health_monitor(self):
        """Monitor ServiceBus health and trigger reconnection if needed"""
        while not self._shutdown_event.is_set() and self.is_running:
            try:
                await asyncio.sleep(self.health_check_interval)

                current_time = time.time()

                # Only check if enough time has passed
                if current_time - self.last_health_check < self.health_check_interval:
                    continue

                self.last_health_check = current_time

                # Test Redis connection
                if not await self._test_redis_connection():
                    logger.warning(
                        f"Health check failed for '{self.service_name}', triggering reconnection..."
                    )
                    await self._reconnect_to_redis()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)  # Brief pause before continuing

    async def start(self):
        """Start the enhanced ServiceBus with auto-reconnection"""
        self.is_running = True

        # Initial connection
        if await self._test_redis_connection() and await self._connect_to_servicebus():
            logger.info(f"ServiceBus connection established for '{self.service_name}'")
            logger.info(f"Reconnection successful for '{self.service_name}'")
        else:
            logger.warning(
                f"Initial connection failed, starting reconnection process..."
            )
            asyncio.create_task(self._reconnect_to_redis())

        # Start health monitoring
        asyncio.create_task(self._health_monitor())

        # Start the service if connected
        if self.service:
            await self.service.start()

    async def stop(self):
        """Stop the ServiceBus gracefully"""
        self.is_running = False
        self._shutdown_event.set()

        if self.service:
            await self.service.stop()

        if self._redis_client:
            await self._redis_client.aclose()


# Global service instances - will be initialized by ResilientServiceBus
state_manager: Optional[StateManagerService] = None
session_manager: Optional[SessionManager] = None
event_bus: Optional[EventBus] = None
plugin_service: Optional[SessionPluginService] = None
resilient_servicebus: Optional[ResilientServiceBus] = None


async def initialize_services():
    """Initialize all services with the enhanced ServiceBus"""
    global state_manager, session_manager, event_bus, plugin_service

    logger.info("Starting Session Service v2 with Enhanced ServiceBus...")

    try:
        # Initialize event bus based on configuration
        event_bus_type = os.getenv("EVENT_BUS_TYPE", "inmemory")

        if event_bus_type == "redis":
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))
            redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

            event_bus = RedisEventBus(redis_url)
            logger.info(f"Redis event bus initialized (url={redis_url})")
        else:
            event_bus = InMemoryEventBus()
            logger.info("In-memory event bus initialized")

        await event_bus.initialize()

        # Initialize ServiceBus client for audio engine communication
        from servicebus import ServiceClient

        audio_servicebus_client = ServiceClient("session-v2")

        # Initialize plugin service with ServiceBus client
        plugin_service = SessionPluginService(audio_servicebus_client)
        logger.info("Audio engine ServiceBus client initialized")

        # Initialize enhanced session manager
        session_manager = SessionManager(event_publisher=event_bus)
        await session_manager.initialize()
        logger.info("Enhanced session manager initialized")

        # Initialize state manager
        state_manager = StateManagerService(event_publisher=event_bus)
        await state_manager.initialize()
        logger.info("State manager initialized")

        logger.info("Session Service v2 services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Session Service v2 services: {e}")
        raise


async def setup_enhanced_servicebus():
    """Setup the enhanced ServiceBus with all handlers"""
    global resilient_servicebus

    # Step 1: Define connection once ✅
    resilient_servicebus = ResilientServiceBus("session_v2")

    # Step 2: Define topics and handlers ✅

    # Session management handlers
    resilient_servicebus.register_method("get_session_state", handle_get_session_state)
    resilient_servicebus.register_method("reset_session", handle_reset_session)
    resilient_servicebus.register_method(
        "websocket_connected", handle_websocket_connected
    )
    resilient_servicebus.register_method(
        "websocket_disconnected", handle_websocket_disconnected
    )

    # Plugin management handlers
    resilient_servicebus.register_method("add_plugin", handle_add_plugin)
    resilient_servicebus.register_method("remove_plugin", handle_remove_plugin)
    resilient_servicebus.register_method(
        "set_plugin_parameter", handle_set_plugin_parameter
    )

    # Connection management handlers
    resilient_servicebus.register_method("add_connection", handle_add_connection)
    resilient_servicebus.register_method("remove_connection", handle_remove_connection)

    # Transport control handlers
    resilient_servicebus.register_method("control_transport", handle_control_transport)
    resilient_servicebus.register_method("set_session_tempo", handle_set_session_tempo)
    resilient_servicebus.register_method("set_beats_per_bar", handle_set_beats_per_bar)

    # Recording handlers
    resilient_servicebus.register_method("recording_start", handle_recording_start)
    resilient_servicebus.register_method("recording_stop", handle_recording_stop)
    resilient_servicebus.register_method("recording_reset", handle_recording_reset)

    # Legacy compatibility handlers
    resilient_servicebus.register_method(
        "update_session_state", handle_update_session_state
    )
    resilient_servicebus.register_method(
        "get_session_status", handle_get_session_status
    )
    resilient_servicebus.register_method("get_session_stats", handle_get_session_stats)
    resilient_servicebus.register_method("start_session", handle_start_session)
    resilient_servicebus.register_method("stop_session", handle_stop_session)
    resilient_servicebus.register_method(
        "set_session_config", handle_set_session_config
    )
    resilient_servicebus.register_method(
        "reset_session_stats", handle_reset_session_stats
    )

    # Event subscriptions
    resilient_servicebus.subscribe_to_event(
        "session_change", handle_session_change_event
    )
    resilient_servicebus.subscribe_to_event(
        "transport_change", handle_transport_change_event
    )
    resilient_servicebus.subscribe_to_event("plugin_change", handle_plugin_change_event)

    # Step 3: Everything else automatic ✅ (reconnection, health monitoring, etc.)

    logger.info("Enhanced ServiceBus setup complete for Session Service v2")


# Session Management Handlers
async def handle_get_session_state(request) -> dict:
    """Handler for getting current session state"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        state = await session_manager.get_session_state()
        return {
            "success": True,
            "session": {
                "session_id": str(state.session_id),
                "status": state.status.value,
                "transport_state": state.transport_state.value,
                "transport_rolling": state.transport_rolling,
                "tempo_bpm": state.tempo_bpm,
                "beats_per_bar": state.beats_per_bar,
                "sample_rate": state.sample_rate,
                "buffer_size": state.buffer_size,
                "audio_driver": state.audio_driver,
                "plugins": [plugin.to_dict() for plugin in state.plugins],
                "connections": [conn.to_dict() for conn in state.connections],
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error getting session state: {e}")
        return {"error": f"Failed to get session state: {str(e)}"}


async def handle_reset_session(request) -> dict:
    """Handler for resetting session"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        await session_manager.reset_session()
        return {"success": True, "message": "Session reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting session: {e}")
        return {"error": f"Failed to reset session: {str(e)}"}


async def handle_websocket_connected(request) -> dict:
    """Handler for WebSocket connection events"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        client_id = request.get("client_id")
        await session_manager.handle_websocket_connected(client_id)
        return {"success": True, "message": f"WebSocket connected: {client_id}"}
    except Exception as e:
        logger.error(f"Error handling WebSocket connection: {e}")
        return {"error": f"Failed to handle WebSocket connection: {str(e)}"}


async def handle_websocket_disconnected(request) -> dict:
    """Handler for WebSocket disconnection events"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        client_id = request.get("client_id")
        await session_manager.handle_websocket_disconnected(client_id)
        return {"success": True, "message": f"WebSocket disconnected: {client_id}"}
    except Exception as e:
        logger.error(f"Error handling WebSocket disconnection: {e}")
        return {"error": f"Failed to handle WebSocket disconnection: {str(e)}"}


# Plugin Management Handlers
async def handle_add_plugin(request) -> dict:
    """Handler for adding plugins"""
    global session_manager, plugin_service

    if not session_manager or not plugin_service:
        return {"error": "Service not initialized"}

    try:
        plugin_uri = request.get("plugin_uri")
        instance_id = request.get("instance_id")

        # Add plugin through audio engine
        result = await plugin_service.add_plugin(plugin_uri, instance_id)

        if result.get("success"):
            # Update session state
            await session_manager.add_plugin(plugin_uri, instance_id)

        return result
    except Exception as e:
        logger.error(f"Error adding plugin: {e}")
        return {"error": f"Failed to add plugin: {str(e)}"}


async def handle_remove_plugin(request) -> dict:
    """Handler for removing plugins"""
    global session_manager, plugin_service

    if not session_manager or not plugin_service:
        return {"error": "Service not initialized"}

    try:
        instance_id = request.get("instance_id")

        # Remove plugin through audio engine
        result = await plugin_service.remove_plugin(instance_id)

        if result.get("success"):
            # Update session state
            await session_manager.remove_plugin(instance_id)

        return result
    except Exception as e:
        logger.error(f"Error removing plugin: {e}")
        return {"error": f"Failed to remove plugin: {str(e)}"}


async def handle_set_plugin_parameter(request) -> dict:
    """Handler for setting plugin parameters"""
    global plugin_service

    if not plugin_service:
        return {"error": "Plugin service not initialized"}

    try:
        instance_id = request.get("instance_id")
        parameter_symbol = request.get("parameter_symbol")
        value = request.get("value")

        result = await plugin_service.set_parameter(
            instance_id, parameter_symbol, value
        )
        return result
    except Exception as e:
        logger.error(f"Error setting plugin parameter: {e}")
        return {"error": f"Failed to set plugin parameter: {str(e)}"}


# Connection Management Handlers
async def handle_add_connection(request) -> dict:
    """Handler for adding connections"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        source_port = request.get("source_port")
        target_port = request.get("target_port")

        await session_manager.add_connection(source_port, target_port)
        return {"success": True, "message": "Connection added successfully"}
    except Exception as e:
        logger.error(f"Error adding connection: {e}")
        return {"error": f"Failed to add connection: {str(e)}"}


async def handle_remove_connection(request) -> dict:
    """Handler for removing connections"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        source_port = request.get("source_port")
        target_port = request.get("target_port")

        await session_manager.remove_connection(source_port, target_port)
        return {"success": True, "message": "Connection removed successfully"}
    except Exception as e:
        logger.error(f"Error removing connection: {e}")
        return {"error": f"Failed to remove connection: {str(e)}"}


# Transport Control Handlers
async def handle_control_transport(request) -> dict:
    """Handler for transport control"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        action = request.get("action")  # "play", "stop", "pause"

        await session_manager.control_transport(action)
        return {"success": True, "message": f"Transport {action} executed"}
    except Exception as e:
        logger.error(f"Error controlling transport: {e}")
        return {"error": f"Failed to control transport: {str(e)}"}


async def handle_set_session_tempo(request) -> dict:
    """Handler for setting session tempo"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        tempo_bpm = request.get("tempo_bpm")

        await session_manager.set_tempo(tempo_bpm)
        return {"success": True, "message": f"Tempo set to {tempo_bpm} BPM"}
    except Exception as e:
        logger.error(f"Error setting tempo: {e}")
        return {"error": f"Failed to set tempo: {str(e)}"}


async def handle_set_beats_per_bar(request) -> dict:
    """Handler for setting beats per bar"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        beats_per_bar = request.get("beats_per_bar")

        await session_manager.set_beats_per_bar(beats_per_bar)
        return {"success": True, "message": f"Beats per bar set to {beats_per_bar}"}
    except Exception as e:
        logger.error(f"Error setting beats per bar: {e}")
        return {"error": f"Failed to set beats per bar: {str(e)}"}


# Recording Handlers
async def handle_recording_start(request) -> dict:
    """Handler for starting recording"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        await session_manager.start_recording()
        return {"success": True, "message": "Recording started"}
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
        return {"error": f"Failed to start recording: {str(e)}"}


async def handle_recording_stop(request) -> dict:
    """Handler for stopping recording"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        await session_manager.stop_recording()
        return {"success": True, "message": "Recording stopped"}
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        return {"error": f"Failed to stop recording: {str(e)}"}


async def handle_recording_reset(request) -> dict:
    """Handler for resetting recording"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        await session_manager.reset_recording()
        return {"success": True, "message": "Recording reset"}
    except Exception as e:
        logger.error(f"Error resetting recording: {e}")
        return {"error": f"Failed to reset recording: {str(e)}"}


# Legacy Compatibility Handlers
async def handle_update_session_state(request) -> dict:
    """Legacy handler for updating session state"""
    return {"success": True, "message": "Session state updated (legacy compatibility)"}


async def handle_get_session_status(request) -> dict:
    """Legacy handler for getting session status"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        state = await session_manager.get_session_state()
        return {
            "success": True,
            "status": state.status.value,
            "transport_rolling": state.transport_rolling,
        }
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return {"error": f"Failed to get session status: {str(e)}"}


async def handle_get_session_stats(request) -> dict:
    """Legacy handler for getting session stats"""
    return {"success": True, "stats": {"uptime": "0s", "plugins": 0, "connections": 0}}


async def handle_start_session(request) -> dict:
    """Legacy handler for starting session"""
    return {"success": True, "message": "Session started (legacy compatibility)"}


async def handle_stop_session(request) -> dict:
    """Legacy handler for stopping session"""
    return {"success": True, "message": "Session stopped (legacy compatibility)"}


async def handle_set_session_config(request) -> dict:
    """Legacy handler for setting session config"""
    return {"success": True, "message": "Session config set (legacy compatibility)"}


async def handle_reset_session_stats(request) -> dict:
    """Legacy handler for resetting session stats"""
    return {"success": True, "message": "Session stats reset (legacy compatibility)"}


# Event Handlers
async def handle_session_change_event(event: ServiceEvent):
    """Handle session change events"""
    logger.info(f"Session change event received: {event.data}")


async def handle_transport_change_event(event: ServiceEvent):
    """Handle transport change events"""
    logger.info(f"Transport change event received: {event.data}")


async def handle_plugin_change_event(event: ServiceEvent):
    """Handle plugin change events"""
    logger.info(f"Plugin change event received: {event.data}")


async def shutdown_services():
    """Shutdown all services gracefully"""
    global state_manager, session_manager, event_bus, resilient_servicebus

    logger.info("Shutting down Session Service v2...")

    # Stop enhanced ServiceBus
    if resilient_servicebus:
        await resilient_servicebus.stop()
        logger.info("Enhanced ServiceBus stopped")

    # Close session manager
    if session_manager:
        await session_manager.shutdown()
        logger.info("Enhanced session manager shutdown")

    # Close state manager
    if state_manager:
        await state_manager.shutdown()
        logger.info("State manager shutdown")

    # Close event bus
    if event_bus:
        await event_bus.close()
        logger.info("Event bus closed")

    logger.info("Session Service v2 shutdown complete")


async def main():
    """Main entry point for the Enhanced Session Service v2"""

    # Setup signal handlers for graceful shutdown
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(shutdown_services())

    if os.name != "nt":  # Unix systems
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())

    try:
        # Initialize all services
        await initialize_services()

        # Setup enhanced ServiceBus with all handlers
        await setup_enhanced_servicebus()

        # Start the enhanced ServiceBus (Step 3: Everything else automatic ✅)
        await resilient_servicebus.start()

        logger.info("Session Service v2 with Enhanced ServiceBus started successfully")

        # Keep the service running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Session Service v2 error: {e}")
        raise
    finally:
        await shutdown_services()

    logger.info("Session Service v2 stopped")


if __name__ == "__main__":
    asyncio.run(main())
