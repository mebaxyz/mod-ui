"""
WebSocket Gateway Service

Dedicated microservice for real-time communication across all MOD UI services.
"""

from .main import app
from .models import (
    ClientConnection,
    EventRouterStats,
    EventSubscription,
    GatewayMessage,
    GatewayStats,
    ServiceStatus,
)
from .services import ConnectionManager, EventRouter, RedisEventSubscriber
from .utils import (
    EVENT_GROUPS,
    EventPriority,
    EventType,
    MessageType,
    WebSocketGatewayConfig,
    config,
    get_all_event_types,
    get_events_for_group,
)

__version__ = "1.0.0"

__all__ = [
    # Main app
    "app",
    # Models
    "ClientConnection",
    "EventSubscription",
    "GatewayMessage",
    "GatewayStats",
    "ServiceStatus",
    "EventRouterStats",
    # Services
    "ConnectionManager",
    "EventRouter",
    "RedisEventSubscriber",
    # Utils
    "config",
    "WebSocketGatewayConfig",
    "EventType",
    "EventPriority",
    "MessageType",
    "EVENT_GROUPS",
    "get_events_for_group",
    "get_all_event_types",
]
