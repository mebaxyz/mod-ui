"""
Event bus and event handling functionality
"""
import asyncio
import json
import time
import logging
from typing import Dict, List, Callable, Any, Optional, Set, Awaitable
from datetime import datetime
import redis.asyncio as redis

from .models import ServiceEvent
from .config import get_config


logger = logging.getLogger(__name__)


class EventBus:
    """Event bus for publishing and subscribing to events"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.config = get_config()
        self._redis = redis_client
        self._connection_pool = None
        self._subscribers: Dict[str, List[Callable]] = {}
        self._is_listening = False
        self._event_buffer: List[ServiceEvent] = []
        self._buffer_lock = asyncio.Lock()
        self._background_tasks: Set[asyncio.Task] = set()
        
    async def get_redis(self) -> redis.Redis:
        """Get Redis connection with connection pooling"""
        if self._redis is None:
            if self.config.enable_connection_pooling and self._connection_pool is None:
                self._connection_pool = redis.ConnectionPool.from_url(
                    self.config.redis_url,
                    max_connections=self.config.redis_max_connections,
                    socket_keepalive=self.config.redis_socket_keepalive,
                    socket_keepalive_options=self.config.redis_socket_keepalive_options
                )
                self._redis = redis.Redis(connection_pool=self._connection_pool)
            else:
                self._redis = redis.Redis.from_url(self.config.redis_url)
        return self._redis

    async def publish(self, event: ServiceEvent) -> int:
        """
        Publish an event to the event bus
        
        Args:
            event: Event to publish
            
        Returns:
            Number of subscribers that received the event
        """
        redis_client = await self.get_redis()
        channel = f"events:{event.event_type}"
        
        # Publish to Redis
        subscribers = await redis_client.publish(channel, event.json())
        
        # Also publish to wildcard channel for global listeners
        await redis_client.publish("events:*", event.json())
        
        if self.config.debug_mode:
            logger.info(f"Published event {event.event_type} from {event.source_service} to {subscribers} subscribers")
        
        return subscribers

    async def publish_batch(self, events: List[ServiceEvent]) -> int:
        """Publish multiple events in a batch"""
        if not events:
            return 0
        
        total_subscribers = 0
        for event in events:
            subscribers = await self.publish(event)
            total_subscribers += subscribers
        
        return total_subscribers

    def subscribe(
        self, 
        event_type: str, 
        handler: Callable[[ServiceEvent], Awaitable[None]]
    ) -> None:
        """
        Subscribe to events of a specific type
        
        Args:
            event_type: Type of events to subscribe to (use "*" for all events)
            handler: Async function to handle events
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed to events of type '{event_type}'")

    def unsubscribe(
        self, 
        event_type: str, 
        handler: Callable[[ServiceEvent], Awaitable[None]]
    ) -> bool:
        """
        Unsubscribe from events
        
        Args:
            event_type: Type of events to unsubscribe from
            handler: Handler function to remove
            
        Returns:
            True if handler was found and removed
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]
                logger.info(f"Unsubscribed from events of type '{event_type}'")
                return True
            except ValueError:
                pass
        
        return False

    async def start_listening(self) -> None:
        """Start listening for events"""
        if self._is_listening or not self._subscribers:
            return
        
        self._is_listening = True
        
        # Start event listening task
        task = asyncio.create_task(self._event_listening_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        # Start buffer processing task
        task = asyncio.create_task(self._buffer_processing_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        logger.info("Event bus started listening")

    async def stop_listening(self) -> None:
        """Stop listening for events"""
        self._is_listening = False
        
        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        logger.info("Event bus stopped listening")

    async def _event_listening_loop(self) -> None:
        """Main event listening loop"""
        redis_client = await self.get_redis()
        pubsub = redis_client.pubsub()
        
        # Subscribe to all event types we're interested in
        for event_type in self._subscribers.keys():
            if event_type == "*":
                await pubsub.subscribe("events:*")
            else:
                await pubsub.subscribe(f"events:{event_type}")
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        event_data = json.loads(message['data'])
                        event = ServiceEvent.parse_obj(event_data)
                        
                        # Add to buffer for processing
                        async with self._buffer_lock:
                            self._event_buffer.append(event)
                            
                            # Prevent buffer overflow
                            if len(self._event_buffer) > self.config.event_buffer_size:
                                self._event_buffer = self._event_buffer[-self.config.event_buffer_size:]
                        
                    except Exception as e:
                        logger.error(f"Error parsing event: {e}")
                        
        except Exception as e:
            logger.error(f"Error in event listening loop: {e}")
        finally:
            await pubsub.close()

    async def _buffer_processing_loop(self) -> None:
        """Process buffered events"""
        while self._is_listening:
            try:
                # Get events from buffer
                events_to_process = []
                async with self._buffer_lock:
                    if self._event_buffer:
                        batch_size = min(len(self._event_buffer), self.config.event_batch_size)
                        events_to_process = self._event_buffer[:batch_size]
                        self._event_buffer = self._event_buffer[batch_size:]
                
                # Process events
                if events_to_process:
                    await self._process_events_batch(events_to_process)
                else:
                    # No events, wait a bit
                    await asyncio.sleep(self.config.batch_timeout)
                
            except Exception as e:
                logger.error(f"Error in buffer processing loop: {e}")
                await asyncio.sleep(1)

    async def _process_events_batch(self, events: List[ServiceEvent]) -> None:
        """Process a batch of events"""
        for event in events:
            await self._handle_event(event)

    async def _handle_event(self, event: ServiceEvent) -> None:
        """Handle a single event by calling all relevant handlers"""
        handlers = []
        
        # Get specific event type handlers
        if event.event_type in self._subscribers:
            handlers.extend(self._subscribers[event.event_type])
        
        # Get wildcard handlers
        if "*" in self._subscribers:
            handlers.extend(self._subscribers["*"])
        
        # Execute handlers concurrently
        if handlers:
            tasks = []
            for handler in handlers:
                task = asyncio.create_task(self._safe_call_handler(handler, event))
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call_handler(self, handler: Callable, event: ServiceEvent) -> None:
        """Safely call an event handler"""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in event handler: {e}")

    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get statistics about event handling"""
        async with self._buffer_lock:
            buffer_size = len(self._event_buffer)
        
        return {
            "is_listening": self._is_listening,
            "subscriber_count": len(self._subscribers),
            "event_types": list(self._subscribers.keys()),
            "buffer_size": buffer_size,
            "max_buffer_size": self.config.event_buffer_size,
            "background_tasks": len(self._background_tasks)
        }

    async def close(self) -> None:
        """Close event bus and clean up resources"""
        await self.stop_listening()
        
        if self._redis:
            await self._redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()


