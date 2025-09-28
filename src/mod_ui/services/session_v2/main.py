"""
Modern Session Service v2 - Pure Redis Pub/Sub Service

This is a pure Redis pub/sub service for session management,
built for inter-service communication without HTTP endpoints.
"""

import asyncio
import logging
import os
import signal
from typing import Optional

# Import common service infrastructure
from servicebus import CommConfig, ServiceServer, set_config

from .services.state_manager import StateManagerService
from .utils.event_bus import EventBus, InMemoryEventBus, RedisEventBus

# Global service instances
state_manager: Optional[StateManagerService] = None
event_bus: Optional[EventBus] = None
service_server: Optional[ServiceServer] = None


async def initialize_services():
    """Initialize all services"""
    global state_manager, event_bus, service_server

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

        # Initialize ServiceServer for Redis pub/sub communication
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # Configure ServiceBus
        config = CommConfig(redis_url=redis_url)
        set_config(config)

        service_server = ServiceServer("session")

        # Register session handlers
        service_server.register_handler("get_session_state", handle_get_session_state)
        service_server.register_handler(
            "update_session_state", handle_update_session_state
        )
        service_server.register_handler("control_transport", handle_control_transport)
        service_server.register_handler("get_session_status", handle_get_session_status)
        service_server.register_handler("set_session_tempo", handle_set_session_tempo)
        service_server.register_handler("get_session_stats", handle_get_session_stats)
        service_server.register_handler("start_session", handle_start_session)
        service_server.register_handler("stop_session", handle_stop_session)
        service_server.register_handler("reset_session", handle_reset_session)
        service_server.register_handler("set_session_config", handle_set_session_config)
        service_server.register_handler(
            "reset_session_stats", handle_reset_session_stats
        )

        await service_server.start()
        logger.info("ServiceServer started for Redis pub/sub communication")

        logger.info("Session Service v2 startup complete")

    except Exception as e:
        logger.error(f"Failed to start Session Service v2: {e}")
        raise


async def shutdown_services():
    """Shutdown all services gracefully"""
    global state_manager, event_bus, service_server

    logger = logging.getLogger(__name__)
    logger.info("Shutting down Session Service v2...")

    # Close services
    if service_server:
        await service_server.stop()
        logger.info("ServiceServer stopped")

    # Close state manager
    if state_manager:
        await state_manager.shutdown()
        logger.info("State manager shutdown")

    # Close event bus
    if event_bus:
        await event_bus.close()
        logger.info("Event bus closed")

    logger.info("Session Service v2 shutdown complete")


