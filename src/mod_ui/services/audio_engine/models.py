"""
Audio Engine Service Models

Defines the data models for audio engine operations.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PluginInstance(BaseModel):
    """Represents a plugin instance in the audio engine"""

    instance_id: str
    plugin_uri: str
    x: float = 0.0
    y: float = 0.0
    ports: Dict[str, float] = Field(default_factory=dict)
    designations: Dict[str, Optional[str]] = Field(default_factory=dict)
    preset_uri: Optional[str] = None
    bypass: bool = False
    enabled: bool = True


class AudioConnection(BaseModel):
    """Represents an audio connection between ports"""

    from_port: str
    to_port: str
    connection_id: Optional[str] = None


class TransportState(BaseModel):
    """Transport/timing state of the audio engine"""

    rolling: bool = False
    bpm: float = 120.0
    bpb: float = 4.0
    sync_mode: str = "none"
    speed: float = 1.0


class AudioPortInfo(BaseModel):
    """Information about an audio port"""

    symbol: str
    name: str
    direction: str  # "input" or "output"
    type: str  # "audio", "cv", "midi", "atom"
    connected: bool = False


class PluginParameterChange(BaseModel):
    """Parameter change event from audio engine"""

    instance_id: str
    port_symbol: str
    value: float
    timestamp: Optional[float] = None


class AudioEngineState(BaseModel):
    """Complete state of the audio engine"""

    plugins: Dict[str, PluginInstance] = Field(default_factory=dict)
    connections: List[AudioConnection] = Field(default_factory=list)
    transport: TransportState = Field(default_factory=TransportState)
    audio_ports_in: List[AudioPortInfo] = Field(default_factory=list)
    audio_ports_out: List[AudioPortInfo] = Field(default_factory=list)
    cv_ports_in: List[AudioPortInfo] = Field(default_factory=list)
    cv_ports_out: List[AudioPortInfo] = Field(default_factory=list)
    midi_ports: List[AudioPortInfo] = Field(default_factory=list)


# Command types for common operations
class AddPluginCommand(BaseModel):
    """Add a plugin instance to the audio engine"""

    instance_id: str
    plugin_uri: str
    x: float = 0.0
    y: float = 0.0


class RemovePluginCommand(BaseModel):
    """Remove a plugin instance from the audio engine"""

    instance_id: str


class SetParameterCommand(BaseModel):
    """Set a plugin parameter value"""

    instance_id: str
    port_symbol: str
    value: float


class ConnectPortsCommand(BaseModel):
    """Connect two audio ports"""

    from_port: str
    to_port: str


class DisconnectPortsCommand(BaseModel):
    """Disconnect two audio ports"""

    from_port: str
    to_port: str


class SetTransportCommand(BaseModel):
    """Set transport state"""

    rolling: Optional[bool] = None
    bpm: Optional[float] = None
    bpb: Optional[float] = None


class LoadPresetCommand(BaseModel):
    """Load a plugin preset"""

    instance_id: str
    preset_uri: str


class BypassPluginCommand(BaseModel):
    """Bypass or enable a plugin"""

    instance_id: str
    bypass: bool