class EventPublisher:
    """Helper class for publishing events from services"""
    
    def __init__(self, service_name: str, event_bus: Optional[EventBus] = None):
        self.service_name = service_name
        self.event_bus = event_bus or EventBus()
    
    async def publish_service_started(self, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Publish service started event"""
        event = ServiceEvent(
            event_type="service.started",
            service_name=self.service_name,
            timestamp=datetime.utcnow(),
            data=metadata or {}
        )
        return await self.event_bus.publish(event)

    async def publish_service_stopped(self, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Publish service stopped event"""
        event = ServiceEvent(
            event_type="service.stopped",
            service_name=self.service_name,
            timestamp=datetime.utcnow(),
            data=metadata or {}
        )
        return await self.event_bus.publish(event)
    
    async def publish_service_error(self, error: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Publish service error event"""
        data = {"error": error}
        if metadata:
            data.update(metadata)
        
        event = ServiceEvent(
            event_type="service.error",
            service_name=self.service_name,
            timestamp=datetime.utcnow(),
            data=data
        )
        return await self.event_bus.publish(event)
    
    async def publish_custom_event(
        self, 
        event_type: str, 
        data: Dict[str, Any]
    ) -> int:
        """Publish a custom event"""
        event = ServiceEvent(
            event_type=event_type,
            service_name=self.service_name,
            timestamp=datetime.utcnow(),
            data=data
        )
        return await self.event_bus.publish(event)


# Decorator for event handlers
def event_handler(event_type: str):
    """Decorator to mark methods as event handlers"""
    def decorator(func: Callable):
        func._event_handler_type = event_type
        return func
    return decorator


class EventSubscriber:
    """Base class for services that want to subscribe to events"""
    
    def __init__(self, service_name: str, event_bus: Optional[EventBus] = None):
        self.service_name = service_name
        self.event_bus = event_bus or EventBus()
    
    async def start_subscribing(self) -> None:
        """Start subscribing to events"""
        # Auto-discover event handlers
        for method_name in dir(self):
            method = getattr(self, method_name)
            if hasattr(method, '_event_handler_type'):
                event_type = method._event_handler_type
                self.event_bus.subscribe(event_type, method)
        
        await self.event_bus.start_listening()
    
    async def stop_subscribing(self) -> None:
        """Stop subscribing to events"""
        await self.event_bus.stop_listening()