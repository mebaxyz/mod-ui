"""
FastAPI Models for MOD UI

Pydantic models for request/response validation and documentation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime


# System Models
class SystemInfo(BaseModel):
    version: str
    hardware: str
    uptime: int
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    framework: str = "FastAPI"


class SystemResponse(BaseModel):
    success: bool = True
    data: SystemInfo
    message: Optional[str] = None


# Plugin Models
class PluginPort(BaseModel):
    symbol: str
    name: str
    type: str  # "audio", "control", "cv", "midi"
    direction: str  # "input", "output"
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    default: Optional[float] = None
    unit: Optional[str] = None


class PluginInfo(BaseModel):
    uri: str
    name: str
    description: Optional[str] = None
    category: str
    author: str
    version: str
    ports: List[PluginPort] = []


class PluginListResponse(BaseModel):
    success: bool = True
    data: Dict[str, List[str]] = Field(default_factory=lambda: {"plugins": []})


class PluginInfoResponse(BaseModel):
    success: bool = True
    data: PluginInfo


# Pedalboard Models
class PedalboardPlugin(BaseModel):
    id: str
    uri: str
    x: int
    y: int
    parameters: Dict[str, float] = Field(default_factory=dict)


class PedalboardConnection(BaseModel):
    source: str
    target: str


class PedalboardInfo(BaseModel):
    id: str
    title: str
    modified: datetime
    plugins: List[PedalboardPlugin] = []
    connections: List[PedalboardConnection] = []


class PedalboardListResponse(BaseModel):
    success: bool = True
    data: Dict[str, List[PedalboardInfo]] = Field(
        default_factory=lambda: {"pedalboards": []}
    )


class PedalboardCurrentResponse(BaseModel):
    success: bool = True
    data: PedalboardInfo


# Parameter Models
class ParameterValue(BaseModel):
    value: float = Field(..., description="Parameter value to set")


class ParameterInfo(BaseModel):
    symbol: str
    value: float
    minimum: float
    maximum: float
    unit: Optional[str] = None


class ParametersResponse(BaseModel):
    success: bool = True
    data: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {"parameters": {}}
    )


# Addressing Models
class AddressingRequest(BaseModel):
    uri: str
    label: str = Field(..., max_length=64)
    minimum: float
    maximum: float
    value: float
    steps: int = Field(default=33, ge=2, le=127)
    tempo: bool = False
    dividers: Optional[List[int]] = None
    page: Optional[int] = None
    subpage: Optional[int] = None
    coloured: Optional[bool] = None
    momentary: Optional[bool] = None
    operational_mode: str = Field(default="=", pattern="^[=<>]$")


# Connection Models
class ConnectionRequest(BaseModel):
    source: str = Field(..., description="Source port identifier")
    target: str = Field(..., description="Target port identifier")


# WebSocket Models
class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)


class ParameterChangeMessage(WebSocketMessage):
    type: str = "parameter_changed"
    data: Dict[str, Union[str, float]]  # instance_id, symbol, value


class PedalboardChangeMessage(WebSocketMessage):
    type: str = "pedalboard_changed"
    data: Dict[str, Any]  # action, plugin details, etc.


class HardwareEventMessage(WebSocketMessage):
    type: str = "hardware_event"
    data: Dict[str, Union[str, int]]  # event, footswitch_id, etc.


class StatusUpdateMessage(WebSocketMessage):
    type: str = "status_update"
    data: Dict[str, float]  # cpu_usage, memory_usage, etc.


# Hardware Models
class FootswitchInfo(BaseModel):
    id: int
    pressed: bool


class HardwareStatus(BaseModel):
    connected: bool
    firmware_version: Optional[str] = None
    temperature: Optional[float] = None
    footswitches: List[FootswitchInfo] = []


class HardwareStatusResponse(BaseModel):
    success: bool = True
    data: HardwareStatus


# Bank Models
class BankInfo(BaseModel):
    id: str
    name: str
    pedalboards: List[str] = []


class BankListResponse(BaseModel):
    success: bool = True
    data: Dict[str, List[BankInfo]] = Field(default_factory=lambda: {"banks": []})


class BankCreateRequest(BaseModel):
    name: str = Field(..., max_length=64)


class BankCreateResponse(BaseModel):
    success: bool = True
    data: Dict[str, str] = Field(default_factory=lambda: {"id": ""})


# Monitoring Models
class CpuInfo(BaseModel):
    usage_percent: float
    load_average: List[float] = Field(default_factory=list)


class MemoryInfo(BaseModel):
    total: int  # MB
    used: int  # MB
    free: int  # MB
    usage_percent: float


class AudioInfo(BaseModel):
    jack_running: bool
    sample_rate: int
    buffer_size: int
    latency: float  # ms


class MonitoringResponse(BaseModel):
    success: bool = True
    data: Union[CpuInfo, MemoryInfo, AudioInfo]


# Error Models
class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    code: str


# Generic Success Response
class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Dict[str, Any]] = None


# Favorites Models
class FavoriteRequest(BaseModel):
    uri: str = Field(..., description="Plugin URI to add/remove from favorites")


# Snapshot Models
class SnapshotInfo(BaseModel):
    id: int
    name: str
    timestamp: datetime


class SnapshotListResponse(BaseModel):
    success: bool = True
    data: Dict[str, List[SnapshotInfo]] = Field(
        default_factory=lambda: {"snapshots": []}
    )


class SnapshotSaveRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=64)


class SnapshotLoadRequest(BaseModel):
    id: int = Field(..., ge=0)
