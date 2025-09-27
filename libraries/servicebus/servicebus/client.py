"""
Enhanced service client for microservice communication
"""
import asyncio
import json
import uuid
import time
from typing import Any, Dict, Optional, Type, TypeVar, Generic, List, Callable
from contextlib import asynccontextmanager
import redis.asyncio as redis

from .models import (
    ServiceRequest, ServiceResponse, RequestMetrics,
    ServiceHealth, ServiceCapability, ServiceEvent
)
from .config import get_config


T = TypeVar('T')


class ServiceClient:
    """Enhanced client for communicating with microservices"""
    
    def __init__(
        self, 
        service_name: str,
        redis_client: Optional[redis.Redis] = None
    ):
        self.service_name = service_name
        self.config = get_config()
        self._redis = redis_client
        self._connection_pool = None
        self._metrics: Dict[str, RequestMetrics] = {}
        self._cached_responses: Dict[str, tuple] = {}  # (response, expiry_time)
        self._pending_requests: Dict[str, asyncio.Event] = {}
        self._request_queue: List[ServiceRequest] = []
        self._batch_lock = asyncio.Lock()
        
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
        """
        Make a service call with enhanced features
        
        Args:
            target_service: Name of the target service
            request_type: Type of request (e.g., "get_plugins", "create_user")
            data: Request data
            timeout: Request timeout (uses config default if None)
            return_type: Expected return type for validation
            enable_caching: Enable response caching (uses config default if None)
            max_retries: Maximum retry attempts (uses config default if None)
            
        Returns:
            Parsed response data
        """
        timeout = timeout or self.config.default_timeout
        enable_caching = enable_caching if enable_caching is not None else self.config.enable_caching
        max_retries = max_retries if max_retries is not None else self.config.max_retries
        
        # Check cache first
        if enable_caching:
            cache_key = self._get_cache_key(target_service, request_type, data)
            if cached := self._get_cached_response(cache_key):
                return cached if return_type is None else return_type.parse_obj(cached)
        
        # Create request
        request = ServiceRequest(
            id=str(uuid.uuid4()),
            source_service=self.service_name,
            target_service=target_service,
            request_type=request_type,
            data=data or {}
        )
        
        # Track metrics
        start_time = time.time()
        
        # Retry logic
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                response = await self._make_request(request, timeout)
                
                # Record success metrics
                elapsed = time.time() - start_time
                self._record_metrics(request, response, elapsed, attempt)
                
                # Cache successful responses
                if enable_caching and response.success:
                    cache_key = self._get_cache_key(target_service, request_type, data)
                    self._cache_response(cache_key, response.data)
                
                if not response.success:
                    raise RuntimeError(f"Service call failed: {response.error}")
                
                return response.data if return_type is None else return_type.parse_obj(response.data)
                
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                break
        
        # Record failure metrics
        elapsed = time.time() - start_time
        self._record_metrics(request, None, elapsed, max_retries, error=str(last_exception))
        raise last_exception

    async def _make_request(self, request: ServiceRequest, timeout: float) -> ServiceResponse:
        """Make the actual Redis request"""
        redis_client = await self.redis
        
        # Send request
        request_channel = f"service:{request.target_service}:requests"
        response_channel = f"service:{self.service_name}:responses:{request.id}"
        
        await redis_client.publish(request_channel, request.json())
        
        # Listen for response
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(response_channel)
        
        try:
            async with asyncio.timeout(timeout):
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        response_data = json.loads(message['data'])
                        return ServiceResponse.parse_obj(response_data)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request timed out after {timeout} seconds")
        finally:
            await pubsub.unsubscribe(response_channel)
            await pubsub.close()

    def _get_cache_key(self, target_service: str, request_type: str, data: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for request"""
        data_str = json.dumps(data or {}, sort_keys=True)
        return f"{target_service}:{request_type}:{hash(data_str)}"

    def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get cached response if not expired"""
        if cache_key in self._cached_responses:
            response, expiry_time = self._cached_responses[cache_key]
            if time.time() < expiry_time:
                return response
            else:
                del self._cached_responses[cache_key]
        return None

    def _cache_response(self, cache_key: str, response: Any) -> None:
        """Cache response with TTL"""
        expiry_time = time.time() + self.config.cache_ttl
        self._cached_responses[cache_key] = (response, expiry_time)

    def _record_metrics(
        self, 
        request: ServiceRequest, 
        response: Optional[ServiceResponse], 
        elapsed_seconds: float,
        attempts: int,
        error: Optional[str] = None
    ) -> None:
        """Record request metrics"""
        if not self.config.enable_metrics:
            return
            
        metrics = RequestMetrics(
            request_id=request.id,
            source_service=request.source_service,
            target_service=request.target_service,
            request_type=request.request_type,
            timestamp=request.timestamp,
            response_time_seconds=elapsed_seconds,
            success=response.success if response else False,
            attempts=attempts + 1,
            error_message=error
        )
        
        self._metrics[request.id] = metrics
        
        # Clean old metrics
        current_time = time.time()
        retention_cutoff = current_time - self.config.metrics_retention_seconds
        self._metrics = {
            req_id: metric for req_id, metric in self._metrics.items()
            if metric.timestamp.timestamp() > retention_cutoff
        }

    async def get_service_health(self, target_service: str) -> ServiceHealth:
        """Get health status of a service"""
        response = await self.call(
            target_service=target_service,
            request_type="health_check",
            return_type=dict
        )
        return ServiceHealth.parse_obj(response)

    async def get_service_capabilities(self, target_service: str) -> List[ServiceCapability]:
        """Get capabilities of a service"""
        response = await self.call(
            target_service=target_service,
            request_type="get_capabilities",
            return_type=dict
        )
        return [ServiceCapability.parse_obj(cap) for cap in response.get("capabilities", [])]

    async def publish_event(self, event: ServiceEvent) -> None:
        """Publish an event to the event bus"""
        redis_client = await self.redis
        event_channel = f"events:{event.event_type}"
        await redis_client.publish(event_channel, event.json())

    async def batch_call(
        self,
        requests: List[tuple],  # (target_service, request_type, data)
        timeout: Optional[float] = None
    ) -> List[Any]:
        """Make multiple service calls concurrently"""
        tasks = []
        for target_service, request_type, data in requests:
            task = asyncio.create_task(
                self.call(target_service, request_type, data, timeout)
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_metrics(self, last_n: Optional[int] = None) -> List[RequestMetrics]:
        """Get request metrics"""
        metrics = list(self._metrics.values())
        metrics.sort(key=lambda m: m.timestamp, reverse=True)
        
        if last_n:
            metrics = metrics[:last_n]
        
        return metrics

    async def close(self) -> None:
        """Close connections and clean up resources"""
        if self._redis:
            await self._redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()


class TypedServiceClient(ServiceClient, Generic[T]):
    """Type-safe service client for specific service types"""
    
    def __init__(
        self,
        service_name: str,
        target_service: str,
        response_type: Type[T],
        redis_client: Optional[redis.Redis] = None
    ):
        super().__init__(service_name, redis_client)
        self.target_service = target_service
        self.response_type = response_type

    async def call_typed(
        self,
        request_type: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> T:
        """Make a typed service call"""
        return await self.call(
            target_service=self.target_service,
            request_type=request_type,
            data=data,
            timeout=timeout,
            return_type=self.response_type
        )


@asynccontextmanager
async def service_client(service_name: str):
    """Context manager for service client"""
    client = ServiceClient(service_name)
    try:
        yield client
    finally:
        await client.close()