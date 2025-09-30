"""
Resilient ServiceBus - Auto-reconnecting, self-healing ServiceBus wrapper

This provides the simple interface you want:
1. Define connection once
2. Define topics and handlers
3. Everything else is handled automatically (reconnection, health checks, etc.)
"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional

import redis.asyncio as redis

from .config import get_config
from .models import ServiceEvent
from .service import Service

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
        self._last_connection_time = 0.0
        self._connection_failures = 0

        # Background tasks
        self._health_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None

        logger.info("ResilientServiceBus created for service '%s'", service_name)

    def on_event(
        self, event_type: str, handler: Callable[[ServiceEvent], Awaitable[None]]
    ) -> None:
        """
        Register an event handler - SIMPLE INTERFACE

        Args:
            event_type: Type of event to listen for (e.g., "websocket_broadcast")
            handler: Async function to handle the event
        """
        self._event_handlers[event_type] = handler
        logger.info("Registered handler for event type '%s'", event_type)

        # If already running, subscribe immediately
        if self._current_service and self._is_running:
            try:
                self._current_service.subscribe_to_event(event_type, handler)
                logger.info(
                    "Immediately subscribed to '%s' (service already running)",
                    event_type,
                )
            except Exception as e:  # pylint: disable=broad-except
                logger.warning(
                    "Failed to immediately subscribe to '%s': %s",
                    event_type,
                    e,
                )

    async def start(self) -> None:
        """
        Start the resilient ServiceBus - SIMPLE INTERFACE
        All reconnection, health checks, etc. happen automatically
        """
        if self._is_running:
            logger.warning(
                "ResilientServiceBus for '%s' is already running",
                self.service_name,
            )
            return

        logger.info("Starting ResilientServiceBus for '%s'...", self.service_name)
        self._should_stop = False

        # Start the connection management
        await self._ensure_connection()

        # Start background health monitoring
        self._health_task = asyncio.create_task(self._health_monitoring_loop())

        self._is_running = True
        logger.info(
            "ResilientServiceBus for '%s' started successfully",
            self.service_name,
        )

    async def stop(self) -> None:
        """Stop the resilient ServiceBus"""
        if not self._is_running:
            return

        logger.info("Stopping ResilientServiceBus for '%s'...", self.service_name)
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

    async def publish_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Publish an event - handles connection issues automatically

        Returns:
            bool: True if published successfully, False if failed
        """
        if not self._current_service:
            logger.warning(
                "Cannot publish event '%s' - no active connection",
                event_type,
            )
            return False

        try:
            await self._current_service.publish_event(event_type, data)
            return True
        except Exception as e:
            logger.error("Failed to publish event '%s': %s", event_type, e)
            # Trigger reconnection
            asyncio.create_task(self._handle_connection_failure())
            return False

    async def call_service(
        self, service_name: str, method: str, *args, **kwargs
    ) -> Any:
        """
        Call another service - handles connection issues automatically

        Returns:
            Result of the service call, or raises exception if failed
        """
        if not self._current_service:
            raise RuntimeError("No active ServiceBus connection")

        try:
            # Accessing a protected member and dynamic client API - narrow with localized pylint disables
            # pylint: disable=protected-access, no-member
            client = self._current_service._client
            return await client.call_service(
                service_name, method, {"args": args, "kwargs": kwargs}
            )
            # pylint: enable=protected-access, no-member
        except Exception as e:
            logger.error("Failed to call %s.%s: %s", service_name, method, e)
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
                "Creating new ServiceBus connection for '%s'...",
                self.service_name,
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
                logger.info("Subscribed to event '%s'", event_type)

            # Update connection state
            self._last_connection_time = time.time()
            self._connection_failures = 0
            self._reconnect_delay = 1.0  # Reset backoff

            logger.info(
                "ServiceBus connection established for '%s'",
                self.service_name,
            )
            return True

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to create ServiceBus connection: %s", e)
            self._connection_failures += 1
            await self._disconnect()
            return False

    async def _disconnect(self) -> None:
        """Clean up current connection"""
        if self._current_service:
            try:
                await self._current_service.stop()
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("Error stopping service: %s", e)
            finally:
                self._current_service = None

        if self._redis_client:
            try:
                await self._redis_client.close()
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("Error closing Redis client: %s", e)
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
            # pylint: disable=protected-access, no-member
            client = self._current_service._client
            await client.call_service(self.service_name, "ping")
            # pylint: enable=protected-access, no-member

            return True
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("Connection health check failed: %s", e)
            return False

    async def _handle_connection_failure(self) -> None:
        """Handle connection failure - trigger reconnection"""
        if self._should_stop:
            return

        logger.warning("Connection failure detected for '%s'", self.service_name)

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
            logger.info("Reconnection failed, retrying in %.1fs...", delay)

            await asyncio.sleep(delay)
            self._reconnect_delay *= self._reconnect_backoff

        if not self._should_stop:
            logger.info("Reconnection successful for '%s'", self.service_name)

    async def _health_monitoring_loop(self) -> None:
        """Background health monitoring"""
        while not self._should_stop:
            try:
                if not await self._test_connection():
                    logger.warning("Health check failed for '%s'", self.service_name)
                    await self._handle_connection_failure()
                else:
                    # Connection is healthy
                    pass

                # Check every 30 seconds
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:  # pylint: disable=broad-except
                logger.error("Error in health monitoring: %s", e)
                await asyncio.sleep(10)


# Convenience function for the simple interface you want
async def create_resilient_service(
    service_name: str,
    event_handlers: Optional[
        Dict[str, Callable[[ServiceEvent], Awaitable[None]]]
    ] = None,
    redis_url: Optional[str] = None,
) -> ResilientServiceBus:
    """
    Create and start a resilient ServiceBus with the simple interface

    Args:
        service_name: Name of your service
        event_handlers: Dict of event_type -> handler function
        redis_url: Redis connection URL (optional)

    Returns:
        Started ResilientServiceBus instance

    Example:
        async def handle_websocket_msg(event):
            print(f"Got message: {event.data}")

        bus = await create_resilient_service(
            "webui_gateway",
            {"websocket_broadcast": handle_websocket_msg}
        )
        # That's it! Everything else is automatic
    """
    bus = ResilientServiceBus(service_name, redis_url)

    # Register event handlers
    if event_handlers:
        for event_type, handler in event_handlers.items():
            bus.on_event(event_type, handler)

    # Start it
    await bus.start()

    return bus
