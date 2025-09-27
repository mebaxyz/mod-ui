"""
Service Discovery and Registry for MOD UI Microservices
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

import redis.asyncio as redis

from .flexible_models_proposal import ServiceCapability, ServiceRegistration

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Central service registry using Redis"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self._services: Dict[str, ServiceRegistration] = {}

    async def connect(self):
        """Connect to Redis"""
        if not self.redis:
            self.redis = redis.from_url(self.redis_url)

    async def register_service(self, registration: ServiceRegistration, ttl: int = 30):
        """Register a service with TTL for health checking"""
        await self.connect()

        key = f"service:registry:{registration.service_name}"
        await self.redis.setex(key, ttl, registration.json())

        # Also register individual capabilities for easy lookup
        for cap in registration.capabilities:
            cap_key = f"service:capability:{cap.request_type}"
            await self.redis.sadd(cap_key, registration.service_name)
            await self.redis.expire(cap_key, ttl)

        logger.info(
            f"Registered service {registration.service_name} with {len(registration.capabilities)} capabilities"
        )

    async def discover_services(self) -> Dict[str, ServiceRegistration]:
        """Get all registered services"""
        await self.connect()

        keys = await self.redis.keys("service:registry:*")
        services = {}

        for key in keys:
            data = await self.redis.get(key)
            if data:
                try:
                    reg = ServiceRegistration.parse_raw(data)
                    services[reg.service_name] = reg
                except Exception as e:
                    logger.warning(f"Failed to parse service registration: {e}")

        return services

    async def find_service_for_request(self, request_type: str) -> List[str]:
        """Find services that can handle a specific request type"""
        await self.connect()

        cap_key = f"service:capability:{request_type}"
        services = await self.redis.smembers(cap_key)
        return [s.decode() for s in services] if services else []

    async def get_service_info(
        self, service_name: str
    ) -> Optional[ServiceRegistration]:
        """Get detailed info about a specific service"""
        await self.connect()

        key = f"service:registry:{service_name}"
        data = await self.redis.get(key)

        if data:
            try:
                return ServiceRegistration.parse_raw(data)
            except Exception as e:
                logger.warning(
                    f"Failed to parse service registration for {service_name}: {e}"
                )

        return None


class AutoDiscoveryServiceClient:
    """Service client with automatic service discovery"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.registry = ServiceRegistry(redis_url)
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        if not self.redis:
            self.redis = redis.from_url(self.redis_url)

    async def make_request(
        self,
        request_type: str,
        data: Dict[str, Any],
        timeout: float = 5.0,
        prefer_service: Optional[str] = None,
    ):
        """Make a request with automatic service discovery"""

        # Find services that can handle this request
        available_services = await self.registry.find_service_for_request(request_type)

        if not available_services:
            raise Exception(f"No services available for request type: {request_type}")

        # Prefer specific service if requested
        target_service = (
            prefer_service
            if prefer_service in available_services
            else available_services[0]
        )

        # Create flexible request
        request = FlexibleServiceRequest(
            request_type=request_type,
            service_name=target_service,
            data=data,
            timeout=timeout,
        )

        # Send via Redis pub/sub
        await self.connect()
        channel = f"service:{target_service}:requests"
        await self.redis.publish(channel, request.json())

        # Wait for response (simplified - would need proper correlation handling)
        # ... implementation details ...
