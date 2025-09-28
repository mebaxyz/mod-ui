"""
MOD UI FastAPI Application - Modular Architecture

Modern FastAPI-based implementation of the MOD UI web interface.
This replaces the legacy Tornado-based webserver with a modern async framework.
"""

import logging
import os
import sys
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# Import modular routers
from .routers import (
    data_router,
    effects_router,
    pages_router,
    static_router,
    system_router,
)
from .routers.static import get_static_mounts

# Configuration
HTML_DIR = os.environ.get("MOD_HTML_DIR", "/app/html")
DEVICE_WEBSERVER_PORT = int(os.environ.get("MOD_PORT", 8888))
LOG = int(os.environ.get("MOD_LOG", 1))

# Configure logging
logging.basicConfig(level=(logging.DEBUG if LOG else logging.WARNING))
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="MOD UI API",
    description="Modern FastAPI-based MOD UI web interface",
    version=os.environ.get("MOD_VERSION", "1.0.0"),
    docs_url="/docs" if LOG else None,  # Only show docs in debug mode
    redoc_url="/redoc" if LOG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static file mounts
for mount_path, directory, name in get_static_mounts():
    if os.path.exists(directory):
        app.mount(mount_path, StaticFiles(directory=directory), name=name)
        logger.info(f"Mounted static files: {mount_path} -> {directory}")
    else:
        logger.warning(f"Static directory not found: {directory}")

# Register all routers
app.include_router(effects_router, prefix="", tags=["effects"])
app.include_router(system_router, prefix="", tags=["system"])
app.include_router(pages_router, prefix="", tags=["pages"])
app.include_router(static_router, prefix="", tags=["static"])
app.include_router(data_router, prefix="", tags=["data"])

logger.info("FastAPI application initialized with modular architecture")
logger.info(f"Active routers: effects, system, pages, static, data")
logger.info(f"HTML directory: {HTML_DIR}")
logger.info(f"Server port: {DEVICE_WEBSERVER_PORT}")

# Optional: Import and check for session availability
try:
    from mod_ui.utils.mod_legacy.session import SESSION
except ImportError:
    SESSION = None

# Optional: Load LV2 plugins
try:
    from mod_ui.utils.modtools.utils import get_plugin_info, get_plugin_list

    # Initialize plugin information
    logger.info("Loading LV2 plugins...")
    plugin_list = get_plugin_list()
    logger.info(f"✅ Loaded {len(plugin_list)} LV2 plugins")

    # Store plugins for use by routers
    app.state.plugins = plugin_list
    app.state.get_plugin_info = get_plugin_info

except ImportError as e:
    logger.warning(f"⚠️ Plugin utilities not available: {e}")
    app.state.plugins = []
    app.state.get_plugin_info = None
except Exception as e:
    logger.error(f"❌ Error loading plugins: {e}")
    app.state.plugins = []
    app.state.get_plugin_info = None

# Store global state for routers
app.state.html_dir = HTML_DIR
app.state.session_available = True  # Session service v2 is available


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 MOD UI FastAPI application started")
    logger.info("📡 WebSocket functionality handled by Session Service v2")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("🛑 MOD UI FastAPI application shutting down")
    logger.info("📡 WebSocket connections handled by Session Service v2")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=DEVICE_WEBSERVER_PORT,
        log_level="debug" if LOG else "warning",
        reload=bool(LOG),  # Enable reload in debug mode
    )
