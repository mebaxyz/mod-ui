"""
Event Bus System for Session Service

Provides event-driven communication between services and WebSocket clients.
Supports both in-memory and Redis-based implementations for scalability.
"""

import asyncio
import json
import logging
import weakref
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..models.events import EventType, SessionEvent


class EventBus:
    """
    Abstract base class for event bus implementations
    """

    async def publish(self, event: SessionEvent) -> None:
        """Publish an event to the bus"""
        raise NotImplementedError

    async def subscribe(self, event_type: EventType, handler: Callable) -> str:
        """Subscribe to events of a specific type. Returns subscription ID."""
        raise NotImplementedError

    async def subscribe_all(self, handler: Callable) -> str:
        """Subscribe to all events. Returns subscription ID."""
        raise NotImplementedError

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events. Returns True if successful."""
        raise NotImplementedError

    async def close(self) -> None:
        """Close the event bus and cleanup resources"""
        raise NotImplementedError


class InMemoryEventBus(EventBus):
    """
    In-memory event bus implementation for single-process scenarios

    Features:
    - Fast local event distribution
    - Type-based event filtering
    - Weak references to prevent memory leaks
    - Event history for debugging
    """

    def __init__(self, max_history: int = 1000):
        self.logger = logging.getLogger(__name__)
        self._subscribers: Dict[EventType, Dict[str, Callable]] = {}
        self._all_subscribers: Dict[str, Callable] = {}
        self._subscription_counter = 0
        self._event_history: List[SessionEvent] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()

        self.logger.info("InMemoryEventBus initialized")

    async def publish(self, event: SessionEvent) -> None:
        """Publish an event to all subscribers"""
        try:
            async with self._lock:
                # Add to history
                self._event_history.append(event)
                if len(self._event_history) > self._max_history:
                    self._event_history.pop(0)

                # Notify type-specific subscribers
                if event.event_type in self._subscribers:
                    subscribers = list(self._subscribers[event.event_type].values())
                    for handler in subscribers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(event)
                            else:
                                handler(event)
                        except Exception as e:
                            self.logger.error(f"Error in event handler: {e}")

                # Notify all-event subscribers
                all_subscribers = list(self._all_subscribers.values())
                for handler in all_subscribers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        self.logger.error(f"Error in all-event handler: {e}")

                self.logger.debug(
                    f"Published event: {event.event_type} from {event.source_service}"
                )

        except Exception as e:
            self.logger.error(f"Failed to publish event: {e}")
            raise

    async def subscribe(self, event_type: EventType, handler: Callable) -> str:
        """Subscribe to events of a specific type"""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = {}

            subscription_id = f"sub_{self._subscription_counter}"
            self._subscription_counter += 1

            self._subscribers[event_type][subscription_id] = handler

            self.logger.debug(f"Added subscription {subscription_id} for {event_type}")
            return subscription_id

    async def subscribe_all(self, handler: Callable) -> str:
        """Subscribe to all events"""
        async with self._lock:
            subscription_id = f"all_{self._subscription_counter}"
            self._subscription_counter += 1

            self._all_subscribers[subscription_id] = handler

            self.logger.debug(f"Added all-events subscription {subscription_id}")
            return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        async with self._lock:
            # Check all-event subscribers
            if subscription_id in self._all_subscribers:
                del self._all_subscribers[subscription_id]
                self.logger.debug(f"Removed all-events subscription {subscription_id}")
                return True

            # Check type-specific subscribers
            for event_type, subscribers in self._subscribers.items():
                if subscription_id in subscribers:
                    del subscribers[subscription_id]
                    if not subscribers:  # Clean up empty subscriber lists
                        del self._subscribers[event_type]
                    self.logger.debug(
                        f"Removed subscription {subscription_id} for {event_type}"
                    )
                    return True

            return False

    async def get_event_history(
        self, limit: Optional[int] = None
    ) -> List[SessionEvent]:
        """Get recent event history"""
        async with self._lock:
            if limit is None:
                return self._event_history.copy()
            else:
                return self._event_history[-limit:].copy()

    async def get_subscriber_count(self) -> Dict[str, int]:
        """Get subscriber counts for debugging"""
        async with self._lock:
            type_counts = {
                str(event_type): len(subs)
                for event_type, subs in self._subscribers.items()
            }
            return {
                "all_subscribers": len(self._all_subscribers),
                "type_subscribers": type_counts,
                "total_subscriptions": len(self._all_subscribers)
                + sum(len(subs) for subs in self._subscribers.values()),
            }

    async def close(self) -> None:
        """Close the event bus"""
        async with self._lock:
            self._subscribers.clear()
            self._all_subscribers.clear()
            self._event_history.clear()

        self.logger.info("InMemoryEventBus closed")


class RedisEventBus(EventBus):
    """
    Redis-based event bus implementation for multi-process/distributed scenarios

    Features:
    - Cross-process event distribution
    - Persistent event storage
    - Redis pub/sub for real-time delivery
    - Automatic reconnection
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.logger = logging.getLogger(__name__)
        self.redis_url = redis_url
        self._subscribers: Dict[str, Callable] = {}
        self._subscription_counter = 0
        self._redis = None
        self._pubsub = None
        self._listener_task = None

        self.logger.info(f"RedisEventBus initialized with URL: {redis_url}")

    async def initialize(self) -> None:
        """Initialize Redis connections"""
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(self.redis_url)
            self._pubsub = self._redis.pubsub()

            # Subscribe to the events channel
            await self._pubsub.subscribe("mod_ui_events")

            # Start listener task
            self._listener_task = asyncio.create_task(self._listen_for_events())

            self.logger.info("RedisEventBus initialized successfully")

        except ImportError:
            self.logger.error(
                "redis package not installed. Install with: pip install redis"
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis: {e}")
            raise

    async def publish(self, event: SessionEvent) -> None:
        """Publish an event via Redis"""
        try:
            if self._redis is None:
                await self.initialize()

            # Serialize event to JSON
            event_data = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "source_service": event.source_service,
                "session_id": event.session_id,
                "timestamp": event.timestamp.isoformat(),
                "priority": event.priority.value,
                "data": event.data,
                "target_clients": event.target_clients,
            }

            event_json = json.dumps(event_data)

            # Publish to Redis
            await self._redis.publish("mod_ui_events", event_json)

            # Store in Redis with expiration (24 hours)
            await self._redis.setex(f"event:{event.event_id}", 86400, event_json)

            self.logger.debug(f"Published event to Redis: {event.event_type}")

        except Exception as e:
            self.logger.error(f"Failed to publish event to Redis: {e}")
            raise

    async def subscribe(self, event_type: EventType, handler: Callable) -> str:
        """Subscribe to events of a specific type"""
        subscription_id = f"sub_{self._subscription_counter}_{event_type.value}"
        self._subscription_counter += 1

        self._subscribers[subscription_id] = {
            "handler": handler,
            "event_type": event_type,
            "all_events": False,
        }

        self.logger.debug(
            f"Added Redis subscription {subscription_id} for {event_type}"
        )
        return subscription_id

    async def subscribe_all(self, handler: Callable) -> str:
        """Subscribe to all events"""
        subscription_id = f"all_{self._subscription_counter}"
        self._subscription_counter += 1

        self._subscribers[subscription_id] = {
            "handler": handler,
            "event_type": None,
            "all_events": True,
        }

        self.logger.debug(f"Added Redis all-events subscription {subscription_id}")
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        if subscription_id in self._subscribers:
            del self._subscribers[subscription_id]
            self.logger.debug(f"Removed Redis subscription {subscription_id}")
            return True
        return False

    async def _listen_for_events(self) -> None:
        """Listen for events from Redis pub/sub"""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event = SessionEvent(
                            event_id=event_data["event_id"],
                            event_type=EventType(event_data["event_type"]),
                            source_service=event_data["source_service"],
                            session_id=event_data.get("session_id"),
                            timestamp=datetime.fromisoformat(event_data["timestamp"]),
                            priority=event_data["priority"],
                            data=event_data["data"],
                            target_clients=event_data.get("target_clients"),
                        )

                        # Notify subscribers
                        for sub_id, sub_info in self._subscribers.items():
                            try:
                                handler = sub_info["handler"]
                                if (
                                    sub_info["all_events"]
                                    or sub_info["event_type"] == event.event_type
                                ):
                                    if asyncio.iscoroutinefunction(handler):
                                        await handler(event)
                                    else:
                                        handler(event)
                            except Exception as e:
                                self.logger.error(
                                    f"Error in Redis event handler {sub_id}: {e}"
                                )

                    except Exception as e:
                        self.logger.error(f"Failed to process Redis event: {e}")

        except Exception as e:
            self.logger.error(f"Redis listener error: {e}")

    async def close(self) -> None:
        """Close Redis connections"""
        try:
            if self._listener_task:
                self._listener_task.cancel()
                try:
                    await self._listener_task
                except asyncio.CancelledError:
                    pass

            if self._pubsub:
                await self._pubsub.close()

            if self._redis:
                await self._redis.close()

            self._subscribers.clear()

            self.logger.info("RedisEventBus closed")

        except Exception as e:
            self.logger.error(f"Error closing Redis connections: {e}")


# Event bus factory
def create_event_bus(
    use_redis: bool = False, redis_url: str = "redis://localhost:6379"
) -> EventBus:
    """Create an event bus instance"""
    if use_redis:
        return RedisEventBus(redis_url)
    else:
        return InMemoryEventBus()


# Event bus singleton for easy access
_event_bus_instance: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = create_event_bus()
        if hasattr(_event_bus_instance, "initialize"):
            await _event_bus_instance.initialize()
    return _event_bus_instance


async def close_event_bus() -> None:
    """Close the global event bus instance"""
    global _event_bus_instance
    if _event_bus_instance is not None:
        await _event_bus_instance.close()
        _event_bus_instance = None
