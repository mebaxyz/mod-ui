"""
Core data models for microservice communication
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ResponseStatus(str, Enum):
    """Response status codes"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RATE_LIMITED = "rate_limited"


class ServiceRequest(BaseModel):
    """Flexible service request model with dynamic request types"""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_type: str  # Dynamic - accepts any string
    service_name: str  # Target service name
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    source_service: str = "unknown"
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timeout: Optional[float] = None  # Per-request timeout override
    priority: int = Field(default=0)  # Message priority (higher = more important)
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Extra context
    
    @validator('request_type')
    def request_type_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('request_type cannot be empty')
        return v.strip()

    @validator('service_name')
    def service_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('service_name cannot be empty')
        return v.strip()


class ServiceResponse(BaseModel):
    """Flexible service response model"""

    request_id: str
    correlation_id: str
    status: ResponseStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    error_code: Optional[str] = None  # Structured error codes like "PLUGIN_NOT_FOUND"
    timestamp: datetime = Field(default_factory=datetime.now)
    processing_time_ms: Optional[float] = None
    service_name: str  # Which service handled this
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        """Check if the response indicates success"""
        return self.status == ResponseStatus.SUCCESS

    @property
    def failed(self) -> bool:
        """Check if the response indicates failure"""
        return not self.success


class ServiceEvent(BaseModel):
    """Event-based message for pub/sub without request/response"""
    
    event_type: str
    service_name: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)  # For filtering/routing
    
    @validator('event_type')
    def event_type_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('event_type cannot be empty')
        return v.strip()


class ServiceCapability(BaseModel):
    """Describes what a service can do"""
    
    request_type: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None  # JSON schema for validation
    output_schema: Optional[Dict[str, Any]] = None  # JSON schema for validation
    timeout_estimate: Optional[float] = None  # Expected response time in seconds
    rate_limit: Optional[int] = None  # Max requests per minute
    tags: List[str] = Field(default_factory=list)  # For categorization
    examples: List[Dict[str, Any]] = Field(default_factory=list)  # Usage examples


class ServiceRegistration(BaseModel):
    """Service registration information for service discovery"""
    
    service_name: str
    capabilities: List[ServiceCapability]
    health_check_endpoint: Optional[str] = None
    version: str = "1.0.0"
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    endpoints: Dict[str, str] = Field(default_factory=dict)  # HTTP endpoints if any


class ServiceHealth(BaseModel):
    """Service health check response"""
    
    service_name: str
    status: str  # "healthy", "unhealthy", "degraded"
    checks: Dict[str, Any] = Field(default_factory=dict)  # Individual health checks
    last_updated: datetime = Field(default_factory=datetime.now)
    uptime_seconds: Optional[float] = None
    version: Optional[str] = None


class RequestMetrics(BaseModel):
    """Metrics for a specific request/response"""
    
    service_name: str
    request_type: str
    duration_ms: float
    success: bool
    timestamp: datetime = Field(default_factory=datetime.now)
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)