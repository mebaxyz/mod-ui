"""
MOD UI FastAPI Application

Modern FastAPI-based implementation of the MOD UI web interface.
This replaces the legacy Tornado-based webserver with a modern async framework.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import legacy MOD components
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from mod.session import SESSION
from mod.settings import (
    HTML_DIR, DEVICE_WEBSERVER_PORT, LOG, DESKTOP,
    FAVORITES_JSON_FILE, DEFAULT_PEDALBOARD, IMAGE_VERSION
)
from mod import check_environment, safe_json_load
from modtools.utils import (
    init as lv2_init, get_plugin_list, get_all_plugins,
    get_plugin_info, get_non_cached_plugin_info
)

# Configure logging
logging.basicConfig(level=(logging.DEBUG if LOG else logging.WARNING))
logger = logging.getLogger(__name__)

# Global state
class AppState:
    def __init__(self):
        self.favorites: List[str] = []
        self.websocket_clients: List[WebSocket] = []

app_state = AppState()

# Create FastAPI application
app = FastAPI(
    title="MOD UI API",
    description="Modern FastAPI-based MOD UI web interface",
    version=IMAGE_VERSION or "1.0.0",
    debug=bool(LOG >= 2)
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DESKTOP else ["http://localhost:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory=HTML_DIR)
app.mount("/static", StaticFiles(directory=HTML_DIR), name="static")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        app_state.websocket_clients.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in app_state.websocket_clients:
            app_state.websocket_clients.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    logger.info("Starting MOD UI FastAPI application")
    
    # Initialize environment and LV2
    check_environment()
    lv2_init()
    
    # Load favorites
    app_state.favorites = safe_json_load(FAVORITES_JSON_FILE, list)
    
    # Clean up invalid favorites
    if len(app_state.favorites) > 0:
        uris = get_plugin_list()
        app_state.favorites = [uri for uri in app_state.favorites if uri in uris]
    
    logger.info("MOD UI FastAPI application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down MOD UI FastAPI application")
    
    # Close all WebSocket connections
    for websocket in manager.active_connections[:]:
        try:
            await websocket.send_text("stop")
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")
    
    # End session
    SESSION.signal_disconnect()
    logger.info("MOD UI FastAPI application shutdown complete")

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main index page"""
    # This is a simplified version - full template rendering will be implemented later
    return HTMLResponse(content="<h1>MOD UI FastAPI</h1><p>Migration in progress...</p>")

# System Information
@app.get("/system/info")
async def get_system_info():
    """Get system information and status"""
    return JSONResponse({
        "success": True,
        "data": {
            "version": IMAGE_VERSION or "1.0.0",
            "hardware": "MOD Duo",
            "uptime": 3600,  # TODO: Get actual uptime
            "framework": "FastAPI",
            "migration_status": "in_progress"
        }
    })

# Plugin Management
@app.get("/effect/list")
async def get_plugin_list_endpoint():
    """List all available plugins"""
    try:
        plugins = get_plugin_list()
        return JSONResponse({
            "success": True,
            "data": {"plugins": plugins}
        })
    except Exception as e:
        logger.error(f"Error getting plugin list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/effect/get")
async def get_plugin_info_endpoint(uri: str):
    """Get information about a specific plugin"""
    try:
        plugin_data = get_plugin_info(uri)
        return JSONResponse({
            "success": True,
            "data": plugin_data
        })
    except Exception as e:
        logger.error(f"Error getting plugin info for {uri}: {e}")
        raise HTTPException(status_code=404, detail=f"Plugin not found: {uri}")

# Favorites Management
@app.post("/favorites/add")
async def add_favorite(uri: str):
    """Add a plugin to favorites"""
    if uri not in app_state.favorites:
        app_state.favorites.append(uri)
        # TODO: Save to favorites file
    return JSONResponse({"success": True, "message": "Added to favorites"})

@app.post("/favorites/remove")
async def remove_favorite(uri: str):
    """Remove a plugin from favorites"""
    if uri in app_state.favorites:
        app_state.favorites.remove(uri)
        # TODO: Save to favorites file
    return JSONResponse({"success": True, "message": "Removed from favorites"})

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    
    # Notify session about WebSocket connection
    await SESSION.websocket_opened(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"WebSocket received: {data}")
            
            # Echo for now - full message handling will be implemented later
            await manager.send_personal_message(f"Echo: {data}", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await SESSION.websocket_closed(websocket)
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Health check endpoint
@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return JSONResponse({
        "success": True,
        "data": {
            "ihm_online": True,
            "ihm_time": 1,
            "timestamp": datetime.now().isoformat()
        }
    })

# Hello endpoint (for remote monitoring)
@app.get("/hello")
async def hello():
    """Remote monitoring endpoint"""
    return JSONResponse({
        "online": len(manager.active_connections) > 0,
        "version": IMAGE_VERSION or "1.0.0",
        "framework": "FastAPI"
    })

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    port = int(os.environ.get("MOD_PORT", DEVICE_WEBSERVER_PORT))
    host = os.environ.get("MOD_HOST", "127.0.0.1" if DESKTOP else "0.0.0.0")
    debug = bool(os.environ.get("MOD_DEBUG", LOG))
    
    logger.info(f"Starting MOD UI FastAPI server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info"
    )