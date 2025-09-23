"""
Common Service Communication Package

Reusable models and utilities for inter-service communication across MOD UI services.
This package provides a standardized way for services to communicate with each other
using Redis-based request-response patterns.
"""

from .client import ServiceClient
from .config import Environment, ServiceClientConfig, ServiceServerConfig
from .decorators import (
    ServiceRegistry,
    SimpleService,
    auto_register_handlers,
    registry,
    service_handler,
)
from .metrics import MetricsCollector, metrics, track_request
from .models import (
    RequestType,
    ResponseStatus,
    ServiceConfig,
    ServiceRequest,
    ServiceResponse,
)
from .server import ServiceServer

__version__ = "1.0.0"

__all__ = [
    # Models
    "RequestType",
    "ResponseStatus",
    "ServiceRequest",
    "ServiceResponse",
    "ServiceConfig",
    # Client
    "ServiceClient",
    # Server
    "ServiceServer",
    # Simplified API
    "SimpleService",
    "ServiceRegistry",
    "service_handler",
    "auto_register_handlers",
    "registry",
    # Configuration
    "ServiceClientConfig",
    "ServiceServerConfig",
    "Environment",
    # Metrics
    "metrics",
    "track_request",
    "MetricsCollector",
]
