"""
MOD UI - Client Interface Service

Consolidated service handling all web client interactions, API endpoints, and WebSocket communication.
This service replaces the individual webui_gateway and api services.
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ...common.resilient_service_bus import ResilientServiceBus
from ...common.models import ServiceHealth, ServiceStatus


# Configuration
SERVICE_NAME = "client_interface"
SERVICE_PORT = int(os.getenv("CLIENT_INTERFACE_PORT", "8080"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
HTML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../html"))

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
        logger.info(f"WebSocket connected: {len(self.active_connections)} active connections")
    
    def disconnect(self, websocket: WebSocket, user_id: Optional[str] = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]
        logger.info(f"WebSocket disconnected: {len(self.active_connections)} active connections")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def send_to_user(self, message: str, user_id: str):
        if user_id in self.user_connections:
            await self.send_personal_message(message, self.user_connections[user_id])
    
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.active_connections.remove(conn)


# Request/Response Models
class PedalboardRequest(BaseModel):
    name: str
    description: Optional[str] = None
    plugins: List[Dict[str, Any]] = []


class PluginRequest(BaseModel):
    uri: str
    x: float
    y: float
    parameters: Optional[Dict[str, float]] = None


class ParameterUpdate(BaseModel):
    plugin_instance: str
    parameter: str
    value: float


# Global instances
connection_manager = ConnectionManager()
service_bus: Optional[ResilientServiceBus] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global service_bus
    
    # Startup
    logger.info(f"Starting {SERVICE_NAME} service on port {SERVICE_PORT}")
    
    # Initialize service bus
    service_bus = ResilientServiceBus(SERVICE_NAME, REDIS_URL)
    await service_bus.start()
    
    # Register service endpoints
    await service_bus.register_service(SERVICE_NAME, f"http://localhost:{SERVICE_PORT}")
    
    # Start background tasks
    asyncio.create_task(status_broadcaster())
    asyncio.create_task(service_health_monitor())
    
    logger.info(f"{SERVICE_NAME} service started successfully")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {SERVICE_NAME} service")
    if service_bus:
        await service_bus.stop()


# Create FastAPI app
app = FastAPI(
    title="MOD UI - Client Interface Service",
    description="Handles all web client interactions, API endpoints, and WebSocket communication",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
if os.path.exists(HTML_DIR):
    app.mount("/static", StaticFiles(directory=HTML_DIR), name="static")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return ServiceHealth(
        service=SERVICE_NAME,
        status=ServiceStatus.HEALTHY,
        details={
            "active_connections": len(connection_manager.active_connections),
            "service_bus_connected": service_bus.is_connected() if service_bus else False
        }
    )


# Main UI endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main UI"""
    html_file = os.path.join(HTML_DIR, "index.html")
    if os.path.exists(html_file):
        with open(html_file, 'r') as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>MOD UI - Client Interface Service</h1>")


@app.get("/pedalboard", response_class=HTMLResponse)
async def pedalboard_ui():
    """Serve pedalboard UI"""
    html_file = os.path.join(HTML_DIR, "pedalboard.html")
    if os.path.exists(html_file):
        with open(html_file, 'r') as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Pedalboard UI</h1>")


# API Endpoints - Pedalboard Management
@app.get("/api/pedalboards")
async def get_pedalboards():
    """Get all pedalboards"""
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service bus not available")
    
    try:
        response = await service_bus.request("system_resource_management", "get_pedalboards", {})
        return response
    except Exception as e:
        logger.error(f"Error getting pedalboards: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pedalboards")


@app.post("/api/pedalboards")
async def create_pedalboard(pedalboard: PedalboardRequest):
    """Create new pedalboard"""
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service bus not available")
    
    try:
        response = await service_bus.request("audio_processing", "create_pedalboard", pedalboard.dict())
        await connection_manager.broadcast(json.dumps({
            "type": "pedalboard_created",
            "data": response
        }))
        return response
    except Exception as e:
        logger.error(f"Error creating pedalboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to create pedalboard")


@app.get("/api/pedalboards/{pedalboard_id}")
async def get_pedalboard(pedalboard_id: str):
    """Get specific pedalboard"""
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service bus not available")
    
    try:
        response = await service_bus.request("system_resource_management", "get_pedalboard", {
            "pedalboard_id": pedalboard_id
        })
        return response
    except Exception as e:
        logger.error(f"Error getting pedalboard {pedalboard_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pedalboard")


@app.put("/api/pedalboards/{pedalboard_id}")
async def update_pedalboard(pedalboard_id: str, pedalboard: PedalboardRequest):
    """Update pedalboard"""
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service bus not available")
    
    try:
        data = pedalboard.dict()
        data["pedalboard_id"] = pedalboard_id
        
        response = await service_bus.request("audio_processing", "update_pedalboard", data)
        await connection_manager.broadcast(json.dumps({
            "type": "pedalboard_updated",
            "data": response
        }))
        return response
    except Exception as e:
        logger.error(f"Error updating pedalboard {pedalboard_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update pedalboard")


