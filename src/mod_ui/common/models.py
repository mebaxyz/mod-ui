"""
Service Communication Models

Pydantic models for inter-service communication using request-response patterns.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class RequestType(str, Enum):
    """Types of service requests"""

    GET_SYSTEM_INFO = "get_system_info"
    GET_SYSTEM_STATS = "get_system_stats"
    GET_HARDWARE_STATUS = "get_hardware_status"
    LOAD_PEDALBOARD = "load_pedalboard"
    SAVE_PEDALBOARD = "save_pedalboard"
    GET_PLUGIN_INFO = "get_plugin_info"
    EXECUTE_COMMAND = "execute_command"
    GET_SESSION_STATE = "get_session_state"
    UPDATE_SESSION_STATE = "update_session_state"
    GET_AUDIO_STATUS = "get_audio_status"
    CONTROL_TRANSPORT = "control_transport"
    # Session service specific requests
    GET_SESSION_STATUS = "get_session_status"
    SET_SESSION_TEMPO = "set_session_tempo"
    GET_SESSION_STATS = "get_session_stats"


class ResponseStatus(str, Enum):
    """Response status codes"""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SERVICE_UNAVAILABLE = "service_unavailable"


class ServiceRequest(BaseModel):
    """Generic service request model"""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_type: RequestType
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    source_service: str
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    class Config:
        use_enum_values = True


class ServiceResponse(BaseModel):
    """Generic service response model"""

    request_id: str
    correlation_id: str
    status: ResponseStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    processing_time_ms: Optional[float] = None

    class Config:
        use_enum_values = True


class ServiceConfig(BaseModel):
    """Configuration for a backend service"""

    service_name: str
    request_channel: str
    response_timeout: float = 5.0
    retry_attempts: int = 1
    enabled: bool = True
