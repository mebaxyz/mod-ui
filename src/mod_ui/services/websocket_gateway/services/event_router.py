"""
Event Router for WebSocket Gateway

Routes events from Redis to appropriate WebSocket clients based on subscriptions.
"""

import asyncio
import json
import logging
import time
from typing import Callable, Dict, List, Optional, Set

from src.mod_ui.services.websocket_gateway.models import EventRouterStats
from src.mod_ui.services.websocket_gateway.services.connection_manager import (
    ConnectionManager,
)
from src.mod_ui.services.websocket_gateway.utils import EventPriority, EventType, config

logger = logging.getLogger(__name__)


class EventRouter:
    """Routes events from Redis to WebSocket clients"""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

        # Event processing
        self.event_queue: asyncio.Queue = asyncio.Queue(
            maxsize=config.EVENT_BUFFER_SIZE
        )
        self.processing_task: Optional[asyncio.Task] = None

        # Statistics
        self.events_processed = 0
        self.events_dropped = 0
        self.last_event_time = 0.0
        self.start_time = time.time()

        # Event filters and transformations
        self.event_filters: Dict[EventType, Callable] = {}
        self.event_transformers: Dict[EventType, Callable] = {}

        # Batch processing
        self.event_batch: List[dict] = []
        self.last_batch_time = time.time()

    async def start(self):
        """Start the event router"""

        if self.processing_task and not self.processing_task.done():
            return

        self.processing_task = asyncio.create_task(self._process_events())
        logger.info("Event router started")

    async def stop(self):
        """Stop the event router"""

        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
            self.processing_task = None

        logger.info("Event router stopped")

    async def route_event(
        self,
        event_type: EventType,
        data: dict,
        priority: EventPriority = EventPriority.NORMAL,
        exclude_clients: Optional[Set[str]] = None,
    ) -> bool:
        """Route an event to subscribed clients"""

        event = {
            "event_type": event_type,
            "data": data,
            "priority": priority,
            "exclude_clients": exclude_clients or set(),
            "timestamp": time.time(),
        }

        try:
            # Add to queue for processing
            self.event_queue.put_nowait(event)
            return True

        except asyncio.QueueFull:
            self.events_dropped += 1
            logger.warning(f"Event queue full, dropped {event_type} event")
            return False

    async def route_redis_event(self, channel: str, message: str):
        """Route event received from Redis"""

        try:
            # Parse Redis message
            data = json.loads(message)

            # Extract event information
            event_type_str = data.get("event_type")
            if not event_type_str:
                # Try to extract from channel name
                if ":" in channel:
                    event_type_str = channel.split(":", 1)[1]
                else:
                    event_type_str = channel

            # Convert to EventType
            try:
                event_type = EventType(event_type_str)
            except ValueError:
                logger.warning(f"Unknown event type from Redis: {event_type_str}")
                return

            # Extract event data and metadata
            event_data = data.get("data", data)
            priority = EventPriority(data.get("priority", EventPriority.NORMAL))
            exclude_clients = set(data.get("exclude_clients", []))

            # Apply event filter if configured
            if event_type in self.event_filters:
                filter_func = self.event_filters[event_type]
                if not filter_func(event_data):
                    logger.debug(f"Event {event_type} filtered out")
                    return

            # Apply event transformer if configured
            if event_type in self.event_transformers:
                transformer_func = self.event_transformers[event_type]
                event_data = transformer_func(event_data)

            # Route the event
            await self.route_event(event_type, event_data, priority, exclude_clients)

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in Redis message: {message}")
        except Exception as e:
            logger.error(f"Error routing Redis event from {channel}: {e}")

    def add_event_filter(self, event_type: EventType, filter_func: Callable):
        """Add event filter function"""
        self.event_filters[event_type] = filter_func
        logger.debug(f"Added filter for {event_type}")

    def remove_event_filter(self, event_type: EventType):
        """Remove event filter function"""
        if event_type in self.event_filters:
            del self.event_filters[event_type]
            logger.debug(f"Removed filter for {event_type}")

    def add_event_transformer(self, event_type: EventType, transformer_func: Callable):
        """Add event transformer function"""
        self.event_transformers[event_type] = transformer_func
        logger.debug(f"Added transformer for {event_type}")

    def remove_event_transformer(self, event_type: EventType):
        """Remove event transformer function"""
        if event_type in self.event_transformers:
            del self.event_transformers[event_type]
            logger.debug(f"Removed transformer for {event_type}")

    def get_stats(self) -> EventRouterStats:
        """Get event router statistics"""

        current_time = time.time()
        uptime = current_time - self.start_time

        return EventRouterStats(
            events_processed=self.events_processed,
            events_dropped=self.events_dropped,
            queue_size=self.event_queue.qsize(),
            uptime=uptime,
            events_per_second=self.events_processed / uptime if uptime > 0 else 0,
            last_event_time=self.last_event_time,
            active_filters=list(self.event_filters.keys()),
            active_transformers=list(self.event_transformers.keys()),
        )

    # Private methods

    async def _process_events(self):
        """Main event processing loop"""

        try:
            while True:
                # Process events in batches for efficiency
                await self._process_event_batch()

        except asyncio.CancelledError:
            logger.info("Event processing cancelled")
        except Exception as e:
            logger.error(f"Error in event processing loop: {e}")

    async def _process_event_batch(self):
        """Process a batch of events"""

        current_time = time.time()

        # Collect events for batch processing
        while (
            len(self.event_batch) < config.EVENT_BATCH_SIZE
            and (current_time - self.last_batch_time) < config.EVENT_BATCH_TIMEOUT
        ):
            try:
                # Wait for event with timeout
                timeout = config.EVENT_BATCH_TIMEOUT - (
                    current_time - self.last_batch_time
                )
                if timeout <= 0:
                    break

                event = await asyncio.wait_for(self.event_queue.get(), timeout=timeout)
                self.event_batch.append(event)
                current_time = time.time()

            except asyncio.TimeoutError:
                break

        # Process batch if we have events
        if self.event_batch:
            await self._process_batch()
            self.event_batch.clear()
            self.last_batch_time = time.time()

    async def _process_batch(self):
        """Process the current event batch"""

        if not self.event_batch:
            return

        # Sort by priority (critical first)
        priority_order = {
            EventPriority.CRITICAL: 0,
            EventPriority.HIGH: 1,
            EventPriority.NORMAL: 2,
            EventPriority.LOW: 3,
        }

        self.event_batch.sort(key=lambda e: priority_order.get(e["priority"], 2))

        # Process events
        tasks = []
        for event in self.event_batch:
            task = self._process_single_event(event)
            tasks.append(task)

        # Execute all events concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Update statistics
        self.events_processed += len(self.event_batch)
        self.last_event_time = time.time()

    async def _process_single_event(self, event: dict):
        """Process a single event"""

        try:
            event_type = event["event_type"]
            data = event["data"]
            exclude_clients = event["exclude_clients"]

            # Route to connection manager
            await self.connection_manager.broadcast_event(
                event_type=event_type, data=data, exclude_clients=exclude_clients
            )

        except Exception as e:
            logger.error(f"Error processing event {event.get('event_type')}: {e}")

    # Built-in event filters and transformers

    @staticmethod
    def _default_system_stats_filter(data: dict) -> bool:
        """Filter system stats events to reduce noise"""

        # Only pass through if significant change
        cpu_load = data.get("cpu_load", 0)
        memory_usage = data.get("memory_usage", 0)

        # Skip if load is very low
        return cpu_load > 0.1 or memory_usage > 0.1

    @staticmethod
    def _default_parameter_change_transformer(data: dict) -> dict:
        """Transform parameter change events for consistency"""

        # Ensure required fields are present
        transformed = {
            "instance_id": data.get("instance_id", ""),
            "symbol": data.get("symbol", ""),
            "value": data.get("value", 0),
            "timestamp": data.get("timestamp", time.time()),
        }

        # Add legacy fields for backward compatibility
        if "port" in data:
            transformed["port"] = data["port"]

        return transformed

    def setup_default_filters_and_transformers(self):
        """Setup default event filters and transformers"""

        # Add default system stats filter
        self.add_event_filter(
            EventType.SYSTEM_STATS_UPDATED, self._default_system_stats_filter
        )

        # Add default parameter change transformer
        self.add_event_transformer(
            EventType.PARAMETER_CHANGED, self._default_parameter_change_transformer
        )
