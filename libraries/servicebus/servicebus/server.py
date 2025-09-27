"""
Enhanced service server for microservice communication
"""
import asyncio
import json
import time
import logging
from typing import Dict, Any, Callable, Optional, List, Awaitable, Set
from datetime import datetime, timedelta
import redis.asyncio as redis

from .models import (
    ServiceRequest, ServiceResponse, ServiceHealth,
    ServiceCapability, ServiceRegistration, ServiceEvent
)
from .config import get_config


logger = logging.getLogger(__name__)


class ServiceServer:
    """Enhanced server for handling microservice requests"""
    
    def __init__(
        self,
        service_name: str,
        redis_client: Optional[redis.Redis] = None
    ):
        self.service_name = service_name
        self.config = get_config()
        self._redis = redis_client
        self._connection_pool = None
        self._handlers: Dict[str, Callable] = {}
        self._capabilities: List[ServiceCapability] = []
        self._is_running = False
        self._health_status = ServiceHealth(
            service_name=service_name,
            status="starting",
            timestamp=datetime.utcnow()
        )
        self._request_count = 0
        self._error_count = 0
        self._start_time = datetime.utcnow()
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._background_tasks: Set[asyncio.Task] = set()
        
    @property
    async def redis(self) -> redis.Redis:
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

    def register_handler(
        self,
        request_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]],
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a request handler
        
        Args:
            request_type: Type of request this handler processes
            handler: Async function to handle the request
            description: Human-readable description of the handler
            input_schema: JSON schema for input validation (optional)
            output_schema: JSON schema for output validation (optional)
        """
        self._handlers[request_type] = handler
        
        # Register capability
        capability = ServiceCapability(
            request_type=request_type,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema
        )
        self._capabilities.append(capability)
        
        logger.info(f"Registered handler for '{request_type}' in service '{self.service_name}'")

    def register_event_handler(
        self,
        event_type: str,
        handler: Callable[[ServiceEvent], Awaitable[None]]
    ) -> None:
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        
        logger.info(f"Registered event handler for '{event_type}' in service '{self.service_name}'")

    async def start(self) -> None:
        """Start the service server"""
        logger.info(f"Starting service server '{self.service_name}'...")
        
        # Register built-in handlers
        await self._register_builtin_handlers()
        
        # Update health status
        self._health_status = ServiceHealth(
            service_name=self.service_name,
            status="healthy",
            timestamp=datetime.utcnow(),
            uptime_seconds=0,
            request_count=0,
            error_count=0
        )
        
        self._is_running = True
        
        # Start background tasks
        await self._start_background_tasks()
        
        # Register service in discovery
        await self._register_service()
        
        # Start listening for requests
        await self._listen_for_requests()

    async def _register_builtin_handlers(self) -> None:
        """Register built-in handlers"""
        self.register_handler(
            "health_check",
            self._handle_health_check,
            "Get service health status"
        )
        
        self.register_handler(
            "get_capabilities",
            self._handle_get_capabilities,
            "Get service capabilities"
        )
        
        self.register_handler(
            "ping",
            self._handle_ping,
            "Simple ping/pong for connectivity testing"
        )

    async def _start_background_tasks(self) -> None:
        """Start background maintenance tasks"""
        # Health reporting task
        if self.config.service_registry_ttl > 0:
            task = asyncio.create_task(self._health_reporting_task())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        
        # Event listening task
        if self._event_handlers:
            task = asyncio.create_task(self._event_listening_task())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _register_service(self) -> None:
        """Register service in discovery system"""
        redis_client = await self.redis
        
        registration = ServiceRegistration(
            service_name=self.service_name,
            capabilities=self._capabilities,
            health=self._health_status
        )
        
        # Store service registration
        registry_key = f"service_registry:{self.service_name}"
        await redis_client.setex(
            registry_key,
            self.config.service_registry_ttl,
            registration.json()
        )
        
        logger.info(f"Registered service '{self.service_name}' in discovery")

    async def _listen_for_requests(self) -> None:
        """Listen for incoming requests - optimized version"""
        redis_client = await self.redis
        request_channel = f"service:{self.service_name}:requests"
        
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(request_channel)
        
        logger.info(f"Service '{self.service_name}' listening for requests on '{request_channel}'")
        
        try:
            # Use async iteration instead of polling - this is the CPU optimization!
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        request_data = json.loads(message['data'])
                        request = ServiceRequest.parse_obj(request_data)
                        
                        # Handle request asynchronously
                        asyncio.create_task(self._handle_request(request))
                        
                    except Exception as e:
                        logger.error(f"Error processing request: {e}")
                        
        except Exception as e:
            logger.error(f"Error in request listener: {e}")
        finally:
            await pubsub.unsubscribe(request_channel)
            await pubsub.close()

    async def _handle_request(self, request: ServiceRequest) -> None:
        """Handle a single request"""
        self._request_count += 1
        start_time = time.time()
        
        try:
            # Find handler
            if request.request_type not in self._handlers:
                error_msg = f"No handler for request type '{request.request_type}'"
                response = ServiceResponse(
                    id=request.id,
                    success=False,
                    error=error_msg,
                    data={}
                )
            else:
                # Execute handler
                handler = self._handlers[request.request_type]
                result = await handler(request.data)
                
                response = ServiceResponse(
                    id=request.id,
                    success=True,
                    data=result
                )
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error handling request {request.id}: {e}")
            response = ServiceResponse(
                id=request.id,
                success=False,
                error=str(e),
                data={}
            )
        
        # Send response
        await self._send_response(request, response)
        
        # Log request metrics
        elapsed = time.time() - start_time
        if self.config.debug_mode:
            logger.info(
                f"Request {request.request_type} from {request.source_service} "
                f"completed in {elapsed:.3f}s (success: {response.success})"
            )

    async def _send_response(self, request: ServiceRequest, response: ServiceResponse) -> None:
        """Send response back to client"""
        redis_client = await self.redis
        response_channel = f"service:{request.source_service}:responses:{request.id}"
        
        await redis_client.publish(response_channel, response.json())

    async def _health_reporting_task(self) -> None:
        """Background task to report health status"""
        while self._is_running:
            try:
                # Update health status
                uptime = (datetime.utcnow() - self._start_time).total_seconds()
                self._health_status = ServiceHealth(
                    service_name=self.service_name,
                    status="healthy",
                    timestamp=datetime.utcnow(),
                    uptime_seconds=uptime,
                    request_count=self._request_count,
                    error_count=self._error_count
                )
                
                # Re-register service
                await self._register_service()
                
                # Wait for next cycle
                await asyncio.sleep(self.config.service_registry_ttl / 2)
                
            except Exception as e:
                logger.error(f"Error in health reporting: {e}")
                await asyncio.sleep(5)

    async def _event_listening_task(self) -> None:
        """Background task to listen for events"""
        if not self._event_handlers:
            return
            
        redis_client = await self.redis
        pubsub = redis_client.pubsub()
        
        # Subscribe to all event types we handle
        for event_type in self._event_handlers.keys():
            await pubsub.subscribe(f"events:{event_type}")
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        event_data = json.loads(message['data'])
                        event = ServiceEvent.parse_obj(event_data)
                        
                        # Handle event asynchronously
                        asyncio.create_task(self._handle_event(event))
                        
                    except Exception as e:
                        logger.error(f"Error processing event: {e}")
                        
        except Exception as e:
            logger.error(f"Error in event listener: {e}")
        finally:
            await pubsub.close()

    async def _handle_event(self, event: ServiceEvent) -> None:
        """Handle a received event"""
        if event.event_type in self._event_handlers:
            for handler in self._event_handlers[event.event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event.event_type}: {e}")

    # Built-in handlers
    
    async def _handle_health_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check request"""
        return self._health_status.dict()

    async def _handle_get_capabilities(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle capabilities request"""
        return {
            "capabilities": [cap.dict() for cap in self._capabilities]
        }

    async def _handle_ping(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request"""
        return {"pong": True, "timestamp": datetime.utcnow().isoformat()}

    async def stop(self) -> None:
        """Stop the service server"""
        logger.info(f"Stopping service server '{self.service_name}'...")
        
        self._is_running = False
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Update health status to stopping
        self._health_status = ServiceHealth(
            service_name=self.service_name,
            status="stopping",
            timestamp=datetime.utcnow()
        )
        
        # Remove from service registry
        redis_client = await self.redis
        registry_key = f"service_registry:{self.service_name}"
        await redis_client.delete(registry_key)
        
        # Close Redis connection
        if self._redis:
            await self._redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()
        
        logger.info(f"Service server '{self.service_name}' stopped")


# Decorator for easier handler registration
def handler(request_type: str, description: str = ""):
    """Decorator to register request handlers"""
    def decorator(func: Callable):
        func._handler_request_type = request_type
        func._handler_description = description
        return func
    return decorator


def event_handler(event_type: str):
    """Decorator to register event handlers"""
    def decorator(func: Callable):
        func._event_handler_type = event_type
        return func
    return decorator


class ServiceServerBuilder:
    """Builder class for service servers with automatic handler discovery"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.server = ServiceServer(service_name)
    
    def register_handlers_from_class(self, handler_class: Any) -> "ServiceServerBuilder":
        """Register all handlers from a class"""
        for method_name in dir(handler_class):
            method = getattr(handler_class, method_name)
            
            # Check for handler decorator
            if hasattr(method, '_handler_request_type'):
                request_type = method._handler_request_type
                description = getattr(method, '_handler_description', '')
                self.server.register_handler(request_type, method, description)
            
            # Check for event handler decorator
            if hasattr(method, '_event_handler_type'):
                event_type = method._event_handler_type
                self.server.register_event_handler(event_type, method)
        
        return self
    
    def build(self) -> ServiceServer:
        """Build the configured service server"""
        return self.server