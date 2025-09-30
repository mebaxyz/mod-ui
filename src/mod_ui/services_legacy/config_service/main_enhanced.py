"""
Configuration Service for MOD UI - ENHANCED with Auto-Reconnecting ServiceBus

This provides exactly what you wanted:
1. Define connection once ✅
2. Define topics and handlers ✅
3. Everything else automatic ✅
"""

import asyncio
import json
import logging
import os
import signal
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

# Import ServiceBus components
import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError
from servicebus import Service, ServiceEvent, get_config
from servicebus.config import CommConfig, set_config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResilientServiceBus:
    """Auto-reconnecting ServiceBus - Same as WebUI Gateway"""

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

    def register_handler(self, method_name: str, handler: Callable):
        """Register a service method handler"""
        if self._current_service:
            self._current_service.register_handler(method_name, handler)
        else:
            logger.warning(
                f"Cannot register handler '{method_name}' - no active service"
            )

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
        }

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


# Global service instances
resilient_bus: Optional[ResilientServiceBus] = None
settings_cache: Optional[Dict[str, Any]] = None

# Path to the settings JSON file
SETTINGS_JSON_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "config" / "settings.json"
)


def get_template_variables() -> Dict[str, Any]:
    """Generate current template variables"""
    # Version variable
    version_arg = "1"
    try:
        # Try to read version from MOD release file
        version_file = "/etc/mod-release/release"
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                image_version = f.read().strip()
                if image_version and len(image_version) > 1:
                    # Strip initial 'v' from version if present
                    version_arg = (
                        image_version[1:] if image_version[0] == "v" else image_version
                    )
                else:
                    version_arg = str(int(time.time()))
        else:
            # Use timestamp as fallback
            version_arg = str(int(time.time()))
    except Exception:
        version_arg = str(int(time.time()))

    return {
        "MOD_VERSION": version_arg,
        "MOD_RELEASE": version_arg,
    }


def load_settings() -> Dict[str, Any]:
    """Load settings from JSON file with caching"""
    global settings_cache

    try:
        # Check if file exists
        if not SETTINGS_JSON_PATH.exists():
            logger.warning(f"Settings file not found: {SETTINGS_JSON_PATH}")
            return {}

        # Load settings from file
        with open(SETTINGS_JSON_PATH, "r") as f:
            settings = json.load(f)

        # Update template variables
        template_vars = get_template_variables()
        settings.update(template_vars)

        # Cache the settings
        settings_cache = settings
        logger.info(f"Loaded settings from {SETTINGS_JSON_PATH}")

        return settings

    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return settings_cache or {}


def save_settings(settings: Dict[str, Any]) -> bool:
    """Save settings to JSON file"""
    global settings_cache

    try:
        # Create directory if it doesn't exist
        SETTINGS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Filter out template variables before saving
        template_vars = get_template_variables()
        filtered_settings = {
            k: v for k, v in settings.items() if k not in template_vars
        }

        # Write to file
        with open(SETTINGS_JSON_PATH, "w") as f:
            json.dump(filtered_settings, f, indent=2)

        # Update cache
        settings_cache = settings
        logger.info(f"Saved settings to {SETTINGS_JSON_PATH}")

        return True

    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False


# ServiceBus method handlers
async def get_settings() -> Dict[str, Any]:
    """Get all configuration settings"""
    return load_settings()


async def get_setting(key: str, default_value: Any = None) -> Any:
    """Get a specific configuration setting"""
    settings = load_settings()
    return settings.get(key, default_value)


async def set_setting(key: str, value: Any) -> bool:
    """Set a configuration setting"""
    settings = load_settings()
    settings[key] = value

    success = save_settings(settings)

    # Publish settings change event
    if success and resilient_bus:
        await resilient_bus.publish_event(
            "settings_changed", {"key": key, "value": value, "timestamp": time.time()}
        )

    return success


async def update_settings(new_settings: Dict[str, Any]) -> bool:
    """Update multiple configuration settings"""
    settings = load_settings()
    settings.update(new_settings)

    success = save_settings(settings)

    # Publish settings change event
    if success and resilient_bus:
        await resilient_bus.publish_event(
            "settings_changed",
            {
                "keys": list(new_settings.keys()),
                "settings": new_settings,
                "timestamp": time.time(),
            },
        )

    return success


async def reset_settings() -> bool:
    """Reset settings to defaults"""
    try:
        if SETTINGS_JSON_PATH.exists():
            SETTINGS_JSON_PATH.unlink()

        global settings_cache
        settings_cache = None

        # Publish reset event
        if resilient_bus:
            await resilient_bus.publish_event(
                "settings_reset", {"timestamp": time.time()}
            )

        logger.info("Settings reset to defaults")
        return True

    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        return False


async def handle_settings_request(event):
    """Handle settings request events from other services"""
    try:
        logger.info(f"📡 Received settings request: {event.event_type}")

        event_data = event.data
        request_type = event_data.get("request_type", "get_all")

        if request_type == "get_all":
            settings = load_settings()

            # Publish response
            if resilient_bus:
                await resilient_bus.publish_event(
                    "settings_response",
                    {
                        "request_id": event_data.get("request_id"),
                        "settings": settings,
                        "timestamp": time.time(),
                    },
                )

    except Exception as e:
        logger.error(f"❌ Error handling settings request: {e}")


async def initialize_enhanced_config_service():
    """ENHANCED ServiceBus initialization for Config Service"""
    global resilient_bus

    try:
        logger.info("🚀 Initializing ENHANCED Config Service with auto-reconnection...")

        # 1️⃣ DEFINE CONNECTION ONCE
        resilient_bus = ResilientServiceBus("config_service")

        # 2️⃣ DEFINE TOPICS AND HANDLERS
        resilient_bus.on_event("settings_request", handle_settings_request)

        # 3️⃣ START - EVERYTHING ELSE IS AUTOMATIC!
        await resilient_bus.start()

        # 4️⃣ REGISTER SERVICE METHODS
        if resilient_bus._current_service:
            resilient_bus._current_service.register_handler(
                "get_settings", get_settings
            )
            resilient_bus._current_service.register_handler("get_setting", get_setting)
            resilient_bus._current_service.register_handler("set_setting", set_setting)
            resilient_bus._current_service.register_handler(
                "update_settings", update_settings
            )
            resilient_bus._current_service.register_handler(
                "reset_settings", reset_settings
            )

        # 5️⃣ LOAD INITIAL SETTINGS
        load_settings()

        logger.info("🎉 ENHANCED Config Service ready! Auto-reconnection active!")

    except Exception as e:
        logger.error(f"❌ Config Service initialization failed: {e}")
        import traceback

        traceback.print_exc()
        resilient_bus = None


async def main():
    """Main function for Config Service"""
    logger.info("🌟 Starting MOD UI Config Service - ENHANCED Version")

    # Initialize enhanced ServiceBus
    await initialize_enhanced_config_service()

    if not resilient_bus:
        logger.error("❌ Failed to initialize ServiceBus, exiting...")
        return

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(shutdown())

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("✅ Config Service is running with ENHANCED ServiceBus!")

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
    logger.info("🛑 Shutting down Config Service...")

    if resilient_bus:
        await resilient_bus.stop()

    logger.info("Config Service stopped")


if __name__ == "__main__":
    asyncio.run(main())
