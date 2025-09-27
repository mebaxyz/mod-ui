"""
Proposed flexible service communication models
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field, validator


class ResponseStatus(str, Enum):
    """Response status codes"""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SERVICE_UNAVAILABLE = "service_unavailable"


class FlexibleServiceRequest(BaseModel):
    """Flexible service request model with dynamic request types"""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_type: str  # Now accepts any string instead of enum
    service_name: str  # Target service name
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    source_service: str = "unknown"
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timeout: Optional[float] = None  # Per-request timeout override
    priority: int = Field(default=0)  # Message priority (higher = more important)

    @validator("request_type")
    def request_type_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("request_type cannot be empty")
        return v.strip()


class FlexibleServiceResponse(BaseModel):
    """Flexible service response model"""

    request_id: str
    correlation_id: str
    status: ResponseStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    error_code: Optional[str] = None  # Structured error codes
    timestamp: datetime = Field(default_factory=datetime.now)
    processing_time_ms: Optional[float] = None
    service_name: str  # Which service handled this

    @property
    def success(self) -> bool:
        """Check if the response indicates success"""
        return self.status == ResponseStatus.SUCCESS


# Service discovery and registration
class ServiceCapability(BaseModel):
    """Describes what a service can do"""

    request_type: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    timeout_estimate: Optional[float] = None


class ServiceRegistration(BaseModel):
    """Service registration info"""

    service_name: str
    capabilities: List[ServiceCapability]
    health_check_endpoint: Optional[str] = None
    version: str = "1.0.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Event-based communication (pub/sub without request/response)
class ServiceEvent(BaseModel):
    """Event-based message for pub/sub"""

    event_type: str
    service_name: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
