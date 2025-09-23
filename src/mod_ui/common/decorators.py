"""
Simplified Service Decorators and Utilities

High-level decorators and utilities to make service creation even easier.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Dict, Optional

from .models import RequestType, ServiceRequest
from .server import ServiceServer

logger = logging.getLogger(__name__)


class SimpleService:
    """
    Simplified service wrapper that makes it easy to create services with decorators.

    Usage:
        service = SimpleService("my-service")

        @service.handler("get_data")
        async def get_data(request):
            return {"data": "value"}

        await service.run()
    """

    def __init__(self, service_name: str, redis_url: str = "redis://localhost:6379"):
        self.service_name = service_name
        self.server = ServiceServer(service_name, redis_url)
        self._handlers = {}

    def handler(self, request_type: str):
        """
        Decorator to register a handler for a request type.

        @service.handler("get_system_info")
        async def handle_system_info(request):
            return {"system": "info"}
        """

        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(request: ServiceRequest) -> Dict[str, Any]:
                try:
                    # Call the handler function
                    if asyncio.iscoroutinefunction(func):
                        result = await func(request)
                    else:
                        result = func(request)

                    # Ensure we return a dict
                    if not isinstance(result, dict):
                        result = {"result": result}

                    return result
                except Exception as e:
                    logger.error(f"Handler {func.__name__} failed: {e}")
                    raise

            # Register with the server
            self.server.register_handler(request_type, wrapper)
            self._handlers[request_type] = func
            logger.info(f"Registered handler for '{request_type}': {func.__name__}")

            return func

        return decorator

    def enum_handler(self, request_type: RequestType):
        """
        Decorator for enum-based request types.

        @service.enum_handler(RequestType.GET_SYSTEM_INFO)
        async def handle_system_info(request):
            return {"system": "info"}
        """
        return self.handler(request_type.value)

    async def run(self):
        """Run the service (blocking)"""
        logger.info(
            f"Starting service '{self.service_name}' with {len(self._handlers)} handlers"
        )

        async with self.server:
            try:
                # Keep running until interrupted
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info(f"Service '{self.service_name}' stopped by user")
            except Exception as e:
                logger.error(f"Service '{self.service_name}' error: {e}")
                raise

    async def start(self):
        """Start the service (non-blocking)"""
        await self.server.start()

    async def stop(self):
        """Stop the service"""
        await self.server.stop()

    def list_handlers(self) -> Dict[str, str]:
        """List all registered handlers"""
        return {req_type: func.__name__ for req_type, func in self._handlers.items()}


def service_handler(request_type: str):
    """
    Standalone decorator for creating service handlers.
    Can be used without creating a SimpleService instance first.

    @service_handler("get_data")
    async def my_handler(request):
        return {"data": "value"}

    # Later:
    service = SimpleService("my-service")
    service.add_handler("get_data", my_handler)
    """

    def decorator(func: Callable):
        # Add metadata to the function
        func._service_handler = True
        func._request_type = request_type
        return func

    return decorator


def auto_register_handlers(service: SimpleService, module_or_dict) -> int:
    """
    Automatically register all functions decorated with @service_handler.

    Args:
        service: SimpleService instance
        module_or_dict: Module or dict containing handler functions

    Returns:
        Number of handlers registered
    """
    count = 0

    # Get functions from module or dict
    if hasattr(module_or_dict, "__dict__"):
        functions = module_or_dict.__dict__.values()
    else:
        functions = module_or_dict.values()

    for obj in functions:
        if callable(obj) and hasattr(obj, "_service_handler"):
            request_type = obj._request_type
            service.server.register_handler(request_type, obj)
            logger.info(f"Auto-registered handler for '{request_type}': {obj.__name__}")
            count += 1

    return count


class ServiceRegistry:
    """
    Registry for managing multiple services in one application.
    """

    def __init__(self):
        self.services: Dict[str, SimpleService] = {}

    def register(self, service: SimpleService):
        """Register a service"""
        self.services[service.service_name] = service
        logger.info(f"Registered service: {service.service_name}")

    def create_service(
        self, name: str, redis_url: str = "redis://localhost:6379"
    ) -> SimpleService:
        """Create and register a new service"""
        service = SimpleService(name, redis_url)
        self.register(service)
        return service

    async def start_all(self):
        """Start all registered services"""
        for service in self.services.values():
            await service.start()
        logger.info(f"Started {len(self.services)} services")

    async def stop_all(self):
        """Stop all registered services"""
        for service in self.services.values():
            await service.stop()
        logger.info(f"Stopped {len(self.services)} services")

    def list_services(self) -> Dict[str, Dict[str, str]]:
        """List all services and their handlers"""
        return {
            name: service.list_handlers() for name, service in self.services.items()
        }


# Global service registry for convenience
registry = ServiceRegistry()
