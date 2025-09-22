"""
Pydantic Data Models for Session Service

Modern type-safe data models replacing the legacy dictionary-based approach.
All models include validation, serialization, and documentation.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class PluginPortType(str, Enum):
    """Plugin port types"""

    AUDIO_INPUT = "audio_input"
    AUDIO_OUTPUT = "audio_output"
    CV_INPUT = "cv_input"
    CV_OUTPUT = "cv_output"
    CONTROL_INPUT = "control_input"
    CONTROL_OUTPUT = "control_output"
    MIDI_INPUT = "midi_input"
    MIDI_OUTPUT = "midi_output"


class PluginParameter(BaseModel):
    """Plugin parameter definition"""

    symbol: str = Field(..., description="Parameter symbol (unique within plugin)")
    name: str = Field(..., description="Human-readable parameter name")
    value: float = Field(..., description="Current parameter value")
    minimum: float = Field(..., description="Minimum allowed value")
    maximum: float = Field(..., description="Maximum allowed value")
    default: float = Field(..., description="Default parameter value")
    unit: Optional[str] = Field(None, description="Parameter unit (Hz, dB, etc.)")
    scale_points: Optional[Dict[str, float]] = Field(
        None, description="Named scale points"
    )
    integer: bool = Field(
        False, description="Whether parameter accepts only integer values"
    )
    logarithmic: bool = Field(
        False, description="Whether parameter uses logarithmic scale"
    )

    @validator("value")
    def validate_value_range(cls, v, values):
        """Ensure value is within min/max range"""
        if "minimum" in values and v < values["minimum"]:
            raise ValueError(f"Value {v} below minimum {values['minimum']}")
        if "maximum" in values and v > values["maximum"]:
            raise ValueError(f"Value {v} above maximum {values['maximum']}")
        return v


class PluginPort(BaseModel):
    """Plugin port definition"""

    symbol: str = Field(..., description="Port symbol (unique within plugin)")
    name: str = Field(..., description="Human-readable port name")
    port_type: PluginPortType = Field(..., description="Type of port")
    index: int = Field(..., description="Port index within plugin")


class PluginModel(BaseModel):
    """Plugin instance in a pedalboard"""

    instance_id: str = Field(..., description="Unique instance identifier")
    plugin_uri: str = Field(..., description="LV2 plugin URI")
    x: float = Field(..., description="X position on pedalboard canvas")
    y: float = Field(..., description="Y position on pedalboard canvas")
    parameters: Dict[str, PluginParameter] = Field(
        default_factory=dict, description="Plugin parameters"
    )
    ports: Dict[str, PluginPort] = Field(
        default_factory=dict, description="Plugin ports"
    )
    enabled: bool = Field(True, description="Whether plugin is enabled (not bypassed)")
    preset: Optional[str] = Field(None, description="Current preset name")

    @validator("instance_id")
    def validate_instance_id(cls, v):
        """Ensure instance_id is a valid identifier"""
        if not v or not isinstance(v, str):
            raise ValueError("instance_id must be a non-empty string")
        return v

    @validator("plugin_uri")
    def validate_plugin_uri(cls, v):
        """Ensure plugin_uri is a valid LV2 URI"""
        if not v.startswith("http"):
            raise ValueError("plugin_uri must be a valid HTTP URI")
        return v


class ConnectionModel(BaseModel):
    """Audio/CV connection between plugin ports"""

    source_port: str = Field(
        ..., description="Source port (plugin_instance/port_symbol)"
    )
    destination_port: str = Field(
        ..., description="Destination port (plugin_instance/port_symbol)"
    )
    connection_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique connection identifier",
    )

    @validator("source_port", "destination_port")
    def validate_port_format(cls, v):
        """Ensure port follows plugin_instance/port_symbol format"""
        if "/" not in v:
            raise ValueError("Port must be in format 'plugin_instance/port_symbol'")
        return v


class PedalboardMetadata(BaseModel):
    """Pedalboard metadata information"""

    title: str = Field(..., description="Pedalboard title")
    description: Optional[str] = Field(None, description="Pedalboard description")
    author: Optional[str] = Field(None, description="Pedalboard author")
    version: Optional[str] = Field("1.0", description="Pedalboard version")
    tags: List[str] = Field(default_factory=list, description="Pedalboard tags")
    screenshot_path: Optional[str] = Field(
        None, description="Path to pedalboard screenshot"
    )
    thumbnail_path: Optional[str] = Field(
        None, description="Path to pedalboard thumbnail"
    )


class PedalboardModel(BaseModel):
    """Complete pedalboard definition"""

    bundle_path: str = Field(..., description="Path to pedalboard bundle directory")
    metadata: PedalboardMetadata = Field(..., description="Pedalboard metadata")
    plugins: Dict[str, PluginModel] = Field(
        default_factory=dict, description="Plugins indexed by instance_id"
    )
    connections: List[ConnectionModel] = Field(
        default_factory=list, description="Audio/CV connections"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    modified_at: datetime = Field(
        default_factory=datetime.now, description="Last modification timestamp"
    )

    @validator("bundle_path")
    def validate_bundle_path(cls, v):
        """Ensure bundle_path has correct extension"""
        if not v.endswith(".pedalboard"):
            raise ValueError("bundle_path must end with '.pedalboard'")
        return v

    def get_plugin(self, instance_id: str) -> Optional[PluginModel]:
        """Get plugin by instance ID"""
        return self.plugins.get(instance_id)

    def add_plugin(self, plugin: PluginModel) -> None:
        """Add plugin to pedalboard"""
        self.plugins[plugin.instance_id] = plugin
        self.modified_at = datetime.now()

    def remove_plugin(self, instance_id: str) -> bool:
        """Remove plugin from pedalboard"""
        if instance_id in self.plugins:
            del self.plugins[instance_id]
            # Remove connections involving this plugin
            self.connections = [
                conn
                for conn in self.connections
                if not (
                    conn.source_port.startswith(f"{instance_id}/")
                    or conn.destination_port.startswith(f"{instance_id}/")
                )
            ]
            self.modified_at = datetime.now()
            return True
        return False

    def add_connection(self, connection: ConnectionModel) -> None:
        """Add connection to pedalboard"""
        self.connections.append(connection)
        self.modified_at = datetime.now()

    def remove_connection(self, source_port: str, destination_port: str) -> bool:
        """Remove connection from pedalboard"""
        for i, conn in enumerate(self.connections):
            if (
                conn.source_port == source_port
                and conn.destination_port == destination_port
            ):
                del self.connections[i]
                self.modified_at = datetime.now()
                return True
        return False


class SessionStatus(str, Enum):
    """Session status values"""

    INITIALIZING = "initializing"
    READY = "ready"
    LOADING_PEDALBOARD = "loading_pedalboard"
    SAVING_PEDALBOARD = "saving_pedalboard"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class TransportState(str, Enum):
    """Transport playback states"""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    RECORDING = "recording"


class SessionState(BaseModel):
    """Current session state"""

    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier",
    )
    status: SessionStatus = Field(
        SessionStatus.INITIALIZING, description="Current session status"
    )
    current_pedalboard: Optional[PedalboardModel] = Field(
        None, description="Currently loaded pedalboard"
    )
    websocket_clients: int = Field(
        0, description="Number of connected WebSocket clients"
    )
    audio_engine_connected: bool = Field(
        False, description="Whether audio engine is connected"
    )
    hardware_connected: bool = Field(False, description="Whether hardware is connected")
    last_activity: datetime = Field(
        default_factory=datetime.now, description="Last activity timestamp"
    )
    error_message: Optional[str] = Field(
        None, description="Current error message if status is ERROR"
    )

    # Transport state
    transport_state: TransportState = Field(
        TransportState.STOPPED, description="Current transport state"
    )
    tempo_bpm: float = Field(120.0, description="Current tempo in BPM")

    # Audio system configuration
    sample_rate: int = Field(48000, description="Audio sample rate")
    buffer_size: int = Field(256, description="Audio buffer size")
    audio_driver: str = Field("jack", description="Audio driver")

    # System monitoring
    cpu_load: float = Field(0.0, description="CPU load percentage")
    xrun_count: int = Field(0, description="Audio buffer underruns/overruns")
    uptime_seconds: int = Field(0, description="Service uptime in seconds")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now, description="Session creation time"
    )
    modified_at: datetime = Field(
        default_factory=datetime.now, description="Last modification time"
    )

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.now()

    def set_error(self, message: str) -> None:
        """Set error status with message"""
        self.status = SessionStatus.ERROR
        self.error_message = message
        self.update_activity()

    def clear_error(self) -> None:
        """Clear error status"""
        if self.status == SessionStatus.ERROR:
            self.status = SessionStatus.READY
            self.error_message = None
            self.update_activity()


class HardwareDevice(BaseModel):
    """Hardware device information"""

    device_id: str = Field(..., description="Unique device identifier")
    device_uri: str = Field(..., description="Device URI")
    label: str = Field(..., description="Device label")
    version: str = Field(..., description="Device firmware version")
    connected: bool = Field(False, description="Whether device is connected")
    actuators: List[Dict[str, Any]] = Field(
        default_factory=list, description="Available actuators"
    )


class SystemStats(BaseModel):
    """System resource statistics"""

    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    disk_percent: float = Field(..., description="Disk usage percentage")
    audio_xruns: int = Field(0, description="Audio buffer underruns/overruns")
    jack_sample_rate: Optional[int] = Field(None, description="JACK sample rate")
    jack_buffer_size: Optional[int] = Field(None, description="JACK buffer size")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Statistics timestamp"
    )


# Import event models
from .events import EventType
from .events import SessionEvent as Event

# Export all models
__all__ = [
    # Core models
    "PedalboardModel",
    "PluginModel",
    "ConnectionModel",
    "PedalboardMetadata",
    "PluginParameter",
    "PluginPort",
    "PluginPortType",
    "SessionState",
    "SessionStatus",
    "TransportState",
    "HardwareDevice",
    "SystemStats",
    # Event models
    "Event",
    "EventType",
]
