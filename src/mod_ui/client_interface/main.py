"""
MOD UI - Client Interface Service

Simplified client interface that communicates directly with the session_manager service via ZeroMQ.
Provides essential API endpoints for audio processing functionality.
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .zmq_client import ZMQClient

# Configuration
SERVICE_NAME = "client_interface"
SERVICE_PORT = int(os.getenv("CLIENT_INTERFACE_PORT", "8080"))
HTML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../static"))

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id:
            self.user_connections[user_id] = websocket
        logger.info(
            f"WebSocket connected: {len(self.active_connections)} active connections"
        )

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # Remove from user connections if present
        for user_id, user_ws in list(self.user_connections.items()):
            if user_ws == websocket:
                del self.user_connections[user_id]
                break
        logger.info(
            f"WebSocket disconnected: {len(self.active_connections)} active connections"
        )

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user"""
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                await self.disconnect(self.user_connections[user_id])


# Request/Response Models
class PluginRequest(BaseModel):
    uri: str
    x: float = 0.0
    y: float = 0.0


class ParameterUpdate(BaseModel):
    instance_id: str
    port: str
    value: float


class PedalboardRequest(BaseModel):
    name: str
    description: Optional[str] = ""


# Global instances
connection_manager = ConnectionManager()
zmq_client: Optional[ZMQClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global zmq_client

    # Startup
    logger.info(f"Starting {SERVICE_NAME} service on port {SERVICE_PORT}")

    # Initialize ZMQ client
    zmq_client = ZMQClient(SERVICE_NAME)
    await zmq_client.start()

    logger.info("ZMQ client started")
    logger.info(f"{SERVICE_NAME} service started successfully")

    try:
        yield
    finally:
        # Cleanup
        logger.info(f"Shutting down {SERVICE_NAME} service")

        # Stop ZMQ client
        if zmq_client:
            await zmq_client.stop()

        logger.info(f"{SERVICE_NAME} service stopped")


# Create FastAPI application
app = FastAPI(
    title="MOD UI Client Interface",
    description="Web client interface for MOD UI audio processing",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
if os.path.exists(HTML_DIR):
    app.mount("/static", StaticFiles(directory=HTML_DIR), name="static")
    logger.info(f"Serving static files from {HTML_DIR}")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": SERVICE_NAME,
        "status": "healthy",
        "details": {
            "active_connections": len(connection_manager.active_connections),
            "zmq_client_connected": (
                zmq_client.is_connected() if zmq_client else False
            ),
        },
    }


# Session Manager API Endpoints
@app.get("/api/plugins/available")
async def get_available_plugins():
    """Get available plugins"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")

    try:
        result = await zmq_client.call("session_manager", "get_available_plugins", timeout=10.0)
        if result and result.get("success"):
            return {"plugins": result.get("plugins", [])}
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get plugins"))
    except Exception as e:
        logger.error(f"Error getting available plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plugins")
async def load_plugin(plugin: PluginRequest):
    """Load a plugin"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")

    try:
        result = await zmq_client.call("session_manager", "load_plugin", uri=plugin.uri, timeout=10.0)
        if result and result.get("success"):
            # Broadcast to WebSocket clients
            await connection_manager.broadcast({
                "event": "plugin_loaded",
                "data": {
                    "instance_id": result.get("instance_id"),
                    "uri": plugin.uri,
                    "x": plugin.x,
                    "y": plugin.y
                }
            })
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to load plugin"))
    except Exception as e:
        logger.error(f"Error loading plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/plugins/{instance_id}")
async def unload_plugin(instance_id: str):
    """Unload a plugin"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")

    try:
        result = await zmq_client.call("session_manager", "unload_plugin", instance_id=instance_id, timeout=10.0)
        if result and result.get("success"):
            # Broadcast to WebSocket clients
            await connection_manager.broadcast({
                "event": "plugin_unloaded",
                "data": {"instance_id": instance_id}
            })
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to unload plugin"))
    except Exception as e:
        logger.error(f"Error unloading plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/plugins/parameters")
async def update_parameter(param_update: ParameterUpdate):
    """Update plugin parameter"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")

    try:
        result = await zmq_client.call(
            "session_manager", 
            "set_parameter",
            instance_id=param_update.instance_id,
            port=param_update.port,
            value=param_update.value,
            timeout=5.0
        )
        if result and result.get("success"):
            # Broadcast to WebSocket clients
            await connection_manager.broadcast({
                "event": "parameter_changed",
                "data": {
                    "instance_id": param_update.instance_id,
                    "port": param_update.port,
                    "value": param_update.value
                }
            })
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to update parameter"))
    except Exception as e:
        logger.error(f"Error updating parameter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pedalboards")
async def create_pedalboard(pedalboard: PedalboardRequest):
    """Create new pedalboard"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")

    try:
        result = await zmq_client.call(
            "session_manager",
            "create_pedalboard", 
            name=pedalboard.name,
            timeout=10.0
        )
        if result and result.get("success"):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to create pedalboard"))
    except Exception as e:
        logger.error(f"Error creating pedalboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pedalboards/current")
async def get_current_pedalboard():
    """Get current pedalboard"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")

    try:
        result = await zmq_client.call("session_manager", "get_current_pedalboard", timeout=5.0)
        if result and result.get("success"):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get current pedalboard"))
    except Exception as e:
        logger.error(f"Error getting current pedalboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/health")
async def get_session_health():
    """Get session manager health status"""
    if not zmq_client:
        raise HTTPException(status_code=503, detail="ZMQ client not available")

    try:
        result = await zmq_client.call("session_manager", "health_check", timeout=5.0)
        return result
    except Exception as e:
        logger.error(f"Error getting session health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: Optional[str] = None):
    """WebSocket endpoint for real-time communication"""
    await connection_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_json()
            
            # Echo back for now (can be extended for specific message handling)
            await websocket.send_json({
                "event": "echo",
                "data": data,
                "timestamp": asyncio.get_event_loop().time()
            })
            
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await connection_manager.disconnect(websocket)


# Root endpoint to serve main page
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve main page"""
    index_path = os.path.join(HTML_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return f.read()
    return """
    <html>
        <head><title>MOD UI</title></head>
        <body>
            <h1>MOD UI Client Interface</h1>
            <p>Status: <span id="status">Connecting...</span></p>
            <script>
                const ws = new WebSocket('ws://localhost:8080/ws');
                ws.onopen = () => document.getElementById('status').textContent = 'Connected';
                ws.onclose = () => document.getElementById('status').textContent = 'Disconnected';
                ws.onerror = () => document.getElementById('status').textContent = 'Error';
            </script>
        </body>
    </html>
    """


def main():
    """Main entry point"""
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()