"""
Data Models for WebSocket Gateway Service

Pydantic models for client connections, subscriptions, and service statistics.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class ConnectionStatus(str, Enum):
    """WebSocket connection status"""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


class ClientConnection(BaseModel):
    """Model for WebSocket client connection"""

    client_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    connected_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    status: ConnectionStatus = ConnectionStatus.CONNECTING
    subscriptions: Set[str] = Field(default_factory=set)
    messages_sent: int = 0
    messages_received: int = 0

    class Config:
        use_enum_values = True

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.now()

    def add_subscription(self, event_type: str) -> None:
        """Add event type subscription"""
        self.subscriptions.add(event_type)

    def remove_subscription(self, event_type: str) -> None:
        """Remove event type subscription"""
        self.subscriptions.discard(event_type)

    def is_subscribed_to(self, event_type: str) -> bool:
        """Check if subscribed to event type"""
        return event_type in self.subscriptions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "client_id": self.client_id,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "status": self.status,
            "subscriptions": list(self.subscriptions),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
        }


class EventSubscription(BaseModel):
    """Model for event subscriptions"""

    client_id: str
    event_types: List[str]
    created_at: datetime = Field(default_factory=datetime.now)
    filter_data: Optional[Dict[str, Any]] = None


class GatewayMessage(BaseModel):
    """Model for gateway messages"""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str
    source_service: Optional[str] = None
    target_clients: Optional[List[str]] = None
    event_type: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    priority: str = "normal"

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class GatewayStats(BaseModel):
    """Model for gateway service statistics"""

    total_connections: int = 0
    active_connections: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    events_processed: int = 0
    active_subscriptions: int = 0
    uptime_seconds: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)

    def update_timestamp(self) -> None:
        """Update the last updated timestamp"""
        self.last_updated = datetime.now()


class ServiceStatus(BaseModel):
    """Model for individual service status"""

    service_name: str
    service_url: str
    is_healthy: bool = False
    last_health_check: datetime = Field(default_factory=datetime.now)
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


class EventRouterStats(BaseModel):
    """Model for event router statistics"""

    events_processed: int = 0
    events_broadcasted: int = 0
    subscription_changes: int = 0
    active_subscriptions: int = 0
    last_event_time: Optional[datetime] = None

    def record_event(self) -> None:
        """Record an event being processed"""
        self.events_processed += 1
        self.last_event_time = datetime.now()

    def record_broadcast(self) -> None:
        """Record a broadcast being sent"""
        self.events_broadcasted += 1
