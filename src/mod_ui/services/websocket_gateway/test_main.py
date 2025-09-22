"""
Working WebSocket Gateway - Fixed Version
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple connection tracking
connected_clients: Dict[str, WebSocket] = {}

# Create FastAPI app
app = FastAPI(
    title="MOD UI WebSocket Gateway Service",
    description="Real-time communication hub for MOD UI services",
    version="1.0.0-fixed",
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
    logger.info("Ping endpoint called")
    return {"status": "ok", "service": "websocket-gateway"}


@app.get("/status")
async def status():
    """Detailed service status"""
    logger.info("Status endpoint called")
    return {
        "service": "websocket-gateway",
        "version": "1.0.0-fixed",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "connected_clients": len(connected_clients),
        "active_connections": list(connected_clients.keys()),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for client connections"""
    client_id = f"client_{int(time.time() * 1000)}"

    try:
        await websocket.accept()
        connected_clients[client_id] = websocket

        logger.info(f"WebSocket client connected: {client_id}")

        # Send welcome message
        await websocket.send_text(
            json.dumps(
                {
                    "type": "welcome",
                    "client_id": client_id,
                    "timestamp": datetime.now().isoformat(),
                    "gateway_version": "1.0.0-fixed",
                }
            )
        )

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                logger.info(f"Received message from {client_id}: {message}")

                # Handle ping
                if message.get("type") == "ping":
                    await websocket.send_text(
                        json.dumps({"type": "pong", "timestamp": time.time()})
                    )

                # Echo other messages for testing
                elif message.get("type") == "echo":
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "echo_response",
                                "original_message": message,
                                "timestamp": time.time(),
                            }
                        )
                    )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling message from {client_id}: {e}")
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "message": str(e), "timestamp": time.time()}
                    )
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        if client_id in connected_clients:
            del connected_clients[client_id]


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("WEBSOCKET_GATEWAY_PORT", "8081"))
    logger.info(f"Starting simplified WebSocket Gateway on port {port}")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=True)
