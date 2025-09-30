"""
ServiceBus - Service Communication Library

A flexible, high-performance service communication library built on Redis pub/sub
with automatic service discovery, event broadcasting, and performance optimizations.

Originally forked from MOD-UI project, enhanced and modified by Nicolas.
"""

import os

# Import both implementations
from .client import ServiceClient, TypedServiceClient, service_client
from .config import CommConfig, get_config, get_redis_url_from_env, set_config
from .discovery import ServiceDiscovery, ServiceLoadBalancer
from .events import EventBus, EventPublisher, EventSubscriber
from .gateway import GatewayService, create_gateway_service, gateway_service
from .metrics import HealthMonitor, MetricsCollector
from .models import (
    RequestMetrics,
    ServiceCapability,
    ServiceEvent,
    ServiceHealth,
    ServiceRegistration,
    ServiceRequest,
    ServiceResponse,
)
from .resilient import ResilientServiceBus, create_resilient_service
from .server import ServiceServer, ServiceServerBuilder, event_handler, handler
from .service import Service as RedisService
from .service import create_service as create_redis_service
from .service import temporary_service
from .zeromq_service import ZeroMQService
from .zeromq_service import create_service as create_zeromq_service

# Default to ZeroMQ implementation (no Redis dependency)
SERVICEBUS_IMPL = os.getenv("SERVICEBUS_IMPL", "zeromq").lower()

if SERVICEBUS_IMPL == "redis":
    # Use Redis implementation
    Service = RedisService
    create_service = create_redis_service
else:
    # Use ZeroMQ implementation (default)
    Service = ZeroMQService
    create_service = create_zeromq_service

__version__ = "0.1.0"
__all__ = [
    # Unified service class (recommended - defaults to ZeroMQ)
    "Service",
    "create_service",
    "temporary_service",
    # ZeroMQ implementation (lightweight, no broker required)
    "ZeroMQService",
    "create_zeromq_service",
    # Redis implementations (requires Redis server)
    "RedisService",
    "create_redis_service",
    # Resilient service class (auto-reconnecting, for Redis)
    "ResilientServiceBus",
    "create_resilient_service",
    # Gateway service class (for HTTP/WebSocket gateways)
    "GatewayService",
    "gateway_service",
    "create_gateway_service",
    # Core components (for advanced usage)
    "ServiceClient",
    "ServiceServer",
    "TypedServiceClient",
    "ServiceServerBuilder",
    "service_client",
    # Service discovery
    "ServiceDiscovery",
    "ServiceLoadBalancer",
    # Events
    "EventBus",
    "EventPublisher",
    "EventSubscriber",
    # Monitoring
    "MetricsCollector",
    "HealthMonitor",
    # Configuration
    "CommConfig",
    "get_config",
    "set_config",
    "get_redis_url_from_env",
    # Models
    "ServiceRequest",
    "ServiceResponse",
    "ServiceEvent",
    "ServiceHealth",
    "ServiceCapability",
    "ServiceRegistration",
    "RequestMetrics",
    # Decorators
    "handler",
    "event_handler",
]
