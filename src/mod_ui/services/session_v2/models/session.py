"""
Session State Models

Defines data models for session management, transport state,
and system configuration.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TransportState(Enum):
    """Transport playback states"""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    RECORDING = "recording"


class SessionState(BaseModel):
    """Complete session state representation"""

    # Session identification
    session_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)

    # Transport state
    transport_state: TransportState = TransportState.STOPPED
    tempo_bpm: float = Field(default=120.0, ge=1.0, le=300.0)

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

    class Config:
        # Enable enum serialization by value
        use_enum_values = True


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
