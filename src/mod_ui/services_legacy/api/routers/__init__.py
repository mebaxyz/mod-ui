"""
API Routers Package

This package contains modular FastAPI routers organized by functionality.
Each router handles a specific domain of the MOD UI API.
"""

from .data import router as data_router
from .effects import router as effects_router
from .pages import router as pages_router
from .static import router as static_router
from .system import router as system_router

__all__ = [
    "effects_router",
    "system_router",
    "pages_router",
    "static_router",
    "data_router",
]
