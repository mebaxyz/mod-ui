"""
Modern Session Service FastAPI Application

This is the main entry point for the MOD UI Session Service v2,
built with FastAPI and featuring async/await throughout.
"""

import asyncio

import logging
import os
import signal
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from .routers import pedalboard_router, session_router
from .services.state_manager import StateManagerService
from .utils.event_bus import EventBus, InMemoryEventBus, RedisEventBus

# Global service instances
state_manager: Optional[StateManagerService] = None
event_bus: Optional[EventBus] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown"""
    global state_manager, event_bus

    logger = logging.getLogger(__name__)
    logger.info("Starting Session Service v2...")

    try:
        # Initialize event bus based on configuration
        event_bus_type = os.getenv("EVENT_BUS_TYPE", "inmemory")

        if event_bus_type == "redis":
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))

            redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

            event_bus = RedisEventBus(redis_url)
            logger.info(f"Redis event bus initialized (url={redis_url})")
        else:
            event_bus = InMemoryEventBus()
            logger.info("In-memory event bus initialized")

        await event_bus.initialize()

        # Initialize state manager
        state_manager = StateManagerService(event_publisher=event_bus)
        await state_manager.initialize()
        logger.info("State manager initialized")




        # Store services in app state for access from routers
        app.state.event_bus = event_bus
        app.state.state_manager = state_manager


        logger.info("Session Service v2 startup complete")

        yield

    except Exception as e:
        logger.error(f"Failed to start Session Service v2: {e}")
        raise

    finally:
        logger.info("Shutting down Session Service v2...")

                # Close services

        # Close state manager
        if state_manager:
            await state_manager.shutdown()

        # Close event bus
        if event_bus:
            await event_bus.close()

        logger.info("Session Service v2 shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="MOD UI Session Service v2",
    description="Modern session management service for MOD UI with event-driven architecture",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pedalboard_router, prefix="/api/pedalboard", tags=["pedalboard"])
app.include_router(session_router, prefix="/api/session", tags=["session"])
# Realtime WebSocket functionality moved to dedicated WebSocket Gateway Service


@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return {"status": "ok", "service": "session-v2"}


@app.get("/status")
async def status():
    """Detailed status endpoint"""
    global state_manager, event_bus

    status_info = {
        "service": "session-v2", 
        "version": "2.0.0", 
        "status": "running",
        "websocket_note": "Real-time WebSocket communication handled by dedicated WebSocket Gateway Service"
    }

    if state_manager:
        status_info["state_manager"] = "active"

    if event_bus:
        status_info["event_bus"] = "active"

    return status_info


# WebSocket endpoint moved to dedicated WebSocket Gateway Service
# Real-time communication is now handled by the gateway service at /websocket


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
        app, host="0.0.0.0", port=8002, log_level="info", access_log=True
    )

    server = uvicorn.Server(config)

    try:
        logger.info("Starting Session Service v2 on http://0.0.0.0:8002")
        await server.serve()
    except Exception as e:
        logger.error("Failed to start server: %s", str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
