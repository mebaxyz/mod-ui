"""
Event-based communication additions to the service library
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Set

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class EventBus:
    """Pub/Sub event bus for broadcasting events without expecting responses"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None
        self.subscriptions = {}
        self.listening = False

    async def connect(self):
        if not self.redis:
            self.redis = redis.from_url(self.redis_url)

    async def publish_event(
        self, event_type: str, data: Dict[str, Any], service_name: str = "unknown"
    ):
        """Publish an event to all subscribers"""
        await self.connect()

        event = {
            "event_type": event_type,
            "service_name": service_name,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "event_id": str(uuid.uuid4()),
        }

        channel = f"events:{event_type}"
        await self.redis.publish(channel, json.dumps(event))
        logger.debug(f"Published event {event_type} from {service_name}")

    async def subscribe_to_event(self, event_type: str, handler: Callable):
        """Subscribe to a specific event type"""
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []

        self.subscriptions[event_type].append(handler)

        if not self.listening:
            asyncio.create_task(self._listen_for_events())
            self.listening = True

    async def _listen_for_events(self):
        """Listen for events and dispatch to handlers"""
        await self.connect()

        pubsub = self.redis.pubsub()

        # Subscribe to all event channels we're interested in
        for event_type in self.subscriptions:
            await pubsub.subscribe(f"events:{event_type}")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    event_data = json.loads(message["data"])
                    event_type = event_data["event_type"]

                    if event_type in self.subscriptions:
                        for handler in self.subscriptions[event_type]:
                            try:
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(event_data)
                                else:
                                    handler(event_data)
                            except Exception as e:
                                logger.error(f"Error in event handler: {e}")
                except Exception as e:
                    logger.error(f"Error processing event: {e}")


# Example usage in services:
class EffectsServiceWithEvents:
    """Example of how effects service could use events"""

    def __init__(self):
        self.event_bus = EventBus()

    async def add_effect(self, plugin_uri: str, instance_id: str):
        """Add effect and broadcast event"""
        # Do the actual work
        result = await self._add_effect_internal(plugin_uri, instance_id)

        # Broadcast event
        await self.event_bus.publish_event(
            "effect_added",
            {
                "plugin_uri": plugin_uri,
                "instance_id": instance_id,
                "success": result.success,
            },
            "effects_service",
        )

        return result

    async def _add_effect_internal(self, plugin_uri, instance_id):
        # Mock implementation
        class Result:
            success = True

        return Result()
