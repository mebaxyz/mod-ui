"""
Metrics collection and monitoring functionality
"""
import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import redis.asyncio as redis

from .models import RequestMetrics, ServiceHealth
from .config import get_config


class MetricsCollector:
    """Collects and aggregates metrics from microservices"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.config = get_config()
        self._redis = redis_client
        self._connection_pool = None
        self._metrics_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._aggregated_metrics: Dict[str, Dict[str, Any]] = {}
        self._is_collecting = False
        self._background_tasks: Set[asyncio.Task] = set()
        
    async def get_redis(self) -> redis.Redis:
        """Get Redis connection with connection pooling"""
        if self._redis is None:
            if self.config.enable_connection_pooling and self._connection_pool is None:
                self._connection_pool = redis.ConnectionPool.from_url(
                    self.config.redis_url,
                    max_connections=self.config.redis_max_connections,
                    socket_keepalive=self.config.redis_socket_keepalive,
                    socket_keepalive_options=self.config.redis_socket_keepalive_options
                )
                self._redis = redis.Redis(connection_pool=self._connection_pool)
            else:
                self._redis = redis.Redis.from_url(self.config.redis_url)
        return self._redis

    async def record_request_metric(self, metric: RequestMetrics) -> None:
        """Record a request metric"""
        if not self.config.enable_metrics:
            return
        
        service_key = f"{metric.source_service}->{metric.target_service}"
        self._metrics_buffer[service_key].append(metric)
        
        # Also store in Redis for persistence
        redis_client = await self.get_redis()
        metric_key = f"metrics:request:{metric.request_id}"
        await redis_client.setex(
            metric_key,
            self.config.metrics_retention_seconds,
            metric.json()
        )

    async def get_service_metrics(
        self, 
        service_name: str,
        time_range_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get metrics for a specific service"""
        time_range = time_range_seconds or self.config.metrics_retention_seconds
        cutoff_time = datetime.utcnow() - timedelta(seconds=time_range)
        
        # Collect metrics from buffer
        service_metrics = []
        for key, metrics in self._metrics_buffer.items():
            if service_name in key:
                for metric in metrics:
                    if metric.timestamp >= cutoff_time:
                        service_metrics.append(metric)
        
        return self._aggregate_metrics(service_metrics)

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        all_metrics = []
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.config.metrics_retention_seconds)
        
        for metrics in self._metrics_buffer.values():
            for metric in metrics:
                if metric.timestamp >= cutoff_time:
                    all_metrics.append(metric)
        
        system_stats = self._aggregate_metrics(all_metrics)
        
        # Add per-service breakdown
        service_breakdown = {}
        for metric in all_metrics:
            service = metric.target_service
            if service not in service_breakdown:
                service_breakdown[service] = []
            service_breakdown[service].append(metric)
        
        system_stats["services"] = {
            service: self._aggregate_metrics(metrics)
            for service, metrics in service_breakdown.items()
        }
        
        return system_stats

    def _aggregate_metrics(self, metrics: List[RequestMetrics]) -> Dict[str, Any]:
        """Aggregate a list of metrics"""
        if not metrics:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "success_rate": 0.0,
                "avg_response_time": 0.0,
                "min_response_time": 0.0,
                "max_response_time": 0.0,
                "p95_response_time": 0.0,
                "total_attempts": 0,
                "avg_attempts": 0.0,
                "request_types": {}
            }
        
        response_times = [m.response_time_seconds for m in metrics]
        successful = [m for m in metrics if m.success]
        failed = [m for m in metrics if not m.success]
        
        # Calculate percentiles
        response_times.sort()
        p95_index = int(0.95 * len(response_times))
        p95_response_time = response_times[p95_index] if response_times else 0.0
        
        # Request type breakdown
        request_types = defaultdict(lambda: {"count": 0, "success": 0, "avg_time": 0.0})
        for metric in metrics:
            rt = request_types[metric.request_type]
            rt["count"] += 1
            if metric.success:
                rt["success"] += 1
            rt["avg_time"] = (rt["avg_time"] * (rt["count"] - 1) + metric.response_time_seconds) / rt["count"]
        
        return {
            "total_requests": len(metrics),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "success_rate": len(successful) / len(metrics),
            "avg_response_time": sum(response_times) / len(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "p95_response_time": p95_response_time,
            "total_attempts": sum(m.attempts for m in metrics),
            "avg_attempts": sum(m.attempts for m in metrics) / len(metrics),
            "request_types": dict(request_types)
        }

    async def start_collecting(self) -> None:
        """Start background metrics collection"""
        if self._is_collecting:
            return
        
        self._is_collecting = True
        
        # Start metrics aggregation task
        task = asyncio.create_task(self._aggregation_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        # Start cleanup task
        task = asyncio.create_task(self._cleanup_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def stop_collecting(self) -> None:
        """Stop background metrics collection"""
        self._is_collecting = False
        
        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

    async def _aggregation_loop(self) -> None:
        """Background loop to aggregate metrics"""
        while self._is_collecting:
            try:
                # Aggregate metrics every minute
                await asyncio.sleep(60)
                
                # Aggregate and store metrics
                system_metrics = await self.get_system_metrics()
                
                # Store aggregated metrics in Redis
                redis_client = await self.get_redis()
                timestamp = int(time.time())
                metrics_key = f"metrics:aggregated:{timestamp}"
                await redis_client.setex(
                    metrics_key,
                    self.config.metrics_retention_seconds,
                    json.dumps(system_metrics)
                )
                
            except Exception as e:
                # Continue on error
                await asyncio.sleep(10)

    async def _cleanup_loop(self) -> None:
        """Background loop to clean up old metrics"""
        while self._is_collecting:
            try:
                # Clean up every 10 minutes
                await asyncio.sleep(600)
                
                # Clean up old Redis metrics
                redis_client = await self.get_redis()
                
                # Clean up request metrics
                pattern = "metrics:request:*"
                keys = await redis_client.keys(pattern)
                for key in keys:
                    ttl = await redis_client.ttl(key)
                    if ttl <= 0:
                        await redis_client.delete(key)
                
                # Clean up aggregated metrics
                pattern = "metrics:aggregated:*"
                keys = await redis_client.keys(pattern)
                cutoff_time = int(time.time()) - self.config.metrics_retention_seconds
                
                for key in keys:
                    try:
                        timestamp = int(key.split(":")[-1])
                        if timestamp < cutoff_time:
                            await redis_client.delete(key)
                    except (ValueError, IndexError):
                        # Invalid key format, delete it
                        await redis_client.delete(key)
                
            except Exception as e:
                await asyncio.sleep(60)

    async def export_metrics(
        self,
        format_type: str = "json",
        time_range_seconds: Optional[int] = None
    ) -> str:
        """
        Export metrics in various formats
        
        Args:
            format_type: Export format ("json", "prometheus", "csv")
            time_range_seconds: Time range to export
            
        Returns:
            Formatted metrics data
        """
        system_metrics = await self.get_system_metrics()
        
        if format_type == "json":
            return json.dumps(system_metrics, indent=2, default=str)
        elif format_type == "prometheus":
            return self._to_prometheus_format(system_metrics)
        elif format_type == "csv":
            return self._to_csv_format(system_metrics)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _to_prometheus_format(self, metrics: Dict[str, Any]) -> str:
        """Convert metrics to Prometheus format"""
        lines = []
        
        # System-level metrics
        lines.append(f"microservice_total_requests {metrics['total_requests']}")
        lines.append(f"microservice_successful_requests {metrics['successful_requests']}")
        lines.append(f"microservice_failed_requests {metrics['failed_requests']}")
        lines.append(f"microservice_success_rate {metrics['success_rate']}")
        lines.append(f"microservice_avg_response_time {metrics['avg_response_time']}")
        lines.append(f"microservice_p95_response_time {metrics['p95_response_time']}")
        
        # Per-service metrics
        for service_name, service_metrics in metrics.get("services", {}).items():
            service_label = f'service="{service_name}"'
            lines.append(f"microservice_service_requests{{{service_label}}} {service_metrics['total_requests']}")
            lines.append(f"microservice_service_success_rate{{{service_label}}} {service_metrics['success_rate']}")
            lines.append(f"microservice_service_avg_response_time{{{service_label}}} {service_metrics['avg_response_time']}")
        
        return "\n".join(lines)

    def _to_csv_format(self, metrics: Dict[str, Any]) -> str:
        """Convert metrics to CSV format"""
        lines = ["service,total_requests,successful_requests,failed_requests,success_rate,avg_response_time,p95_response_time"]
        
        # System-wide row
        lines.append(f"SYSTEM,{metrics['total_requests']},{metrics['successful_requests']},{metrics['failed_requests']},{metrics['success_rate']:.3f},{metrics['avg_response_time']:.3f},{metrics['p95_response_time']:.3f}")
        
        # Per-service rows
        for service_name, service_metrics in metrics.get("services", {}).items():
            lines.append(f"{service_name},{service_metrics['total_requests']},{service_metrics['successful_requests']},{service_metrics['failed_requests']},{service_metrics['success_rate']:.3f},{service_metrics['avg_response_time']:.3f},{service_metrics['p95_response_time']:.3f}")
        
        return "\n".join(lines)

    async def close(self) -> None:
        """Close metrics collector and clean up"""
        await self.stop_collecting()
        
        if self._redis:
            await self._redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()


class HealthMonitor:
    """Monitor service health and availability"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.config = get_config()
        self._redis = redis_client
        self._connection_pool = None
        self._health_history: Dict[str, List[ServiceHealth]] = defaultdict(list)
        self._is_monitoring = False
        
    async def get_redis(self) -> redis.Redis:
        """Get Redis connection"""
        if self._redis is None:
            if self.config.enable_connection_pooling and self._connection_pool is None:
                self._connection_pool = redis.ConnectionPool.from_url(
                    self.config.redis_url,
                    max_connections=self.config.redis_max_connections
                )
                self._redis = redis.Redis(connection_pool=self._connection_pool)
            else:
                self._redis = redis.Redis.from_url(self.config.redis_url)
        return self._redis

    async def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all services"""
        redis_client = await self.get_redis()
        
        # Get all service registrations
        pattern = "service_registry:*"
        keys = await redis_client.keys(pattern)
        
        services = {}
        healthy_count = 0
        unhealthy_count = 0
        
        for key in keys:
            try:
                data = await redis_client.get(key)
                if data:
                    registration_data = json.loads(data)
                    health = ServiceHealth.parse_obj(registration_data["health"])
                    service_name = registration_data["service_name"]
                    
                    services[service_name] = health
                    
                    if health.status == "healthy":
                        healthy_count += 1
                    else:
                        unhealthy_count += 1
                        
            except Exception:
                continue
        
        return {
            "total_services": len(services),
            "healthy_services": healthy_count,
            "unhealthy_services": unhealthy_count,
            "services": services
        }

    async def get_service_health_history(
        self,
        service_name: str,
        hours: int = 24
    ) -> List[ServiceHealth]:
        """Get health history for a specific service"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        history = self._health_history.get(service_name, [])
        return [h for h in history if h.timestamp >= cutoff_time]

    async def close(self) -> None:
        """Close health monitor"""
        if self._redis:
            await self._redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()