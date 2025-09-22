"""
Hardware Event Models for Hardware Service Communication

These models define the events used for communication between the hardware service
and other services via the Redis event bus.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .events import EventType, SessionEvent


class HardwareConnectionStatus(str, Enum):
    """Hardware connection status"""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"


class ControlChainDeviceStatus(str, Enum):
    """Control Chain device status"""

    ADDED = "added"
    REMOVED = "removed"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class HMIMessageType(str, Enum):
    """HMI message types"""

    HEARTBEAT = "heartbeat"
    CONTROL_ADD = "control_add"
    CONTROL_SET = "control_set"
    CONTROL_REMOVE = "control_remove"
    BANK_CONFIG = "bank_config"
    TUNER = "tuner"
    PING = "ping"


# Event Data Models


class HardwareStatusEventData(BaseModel):
    """Data for hardware status events"""

    device_connected: bool
    device_type: Optional[str] = None
    serial_port: Optional[str] = None
    hmi_version: Optional[str] = None
    last_heartbeat: datetime
    error_message: Optional[str] = None


class ControlChainEventData(BaseModel):
    """Data for Control Chain device events"""

    device_id: int
    device_uri: str
    label: str
    labelsuffix: Optional[str] = None
    version: str
    status: ControlChainDeviceStatus
    metadata: Optional[Dict[str, Any]] = None


class HMIEventData(BaseModel):
    """Data for HMI communication events"""

    message_type: HMIMessageType
    hardware_id: Optional[int] = None
    data: Dict[str, Any]
    callback_required: bool = False


class AudioConnectionEventData(BaseModel):
    """Data for audio connection events"""

    source_port: str
    destination_port: str
    connected: bool
    connection_id: Optional[str] = None


class PluginInstanceEventData(BaseModel):
    """Data for plugin instance events"""

    instance_id: str
    plugin_uri: str
    enabled: bool
    parameters: Dict[str, float] = {}


# Event Factory Functions


def create_hardware_status_event(
    event_type: EventType,
    source_service: str,
    device_connected: bool,
    device_type: Optional[str] = None,
    serial_port: Optional[str] = None,
    hmi_version: Optional[str] = None,
    error_message: Optional[str] = None,
    session_id: Optional[str] = None,
) -> SessionEvent:
    """Create a hardware status event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=HardwareStatusEventData(
            device_connected=device_connected,
            device_type=device_type,
            serial_port=serial_port,
            hmi_version=hmi_version,
            last_heartbeat=datetime.now(),
            error_message=error_message,
        ).model_dump(exclude_none=False, mode="json"),
    )


def create_control_chain_event(
    event_type: EventType,
    source_service: str,
    device_id: int,
    device_uri: str,
    label: str,
    version: str,
    status: ControlChainDeviceStatus,
    labelsuffix: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> SessionEvent:
    """Create a Control Chain device event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=ControlChainEventData(
            device_id=device_id,
            device_uri=device_uri,
            label=label,
            labelsuffix=labelsuffix,
            version=version,
            status=status,
            metadata=metadata,
        ).model_dump(exclude_none=False, mode="json"),
    )


def create_hmi_event(
    event_type: EventType,
    source_service: str,
    message_type: HMIMessageType,
    data: Dict[str, Any],
    hardware_id: Optional[int] = None,
    callback_required: bool = False,
    session_id: Optional[str] = None,
) -> SessionEvent:
    """Create an HMI communication event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=HMIEventData(
            message_type=message_type,
            hardware_id=hardware_id,
            data=data,
            callback_required=callback_required,
        ).model_dump(exclude_none=False, mode="json"),
    )


def create_audio_connection_event(
    event_type: EventType,
    source_service: str,
    source_port: str,
    destination_port: str,
    connected: bool,
    connection_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> SessionEvent:
    """Create an audio connection event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=AudioConnectionEventData(
            source_port=source_port,
            destination_port=destination_port,
            connected=connected,
            connection_id=connection_id,
        ).dict(exclude_none=False),
    )


def create_plugin_instance_event(
    event_type: EventType,
    source_service: str,
    instance_id: str,
    plugin_uri: str,
    enabled: bool,
    parameters: Dict[str, float] = None,
    session_id: Optional[str] = None,
) -> SessionEvent:
    """Create a plugin instance event"""
    return SessionEvent(
        event_type=event_type,
        source_service=source_service,
        session_id=session_id,
        data=PluginInstanceEventData(
            instance_id=instance_id,
            plugin_uri=plugin_uri,
            enabled=enabled,
            parameters=parameters or {},
        ).dict(exclude_none=False),
    )
