"""
Plugin and Pedalboard Models

Enhanced models for plugin management, pedalboard operations,
and parameter control, based on the original MOD UI session functionality.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from .session import AddressingInfo, MidiMapping


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


class ParameterRange(BaseModel):
    """Parameter value range definition"""

    minimum: float = Field(..., description="Minimum value")
    maximum: float = Field(..., description="Maximum value")
    default: float = Field(..., description="Default value")


class PluginParameter(BaseModel):
    """Plugin parameter with full metadata"""

    symbol: str = Field(..., description="Parameter symbol")
    name: str = Field(..., description="Human-readable name")
    shortName: Optional[str] = Field(None, description="Short display name")
    value: float = Field(..., description="Current value")
    ranges: ParameterRange = Field(..., description="Value ranges")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    comment: Optional[str] = Field(None, description="Parameter description")
    designation: Optional[str] = Field(None, description="LV2 designation")
    properties: List[str] = Field(default_factory=list, description="LV2 properties")
    rangeSteps: Optional[int] = Field(
        None, description="Number of steps for discrete parameters"
    )
    scalePoints: List[Dict[str, Union[str, float]]] = Field(
        default_factory=list, description="Named scale points"
    )

    # Addressing information
    addressing: Optional[AddressingInfo] = Field(
        None, description="Hardware/MIDI addressing"
    )
    midi_mapping: Optional[MidiMapping] = Field(None, description="MIDI CC mapping")

    @validator("value")
    def validate_value_in_range(cls, v, values):
        """Ensure value is within parameter range"""
        if "ranges" in values:
            ranges = values["ranges"]
            if v < ranges.minimum or v > ranges.maximum:
                # Clamp to range instead of raising error
                return max(ranges.minimum, min(ranges.maximum, v))
        return v


class PluginPort(BaseModel):
    """Plugin port definition"""

    symbol: str = Field(..., description="Port symbol")
    name: str = Field(..., description="Port name")
    shortName: Optional[str] = Field(None, description="Short display name")
    index: int = Field(..., description="Port index")
    type: PluginPortType = Field(..., description="Port type")
    flow: str = Field(..., description="Port flow (input/output)")
    ranges: Optional[ParameterRange] = Field(
        None, description="Value ranges for control ports"
    )
    units: Optional[Dict[str, str]] = Field(None, description="Port units")
    designation: Optional[str] = Field(None, description="LV2 designation")
    properties: List[str] = Field(default_factory=list, description="LV2 properties")


class PluginInfo(BaseModel):
    """Complete plugin information"""

    uri: str = Field(..., description="Plugin LV2 URI")
    name: str = Field(..., description="Plugin name")
    brand: Optional[str] = Field(None, description="Plugin brand/author")
    label: Optional[str] = Field(None, description="Plugin label")
    comment: Optional[str] = Field(None, description="Plugin description")
    category: List[str] = Field(default_factory=list, description="Plugin categories")
    version: Optional[str] = Field(None, description="Plugin version")
    stability: Optional[str] = Field(None, description="Plugin stability level")
    author: Optional[Dict[str, str]] = Field(None, description="Plugin author info")
    license: Optional[str] = Field(None, description="Plugin license")

    # Port information
    ports: Dict[str, List[PluginPort]] = Field(
        default_factory=dict, description="Plugin ports by type"
    )

    # Parameter definitions
    parameters: Dict[str, PluginParameter] = Field(
        default_factory=dict, description="Plugin parameters"
    )

    # Plugin capabilities
    presets: List[Dict[str, str]] = Field(
        default_factory=list, description="Available presets"
    )

    # GUI information
    gui: Dict[str, Any] = Field(default_factory=dict, description="GUI metadata")


class PluginInstance(BaseModel):
    """Plugin instance in a pedalboard"""

    instance: str = Field(
        ..., description="Instance identifier (e.g., '/graph/effect_1')"
    )
    uri: str = Field(..., description="Plugin LV2 URI")
    x: float = Field(default=0.0, description="X position on canvas")
    y: float = Field(default=0.0, description="Y position on canvas")

    # Plugin state
    bypassed: bool = Field(default=False, description="Bypass state")
    enabled: bool = Field(default=True, description="Enabled state")

    # Parameters with current values
    ports: Dict[str, float] = Field(
        default_factory=dict, description="Port values by symbol"
    )

    # Ranges for validation
    ranges: Dict[str, ParameterRange] = Field(
        default_factory=dict, description="Parameter ranges"
    )

    # Designations for transport sync
    designations: Tuple[
        Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
    ] = Field(
        default=(None, None, None, None, None),
        description="LV2 designations (enabled, freewheel, bpb, bpm, speed)",
    )

    # Addressing information
    addressings: Dict[str, AddressingInfo] = Field(
        default_factory=dict, description="Parameter addressings"
    )

    # MIDI mappings
    midiCCs: Dict[str, Tuple[int, int, float, float]] = Field(
        default_factory=dict, description="MIDI CC mappings (channel, cc, min, max)"
    )
    bypassCC: Optional[Tuple[int, int]] = Field(
        None, description="Bypass MIDI CC (channel, cc)"
    )

    # Preset information
    preset: Optional[str] = Field(None, description="Current preset URI")
    mapPresets: List[str] = Field(default_factory=list, description="Available presets")
    nextPreset: Optional[str] = Field(None, description="Next preset to load")

    # Output values (for display)
    outputs: Dict[str, float] = Field(
        default_factory=dict, description="Output port values"
    )

    # Parameters for patch:Message interface
    parameters: Dict[str, Tuple[str, str]] = Field(
        default_factory=dict, description="Patch parameters (value, writable)"
    )


class Connection(BaseModel):
    """Audio/MIDI/CV connection"""

    source: str = Field(..., description="Source port")
    target: str = Field(..., description="Target port")

    @validator("source", "target")
    def validate_port_format(cls, v):
        """Validate port format"""
        if not isinstance(v, str) or len(v) == 0:
            raise ValueError("Port must be a non-empty string")
        return v


class PedalboardInfo(BaseModel):
    """Pedalboard metadata and structure"""

    title: str = Field(..., description="Pedalboard title")
    uri: str = Field(..., description="Pedalboard URI")
    bundle: str = Field(..., description="Bundle directory path")
    version: int = Field(default=1, description="Pedalboard version")

    # Structure information
    width: int = Field(default=0, description="Canvas width")
    height: int = Field(default=0, description="Canvas height")

    # Plugin instances
    plugins: List[Dict[str, Any]] = Field(
        default_factory=list, description="Plugin instances"
    )

    # Connections
    connections: List[Connection] = Field(
        default_factory=list, description="Audio/MIDI/CV connections"
    )

    # Hardware mappings
    hardware: Dict[str, Any] = Field(
        default_factory=dict, description="Hardware assignments"
    )

    # Metadata
    broken: bool = Field(default=False, description="Whether pedalboard is broken")
    factory: bool = Field(
        default=False, description="Whether pedalboard is factory preset"
    )
    hasTrialPlugins: bool = Field(default=False, description="Contains trial plugins")

    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    modified_at: Optional[datetime] = Field(None, description="Modification timestamp")


class PluginAddRequest(BaseModel):
    """Request to add a plugin to pedalboard"""

    instance: str = Field(..., description="Instance identifier")
    uri: str = Field(..., description="Plugin URI")
    x: float = Field(default=0.0, description="X position")
    y: float = Field(default=0.0, description="Y position")


class PluginRemoveRequest(BaseModel):
    """Request to remove a plugin from pedalboard"""

    instance: str = Field(..., description="Instance identifier")


class ParameterSetRequest(BaseModel):
    """Request to set plugin parameter"""

    instance: str = Field(..., description="Plugin instance")
    parameter: str = Field(..., description="Parameter symbol")
    value: float = Field(..., description="New value")


class ConnectionRequest(BaseModel):
    """Request to create/remove connection"""

    source: str = Field(..., description="Source port")
    target: str = Field(..., description="Target port")


class PresetRequest(BaseModel):
    """Request to load plugin preset"""

    instance: str = Field(..., description="Plugin instance")
    uri: str = Field(..., description="Preset URI")
