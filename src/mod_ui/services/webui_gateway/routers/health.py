"""
Health and Monitoring API Router

Handles health checks and monitoring endpoints for the WebSocket Gateway.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Import global service instances (will be injected at runtime)
connection_manager = None
event_router = None
redis_subscriber = None


def inject_services(cm, er, rs):
    """Inject service instances for router use"""
    global connection_manager, event_router, redis_subscriber
    connection_manager = cm
    event_router = er
    redis_subscriber = rs


@router.get("/ping")
async def ping() -> Dict[str, Any]:
    """Health check endpoint"""
    return {"status": "ok", "service": "webui-gateway"}


@router.get("/status")
async def status() -> Dict[str, Any]:
    """Detailed service status"""
    global connection_manager, event_router, redis_subscriber

    status_info = {
        "service": "websocket-gateway",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }

    if connection_manager:
        stats = connection_manager.get_stats()
        status_info.update(
            {
                "total_connections": stats.total_connections,
                "active_connections": stats.active_connections,
                "total_messages_sent": stats.total_messages_sent,
                "total_messages_received": stats.total_messages_received,
            }
        )

    if event_router:
        router_stats = event_router.get_stats()
        status_info.update(
            {
                "events_processed": router_stats.events_processed,
                "active_subscriptions": router_stats.active_subscriptions,
            }
        )

    if redis_subscriber:
        status_info["redis_connected"] = redis_subscriber.is_connected()

    return status_info


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check health of WebSocket gateway services"""
    global connection_manager, event_router, redis_subscriber

    try:
        health_info = {
            "success": True,
            "health": "healthy",
            "services": {},
            "timestamp": datetime.now().isoformat(),
        }

        if connection_manager:
            stats = connection_manager.get_stats()
            health_info["services"]["connection_manager"] = "healthy"
            health_info["connected_clients"] = stats.active_connections
        else:
            health_info["services"]["connection_manager"] = "unavailable"

        if event_router:
            health_info["services"]["event_router"] = "healthy"
        else:
            health_info["services"]["event_router"] = "unavailable"

        if redis_subscriber:
            health_info["services"]["redis_subscriber"] = (
                "healthy" if redis_subscriber.is_connected() else "disconnected"
            )
        else:
            health_info["services"]["redis_subscriber"] = "unavailable"

        return health_info

    except Exception as e:
        return {
            "success": False,
            "health": "unhealthy",
            "error": str(e),
            "services": {
                "connection_manager": "unknown",
                "event_router": "unknown",
                "redis_subscriber": "unknown",
            },
        }
