"""
Audio Engine Service Models

Defines the data models for audio engine operations, including JACK connections and LV2 plugin management.
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


# JACK Management Models
class JackPortInfo(BaseModel):
    """Information about a JACK port"""

    name: str
    alias: Optional[str] = None
    is_audio: bool
    is_output: bool
    connected_ports: List[str] = Field(default_factory=list)


class JackConnectionInfo(BaseModel):
    """JACK connection information"""

    output_port: str
    input_port: str
    connection_id: Optional[str] = None


class JackData(BaseModel):
    """JACK system data"""

    cpu_load: float = 0.0
    xruns: int = 0
    rolling: bool = False
    bpb: float = 4.0
    bpm: float = 120.0
    buffer_size: int = 512
    sample_rate: float = 48000.0


# LV2 Plugin Management Models
class LV2PluginPort(BaseModel):
    """LV2 plugin port information"""

    symbol: str
    name: str
    is_input: bool
    is_audio: bool
    is_cv: bool
    is_midi: bool
    is_control: bool
    default_value: Optional[float] = None
    minimum_value: Optional[float] = None
    maximum_value: Optional[float] = None
    scale_points: List[Dict[str, Any]] = Field(default_factory=list)


class LV2PluginInfo(BaseModel):
    """Detailed LV2 plugin information"""

    uri: str
    name: str
    brand: str = ""
    comment: str = ""
    version: str = ""
    license: str = ""
    author: str = ""
    category: List[str] = Field(default_factory=list)
    bundle_path: str = ""
    binary: str = ""
    ports: List[LV2PluginPort] = Field(default_factory=list)
    presets: List[Dict[str, str]] = Field(default_factory=list)
    has_gui: bool = False


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

    # JACK specific state
    jack_data: JackData = Field(default_factory=JackData)
    jack_hardware_ports: List[JackPortInfo] = Field(default_factory=list)
    jack_connections: List[JackConnectionInfo] = Field(default_factory=list)


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


# JACK Command Types
class ConnectJackPortsCommand(BaseModel):
    """Connect two JACK ports"""

    output_port: str
    input_port: str


class DisconnectJackPortsCommand(BaseModel):
    """Disconnect two JACK ports"""

    output_port: str
    input_port: str


class DisconnectAllJackPortsCommand(BaseModel):
    """Disconnect all connections from a JACK port"""

    port_name: str


class SetJackBufferSizeCommand(BaseModel):
    """Set JACK buffer size"""

    buffer_size: int


# LV2 Command Types
class ScanPluginsCommand(BaseModel):
    """Rescan all LV2 plugins"""

    force_refresh: bool = False


class AddBundleCommand(BaseModel):
    """Add an LV2 bundle to the plugin world"""

    bundle_path: str


class RemoveBundleCommand(BaseModel):
    """Remove an LV2 bundle from the plugin world"""

    bundle_path: str
    resource: Optional[str] = None


class GetPluginInfoCommand(BaseModel):
    """Get detailed information about an LV2 plugin"""

    plugin_uri: str
