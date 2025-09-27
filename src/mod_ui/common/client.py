"""
Service Communication Client

Async client for making requests to backend services via Redis pub/sub.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

import redis.asyncio as redis

from .models import ResponseStatus, ServiceRequest, ServiceResponse

logger = logging.getLogger(__name__)


class ServiceClient:
    """
    Client for making requests to backend services via Redis.

    This client implements a request-response pattern using Redis pub/sub
    where requests are published to service-specific channels and responses
    are received via correlation IDs.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_timeout: float = 5.0,
        max_retries: int = 1,
    ):
        """
        Initialize the service client.

        Args:
            redis_url: Redis connection URL
            default_timeout: Default timeout for requests in seconds
            max_retries: Maximum number of retry attempts
        """
        self.redis_url = redis_url
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.redis: Optional[redis.Redis] = None
        self.response_channels: Dict[str, asyncio.Queue] = {}

    async def connect(self) -> None:
        """Connect to Redis"""
        if self.redis is None:
            self.redis = redis.from_url(self.redis_url)
            logger.info("Service client connected to Redis")

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.info("Service client disconnected from Redis")

    async def make_request(
        self,
        request_type: str,
        data: Dict[str, Any],
        service_name: str,
        timeout: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> ServiceResponse:
        """
        Make a request to a backend service.

        Args:
            request_type: Type of request (e.g., 'get_system_info')
            data: Request data payload
            service_name: Name of the target service
            timeout: Request timeout in seconds (uses default if None)
            correlation_id: Optional correlation ID for tracking

        Returns:
            ServiceResponse: The service response

        Raises:
            Exception: If request fails or times out
        """
        if not self.redis:
            await self.connect()

        request_timeout = timeout or self.default_timeout

        # Create request
        request_data = {
            "request_type": request_type,
            "data": data,
            "source_service": "unknown",  # Will be set by calling service
        }
        if correlation_id is not None:
            request_data["correlation_id"] = correlation_id

        request = ServiceRequest(**request_data)

        # Create response queue for this correlation ID
        response_queue = asyncio.Queue()
        self.response_channels[request.correlation_id] = response_queue

        try:
            # Publish request to service channel
            channel = f"service:{service_name}:requests"
            await self.redis.publish(channel, request.json())

            logger.debug(f"Published request {request.request_id} to {channel}")

            # Wait for response
            return await self._wait_for_response(
                request.correlation_id, request_timeout
            )

        finally:
            # Clean up response channel
            if request.correlation_id in self.response_channels:
                del self.response_channels[request.correlation_id]

    async def _wait_for_response(
        self, correlation_id: str, timeout: float
    ) -> ServiceResponse:
        """
        Wait for a response with the given correlation ID.

        Args:
            correlation_id: Correlation ID to wait for
            timeout: Timeout in seconds

        Returns:
            ServiceResponse: The response

        Raises:
            asyncio.TimeoutError: If timeout is exceeded
        """
        try:
            # Start listening for responses
            pubsub = self.redis.pubsub()
            response_channel = f"responses:{correlation_id}"

            await pubsub.subscribe(response_channel)

            # Wait for response with timeout
            start_time = time.time()

            while time.time() - start_time < timeout:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=min(0.1, timeout - (time.time() - start_time)),
                )

                if message:
                    try:
                        response_data = json.loads(message["data"])
                        response = ServiceResponse(**response_data)

                        await pubsub.unsubscribe(response_channel)

                        # Calculate processing time
                        if response.processing_time_ms is None:
                            response.processing_time_ms = (
                                time.time() - start_time
                            ) * 1000

                        logger.debug(
                            f"Received response for correlation ID {correlation_id}"
                        )
                        return response

                    except Exception as e:
                        logger.error(f"Failed to parse response: {e}")
                        continue

            # Timeout
            await pubsub.unsubscribe(response_channel)
            raise asyncio.TimeoutError(
                f"Timeout waiting for response to correlation ID {correlation_id}"
            )

        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
            raise

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