@app.delete("/api/pedalboards/{pedalboard_id}")
async def delete_pedalboard(pedalboard_id: str):
    """Delete pedalboard"""
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service bus not available")
    
    try:
        response = await service_bus.request("system_resource_management", "delete_pedalboard", {
            "pedalboard_id": pedalboard_id
        })
        await connection_manager.broadcast(json.dumps({
            "type": "pedalboard_deleted",
            "data": {"pedalboard_id": pedalboard_id}
        }))
        return response
    except Exception as e:
        logger.error(f"Error deleting pedalboard {pedalboard_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete pedalboard")


# API Endpoints - Plugin Management
@app.get("/api/plugins")
async def get_available_plugins():
    """Get available plugins"""
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service bus not available")
    
    try:
        response = await service_bus.request("audio_processing", "get_available_plugins", {})
        return response
    except Exception as e:
        logger.error(f"Error getting plugins: {e}")
        raise HTTPException(status_code=500, detail="Failed to get plugins")


@app.post("/api/plugins")
async def add_plugin(plugin: PluginRequest):
    """Add plugin to current pedalboard"""
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service bus not available")
    
    try:
        response = await service_bus.request("audio_processing", "add_plugin", plugin.dict())
        await connection_manager.broadcast(json.dumps({
            "type": "plugin_added",
            "data": response
        }))
        return response
    except Exception as e:
        logger.error(f"Error adding plugin: {e}")
        raise HTTPException(status_code=500, detail="Failed to add plugin")


@app.delete("/api/plugins/{instance_id}")
async def remove_plugin(instance_id: str):
    """Remove plugin from current pedalboard"""
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service bus not available")
    
    try:
        response = await service_bus.request("audio_processing", "remove_plugin", {
            "instance_id": instance_id
        })
        await connection_manager.broadcast(json.dumps({
            "type": "plugin_removed",
            "data": {"instance_id": instance_id}
        }))
        return response
    except Exception as e:
        logger.error(f"Error removing plugin {instance_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove plugin")


# API Endpoints - Parameter Control
@app.put("/api/parameters")
async def update_parameter(param_update: ParameterUpdate):
    """Update plugin parameter"""
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service bus not available")
    
    try:
        response = await service_bus.request("audio_processing", "update_parameter", param_update.dict())
        await connection_manager.broadcast(json.dumps({
            "type": "parameter_updated",
            "data": param_update.dict()
        }))
        return response
    except Exception as e:
        logger.error(f"Error updating parameter: {e}")
        raise HTTPException(status_code=500, detail="Failed to update parameter")


# API Endpoints - System Status
@app.get("/api/system/status")
async def get_system_status():
    """Get system status"""
    if not service_bus:
        raise HTTPException(status_code=503, detail="Service bus not available")
    
    try:
        response = await service_bus.request("system_resource_management", "get_system_status", {})
        return response
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time communication"""
    user_id = None
    
    try:
        await connection_manager.connect(websocket, user_id)
        
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "data": {"service": SERVICE_NAME}
        }))
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }))
                
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket, user_id)


async def handle_websocket_message(websocket: WebSocket, message: Dict[str, Any]):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    try:
        if message_type == "parameter_update":
            # Real-time parameter updates
            if service_bus:
                await service_bus.request("audio_processing", "update_parameter", data)
                await connection_manager.broadcast(json.dumps({
                    "type": "parameter_updated",
                    "data": data
                }))
        
        elif message_type == "get_status":
            # Send current status
            if service_bus:
                status = await service_bus.request("system_resource_management", "get_system_status", {})
                await websocket.send_text(json.dumps({
                    "type": "status_update",
                    "data": status
                }))
        
        elif message_type == "ping":
            # Heartbeat
            await websocket.send_text(json.dumps({
                "type": "pong",
                "data": {"timestamp": data.get("timestamp")}
            }))
        
        else:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"message": f"Unknown message type: {message_type}"}
            }))
            
    except Exception as e:
        logger.error(f"Error handling WebSocket message {message_type}: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {"message": f"Error processing {message_type}"}
        }))


# Background tasks
async def status_broadcaster():
    """Broadcast system status updates periodically"""
    while True:
        try:
            await asyncio.sleep(30)  # Every 30 seconds
            
            if service_bus and len(connection_manager.active_connections) > 0:
                status = await service_bus.request("system_resource_management", "get_system_status", {})
                await connection_manager.broadcast(json.dumps({
                    "type": "status_update",
                    "data": status
                }))
        except Exception as e:
            logger.error(f"Error broadcasting status: {e}")


async def service_health_monitor():
    """Monitor service health and connectivity"""
    while True:
        try:
            await asyncio.sleep(60)  # Every minute
            
            if service_bus:
                # Check service bus health
                health_status = await service_bus.get_health()
                logger.info(f"Service bus health: {health_status}")
                
                # Broadcast health updates if needed
                if not service_bus.is_connected():
                    await connection_manager.broadcast(json.dumps({
                        "type": "service_warning",
                        "data": {"message": "Service connectivity issues detected"}
                    }))
        except Exception as e:
            logger.error(f"Error in health monitor: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=False,
        log_level="info"
    )