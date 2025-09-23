"""
Service Metrics and Monitoring

Metrics collection and monitoring utilities for service communication.
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class RequestMetrics:
    """Metrics for a single request"""

    request_id: str
    request_type: str
    service_name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "pending"
    error_message: Optional[str] = None

    @property
    def duration_ms(self) -> Optional[float]:
        """Request duration in milliseconds"""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def complete(self, status: str = "success", error_message: Optional[str] = None):
        """Mark request as completed"""
        self.end_time = time.time()
        self.status = status
        self.error_message = error_message


@dataclass
class ServiceMetrics:
    """Aggregated metrics for a service"""

    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = float("inf")
    max_response_time_ms: float = 0.0
    current_active_requests: int = 0
    last_request_time: Optional[datetime] = None

    # Recent response times for calculating moving average
    _recent_times: deque = field(default_factory=lambda: deque(maxlen=100))

    def add_request(self, duration_ms: float, success: bool = True):
        """Add a completed request to metrics"""
        self.total_requests += 1
        self.last_request_time = datetime.now()

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        # Update response time metrics
        self._recent_times.append(duration_ms)
        self.min_response_time_ms = min(self.min_response_time_ms, duration_ms)
        self.max_response_time_ms = max(self.max_response_time_ms, duration_ms)

        # Calculate moving average
        if self._recent_times:
            self.avg_response_time_ms = sum(self._recent_times) / len(
                self._recent_times
            )

    @property
    def success_rate(self) -> float:
        """Success rate as percentage"""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def error_rate(self) -> float:
        """Error rate as percentage"""
        return 100.0 - self.success_rate


class MetricsCollector:
    """Centralized metrics collection system"""

    def __init__(self):
        self.service_metrics: Dict[str, ServiceMetrics] = {}
        self.active_requests: Dict[str, RequestMetrics] = {}
        self.request_history: deque = deque(maxlen=1000)  # Keep last 1000 requests
        self.logger = logging.getLogger(__name__)

    def start_request(
        self, request_id: str, request_type: str, service_name: str
    ) -> RequestMetrics:
        """Start tracking a new request"""
        metrics = RequestMetrics(
            request_id=request_id,
            request_type=request_type,
            service_name=service_name,
            start_time=time.time(),
        )

        self.active_requests[request_id] = metrics

        # Update service metrics
        if service_name not in self.service_metrics:
            self.service_metrics[service_name] = ServiceMetrics(service_name)

        self.service_metrics[service_name].current_active_requests += 1

        return metrics

    def complete_request(
        self,
        request_id: str,
        status: str = "success",
        error_message: Optional[str] = None,
    ):
        """Complete tracking a request"""
        if request_id not in self.active_requests:
            self.logger.warning(f"Completing unknown request: {request_id}")
            return

        metrics = self.active_requests.pop(request_id)
        metrics.complete(status, error_message)

        # Update service metrics
        service_metrics = self.service_metrics[metrics.service_name]
        service_metrics.current_active_requests -= 1

        if metrics.duration_ms is not None:
            service_metrics.add_request(metrics.duration_ms, status == "success")

        # Add to history
        self.request_history.append(metrics)

        # Log slow requests
        if metrics.duration_ms and metrics.duration_ms > 1000:  # > 1 second
            self.logger.warning(
                f"Slow request: {request_id} took {metrics.duration_ms:.1f}ms"
            )

    def get_service_metrics(self, service_name: str) -> Optional[ServiceMetrics]:
        """Get metrics for a specific service"""
        return self.service_metrics.get(service_name)

    def get_all_metrics(self) -> Dict[str, ServiceMetrics]:
        """Get metrics for all services"""
        return self.service_metrics.copy()

    def get_system_summary(self) -> Dict[str, Any]:
        """Get overall system metrics summary"""
        total_requests = sum(m.total_requests for m in self.service_metrics.values())
        total_errors = sum(m.failed_requests for m in self.service_metrics.values())
        active_requests = sum(
            m.current_active_requests for m in self.service_metrics.values()
        )

        avg_response_times = [
            m.avg_response_time_ms
            for m in self.service_metrics.values()
            if m.avg_response_time_ms > 0
        ]
        system_avg_response = (
            sum(avg_response_times) / len(avg_response_times)
            if avg_response_times
            else 0
        )

        return {
            "total_services": len(self.service_metrics),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "active_requests": active_requests,
            "system_error_rate": (
                (total_errors / total_requests * 100) if total_requests > 0 else 0
            ),
            "system_avg_response_ms": system_avg_response,
            "uptime_info": {
                "oldest_request": min(
                    (
                        m.last_request_time
                        for m in self.service_metrics.values()
                        if m.last_request_time
                    ),
                    default=None,
                ),
                "newest_request": max(
                    (
                        m.last_request_time
                        for m in self.service_metrics.values()
                        if m.last_request_time
                    ),
                    default=None,
                ),
            },
        }

    def reset_metrics(self, service_name: Optional[str] = None):
        """Reset metrics for a service or all services"""
        if service_name:
            if service_name in self.service_metrics:
                self.service_metrics[service_name] = ServiceMetrics(service_name)
        else:
            self.service_metrics.clear()
            self.active_requests.clear()
            self.request_history.clear()


# Global metrics collector
metrics = MetricsCollector()


def track_request(request_id: str, request_type: str, service_name: str):
    """Decorator/context manager for tracking requests"""

    class RequestTracker:
        def __init__(self):
            self.metrics = None

        def __enter__(self):
            self.metrics = metrics.start_request(request_id, request_type, service_name)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                metrics.complete_request(request_id, "success")
            else:
                metrics.complete_request(request_id, "error", str(exc_val))

    return RequestTracker()
