"""
Configuration Service

Dedicated microservice for serving MOD UI configuration settings.
Serves the settings.py file from the mod directory as REST API endpoints.
"""

import asyncio
import logging
import os
import signal
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.mod_ui.services.config_service.routers.config import router as config_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    logger = logging.getLogger(__name__)
    logger.info("Starting Configuration Service...")

    yield

    logger.info("Shutting down Configuration Service...")


# Create FastAPI application
app = FastAPI(
    title="MOD UI Configuration Service",
    description="Serves MOD UI configuration settings from settings.py",
    version="1.0.0",
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

# Include config router
app.include_router(config_router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "config-service"}


# Development server entry point
async def main():
    """Main entry point for development server"""

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
        port=int(os.getenv("CONFIG_SERVICE_PORT", "8083")),
        log_level="info",
        access_log=True,
    )

    server = uvicorn.Server(config)

    try:
        logger.info("Starting Configuration Service on http://0.0.0.0:8083")
        await server.serve()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
