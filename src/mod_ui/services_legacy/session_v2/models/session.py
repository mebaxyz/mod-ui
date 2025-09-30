"""
Session State Models

Defines data models for session management, transport state,
and system configuration. Enhanced with comprehensive session functionality
from the original MOD UI session system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class TransportState(Enum):
    """Transport playback states"""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    RECORDING = "recording"


class TransportSyncMode(Enum):
    """Transport synchronization modes"""

    INTERNAL = "none"
    MIDI_CLOCK_SLAVE = "midi_clock_slave"
    ABLETON_LINK = "link"


class SessionStatus(Enum):
    """Session status states"""

    INITIALIZING = "initializing"
    READY = "ready"
    LOADING_PEDALBOARD = "loading_pedalboard"
    SAVING_PEDALBOARD = "saving_pedalboard"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class MidiMapping(BaseModel):
    """MIDI controller mapping"""

    channel: int = Field(..., ge=0, le=15, description="MIDI channel (0-15)")
    controller: int = Field(..., ge=0, le=127, description="MIDI CC number")
    minimum: float = Field(..., description="Minimum parameter value")
    maximum: float = Field(..., description="Maximum parameter value")


class AddressingInfo(BaseModel):
    """Hardware/MIDI addressing information"""

    actuator_uri: str = Field(..., description="URI of the actuator/controller")
    label: str = Field(..., description="Display label for control")
    minimum: float = Field(..., description="Minimum value")
    maximum: float = Field(..., description="Maximum value")
    value: float = Field(..., description="Current value")
    steps: int = Field(default=33, description="Number of steps")
    tempo: bool = Field(default=False, description="Tempo-synced parameter")
    dividers: Optional[List[float]] = Field(None, description="Tempo dividers")
    page: Optional[int] = Field(None, description="Hardware page number")
    subpage: Optional[int] = Field(None, description="Hardware subpage number")
    coloured: Optional[str] = Field(None, description="LED color")
    momentary: Optional[bool] = Field(None, description="Momentary mode")
    operational_mode: Optional[str] = Field(None, description="CV operational mode")


class SnapshotData(BaseModel):
    """Pedalboard snapshot data"""

    name: str = Field(..., description="Snapshot name")
    parameters: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, description="Parameter values by plugin instance"
    )
    created_at: datetime = Field(default_factory=datetime.now)


class RecordingState(BaseModel):
    """Audio recording state"""

    is_recording: bool = Field(default=False)
    is_playing: bool = Field(default=False)
    has_recording: bool = Field(default=False)
    recording_length_seconds: float = Field(default=0.0)


class BankInfo(BaseModel):
    """Pedalboard bank information"""

    bank_id: int = Field(..., description="Bank identifier")
    title: str = Field(..., description="Bank title")
    pedalboards: List[Dict[str, Any]] = Field(
        default_factory=list, description="Pedalboards in this bank"
    )


class SessionState(BaseModel):
    """Complete session state representation"""

    # Session identification
    session_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)

    # Session status
    status: SessionStatus = Field(default=SessionStatus.INITIALIZING)
    error_message: Optional[str] = Field(
        None, description="Error message if status is ERROR"
    )

    # Transport state
    transport_state: TransportState = TransportState.STOPPED
    transport_sync: TransportSyncMode = Field(default=TransportSyncMode.INTERNAL)
    transport_rolling: bool = Field(default=False, description="Transport is rolling")
    tempo_bpm: float = Field(default=120.0, ge=30.0, le=300.0)
    beats_per_bar: float = Field(
        default=4.0, ge=1.0, le=16.0, description="Time signature"
    )

    # Current pedalboard state
    pedalboard_name: Optional[str] = Field(None, description="Current pedalboard name")
    pedalboard_path: Optional[str] = Field(
        None, description="Current pedalboard file path"
    )
    pedalboard_empty: bool = Field(
        default=True, description="Whether pedalboard is empty"
    )
    pedalboard_modified: bool = Field(
        default=False, description="Whether pedalboard has unsaved changes"
    )
    pedalboard_size: List[int] = Field(
        default=[0, 0], description="Pedalboard canvas size [width, height]"
    )

    # Snapshots
    current_snapshot_id: int = Field(
        default=-1, description="Currently loaded snapshot ID"
    )
    snapshots: Dict[int, SnapshotData] = Field(
        default_factory=dict, description="Available snapshots"
    )

    # Audio system configuration
    sample_rate: int = Field(default=48000)
    buffer_size: int = Field(default=256)
    audio_driver: str = Field(default="jack")

    # System monitoring
    cpu_load: float = Field(default=0.0, ge=0.0, le=100.0)
    xrun_count: int = Field(default=0, ge=0)
    uptime_seconds: int = Field(default=0, ge=0)

    # Client connections
    websocket_clients: int = Field(default=0, ge=0)
    web_connected: bool = Field(
        default=False, description="Whether web UI is connected"
    )

    # Hardware state
    hmi_connected: bool = Field(
        default=False, description="Hardware HMI connection status"
    )
    hardware_connected: bool = Field(
        default=False, description="Hardware device connection"
    )
    audio_engine_connected: bool = Field(
        default=False, description="MOD-Host connection status"
    )

    # MIDI configuration
    midi_aggregated_mode: bool = Field(default=True, description="MIDI aggregated mode")
    midi_loopback_enabled: bool = Field(
        default=False, description="MIDI loopback enabled"
    )

    # Recording state
    recording: RecordingState = Field(default_factory=RecordingState)

    # Bank navigation
    current_bank_id: int = Field(default=0, description="Currently selected bank")
    banks: List[BankInfo] = Field(
        default_factory=list, description="Available pedalboard banks"
    )

    # Plugin state tracking (for compatibility with original session)
    plugins_data: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Plugin instances and their state"
    )

    # Connections tracking
    connections: List[Dict[str, str]] = Field(
        default_factory=list, description="Audio/MIDI/CV connections"
    )

    # Hardware ports
    audio_ports_in: List[str] = Field(default_factory=list)
    audio_ports_out: List[str] = Field(default_factory=list)
    cv_ports_in: List[str] = Field(default_factory=list)
    cv_ports_out: List[str] = Field(default_factory=list)
    midi_ports: List[Dict[str, Any]] = Field(default_factory=list)

    # Tuner state
    tuner_on: bool = Field(default=False, description="Whether tuner is active")
    tuner_input_port: int = Field(default=1, description="Tuner input port")
    tuner_mute: bool = Field(default=False, description="Whether tuner mutes outputs")
    tuner_ref_freq: int = Field(default=440, description="Tuner reference frequency")

    class Config:
        # Enable enum serialization by value
        use_enum_values = True

    def update_activity(self) -> None:
        """Update last modification timestamp"""
        self.modified_at = datetime.now()

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

    @validator("tempo_bpm")
    def validate_tempo(cls, v):
        """Validate tempo is within reasonable range"""
        if not 30.0 <= v <= 300.0:
            raise ValueError("Tempo must be between 30 and 300 BPM")
        return v


class SessionSnapshot(BaseModel):
    """Saved session state snapshot"""

    # Snapshot metadata
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.now)

    # Saved session state
    session_state: SessionState

    # Associated pedalboard (optional)
    pedalboard_bundle_path: Optional[str] = None

    class Config:
        use_enum_values = True


class SystemInfo(BaseModel):
    """System information and capabilities"""

    # Service information
    service_name: str = "mod-ui-session-v2"
    service_version: str = "2.0.0"

    # Audio system capabilities
    available_sample_rates: list[int] = Field(
        default=[22050, 44100, 48000, 88200, 96000]
    )
    available_buffer_sizes: list[int] = Field(default=[64, 128, 256, 512, 1024, 2048])
    available_audio_drivers: list[str] = Field(default=["jack", "alsa", "dummy"])

    # Current system state
    uptime_seconds: int = Field(default=0, ge=0)
    start_time: datetime = Field(default_factory=datetime.now)

    # Resource usage
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    class Config:
        use_enum_values = True
