"""
Simple WebSocket Gateway Service

A working version with essential functionality.
"""

import asyncio
import json
import logging
import os
import signal
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Simple connection manager
active_connections: Dict[str, WebSocket] = {}

app = FastAPI(
    title="MOD UI WebSocket Gateway Service",
    description="Dedicated real-time communication hub for all MOD UI services",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return {"status": "ok", "service": "websocket-gateway"}

@app.get("/status")
async def status():
    """Detailed service status"""
    return {
        "service": "websocket-gateway",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(active_connections),
    }

async def broadcast_message(message: Any) -> int:
    """Broadcast a message to all connected clients"""
    if not active_connections:
        return 0
    
    # Convert message to string if needed
    message_str = json.dumps(message) if isinstance(message, dict) else str(message)
    
    # Send to all clients, removing disconnected ones
    disconnected_clients = []
    
    for client_id, websocket in active_connections.items():
        try:
            await websocket.send_text(message_str)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to send to {client_id}: {e}")
            disconnected_clients.append(client_id)
    
    # Clean up disconnected clients
    for client_id in disconnected_clients:
        active_connections.pop(client_id, None)
    
    return len(active_connections)

@app.get("/clients")
async def list_clients():
    """List all connected clients"""
    return {
        "success": True,
        "clients": [{"client_id": client_id} for client_id in active_connections.keys()],
        "count": len(active_connections),
    }

@app.post("/broadcast")
async def broadcast_endpoint(message: Dict[str, Any]):
    """Broadcast a message to all connected clients"""
    count = await broadcast_message(message)
    return {
        "success": True,
        "message": "Message broadcast",
        "clients_reached": count,
    }

async def send_stats_message(cpu_load: float, xruns: int) -> int:
    """Send stats message in legacy format: 'stats CPU_LOAD XRUNS'"""
    message = f"stats {cpu_load:.1f} {xruns}"
    return await broadcast_message(message)

async def send_sys_stats_message(mem_load: float, cpu_freq: str, cpu_temp: str) -> int:
    """Send system stats message in legacy format: 'sys_stats MEM_LOAD CPU_FREQ CPU_TEMP'"""
    message = f"sys_stats {mem_load:.1f} {cpu_freq} {cpu_temp}"
    return await broadcast_message(message)

async def send_transport_message(rolling: bool = False, bpb: float = 4.0, bpm: float = 120.0, sync: str = "none") -> int:
    """Send transport message to all connected clients."""
    message = f"transport {int(rolling)} {bpb} {bpm} {sync}"
    return await broadcast_message(message)

async def send_loading_start_message(empty: bool = True, modified: bool = False) -> int:
    """Send loading_start message to all connected clients."""
    message = f"loading_start {int(empty)} {int(modified)}"
    return await broadcast_message(message)

async def send_loading_end_message(snapshot_id: int = 0) -> int:
    """Send loading_end message to all connected clients."""
    message = f"loading_end {snapshot_id}"
    return await broadcast_message(message)

async def send_truebypass_message(left: bool = False, right: bool = False) -> int:
    """Send truebypass message to all connected clients."""
    message = f"truebypass {int(left)} {int(right)}"
    return await broadcast_message(message)

async def send_size_message(width: int = 0, height: int = 0) -> int:
    """Send size message to all connected clients."""
    message = f"size {width} {height}"
    return await broadcast_message(message)

async def send_ping_message() -> int:
    """Send ping message to all clients"""
    return await broadcast_message("ping")

async def send_data_ready_message(counter: int) -> int:
    """Send data_ready message in legacy format: 'data_ready COUNTER'"""
    message = f"data_ready {counter}"
    return await broadcast_message(message)

# Legacy message endpoints for compatibility
@app.post("/legacy/stats")
async def send_stats(stats_data: Dict[str, Any]):
    """Send legacy stats message"""
    cpu_load = float(stats_data.get("cpu_load", 0.0))
    xruns = int(stats_data.get("xruns", 0))
    message = f"stats {cpu_load:.1f} {xruns}"
    
    await broadcast_message(message)
    return {"success": True, "message": "Stats sent", "clients_reached": len(active_connections)}

@app.post("/legacy/sys_stats")
async def send_sys_stats(sys_stats_data: Dict[str, Any]):
    """Send legacy system stats message"""
    mem_load = float(sys_stats_data.get("mem_load", 0.0))
    cpu_freq = str(sys_stats_data.get("cpu_freq", "0"))
    cpu_temp = str(sys_stats_data.get("cpu_temp", "0"))
    message = f"sys_stats {mem_load:.1f} {cpu_freq} {cpu_temp}"
    
    await broadcast_message(message)
    return {"success": True, "message": "System stats sent", "clients_reached": len(active_connections)}

@app.get("/health")
async def health_check():
    """Check health of WebSocket gateway services"""
    return {
        "success": True,
        "health": "healthy",
        "timestamp": datetime.now().isoformat(),
        "connected_clients": len(active_connections),
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for client connections"""
    logger = logging.getLogger(__name__)
    client_id = f"client_{len(active_connections)+1}"
    data_ready_counter = 1
    
    try:
        await websocket.accept()
        active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")
        
        # First, send the initial data_ready message that frontend is waiting for
        await websocket.send_text(f"data_ready {data_ready_counter}")
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                logger.info(f"Received from {client_id}: {data}")
                
                # Handle ping
                if data.strip() == "ping":
                    await websocket.send_text("pong")
                    continue
                
                # Handle data_ready response from frontend
                if data.startswith("data_ready "):
                    # Frontend responded to our data_ready, now send initialization sequence
                    logger.info(f"Frontend responded with data_ready, sending initialization sequence")
                    
                    # Send transport message (required for frontend initialization)
                    await websocket.send_text("transport 0 4.0 120.0 none")
                    
                    # Send truebypass message
                    await websocket.send_text("truebypass 0 0")
                    
                    # Send loading start message  
                    await websocket.send_text("loading_start 1 0")
                    
                    # Send size message (default pedalboard size)
                    await websocket.send_text("size 0 0")
                    
                    # Send loading end message
                    await websocket.send_text("loading_end 0")
                    continue
                
                # Handle other messages as needed
                logger.info(f"Unhandled message from {client_id}: {data}")
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        active_connections.pop(client_id, None)

# Development server entry point
async def main():
    """Main entry point for development server"""
    import uvicorn

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, _frame):
        logger.info("Received signal %d, shutting down...", signum)
        asyncio.get_event_loop().stop()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.getenv("WEBSOCKET_GATEWAY_PORT", "8081")),
        log_level="info",
        access_log=True,
    )

    server = uvicorn.Server(config)

    try:
        logger.info("Starting WebSocket Gateway Service on http://0.0.0.0:8081")
        await server.serve()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())