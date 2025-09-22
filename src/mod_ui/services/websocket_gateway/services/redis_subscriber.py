"""
Redis Event Subscriber for WebSocket Gateway

Subscribes to Redis channels and forwards events to the event router.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Set

import redis.asyncio as redis

from src.mod_ui.services.websocket_gateway.services.event_router import EventRouter
from src.mod_ui.services.websocket_gateway.utils import config

logger = logging.getLogger(__name__)


class RedisEventSubscriber:
    """Subscribes to Redis events and forwards them to the event router"""

    def __init__(self, event_router: EventRouter):
        self.event_router = event_router

        # Redis connection
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None

        # Subscription management
        self.subscribed_channels: Set[str] = set()
        self.subscription_patterns: Set[str] = set()

        # Processing tasks
        self.subscriber_task: Optional[asyncio.Task] = None
        self.reconnect_task: Optional[asyncio.Task] = None

        # Connection state
        self.is_connected = False
        self.connection_attempts = 0
        self.last_connection_attempt = 0.0

        # Statistics
        self.messages_received = 0
        self.messages_processed = 0
        self.connection_errors = 0
        self.start_time = time.time()

    async def start(self):
        """Start the Redis subscriber"""

        if self.subscriber_task and not self.subscriber_task.done():
            return

        await self._connect()
        await self._setup_default_subscriptions()

        # Start subscriber task
        self.subscriber_task = asyncio.create_task(self._message_loop())

        # Start reconnection task
        self.reconnect_task = asyncio.create_task(self._reconnect_loop())

        logger.info("Redis event subscriber started")

    async def stop(self):
        """Stop the Redis subscriber"""

        # Cancel tasks
        if self.subscriber_task:
            self.subscriber_task.cancel()
            try:
                await self.subscriber_task
            except asyncio.CancelledError:
                pass
            self.subscriber_task = None

        if self.reconnect_task:
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                pass
            self.reconnect_task = None

        # Close Redis connection
        await self._disconnect()

        logger.info("Redis event subscriber stopped")

    async def subscribe_to_channel(self, channel: str):
        """Subscribe to a specific Redis channel"""

        if not self.is_connected:
            logger.warning(f"Cannot subscribe to {channel}: not connected to Redis")
            return False

        try:
            await self.pubsub.subscribe(channel)
            self.subscribed_channels.add(channel)
            logger.info(f"Subscribed to Redis channel: {channel}")
            return True

        except Exception as e:
            logger.error(f"Error subscribing to channel {channel}: {e}")
            return False

    async def unsubscribe_from_channel(self, channel: str):
        """Unsubscribe from a specific Redis channel"""

        if not self.is_connected:
            return False

        try:
            await self.pubsub.unsubscribe(channel)
            self.subscribed_channels.discard(channel)
            logger.info(f"Unsubscribed from Redis channel: {channel}")
            return True

        except Exception as e:
            logger.error(f"Error unsubscribing from channel {channel}: {e}")
            return False

    async def subscribe_to_pattern(self, pattern: str):
        """Subscribe to Redis channels matching a pattern"""

        if not self.is_connected:
            logger.warning(
                f"Cannot subscribe to pattern {pattern}: not connected to Redis"
            )
            return False

        try:
            await self.pubsub.psubscribe(pattern)
            self.subscription_patterns.add(pattern)
            logger.info(f"Subscribed to Redis pattern: {pattern}")
            return True

        except Exception as e:
            logger.error(f"Error subscribing to pattern {pattern}: {e}")
            return False

    async def unsubscribe_from_pattern(self, pattern: str):
        """Unsubscribe from Redis pattern"""

        if not self.is_connected:
            return False

        try:
            await self.pubsub.punsubscribe(pattern)
            self.subscription_patterns.discard(pattern)
            logger.info(f"Unsubscribed from Redis pattern: {pattern}")
            return True

        except Exception as e:
            logger.error(f"Error unsubscribing from pattern {pattern}: {e}")
            return False

    def get_stats(self) -> dict:
        """Get subscriber statistics"""

        uptime = time.time() - self.start_time

        return {
            "is_connected": self.is_connected,
            "subscribed_channels": list(self.subscribed_channels),
            "subscription_patterns": list(self.subscription_patterns),
            "messages_received": self.messages_received,
            "messages_processed": self.messages_processed,
            "connection_errors": self.connection_errors,
            "connection_attempts": self.connection_attempts,
            "uptime": uptime,
            "messages_per_second": (
                self.messages_processed / uptime if uptime > 0 else 0
            ),
        }

    # Private methods

    async def _connect(self) -> bool:
        """Connect to Redis"""

        try:
            self.connection_attempts += 1
            self.last_connection_attempt = time.time()

            # Create Redis client
            self.redis_client = redis.from_url(
                config.get_redis_url(),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30,
            )

            # Test connection
            await self.redis_client.ping()

            # Create pubsub client
            self.pubsub = self.redis_client.pubsub()

            self.is_connected = True
            self.connection_errors = 0

            logger.info(
                f"Connected to Redis at {config.REDIS_HOST}:{config.REDIS_PORT}"
            )
            return True

        except Exception as e:
            self.connection_errors += 1
            logger.error(f"Failed to connect to Redis: {e}")
            await self._disconnect()
            return False

    async def _disconnect(self):
        """Disconnect from Redis"""

        self.is_connected = False

        try:
            if self.pubsub:
                await self.pubsub.close()
                self.pubsub = None

            if self.redis_client:
                await self.redis_client.close()
                self.redis_client = None

        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")

        self.subscribed_channels.clear()
        self.subscription_patterns.clear()

    async def _setup_default_subscriptions(self):
        """Setup default Redis channel subscriptions"""

        if not self.is_connected:
            return

        # Subscribe to all MOD UI events
        pattern = config.get_redis_channel("*")
        await self.subscribe_to_pattern(pattern)

        # Subscribe to specific channels for better control
        default_channels = [
            config.get_redis_channel("events"),
            config.get_redis_channel("session"),
            config.get_redis_channel("pedalboard"),
            config.get_redis_channel("hardware"),
            config.get_redis_channel("system"),
        ]

        for channel in default_channels:
            await self.subscribe_to_channel(channel)

    async def _message_loop(self):
        """Main message processing loop"""

        try:
            while True:
                if not self.is_connected or not self.pubsub:
                    await asyncio.sleep(1)
                    continue

                try:
                    # Get message from Redis
                    message = await self.pubsub.get_message(timeout=1.0)

                    if message is None:
                        continue

                    await self._process_message(message)

                except asyncio.TimeoutError:
                    continue
                except redis.ConnectionError as e:
                    logger.error(f"Redis connection error: {e}")
                    self.is_connected = False
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error in message loop: {e}")
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("Redis message loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in message loop: {e}")

    async def _process_message(self, message: dict):
        """Process a Redis message"""

        try:
            self.messages_received += 1

            # Skip subscription/unsubscription messages
            message_type = message.get("type", "")
            if message_type in [
                "subscribe",
                "unsubscribe",
                "psubscribe",
                "punsubscribe",
            ]:
                return

            # Get channel and data
            channel = message.get("channel", "")
            pattern = message.get("pattern", "")
            data = message.get("data", "")

            if not data or not isinstance(data, str):
                return

            # Use pattern if available (for pattern subscriptions)
            channel_name = pattern or channel

            # Forward to event router
            await self.event_router.route_redis_event(channel_name, data)

            self.messages_processed += 1

        except Exception as e:
            logger.error(f"Error processing Redis message: {e}")

    async def _reconnect_loop(self):
        """Automatic reconnection loop"""

        try:
            while True:
                await asyncio.sleep(10)  # Check every 10 seconds

                if not self.is_connected:
                    # Only reconnect if enough time has passed
                    if time.time() - self.last_connection_attempt > 5:
                        logger.info("Attempting to reconnect to Redis...")

                        if await self._connect():
                            await self._setup_default_subscriptions()
                            logger.info("Successfully reconnected to Redis")
                        else:
                            logger.warning("Failed to reconnect to Redis")

        except asyncio.CancelledError:
            logger.info("Redis reconnect loop cancelled")
        except Exception as e:
            logger.error(f"Error in reconnect loop: {e}")