# ServiceServer request handlers for Redis pub/sub communication
async def handle_get_session_state(request) -> dict:
    """Handler for getting current session state"""
    global state_manager

    if not state_manager:
        return {"error": "State manager not initialized"}

    try:
        # Get current session state from state manager
        state = await state_manager.get_session_state()
        return {
            "success": True,
            "session": {
                "transport_state": state.transport_state,
                "tempo_bpm": state.tempo_bpm,
                "sample_rate": state.sample_rate,
                "buffer_size": state.buffer_size,
                "audio_driver": state.audio_driver,
                "cpu_load": state.cpu_load,
                "xrun_count": state.xrun_count,
                "uptime_seconds": state.uptime_seconds,
                "created_at": state.created_at.isoformat(),
                "modified_at": state.modified_at.isoformat(),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_get_session_status(request) -> dict:
    """Handler for getting session status (alias for get_session_state)"""
    return await handle_get_session_state(request)


async def handle_update_session_state(request) -> dict:
    """Handler for updating session state"""
    global state_manager

    if not state_manager:
        return {"error": "State manager not initialized"}

    try:
        data = request.data

        # Update session state based on provided data
        if "tempo_bpm" in data:
            await state_manager.set_tempo(data["tempo_bpm"])

        if "transport_state" in data:
            if data["transport_state"] == "playing":
                await state_manager.start_transport()
            elif data["transport_state"] == "stopped":
                await state_manager.stop_transport()

        if "sample_rate" in data:
            await state_manager.set_sample_rate(data["sample_rate"])

        if "buffer_size" in data:
            await state_manager.set_buffer_size(data["buffer_size"])

        # Get updated state
        updated_state = await state_manager.get_session_state()

        return {
            "success": True,
            "message": "Session state updated",
            "session": {
                "transport_state": updated_state.transport_state,
                "tempo_bpm": updated_state.tempo_bpm,
                "sample_rate": updated_state.sample_rate,
                "buffer_size": updated_state.buffer_size,
                "cpu_load": updated_state.cpu_load,
                "xrun_count": updated_state.xrun_count,
                "uptime_seconds": updated_state.uptime_seconds,
                "modified_at": updated_state.modified_at.isoformat(),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_control_transport(request) -> dict:
    """Handler for transport control"""
    global state_manager

    if not state_manager:
        return {"error": "State manager not initialized"}

    try:
        data = request.data
        action = data.get("action", "")

        if action == "play":
            await state_manager.start_transport()
            transport_state = "playing"
        elif action == "stop":
            await state_manager.stop_transport()
            transport_state = "stopped"
        elif action == "pause":
            await state_manager.pause_transport()
            transport_state = "paused"
        else:
            return {"success": False, "error": f"Unknown transport action: {action}"}

        return {
            "success": True,
            "transport_state": transport_state,
            "message": f"Transport {action} successful",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_set_session_tempo(request) -> dict:
    """Handler for setting session tempo"""
    global state_manager

    if not state_manager:
        return {"error": "State manager not initialized"}

    try:
        data = request.data
        bpm = data.get("bpm", 120.0)

        await state_manager.set_tempo(bpm)

        return {"success": True, "tempo_bpm": bpm, "message": f"Tempo set to {bpm} BPM"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_get_session_stats(request) -> dict:
    """Handler for getting session statistics"""
    global state_manager

    if not state_manager:
        return {"error": "State manager not initialized"}

    try:
        state = await state_manager.get_session_state()

        return {
            "success": True,
            "stats": {
                "cpu_load": state.cpu_load,
                "xrun_count": state.xrun_count,
                "uptime_seconds": state.uptime_seconds,
                "sample_rate": state.sample_rate,
                "buffer_size": state.buffer_size,
                "transport_state": state.transport_state,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_start_session(request) -> dict:
    """Handler for starting a session"""
    global state_manager

    if not state_manager:
        return {"error": "State manager not initialized"}

    try:
        data = request.data
        pedalboard_path = data.get("pedalboard_path")

        # Reset session first
        await state_manager.reset_session()

        # Load pedalboard if specified
        if pedalboard_path:
            # This would integrate with pedalboard service in the future
            pass

        # Get current state after start
        state = await state_manager.get_session_state()

        return {
            "success": True,
            "message": "Session started successfully",
            "session_id": "current",
            "session": {
                "transport_state": state.transport_state,
                "tempo_bpm": state.tempo_bpm,
                "created_at": state.created_at.isoformat(),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_stop_session(request) -> dict:
    """Handler for stopping a session"""
    global state_manager

    if not state_manager:
        return {"error": "State manager not initialized"}

    try:
        # Stop transport and reset
        await state_manager.stop_transport()
        await state_manager.reset_session()

        return {
            "success": True,
            "message": "Session stopped successfully",
            "timestamp": state_manager._session_state.modified_at.isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_reset_session(request) -> dict:
    """Handler for resetting a session"""
    global state_manager

    if not state_manager:
        return {"error": "State manager not initialized"}

    try:
        await state_manager.reset_session()

        return {"success": True, "message": "Session reset successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_set_session_config(request) -> dict:
    """Handler for setting session configuration"""
    global state_manager

    if not state_manager:
        return {"error": "State manager not initialized"}

    try:
        data = request.data
        config = {}

        if "sample_rate" in data:
            await state_manager.set_sample_rate(data["sample_rate"])
            config["sample_rate"] = data["sample_rate"]

        if "buffer_size" in data:
            await state_manager.set_buffer_size(data["buffer_size"])
            config["buffer_size"] = data["buffer_size"]

        if "audio_driver" in data:
            # This would be implemented when we have actual audio driver management
            config["audio_driver"] = data["audio_driver"]

        return {
            "success": True,
            "config": config,
            "message": "Configuration updated successfully",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_reset_session_stats(request) -> dict:
    """Handler for resetting session statistics"""
    global state_manager

    if not state_manager:
        return {"error": "State manager not initialized"}

    try:
        await state_manager.reset_stats()
        state = await state_manager.get_session_state()

        return {
            "success": True,
            "message": "Statistics reset successfully",
            "stats": {
                "cpu_load": state.cpu_load,
                "xrun_count": state.xrun_count,
                "uptime_seconds": state.uptime_seconds,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def main():
    """Main entry point for the service"""
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

    try:
        # Initialize services
        await initialize_services()

        logger.info("Session Service v2 is running - Press Ctrl+C to shutdown")

        # Keep the service running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Service error: %s", str(e))
        raise
    finally:
        # Shutdown services
        await shutdown_services()


if __name__ == "__main__":
    asyncio.run(main())
