"""
Performance improvements for the service communication library
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class HighPerformanceServiceClient:
    """Optimized service client with connection pooling and batching"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.connection_pool = None
        self.redis = None
        self.pending_requests = {}
        self.batch_size = 10
        self.batch_timeout = 0.01  # 10ms batching window

    async def connect(self):
        if not self.connection_pool:
            self.connection_pool = redis.ConnectionPool.from_url(
                self.redis_url, max_connections=20
            )
            self.redis = redis.Redis(connection_pool=self.connection_pool)

    async def make_requests_batch(self, requests: List[Dict[str, Any]]) -> List[Any]:
        """Send multiple requests in a single Redis pipeline for better performance"""
        await self.connect()

        pipe = self.redis.pipeline()
        correlation_ids = []

        for req_data in requests:
            correlation_id = str(uuid.uuid4())
            correlation_ids.append(correlation_id)

            request = {"correlation_id": correlation_id, **req_data}

            channel = f"service:{req_data['service_name']}:requests"
            pipe.publish(channel, json.dumps(request))

        # Execute pipeline
        await pipe.execute()

        # Wait for responses
        responses = await asyncio.gather(
            *[self._wait_for_response(cid) for cid in correlation_ids]
        )

        return responses

    async def _wait_for_response(self, correlation_id: str, timeout: float = 5.0):
        """Optimized response waiting with timeout"""
        # Simplified - would implement proper response correlation
        await asyncio.sleep(0.01)  # Mock processing time
        return {"success": True, "correlation_id": correlation_id}


class StreamingServiceResponse:
    """For handling large responses or streaming data"""

    def __init__(self, correlation_id: str, redis_client):
        self.correlation_id = correlation_id
        self.redis = redis_client

    async def stream_chunks(self):
        """Stream response data in chunks"""
        key = f"response:stream:{self.correlation_id}"

        while True:
            chunk = await self.redis.lpop(key)
            if chunk is None:
                # Check if stream is complete
                complete_key = f"response:complete:{self.correlation_id}"
                if await self.redis.get(complete_key):
                    break
                # Wait a bit and try again
                await asyncio.sleep(0.1)
                continue

            yield json.loads(chunk)


class CachedServiceClient:
    """Service client with built-in caching for expensive operations"""

    def __init__(self, redis_url: str = "redis://localhost:6379", cache_ttl: int = 300):
        self.redis_url = redis_url
        self.cache_ttl = cache_ttl
        self.redis = None

    async def connect(self):
        if not self.redis:
            self.redis = redis.from_url(self.redis_url)

    async def make_cached_request(
        self,
        request_type: str,
        data: Dict[str, Any],
        service_name: str,
        cache_key: Optional[str] = None,
        force_refresh: bool = False,
    ):
        """Make request with automatic caching of responses"""
        await self.connect()

        if cache_key is None:
            # Generate cache key from request
            cache_key = f"cache:{service_name}:{request_type}:{hash(json.dumps(data, sort_keys=True))}"

        # Check cache first
        if not force_refresh:
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return json.loads(cached)

        # Make actual request
        response = await self._make_request(request_type, data, service_name)

        # Cache the response
        await self.redis.setex(cache_key, self.cache_ttl, json.dumps(response))

        return response

    async def _make_request(
        self, request_type: str, data: Dict[str, Any], service_name: str
    ):
        # Simplified request implementation
        return {"success": True, "data": data, "cached": False}


# Monitoring and metrics
class ServiceMetrics:
    """Collect metrics about service performance"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None

    async def connect(self):
        if not self.redis:
            self.redis = redis.from_url(self.redis_url)

    async def record_request(
        self, service_name: str, request_type: str, duration_ms: float, success: bool
    ):
        """Record request metrics"""
        await self.connect()

        timestamp = int(time.time())
        key_prefix = f"metrics:{service_name}:{request_type}"

        # Increment counters
        await self.redis.incr(f"{key_prefix}:count")
        if success:
            await self.redis.incr(f"{key_prefix}:success")
        else:
            await self.redis.incr(f"{key_prefix}:errors")

        # Track response times (simplified - would use proper time series)
        await self.redis.lpush(f"{key_prefix}:times", duration_ms)
        await self.redis.ltrim(f"{key_prefix}:times", 0, 99)  # Keep last 100

    async def get_service_stats(self, service_name: str) -> Dict[str, Any]:
        """Get performance statistics for a service"""
        await self.connect()

        keys = await self.redis.keys(f"metrics:{service_name}:*")
        stats = {}

        for key in keys:
            key_str = key.decode()
            if key_str.endswith(":count"):
                count = await self.redis.get(key)
                request_type = key_str.split(":")[2]
                stats[request_type] = {"count": int(count) if count else 0}

        return stats
