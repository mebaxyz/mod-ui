"""
Service Server

Async server component for handling incoming service requests via Redis pub/sub.
This is the counterpart to ServiceClient - services use this to listen for requests
and send responses back.
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, Optional

import redis.asyncio as redis

from .models import ResponseStatus, ServiceRequest, ServiceResponse

logger = logging.getLogger(__name__)


class ServiceServer:
    """
    Server for handling incoming service requests via Redis.

    This server listens for requests on service-specific channels and
    allows services to register handlers for different request types.
    """

    def __init__(
        self,
        service_name: str,
        redis_url: str = "redis://localhost:6379",
    ):
        """
        Initialize the service server.

        Args:
            service_name: Name of this service (used for channel naming)
            redis_url: Redis connection URL
        """
        self.service_name = service_name
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.handlers: Dict[str, Callable] = {}
        self.running = False
        self._listen_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Connect to Redis and set up subscription"""
        if self.redis is None:
            self.redis = redis.from_url(self.redis_url)
            self.pubsub = self.redis.pubsub()

            # Subscribe to our service's request channel
            request_channel = f"service:{self.service_name}:requests"
            await self.pubsub.subscribe(request_channel)

            logger.info(f"Service server '{self.service_name}' connected to Redis")
            logger.info(f"Listening on channel: {request_channel}")

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.running:
            await self.stop()

        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.aclose()
            self.pubsub = None

        if self.redis:
            await self.redis.aclose()
            self.redis = None

        logger.info(f"Service server '{self.service_name}' disconnected from Redis")

    def register_handler(self, request_type: str, handler: Callable) -> None:
        """
        Register a handler for a specific request type.

        Args:
            request_type: Type of request to handle (e.g., 'get_system_info')
            handler: Async function to handle the request
                    Should accept (request: ServiceRequest) -> Dict[str, Any]
        """
        self.handlers[request_type] = handler
        logger.info(f"Registered handler for request type: {request_type}")

    async def start(self) -> None:
        """Start listening for requests"""
        if not self.redis:
            await self.connect()

        self.running = True
        self._listen_task = asyncio.create_task(self._listen_for_requests())
        logger.info(f"Service server '{self.service_name}' started")

    async def stop(self) -> None:
        """Stop listening for requests"""
        self.running = False

        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        logger.info(f"Service server '{self.service_name}' stopped")

    async def _listen_for_requests(self) -> None:
        """Main loop for listening to incoming requests"""
        try:
            # Use async iteration instead of polling
            async for message in self.pubsub.listen():
                if not self.running:
                    break

                if message["type"] == "message":
                    try:
                        await self._handle_message(message["data"])
                    except Exception as e:
                        logger.error(f"Error in request handler: {e}")
                        await asyncio.sleep(0.1)  # Brief pause before continuing

        except asyncio.CancelledError:
            logger.info(f"Request listener for '{self.service_name}' cancelled")
            raise
        except Exception as e:
            logger.error(f"Fatal error in request listener: {e}")
            raise

    async def _handle_message(self, message_data: bytes) -> None:
        """Handle an incoming request message"""
        start_time = time.time()

        try:
            # Parse the request
            request_dict = json.loads(message_data)
            request = ServiceRequest(**request_dict)

            logger.debug(
                f"Received request {request.request_id} of type {request.request_type}"
            )

            # Check if we have a handler for this request type
            handler = self.handlers.get(request.request_type)
            if not handler:
                await self._send_error_response(
                    request,
                    f"No handler registered for request type: {request.request_type}",
                )
                return

            # Execute the handler
            try:
                response_data = await handler(request)
                await self._send_success_response(request, response_data, start_time)

            except Exception as e:
                logger.error(f"Handler error for request {request.request_id}: {e}")
                await self._send_error_response(request, str(e))

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse request JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to handle message: {e}")

    async def _send_success_response(
        self, request: ServiceRequest, data: Dict[str, Any], start_time: float
    ) -> None:
        """Send a success response"""
        processing_time_ms = (time.time() - start_time) * 1000

        response = ServiceResponse(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=ResponseStatus.SUCCESS,
            data=data,
            processing_time_ms=processing_time_ms,
        )

        await self._send_response(response)
        logger.debug(f"Sent success response for request {request.request_id}")

    async def _send_error_response(
        self, request: ServiceRequest, error_message: str
    ) -> None:
        """Send an error response"""
        response = ServiceResponse(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            status=ResponseStatus.ERROR,
            error_message=error_message,
        )

        await self._send_response(response)
        logger.debug(
            f"Sent error response for request {request.request_id}: {error_message}"
        )

    async def _send_response(self, response: ServiceResponse) -> None:
        """Send a response to the response channel"""
        response_channel = f"responses:{response.correlation_id}"
        response_json = response.json()

        await self.redis.publish(response_channel, response_json)

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
