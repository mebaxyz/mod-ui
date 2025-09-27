"""
Unified microservice class that combines client and server functionality
"""
import asyncio
import logging
from typing import Dict, Any, Callable, Optional, List, Type, TypeVar, Awaitable
from datetime import datetime
import redis.asyncio as redis

from .client import ServiceClient
from .server import ServiceServer, handler, event_handler
from .discovery import ServiceDiscovery
from .events import EventBus, EventPublisher, EventSubscriber
from .metrics import MetricsCollector
from .models import (
    ServiceRequest, ServiceResponse, ServiceEvent, ServiceHealth,
    ServiceCapability, RequestMetrics
)
from .config import get_config


logger = logging.getLogger(__name__)
T = TypeVar('T')


class Service:
    """
    Unified service class that combines client and server functionality
    
    This class allows a service to both:
    - Handle incoming requests (server functionality)
    - Make calls to other services (client functionality)
    - Participate in service discovery
    - Publish and subscribe to events
    - Collect metrics
    
    Example:
        service = Service("effects-service")
        
        # Register handlers (server functionality)
        service.register_handler("get_plugins", my_handler)
        
        # Start the service
        await service.start()
        
        # Make calls to other services (client functionality)
        response = await service.call("config-service", "get_config")
        
        # Publish events
        await service.publish_event("plugin.loaded", {"uri": plugin_uri})
        
        # Subscribe to events
        service.subscribe_to_event("user.created", my_event_handler)
    """
    
    def __init__(
        self,
        service_name: str,
        redis_client: Optional[redis.Redis] = None,
        enable_discovery: bool = True,
        enable_events: bool = True,
        enable_metrics: bool = True
    ):
        self.service_name = service_name
        self.config = get_config()
        
        # Core components
        self._redis = redis_client
        self._server = ServiceServer(service_name, redis_client)
        self._client = ServiceClient(service_name, redis_client)
        
        # Optional components
        self._discovery = ServiceDiscovery(redis_client) if enable_discovery else None
        self._event_bus = EventBus(redis_client) if enable_events else None
        self._event_publisher = EventPublisher(service_name, self._event_bus) if enable_events else None
        self._metrics = MetricsCollector(redis_client) if enable_metrics else None
        
        self._is_running = False
        self._startup_tasks: List[Callable[[], Awaitable[None]]] = []
        self._shutdown_tasks: List[Callable[[], Awaitable[None]]] = []

    # Server functionality delegation
    
    def register_handler(
        self,
        request_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]],
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a request handler (server functionality)"""
        return self._server.register_handler(
            request_type, handler, description, input_schema, output_schema
        )

    def register_event_handler(
        self,
        event_type: str,
        handler: Callable[[ServiceEvent], Awaitable[None]]
    ) -> None:
        """Register an event handler (server functionality)"""
        if self._event_bus:
            self._event_bus.subscribe(event_type, handler)
        return self._server.register_event_handler(event_type, handler)

    # Client functionality delegation
    
    async def call(
        self,
        target_service: str,
        request_type: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        return_type: Optional[Type[T]] = None,
        enable_caching: Optional[bool] = None,
        max_retries: Optional[int] = None
    ) -> T:
        """Make a service call (client functionality)"""
        return await self._client.call(
            target_service, request_type, data, timeout, 
            return_type, enable_caching, max_retries
        )

    async def batch_call(
        self,
        requests: List[tuple],  # (target_service, request_type, data)
        timeout: Optional[float] = None
    ) -> List[Any]:
        """Make multiple service calls concurrently (client functionality)"""
        return await self._client.batch_call(requests, timeout)

    # Service discovery functionality
    
    async def discover_services(self, refresh: bool = False) -> Dict[str, Any]:
        """Discover available services"""
        if not self._discovery:
            raise RuntimeError("Service discovery not enabled")
        
        services = await self._discovery.discover_services(refresh)
        return {
            name: {
                "status": reg.health.status,
                "capabilities": [cap.request_type for cap in reg.capabilities],
                "uptime": reg.health.uptime_seconds,
                "request_count": reg.health.request_count
            }
            for name, reg in services.items()
        }

    async def find_service_for_request(self, request_type: str) -> Optional[str]:
        """Find a service that can handle a specific request type"""
        if not self._discovery:
            return None
        
        from .discovery import ServiceLoadBalancer
        balancer = ServiceLoadBalancer(self._discovery)
        return await balancer.get_service_for_request(request_type)

    async def wait_for_service(
        self, 
        service_name: str, 
        timeout: float = 30.0
    ) -> bool:
        """Wait for a service to become available"""
        if not self._discovery:
            return False
        
        try:
            await self._discovery.wait_for_service(service_name, timeout)
            return True
        except TimeoutError:
            return False

    # Event functionality
    
    async def publish_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> int:
        """Publish an event"""
        if not self._event_publisher:
            raise RuntimeError("Events not enabled")
        
        return await self._event_publisher.publish_custom_event(event_type, data)

    def subscribe_to_event(
        self,
        event_type: str,
        handler: Callable[[ServiceEvent], Awaitable[None]]
    ) -> None:
        """Subscribe to an event type"""
        if not self._event_bus:
            raise RuntimeError("Events not enabled")
        
        self._event_bus.subscribe(event_type, handler)

    # Convenience methods for common events
    
    async def publish_service_started(self, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Publish service started event"""
        if self._event_publisher:
            return await self._event_publisher.publish_service_started(metadata)
        return 0

    async def publish_service_stopped(self, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Publish service stopped event"""
        if self._event_publisher:
            return await self._event_publisher.publish_service_stopped(metadata)
        return 0

    async def publish_error(self, error: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Publish service error event"""
        if self._event_publisher:
            return await self._event_publisher.publish_service_error(error, metadata)
        return 0

    # Health and metrics
    
    async def get_health(self) -> ServiceHealth:
        """Get service health"""
        return self._server._health_status

    async def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        if not self._metrics:
            return {"metrics_disabled": True}
        
        return await self._metrics.get_service_metrics(self.service_name)

    def get_client_metrics(self) -> List[RequestMetrics]:
        """Get client request metrics"""
        return self._client.get_metrics()

    # Lifecycle management
    
    def add_startup_task(self, task: Callable[[], Awaitable[None]]) -> None:
        """Add a task to run during startup"""
        self._startup_tasks.append(task)

    def add_shutdown_task(self, task: Callable[[], Awaitable[None]]) -> None:
        """Add a task to run during shutdown"""
        self._shutdown_tasks.append(task)

    async def start(self) -> None:
        """Start the microservice"""
        if self._is_running:
            logger.warning(f"Service '{self.service_name}' is already running")
            return

        logger.info(f"Starting microservice '{self.service_name}'...")

        try:
            # Start metrics collection
            if self._metrics:
                await self._metrics.start_collecting()

            # Start service discovery monitoring
            if self._discovery:
                await self._discovery.start_monitoring()

            # Start event bus
            if self._event_bus:
                await self._event_bus.start_listening()

            # Run startup tasks
            for task in self._startup_tasks:
                try:
                    await task()
                except Exception as e:
                    logger.error(f"Error in startup task: {e}")

            # Start the server (this will block and listen for requests)
            # We run this as a background task so we can continue
            self._server_task = asyncio.create_task(self._server.start())
            
            # Give the server time to register
            await asyncio.sleep(0.5)
            
            self._is_running = True
            
            # Publish service started event
            await self.publish_service_started({
                "version": getattr(self, 'version', '1.0.0'),
                "capabilities": len(self._server._capabilities)
            })

            logger.info(f"Microservice '{self.service_name}' started successfully")

        except Exception as e:
            logger.error(f"Failed to start microservice '{self.service_name}': {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the microservice"""
        if not self._is_running:
            return

        logger.info(f"Stopping microservice '{self.service_name}'...")

        self._is_running = False

        try:
            # Publish service stopped event
            await self.publish_service_stopped()

            # Run shutdown tasks
            for task in self._shutdown_tasks:
                try:
                    await task()
                except Exception as e:
                    logger.error(f"Error in shutdown task: {e}")

            # Stop server
            if hasattr(self, '_server_task'):
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass
            
            await self._server.stop()

            # Stop other components
            if self._event_bus:
                await self._event_bus.close()

            if self._discovery:
                await self._discovery.close()

            if self._metrics:
                await self._metrics.close()

            # Close client
            await self._client.close()

            logger.info(f"Microservice '{self.service_name}' stopped")

        except Exception as e:
            logger.error(f"Error stopping microservice '{self.service_name}': {e}")

    async def run_forever(self) -> None:
        """Start the service and run forever"""
        await self.start()
        
        try:
            # Keep the service running
            while self._is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop()

    # Context manager support
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()

    # Decorator support for auto-registration
    
    def register_handlers_from_class(self, handler_class: Any) -> "Service":
        """Register all handlers from a class using decorators"""
        for method_name in dir(handler_class):
            method = getattr(handler_class, method_name)
            
            # Check for handler decorator
            if hasattr(method, '_handler_request_type'):
                request_type = method._handler_request_type
                description = getattr(method, '_handler_description', '')
                self.register_handler(request_type, method, description)
            
            # Check for event handler decorator
            if hasattr(method, '_event_handler_type'):
                event_type = method._event_handler_type
                self.register_event_handler(event_type, method)
        
        return self

    # Smart request routing (calls local handler or remote service)
    
    async def smart_call(
        self,
        request_type: str,
        data: Optional[Dict[str, Any]] = None,
        prefer_local: bool = True,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Smart call that tries local handler first, then remote services
        
        Args:
            request_type: Type of request
            data: Request data
            prefer_local: Whether to prefer local handlers
            timeout: Request timeout
            
        Returns:
            Response data
        """
        # Check if we have a local handler
        if prefer_local and request_type in self._server._handlers:
            try:
                handler = self._server._handlers[request_type]
                return await handler(data or {})
            except Exception as e:
                logger.warning(f"Local handler failed for {request_type}: {e}")
                # Fall through to remote call
        
        # Try to find a remote service
        target_service = await self.find_service_for_request(request_type)
        if target_service:
            return await self.call(target_service, request_type, data, timeout)
        
        # If prefer_local is False, try local handler as fallback
        if not prefer_local and request_type in self._server._handlers:
            handler = self._server._handlers[request_type]
            return await handler(data or {})
        
        raise RuntimeError(f"No handler found for request type '{request_type}'")


# Convenience function for creating a microservice
def create_service(
    service_name: str,
    redis_url: Optional[str] = None,
    **kwargs
) -> Service:
    """
    Create a service with optional Redis configuration
    
    Args:
        service_name: Name of the service
        redis_url: Redis connection URL (optional)
        **kwargs: Additional arguments for Service
        
    Returns:
        Configured Service instance
    """
    redis_client = None
    if redis_url:
        import redis.asyncio as redis
        redis_client = redis.Redis.from_url(redis_url)
    
    return Service(service_name, redis_client, **kwargs)


# Context manager for temporary services
async def temporary_service(service_name: str, **kwargs):
    """Context manager for creating temporary services"""
    service = Service(service_name, **kwargs)
    try:
        await service.start()
        yield service
    finally:
        await service.stop()