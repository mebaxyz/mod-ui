"""
Event System Models for Session Service

Defines the event-driven communication system between services.
Events are used for loose coupling and real-time updates.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event types for the session system"""

    # Pedalboard events
    PEDALBOARD_LOADED = "pedalboard_loaded"
    PEDALBOARD_SAVED = "pedalboard_saved"
    PEDALBOARD_CHANGED = "pedalboard_changed"
    PEDALBOARD_CLEARED = "pedalboard_cleared"

    # Plugin events
    PLUGIN_ADDED = "plugin_added"
    PLUGIN_REMOVED = "plugin_removed"
    PLUGIN_MOVED = "plugin_moved"
    PLUGIN_ENABLED = "plugin_enabled"
    PLUGIN_DISABLED = "plugin_disabled"
    PLUGIN_PRESET_CHANGED = "plugin_preset_changed"

    # Parameter events
    PARAMETER_CHANGED = "parameter_changed"
    PARAMETER_ADDRESSED = "parameter_addressed"
    PARAMETER_UNADDRESSED = "parameter_unaddressed"

    # Connection events
    CONNECTION_ADDED = "connection_added"
    CONNECTION_REMOVED = "connection_removed"

    # Client events
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"
    CLIENT_SUBSCRIBED = "client_subscribed"
    CLIENT_UNSUBSCRIBED = "client_unsubscribed"

    # Hardware events
    HARDWARE_CONNECTED = "hardware_connected"
    HARDWARE_DISCONNECTED = "hardware_disconnected"
    HARDWARE_STATUS_UPDATED = "hardware_status_updated"
    HARDWARE_ERROR = "hardware_error"

    # Control Chain events
    CONTROL_CHAIN_DEVICE_ADDED = "control_chain_device_added"
    CONTROL_CHAIN_DEVICE_REMOVED = "control_chain_device_removed"
    CONTROL_CHAIN_DEVICE_CONNECTED = "control_chain_device_connected"
    CONTROL_CHAIN_DEVICE_DISCONNECTED = "control_chain_device_disconnected"
    CONTROL_CHAIN_ACTUATOR_ADDED = "control_chain_actuator_added"

    # HMI events
    HMI_MESSAGE_RECEIVED = "hmi_message_received"
    HMI_CONTROL_ADDED = "hmi_control_added"
    HMI_CONTROL_CHANGED = "hmi_control_changed"
    HMI_CONTROL_REMOVED = "hmi_control_removed"

    # Audio connection events
    AUDIO_CONNECTION_ADDED = "audio_connection_added"
    AUDIO_CONNECTION_REMOVED = "audio_connection_removed"

    # Audio engine events
    AUDIO_ENGINE_STARTED = "audio_engine_started"
    AUDIO_ENGINE_STOPPED = "audio_engine_stopped"
    AUDIO_ENGINE_XRUN = "audio_engine_xrun"

    # Session events
    SESSION_STARTED = "session_started"
    SESSION_STOPPED = "session_stopped"
    SESSION_RESET = "session_reset"
    SESSION_ERROR = "session_error"
    SESSION_TRANSPORT_CHANGED = "session_transport_changed"
    SESSION_CONFIG_CHANGED = "session_config_changed"

    # System events
    SYSTEM_STATS_UPDATED = "system_stats_updated"
    SCREENSHOT_GENERATED = "screenshot_generated"
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"


