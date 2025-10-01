"""
ZeroMQ-based Service Implementation

Drop-in replacement for Redis-based ServiceBus using ZeroMQ for lightweight
inter-process communication without requiring a Redis server.
"""

import asyncio
import json
import logging
import uuid
import zlib
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import zmq
import zmq.asyncio
import zmq.error

from .config import get_config
from .models import ServiceEvent, ServiceRequest

logger = logging.getLogger(__name__)

# Local pragmatic pylint disables for this module. The implementation is
# intentionally compact (many sockets/handlers) and uses broad exception
# catches in a few places to keep the runtime resilient to transport
# problems; these are safe here and handled/logged.
# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-nested-blocks,duplicate-code,broad-except


class ZeroMQService:
    """
    ZeroMQ-based service class for inter-process communication

    Provides the same API as the Redis-based Service class but uses ZeroMQ
    for lightweight communication without requiring a broker.
    """

    def __init__(
        self,
        service_name: str,
        base_port: Optional[int] = None,
        bind_address: Optional[str] = None,
        rcv_timeout_ms: Optional[int] = None,
        snd_timeout_ms: Optional[int] = None,
        hash_modulus: Optional[int] = None,
    ):
        self.service_name = service_name

        # Load defaults from CommConfig if not supplied
        cfg = get_config()

        self.base_port = (
            int(base_port) if base_port is not None else int(cfg.zeromq_base_port)
        )
        self.bind_address = (
            bind_address if bind_address is not None else cfg.zeromq_bind_address
        )
        self.rcv_timeout_ms = (
            int(rcv_timeout_ms)
            if rcv_timeout_ms is not None
            else int(cfg.zeromq_rcv_timeout_ms)
        )
        self.snd_timeout_ms = (
            int(snd_timeout_ms)
            if snd_timeout_ms is not None
            else int(cfg.zeromq_snd_timeout_ms)
        )
        self.hash_modulus = (
            int(hash_modulus)
            if hash_modulus is not None
            else int(cfg.zeromq_hash_modulus)
        )
        self.context = zmq.asyncio.Context()

        # Sockets
        self.rpc_socket = None  # REP socket for handling incoming RPC calls
        self.pub_socket = None  # PUB socket for publishing events
        self.sub_socket = None  # SUB socket for subscribing to events
        self.req_sockets = {}  # REQ sockets for calling other services

        # Handlers
        self._handlers: Dict[str, Callable] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}

        # State
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._service_ports: Dict[str, int] = {}  # Track other services' ports

        # Service discovery - simple port mapping
        self._assign_ports()

    def _assign_ports(self):
        """Assign ports based on service name hash for deterministic allocation"""
        # Use a stable hash (crc32) so different Python processes compute the same ports
        service_hash = zlib.crc32(self.service_name.encode("utf-8")) % self.hash_modulus
        self.rpc_port = self.base_port + service_hash
        self.pub_port = self.base_port + service_hash + self.hash_modulus
        self.sub_port = self.base_port + service_hash + 2 * self.hash_modulus

        logger.info(
            "Service '%s' hash=%s, base_port=%s: RPC=%s, PUB=%s, SUB=%s",
            self.service_name,
            service_hash,
            self.base_port,
            self.rpc_port,
            self.pub_port,
            self.sub_port,
        )

    async def start(self) -> bool:
        """Start the ZeroMQ service"""
        try:
            # RPC socket (REP) - handles incoming method calls
            self.rpc_socket = self.context.socket(zmq.REP)
            # Apply socket-level timeouts for safety
            try:
                self.rpc_socket.setsockopt(zmq.RCVTIMEO, max(1, self.rcv_timeout_ms))
                self.rpc_socket.setsockopt(zmq.SNDTIMEO, max(1, self.snd_timeout_ms))
            except Exception:
                # Not all transports honor these options; ignore if setting fails
                pass
            self.rpc_socket.bind(f"tcp://{self.bind_address}:{self.rpc_port}")

            # PUB socket - publishes events
            self.pub_socket = self.context.socket(zmq.PUB)
            try:
                self.pub_socket.setsockopt(zmq.SNDTIMEO, max(1, self.snd_timeout_ms))
            except Exception:
                pass
            self.pub_socket.bind(f"tcp://{self.bind_address}:{self.pub_port}")

            # SUB socket - subscribes to events from other services
            self.sub_socket = self.context.socket(zmq.SUB)
            try:
                self.sub_socket.setsockopt(zmq.RCVTIMEO, max(1, self.rcv_timeout_ms))
            except Exception:
                pass
            # Subscribe to all events initially
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

            # Connect to other services' PUB sockets
            self._connect_to_event_sources()
            # Register default handlers (health) if not provided
            if "health" not in self._handlers:
                # register a simple health handler pointing to get_health
                async def _health_handler(**_kwargs):
                    health = await self.get_health()
                    # Convert datetimes to isoformat for JSON compatibility
                    health["last_checked"] = datetime.now().isoformat()
                    return health

                self.register_handler("health", _health_handler)
            self._running = True
            self._tasks.append(asyncio.create_task(self._handle_rpc_calls()))
            self._tasks.append(asyncio.create_task(self._handle_events()))

            # Give sockets time to bind
            await asyncio.sleep(0.1)

            logger.info("ZeroMQ Service '%s' started successfully", self.service_name)
            return True

        except Exception as e:
            logger.error(
                "Failed to start ZeroMQ service '%s': %s", self.service_name, e
            )
            await self.stop()
            return False

    async def stop(self):
        """Stop the ZeroMQ service"""
        self._running = False

        # Cancel tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close sockets
        if self.rpc_socket:
            self.rpc_socket.close()
        if self.pub_socket:
            self.pub_socket.close()
        if self.sub_socket:
            self.sub_socket.close()

        for socket in self.req_sockets.values():
            socket.close()
        self.req_sockets.clear()

        # Terminate context
        self.context.term()

        logger.info("ZeroMQ Service '%s' stopped", self.service_name)

    def register_handler(self, method_name: str, handler: Callable) -> "ZeroMQService":
        """Register a handler for RPC method calls"""
        self._handlers[method_name] = handler
        logger.debug("Registered handler for method '%s'", method_name)
        return self

    def register_event_handler(
        self, event_type: str, handler: Callable
    ) -> "ZeroMQService":
        """Register a handler for events"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

        # Subscribe to this event type on our SUB socket
        if self.sub_socket:
            try:
                self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, event_type)
                logger.debug("Subscribed to event type '%s'", event_type)
            except Exception as e:
                logger.warning(
                    "Could not subscribe to event type '%s': %s", event_type, e
                )

        logger.debug("Registered event handler for '%s'", event_type)
        return self

    def _connect_to_event_sources(self):
        """Connect to other services' PUB sockets to receive events"""
        # Connect to the possible PUB ports within the hash space
        # In production, replace this with service discovery.
        for offset in range(0, self.hash_modulus):
            pub_port = self.base_port + offset + self.hash_modulus
            if pub_port != self.pub_port:  # Don't connect to our own PUB socket
                try:
                    self.sub_socket.connect(f"tcp://127.0.0.1:{pub_port}")
                    logger.debug(
                        "Connected SUB socket to potential PUB port %s",
                        pub_port,
                    )
                except Exception:
                    pass  # Ignore connection errors for non-existent services

    async def publish_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Publish an event to all subscribers"""
        if not self.pub_socket or not self._running:
            logger.warning(
                "Cannot publish event '%s': service not running",
                event_type,
            )
            return False

        try:
            event = ServiceEvent(
                event_type=event_type,
                data=data,
                service_name=self.service_name,
                timestamp=datetime.now(),
            )

            # Ensure timestamp is serializable (use ISO format)
            message = {
                "event_type": event_type,
                "data": data,
                "source_service": self.service_name,
                "timestamp": (
                    event.timestamp.isoformat()
                    if hasattr(event.timestamp, "isoformat")
                    else str(event.timestamp)
                ),
            }

            # Send as multipart message: [topic, data]
            await self.pub_socket.send_multipart(
                [event_type.encode("utf-8"), json.dumps(message).encode("utf-8")]
            )

            logger.debug(
                "Published event '%s' from '%s'", event_type, self.service_name
            )
            return True

        except Exception as e:
            logger.error("Failed to publish event '%s': %s", event_type, e)
            return False

    async def call(
        self, service_name: str, method: str, timeout: Optional[float] = None, **kwargs
    ) -> Any:
        """Call a method on another service"""
        try:
            # Get or create REQ socket for this service
            if service_name not in self.req_sockets:
                service_port = self._get_service_rpc_port(service_name)
                req_socket = self.context.socket(zmq.REQ)
                req_socket.connect(f"tcp://127.0.0.1:{service_port}")
                self.req_sockets[service_name] = req_socket

            req_socket = self.req_sockets[service_name]
            # If the socket was closed for some reason, recreate it
            try:
                closed_attr = getattr(req_socket, "closed", None)
                if closed_attr:
                    raise Exception("REQ socket was closed, recreating")
            except Exception:
                try:
                    req_socket.close()
                except Exception:
                    pass
                service_port = self._get_service_rpc_port(service_name)
                req_socket = self.context.socket(zmq.REQ)
                req_socket.connect(f"tcp://127.0.0.1:{service_port}")
                self.req_sockets[service_name] = req_socket

            # Create request
            request = ServiceRequest(
                request_type=method,
                service_name=service_name,
                data=kwargs,
                source_service=self.service_name,
                request_id=str(uuid.uuid4()),
            )

            request_data = {
                "method": method,
                "params": kwargs,
                "source_service": self.service_name,
                "request_id": request.request_id,
                "timestamp": datetime.now().isoformat(),
            }

            # Send request and wait for response (support optional timeout)
            await req_socket.send_json(request_data)
            try:
                if timeout is not None:
                    response_data = await asyncio.wait_for(
                        req_socket.recv_json(), timeout=timeout
                    )
                else:
                    response_data = await req_socket.recv_json()
            except asyncio.TimeoutError:
                # The REQ/REP state can become unsynchronized on timeouts; recreate socket
                logger.warning(
                    "Timeout waiting for response from %s.%s, recreating REQ socket",
                    service_name,
                    method,
                )
                try:
                    req_socket.close()
                except Exception:
                    pass
                self.req_sockets.pop(service_name, None)
                raise

            if response_data.get("error"):
                raise RuntimeError(f"Remote service error: {response_data['error']}")

            return response_data.get("result")

        except Exception as e:
            logger.error("Failed to call %s.%s: %s", service_name, method, e)
            raise

    def _get_service_rpc_port(self, service_name: str) -> int:
        """Get the RPC port for a service"""
        # Use same stable hash as _assign_ports
        service_hash = zlib.crc32(service_name.encode("utf-8")) % self.hash_modulus
        return self.base_port + service_hash

    async def _handle_rpc_calls(self):
        """Background task to handle incoming RPC calls"""
        logger.info("Starting RPC handler for service '%s'", self.service_name)

        while self._running:
            try:
                if not self.rpc_socket:
                    await asyncio.sleep(0.1)
                    continue

                # Receive request with timeout to avoid blocking indefinitely
                try:
                    request_data = await asyncio.wait_for(
                        self.rpc_socket.recv_json(zmq.NOBLOCK), timeout=0.1
                    )
                except (asyncio.TimeoutError, zmq.Again):
                    # No message available, continue loop
                    await asyncio.sleep(0.01)
                    continue

                method = request_data.get("method")
                params = request_data.get("params", {})
                request_id = request_data.get("request_id")

                logger.debug(
                    "Received RPC call: %s from %s",
                    method,
                    request_data.get("source_service"),
                )

                # Handle the request
                try:
                    if method not in self._handlers:
                        raise ValueError(f"Method '{method}' not found")

                    handler = self._handlers[method]
                    result = handler(**params)

                    # Handle async handlers
                    if asyncio.iscoroutine(result):
                        result = await result

                    # Send successful response
                    response = {
                        "result": result,
                        "error": None,
                        "request_id": request_id,
                        "timestamp": datetime.now().isoformat(),
                    }

                    await self.rpc_socket.send_json(response)

                except Exception as e:
                    logger.exception("Error handling RPC call '%s'", method)

                    # Send error response
                    error_response = {
                        "result": None,
                        "error": str(e),
                        "request_id": request_id,
                        "timestamp": datetime.now().isoformat(),
                    }

                    await self.rpc_socket.send_json(error_response)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in RPC handler")
                await asyncio.sleep(0.1)

        logger.info("RPC handler stopped for service '%s'", self.service_name)

    async def _handle_events(self):
        """Background task to handle incoming events"""
        logger.info("Starting event handler for service '%s'", self.service_name)

        while self._running:
            try:
                if not self.sub_socket:
                    await asyncio.sleep(0.1)
                    continue

                # Receive event with timeout to avoid blocking indefinitely
                try:
                    topic, message_data = await asyncio.wait_for(
                        self.sub_socket.recv_multipart(zmq.NOBLOCK), timeout=0.1
                    )
                except (asyncio.TimeoutError, zmq.Again):
                    # No message available, continue loop
                    await asyncio.sleep(0.01)
                    continue
                event_type = topic.decode("utf-8")
                message = json.loads(message_data.decode("utf-8"))

                # Skip our own events
                if message.get("source_service") == self.service_name:
                    continue

                logger.debug(
                    "Received event '%s' from '%s'",
                    event_type,
                    message.get("source_service"),
                )

                # Handle the event
                if event_type in self._event_handlers:
                    for handler in self._event_handlers[event_type]:
                        try:
                            # Create ServiceEvent object
                            event = ServiceEvent(
                                event_type=event_type,
                                service_name=message.get("source_service"),
                                data=message.get("data", {}),
                                timestamp=datetime.fromisoformat(
                                    message.get("timestamp")
                                ),
                            )

                            result = handler(event)
                            if asyncio.iscoroutine(result):
                                # Don't await - let it run in background
                                asyncio.create_task(result)

                        except Exception:
                            logger.exception("Error handling event '%s'", event_type)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in event handler")
                await asyncio.sleep(0.1)

        logger.info("Event handler stopped for service '%s'", self.service_name)

    # Health and status methods
    async def get_health(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service_name": self.service_name,
            "status": "healthy" if self._running else "stopped",
            "rpc_port": self.rpc_port,
            "pub_port": self.pub_port,
            "handlers": list(self._handlers.keys()),
            "event_handlers": list(self._event_handlers.keys()),
        }

    def is_running(self) -> bool:
        """Check if service is running"""
        return self._running


# Convenience function to create a ZeroMQ service
def create_service(service_name: str, base_port: int = 5555) -> ZeroMQService:
    """Create a new ZeroMQ service instance"""
    return ZeroMQService(service_name, base_port)


# For backward compatibility, alias as Service
Service = ZeroMQService
