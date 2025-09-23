"""
WebSocket Gateway Routers

This package contains all the API routers for the WebSocket Gateway service.
"""

from .banks import router as banks_router
from .effects import router as effects_router
from .favorites import router as favorites_router
from .lv2 import router as lv2_router
from .pedalboard import router as pedalboard_router
from .snapshots import router as snapshots_router
from .system import router as system_router
from .updates import router as updates_router
from .utilities import router as utilities_router

__all__ = [
    "effects_router",
    "favorites_router",
    "snapshots_router",
    "pedalboard_router",
    "banks_router",
    "system_router",
    "updates_router",
    "utilities_router",
    "lv2_router",
]
