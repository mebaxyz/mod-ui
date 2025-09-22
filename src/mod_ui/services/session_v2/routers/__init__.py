"""
Router modules for Session Service v2

This package contains all FastAPI router modules that provide
REST API endpoints for the modernized session service.

Available routers:
- pedalboard: Pedalboard and plugin management
- session: Session lifecycle and transport controls
- realtime: WebSocket connections and event streaming
"""

from .pedalboard import router as pedalboard_router
from .realtime import router as realtime_router
from .session import router as session_router

__all__ = ["pedalboard_router", "session_router", "realtime_router"]