class EventPriority(str, Enum):
    """Event priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class SessionEvent(BaseModel):
    """Base event model for all session events"""

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique event identifier"
    )
    event_type: EventType = Field(..., description="Type of event")
    source_service: str = Field(..., description="Service that generated the event")
    session_id: Optional[str] = Field(
        None, description="Session identifier (if applicable)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Event timestamp"
    )
    priority: EventPriority = Field(EventPriority.NORMAL, description="Event priority")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Event-specific data"
    )
    target_clients: Optional[List[str]] = Field(
        None, description="Specific client IDs to target (None = broadcast)"
    )

    class Config:
        """Pydantic configuration"""

        json_encoders = {datetime: lambda v: v.isoformat()}


# Specific event data models for type safety


class PedalboardEventData(BaseModel):
    """Data for pedalboard-related events"""

    bundle_path: str
    title: str
    plugin_count: int
    connection_count: int


class PluginEventData(BaseModel):
    """Data for plugin-related events"""

    instance_id: str
    plugin_uri: str
    x: Optional[float] = None
    y: Optional[float] = None
    enabled: Optional[bool] = None
    preset: Optional[str] = None


class ParameterEventData(BaseModel):
    """Data for parameter-related events"""

    instance_id: str
    parameter_symbol: str
    value: float
    actuator_uri: Optional[str] = None


class ConnectionEventData(BaseModel):
    """Data for connection-related events"""

    source_port: str
    destination_port: str
    connection_id: str


class ClientEventData(BaseModel):
    """Data for client-related events"""

    client_id: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    subscriptions: Optional[List[str]] = None


class HardwareEventData(BaseModel):
    """Data for hardware-related events"""

    device_id: str
    device_uri: Optional[str] = None
    label: Optional[str] = None
    version: Optional[str] = None
    actuator_count: Optional[int] = None


class AudioEngineEventData(BaseModel):
    """Data for audio engine events"""

    sample_rate: Optional[int] = None
    buffer_size: Optional[int] = None
    xrun_count: Optional[int] = None
    load_average: Optional[float] = None


class SystemStatsEventData(BaseModel):
    """Data for system statistics events"""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    audio_xruns: int
    cpu_frequency: Optional[str] = None
    cpu_temperature: Optional[str] = None
    jack_sample_rate: Optional[int] = None
    jack_buffer_size: Optional[int] = None


# Event factory functions for type safety


def create_pedalboard_event(
    event_type: EventType,
    source_service: str,
    bundle_path: str,
    title: str,
    plugin_count: int,
    connection_count: int,
    session_id: Optional[str] = None,
) -> SessionEvent:
    """Create a pedalboard-related event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=PedalboardEventData(
            bundle_path=bundle_path,
            title=title,
            plugin_count=plugin_count,
            connection_count=connection_count,
        ).dict(),
    )


def create_plugin_event(
    event_type: EventType,
    source_service: str,
    instance_id: str,
    plugin_uri: str,
    session_id: Optional[str] = None,
    **kwargs
) -> SessionEvent:
    """Create a plugin-related event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=PluginEventData(
            instance_id=instance_id, plugin_uri=plugin_uri, **kwargs
        ).dict(),
    )


def create_parameter_event(
    event_type: EventType,
    source_service: str,
    instance_id: str,
    parameter_symbol: str,
    value: float,
    session_id: Optional[str] = None,
    actuator_uri: Optional[str] = None,
) -> SessionEvent:
    """Create a parameter-related event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=ParameterEventData(
            instance_id=instance_id,
            parameter_symbol=parameter_symbol,
            value=value,
            actuator_uri=actuator_uri,
        ).dict(),
    )


def create_connection_event(
    event_type: EventType,
    source_service: str,
    source_port: str,
    destination_port: str,
    connection_id: str,
    session_id: Optional[str] = None,
) -> SessionEvent:
    """Create a connection-related event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=ConnectionEventData(
            source_port=source_port,
            destination_port=destination_port,
            connection_id=connection_id,
        ).dict(),
    )


def create_client_event(
    event_type: EventType,
    source_service: str,
    client_id: str,
    session_id: Optional[str] = None,
    **kwargs
) -> SessionEvent:
    """Create a client-related event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=ClientEventData(client_id=client_id, **kwargs).dict(),
    )


def create_system_stats_event(
    event_type: EventType,
    source_service: str,
    cpu_percent: float,
    memory_percent: float,
    cpu_frequency: str,
    cpu_temperature: str,
    xruns: int,
    session_id: Optional[str] = None,
) -> SessionEvent:
    """Create a system statistics event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=SystemStatsEventData(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=0.0,  # Not currently tracked
            audio_xruns=xruns,
            cpu_frequency=cpu_frequency,
            cpu_temperature=cpu_temperature,
        ).dict(exclude_none=False),
    )
