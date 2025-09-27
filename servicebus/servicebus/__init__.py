"""
ServiceBus - Service Communication Library

A flexible, high-performance service communication library built on Redis pub/sub
with automatic service discovery, event broadcasting, and performance optimizations.
"""

from .client import ServiceClient, TypedServiceClient, service_client
from .server import ServiceServer, ServiceServerBuilder, handler, event_handler
from .service import Service, create_service, temporary_service
from .discovery import ServiceDiscovery, ServiceLoadBalancer
from .events import EventBus, EventPublisher, EventSubscriber
from .metrics import MetricsCollector, HealthMonitor
from .config import CommConfig, get_config, set_config, get_redis_url_from_env
from .models import (
    ServiceRequest,
    ServiceResponse,
    ServiceEvent,
    ServiceHealth,
    ServiceCapability,
    ServiceRegistration,
    RequestMetrics,
)

__version__ = "0.1.0"
__all__ = [
    # Unified service class (recommended)
    "Service",
    "create_service",
    "temporary_service",
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
