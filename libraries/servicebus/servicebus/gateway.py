"""
Gateway Service - Enhanced ServiceBus wrapper for gateway applications

Provides simplified initialization for services that act as HTTP/WebSocket gateways.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Dict, Optional

from .config import CommConfig, set_config
from .models import ServiceEvent
from .service import Service

logger = logging.getLogger(__name__)


class GatewayService:  # pylint: disable=too-many-instance-attributes
    """
    Enhanced Service wrapper specifically designed for gateway applications

    Handles common gateway patterns:
    - Auto-configuration from environment
    - Safe startup that doesn't block HTTP servers
    - Event broadcasting to connected clients
    - Graceful degradation if Redis is unavailable
    """

    def __init__(
        self,
        service_name: str,
        auto_configure: bool = True,
        safe_startup: bool = True,
        enable_websocket_events: bool = True,
    ):
        self.service_name = service_name
        self.auto_configure = auto_configure
        self.safe_startup = safe_startup
        self.enable_websocket_events = enable_websocket_events

        self.service: Optional[Service] = None
        self.is_initialized = False
        self._startup_error = None

        # WebSocket client management (if enabled)
        self.websocket_clients: Dict[str, Any] = {}
        self.broadcast_callback: Optional[
            Callable[[Dict[str, Any]], Awaitable[None]]
        ] = None

    async def initialize(self) -> bool:
        """
        Initialize the gateway service

        Returns:
            True if successful, False if failed (but service can still operate)
        """
        try:
            logger.info("Initializing gateway service '%s'...", self.service_name)

            # Auto-configure ServiceBus from environment
            if self.auto_configure:
                await self._auto_configure()

            # Create service instance
            self.service = Service(
                self.service_name,
                enable_discovery=True,
                enable_events=self.enable_websocket_events,
                enable_metrics=True,
            )

            # Register common gateway event handlers
            if self.enable_websocket_events:
                self._register_websocket_handlers()

            # Start service with safe startup if enabled
            if self.safe_startup:
                await self._safe_start()
            else:
                await self.service.start()

            self.is_initialized = True
            logger.info(
                "Gateway service '%s' initialized successfully",
                self.service_name,
            )
            return True

        except Exception as e:  # pylint: disable=broad-except
            self._startup_error = e
            logger.error("Failed to initialize gateway service: %s", e)
            if not self.safe_startup:
                raise
            return False

    async def _auto_configure(self):
        """Auto-configure ServiceBus from environment variables"""
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        config = CommConfig(redis_url=redis_url)
        set_config(config)
        logger.info("Auto-configured ServiceBus with Redis: %s", redis_url)

    async def _safe_start(self):
        """Start service in background task to avoid blocking"""
        startup_task = asyncio.create_task(self.service.start())

        # Give it a moment to start, but don't wait indefinitely
        try:
            await asyncio.wait_for(startup_task, timeout=2.0)
        except asyncio.TimeoutError:
            logger.warning(
                "Service startup taking longer than expected, continuing in background"
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Service startup failed: %s", e)
            if not self.safe_startup:
                raise

    def _register_websocket_handlers(self):
        """Register common WebSocket event handlers"""
        if not self.service:
            return

        # Handle websocket broadcast events
        async def handle_websocket_broadcast(event: ServiceEvent):
            """Handle WebSocket broadcast events from other services"""
            try:
                if self.broadcast_callback:
                    await self.broadcast_callback(event.data)
                else:
                    logger.debug(
                        "Received websocket broadcast but no callback registered: %s",
                        event.data,
                    )
            except Exception as e:  # pylint: disable=broad-except
                logger.error("Error handling websocket broadcast: %s", e)

        self.service.subscribe_to_event(
            "websocket_broadcast", handle_websocket_broadcast
        )
        logger.info("Registered websocket broadcast handler")

    def set_websocket_broadcast_callback(
        self, callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        """Set callback for websocket broadcast events"""
        self.broadcast_callback = callback
        logger.info("WebSocket broadcast callback registered")

    async def broadcast_to_websockets(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients"""
        if self.broadcast_callback:
            await self.broadcast_callback(message)
        else:
            logger.warning("No websocket broadcast callback registered")

    async def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish event through ServiceBus"""
        if self.service and self.is_initialized:
            await self.service.publish_event(event_type, data)
        else:
            logger.warning(
                "Cannot publish event '%s' - service not initialized",
                event_type,
            )

    async def call_service(
        self, service_name: str, request_type: str, data: Dict[str, Any] = None
    ):
        """Call another service through ServiceBus"""
        if self.service and self.is_initialized:
            return await self.service.call(service_name, request_type, data or {})
        logger.warning(
            "Cannot call service '%s' - service not initialized",
            service_name,
        )
        return None

    async def health_check(self) -> Dict[str, Any]:
        """Get health status of the gateway service"""
        # Prefer public API if available to avoid protected member access
        sb_running = False
        if self.service:
            if hasattr(self.service, "is_running"):
                try:
                    sb_running = self.service.is_running()
                except Exception:
                    sb_running = getattr(self.service, "_is_running", False)
            else:
                sb_running = getattr(self.service, "_is_running", False)

        return {
            "service_name": self.service_name,
            "is_initialized": self.is_initialized,
            "startup_error": str(self._startup_error) if self._startup_error else None,
            "websocket_clients": len(self.websocket_clients),
            "servicebus_running": sb_running,
        }

    async def shutdown(self):
        """Gracefully shutdown the gateway service"""
        if self.service:
            await self.service.stop()
        logger.info("Gateway service '%s' shutdown complete", self.service_name)


@asynccontextmanager
async def gateway_service(
    service_name: str, auto_configure: bool = True, safe_startup: bool = True
):
    """
    Context manager for gateway services

    Usage:
        async with gateway_service("webui_gateway") as gateway:
            # Use gateway.service for ServiceBus operations
            # Use gateway.broadcast_to_websockets() for WebSocket broadcasting
            pass
    """
    gateway = GatewayService(service_name, auto_configure, safe_startup)
    try:
        await gateway.initialize()
        yield gateway
    finally:
        await gateway.shutdown()


# Convenience function for common gateway initialization
async def create_gateway_service(
    service_name: str,
    websocket_broadcast_callback: Optional[
        Callable[[Dict[str, Any]], Awaitable[None]]
    ] = None,
    **kwargs,
) -> GatewayService:
    """
    Create and initialize a gateway service with common patterns

    Args:
        service_name: Name of the service
        websocket_broadcast_callback: Callback for WebSocket broadcasting
        **kwargs: Additional arguments for GatewayService

    Returns:
        Initialized GatewayService instance
    """
    gateway = GatewayService(service_name, **kwargs)
    await gateway.initialize()

    if websocket_broadcast_callback:
        gateway.set_websocket_broadcast_callback(websocket_broadcast_callback)

    return gateway
