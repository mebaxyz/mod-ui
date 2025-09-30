"""
Effects Service - ENHANCED with Auto-Reconnecting ServiceBus

This provides exactly what you wanted:
1. Define connection once ✅
2. Define topics and handlers ✅
3. Everything else automatic ✅
"""

import asyncio
import logging
import os
import time
import signal
from typing import Any, Dict, Optional, Callable, Awaitable
from datetime import datetime

# Import ServiceBus components
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError
from servicebus import Service, ServiceEvent, get_config, CommConfig, set_config

from .handlers import EffectsServiceHandlers

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResilientServiceBus:
    """Auto-reconnecting ServiceBus - Same pattern as other services"""

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

        # Service method handlers
        self._method_handlers: Dict[str, Callable] = {}

        # Reconnection settings
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        self._reconnect_backoff = 1.5
        self._last_connection_time = 0
        self._connection_failures = 0

        # Background tasks
        self._health_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None

        logger.info(f"ResilientServiceBus created for service '{service_name}'")

    def on_event(
        self, event_type: str, handler: Callable[[ServiceEvent], Awaitable[None]]
    ) -> None:
        """Register an event handler"""
        self._event_handlers[event_type] = handler
        logger.info(f"Registered handler for event type '{event_type}'")

        if self._current_service and self._is_running:
            try:
                self._current_service.subscribe_to_event(event_type, handler)
                logger.info(f"Immediately subscribed to '{event_type}'")
            except Exception as e:
                logger.warning(
                    f"Failed to immediately subscribe to '{event_type}': {e}"
                )

    def register_handler(self, method_name: str, handler: Callable) -> None:
        """Register a service method handler"""
        self._method_handlers[method_name] = handler
        logger.info(f"Registered method handler for '{method_name}'")

        if self._current_service and self._is_running:
            try:
                self._current_service.register_handler(method_name, handler)
                logger.info(f"Immediately registered method '{method_name}'")
            except Exception as e:
                logger.warning(
                    f"Failed to immediately register method '{method_name}': {e}"
                )

    async def start(self) -> None:
        """Start the resilient ServiceBus"""
        if self._is_running:
            return

        logger.info(f"Starting ResilientServiceBus for '{self.service_name}'...")
        self._should_stop = False

        await self._ensure_connection()
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

        await self._disconnect()
        logger.info(f"ResilientServiceBus for '{self.service_name}' stopped")

    async def publish_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Publish an event"""
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
            asyncio.create_task(self._handle_connection_failure())
            return False

    @property
    def is_connected(self) -> bool:
        return self._current_service is not None and self._is_running

    @property
    def connection_info(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "is_connected": self.is_connected,
            "is_running": self._is_running,
            "connection_failures": self._connection_failures,
            "last_connection_time": self._last_connection_time,
            "registered_events": list(self._event_handlers.keys()),
            "registered_methods": list(self._method_handlers.keys()),
        }

    @property
    def service_instance(self) -> Optional[Service]:
        """Get the current service instance for handlers that need it"""
        return self._current_service

    # Private methods
    async def _ensure_connection(self) -> bool:
        if self._current_service:
            if await self._test_connection():
                return True
            else:
                await self._disconnect()
        return await self._create_connection()

    async def _create_connection(self) -> bool:
        try:
            logger.info(
                f"Creating new ServiceBus connection for '{self.service_name}'..."
            )

            self._redis_client = redis.Redis.from_url(
                self._redis_url,
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=True,
                health_check_interval=30,
            )

            await self._redis_client.ping()

            self._current_service = Service(
                self.service_name,
                redis_client=self._redis_client,
                enable_discovery=True,
                enable_events=True,
                enable_metrics=True,
            )

            await self._current_service.start()

            # Register all method handlers
            for method_name, handler in self._method_handlers.items():
                self._current_service.register_handler(method_name, handler)
                logger.info(f"Registered method '{method_name}'")

            # Subscribe to all registered events
            for event_type, handler in self._event_handlers.items():
                self._current_service.subscribe_to_event(event_type, handler)
                logger.info(f"Subscribed to event '{event_type}'")

            self._last_connection_time = time.time()
            self._connection_failures = 0
            self._reconnect_delay = 1.0

            logger.info(f"ServiceBus connection established for '{self.service_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create ServiceBus connection: {e}")
            self._connection_failures += 1
            await self._disconnect()
            return False

    async def _disconnect(self) -> None:
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
        if not self._current_service or not self._redis_client:
            return False

        try:
            await self._redis_client.ping()
            client = self._current_service._client
            await client.call_service(self.service_name, "ping")
            return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            return False

    async def _handle_connection_failure(self) -> None:
        if self._should_stop:
            return

        logger.warning(f"Connection failure detected for '{self.service_name}'")

        if self._reconnect_task and not self._reconnect_task.done():
            return

        self._reconnect_task = asyncio.create_task(self._reconnection_loop())

    async def _reconnection_loop(self) -> None:
        while not self._should_stop and not await self._ensure_connection():
            delay = min(self._reconnect_delay, self._max_reconnect_delay)
            logger.info(f"Reconnection failed, retrying in {delay:.1f}s...")

            await asyncio.sleep(delay)
            self._reconnect_delay *= self._reconnect_backoff

        if not self._should_stop:
            logger.info(f"Reconnection successful for '{self.service_name}'")

    async def _health_monitoring_loop(self) -> None:
        while not self._should_stop:
            try:
                if not await self._test_connection():
                    logger.warning(f"Health check failed for '{self.service_name}'")
                    await self._handle_connection_failure()

                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(10)


# Global service instance
resilient_bus: Optional[ResilientServiceBus] = None


async def handle_effect_events(event):
    """Handle effect-related events from other services"""
    try:
        logger.info(f"📡 Received effect event: {event.event_type}")

        event_data = event.data
        effect_id = event_data.get("effect_id")
        action = event_data.get("action", "unknown")

        logger.info(f"✅ Processing effect event - ID: {effect_id}, Action: {action}")

    except Exception as e:
        logger.error(f"❌ Error handling effect event: {e}")


async def initialize_enhanced_effects_service():
    """ENHANCED ServiceBus initialization for Effects Service"""
    global resilient_bus

    try:
        logger.info(
            "🚀 Initializing ENHANCED Effects Service with auto-reconnection..."
        )

        # Setup configuration from environment
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # Configure ServiceBus with Docker environment
        config = CommConfig(redis_url=redis_url)
        set_config(config)

        logger.info(f"Using Redis URL: {redis_url}")

        # 1️⃣ DEFINE CONNECTION ONCE
        resilient_bus = ResilientServiceBus("effects_service", redis_url)

        # 2️⃣ DEFINE TOPICS AND HANDLERS
        resilient_bus.on_event("effect_change", handle_effect_events)
        resilient_bus.on_event("effect_request", handle_effect_events)

        # 3️⃣ START - EVERYTHING ELSE IS AUTOMATIC!
        await resilient_bus.start()

        # 4️⃣ REGISTER SERVICE METHODS
        if resilient_bus.service_instance:
            # Initialize handlers with service instance for event publishing
            handlers = EffectsServiceHandlers(
                service_instance=resilient_bus.service_instance
            )

            # Register all effect handlers
            resilient_bus.register_handler("effect_add", handlers.handle_effect_add)
            resilient_bus.register_handler(
                "effect_remove", handlers.handle_effect_remove
            )
            resilient_bus.register_handler("effect_get", handlers.handle_effect_get)
            resilient_bus.register_handler("effect_list", handlers.handle_effect_list)
            resilient_bus.register_handler(
                "effect_connect", handlers.handle_effect_connect
            )
            resilient_bus.register_handler(
                "effect_disconnect", handlers.handle_effect_disconnect
            )
            resilient_bus.register_handler(
                "effect_parameter_set", handlers.handle_effect_parameter_set
            )
            resilient_bus.register_handler(
                "effect_parameter_address", handlers.handle_effect_parameter_address
            )
            resilient_bus.register_handler(
                "effect_preset_load", handlers.handle_effect_preset_load
            )
            resilient_bus.register_handler(
                "effect_preset_save", handlers.handle_effect_preset_save
            )
            resilient_bus.register_handler(
                "effect_preset_delete", handlers.handle_effect_preset_delete
            )
            resilient_bus.register_handler("effect_image", handlers.handle_effect_image)
            resilient_bus.register_handler("effect_file", handlers.handle_effect_file)

        logger.info("🎉 ENHANCED Effects Service ready! Auto-reconnection active!")

    except Exception as e:
        logger.error(f"❌ Effects Service initialization failed: {e}")
        import traceback

        traceback.print_exc()
        resilient_bus = None


async def main():
    """Main entry point for the Enhanced Effects Service"""
    logger.info("🌟 Starting MOD UI Effects Service - ENHANCED Version")

    # Initialize enhanced ServiceBus
    await initialize_enhanced_effects_service()

    if not resilient_bus:
        logger.error("❌ Failed to initialize ServiceBus, exiting...")
        return

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(shutdown())

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("✅ Effects Service is running with ENHANCED ServiceBus!")

    try:
        # Keep running
        while resilient_bus and resilient_bus.is_connected:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        await shutdown()


async def shutdown():
    """Graceful shutdown"""
    logger.info("🛑 Shutting down Effects Service...")

    if resilient_bus:
        await resilient_bus.stop()

    logger.info("Effects Service stopped")


if __name__ == "__main__":
    asyncio.run(main())
