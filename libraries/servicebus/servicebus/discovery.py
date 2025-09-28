"""
Service discovery and registry functionality
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import redis.asyncio as redis

from .models import ServiceRegistration, ServiceHealth, ServiceCapability
from .config import get_config


class ServiceDiscovery:
    """Service discovery and registry management"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.config = get_config()
        self._redis = redis_client
        self._connection_pool = None
        self._cached_services: Dict[str, ServiceRegistration] = {}
        self._cache_expiry: Dict[str, float] = {}
        self._is_monitoring = False
        
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

    async def discover_services(self, refresh: bool = False) -> Dict[str, ServiceRegistration]:
        """
        Discover all registered services
        
        Args:
            refresh: Force refresh from Redis (ignore cache)
            
        Returns:
            Dictionary of service_name -> ServiceRegistration
        """
        if not refresh and self._is_cache_valid():
            return self._cached_services.copy()
        
        redis_client = await self.get_redis()
        
        # Get all service registry keys
        pattern = "service_registry:*"
        keys = await redis_client.keys(pattern)
        
        services = {}
        for key in keys:
            try:
                data = await redis_client.get(key)
                if data:
                    registration = ServiceRegistration.parse_raw(data)
                    services[registration.service_name] = registration
            except Exception as e:
                # Service might have expired or invalid data
                continue
        
        # Update cache
        self._cached_services = services
        current_time = time.time()
        self._cache_expiry = {
            service_name: current_time + self.config.discovery_refresh_interval
            for service_name in services.keys()
        }
        
        return services.copy()

    async def find_service(self, service_name: str) -> Optional[ServiceRegistration]:
        """Find a specific service by name"""
        services = await self.discover_services()
        return services.get(service_name)

    async def find_services_by_capability(self, request_type: str) -> List[ServiceRegistration]:
        """Find services that support a specific request type"""
        services = await self.discover_services()
        
        matching_services = []
        for registration in services.values():
            for capability in registration.capabilities:
                if capability.request_type == request_type:
                    matching_services.append(registration)
                    break
        
        return matching_services

    async def get_healthy_services(self) -> Dict[str, ServiceRegistration]:
        """Get only services that are currently healthy"""
        services = await self.discover_services()
        
        healthy_services = {}
        for name, registration in services.items():
            if registration.health.status == "healthy":
                healthy_services[name] = registration
        
        return healthy_services

    async def check_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """Check health of a specific service"""
        registration = await self.find_service(service_name)
        return registration.health if registration else None

    async def wait_for_service(
        self, 
        service_name: str, 
        timeout: float = 30.0,
        check_interval: float = 1.0
    ) -> ServiceRegistration:
        """
        Wait for a service to become available
        
        Args:
            service_name: Name of service to wait for
            timeout: Maximum time to wait
            check_interval: How often to check
            
        Returns:
            ServiceRegistration when service becomes available
            
        Raises:
            TimeoutError: If service doesn't become available within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            registration = await self.find_service(service_name)
            if registration and registration.health.status == "healthy":
                return registration
            
            await asyncio.sleep(check_interval)
        
        raise TimeoutError(f"Service '{service_name}' did not become available within {timeout} seconds")

    async def start_monitoring(self) -> None:
        """Start background monitoring of service health"""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self) -> None:
        """Stop background monitoring"""
        self._is_monitoring = False

    async def _monitoring_loop(self) -> None:
        """Background loop to monitor service health and clean up stale entries"""
        while self._is_monitoring:
            try:
                # Refresh service list
                await self.discover_services(refresh=True)
                
                # Clean up expired services
                await self._cleanup_expired_services()
                
                await asyncio.sleep(self.config.discovery_refresh_interval)
                
            except Exception as e:
                # Log error but continue monitoring
                await asyncio.sleep(5)  # Shorter interval on error

    async def _cleanup_expired_services(self) -> None:
        """Remove expired service registrations"""
        redis_client = await self.get_redis()
        pattern = "service_registry:*"
        keys = await redis_client.keys(pattern)
        
        for key in keys:
            ttl = await redis_client.ttl(key)
            if ttl <= 0:  # Expired
                await redis_client.delete(key)

    def _is_cache_valid(self) -> bool:
        """Check if cached services are still valid"""
        if not self._cached_services:
            return False
        
        current_time = time.time()
        for service_name in self._cached_services.keys():
            expiry = self._cache_expiry.get(service_name, 0)
            if current_time >= expiry:
                return False
        
        return True

    async def get_service_statistics(self) -> Dict[str, any]:
        """Get statistics about registered services"""
        services = await self.discover_services()
        
        total_services = len(services)
        healthy_services = sum(
            1 for reg in services.values() 
            if reg.health.status == "healthy"
        )
        
        capabilities = {}
        for registration in services.values():
            for capability in registration.capabilities:
                request_type = capability.request_type
                if request_type not in capabilities:
                    capabilities[request_type] = []
                capabilities[request_type].append(registration.service_name)
        
        return {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": total_services - healthy_services,
            "capabilities": capabilities,
            "services": {
                name: {
                    "status": reg.health.status,
                    "uptime_seconds": reg.health.uptime_seconds,
                    "request_count": reg.health.request_count,
                    "error_count": reg.health.error_count,
                    "capabilities": [cap.request_type for cap in reg.capabilities]
                }
                for name, reg in services.items()
            }
        }

    async def close(self) -> None:
        """Close connections and clean up"""
        await self.stop_monitoring()
        
        if self._redis:
            await self._redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()


class ServiceLoadBalancer:
    """Simple load balancing for service discovery"""
    
    def __init__(self, discovery: ServiceDiscovery):
        self.discovery = discovery
        self._round_robin_counters: Dict[str, int] = {}
    
    async def get_service_for_request(
        self, 
        request_type: str,
        strategy: str = "round_robin"
    ) -> Optional[str]:
        """
        Get a service name to handle a specific request type
        
        Args:
            request_type: Type of request to handle
            strategy: Load balancing strategy ("round_robin", "random", "healthiest")
            
        Returns:
            Service name or None if no suitable service found
        """
        services = await self.discovery.find_services_by_capability(request_type)
        healthy_services = [
            reg for reg in services 
            if reg.health.status == "healthy"
        ]
        
        if not healthy_services:
            return None
        
        if strategy == "round_robin":
            return self._round_robin_select(request_type, healthy_services)
        elif strategy == "random":
            import random
            return random.choice(healthy_services).service_name
        elif strategy == "healthiest":
            # Select service with lowest error rate
            best_service = min(
                healthy_services,
                key=lambda reg: reg.health.error_count / max(reg.health.request_count, 1)
            )
            return best_service.service_name
        else:
            # Default to first available
            return healthy_services[0].service_name
    
    def _round_robin_select(self, request_type: str, services: List[ServiceRegistration]) -> str:
        """Round-robin selection"""
        if request_type not in self._round_robin_counters:
            self._round_robin_counters[request_type] = 0
        
        index = self._round_robin_counters[request_type] % len(services)
        self._round_robin_counters[request_type] += 1
        
        return services[index].service_name