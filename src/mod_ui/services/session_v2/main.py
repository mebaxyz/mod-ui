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

from .integration.audio_engine_client import SessionPluginService
from .services.session_manager import SessionManager
from .services.state_manager import StateManagerService
from .utils.event_bus import EventBus, InMemoryEventBus, RedisEventBus

# Global service instances
state_manager: Optional[StateManagerService] = None
session_manager: Optional[SessionManager] = None
event_bus: Optional[EventBus] = None
service_server: Optional[ServiceServer] = None
plugin_service: Optional[SessionPluginService] = None


async def initialize_services():
    """Initialize all services"""
    global state_manager, session_manager, event_bus, service_server, plugin_service

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

        # Initialize ServiceBus client for audio engine communication
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # Configure ServiceBus for audio engine communication
        config = CommConfig(redis_url=redis_url)
        set_config(config)

        from servicebus import ServiceClient

        audio_servicebus_client = ServiceClient("session-v2")

        # Initialize plugin service with ServiceBus client
        plugin_service = SessionPluginService(audio_servicebus_client)
        logger.info("Audio engine ServiceBus client initialized")

        # Initialize enhanced session manager
        session_manager = SessionManager(event_publisher=event_bus)
        await session_manager.initialize()
        logger.info("Enhanced session manager initialized")

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

        # Register enhanced session handlers
        service_server.register_handler("get_session_state", handle_get_session_state)
        service_server.register_handler("reset_session", handle_reset_session)
        service_server.register_handler(
            "websocket_connected", handle_websocket_connected
        )
        service_server.register_handler(
            "websocket_disconnected", handle_websocket_disconnected
        )

        # Plugin management handlers
        service_server.register_handler("add_plugin", handle_add_plugin)
        service_server.register_handler("remove_plugin", handle_remove_plugin)
        service_server.register_handler(
            "set_plugin_parameter", handle_set_plugin_parameter
        )

        # Connection management handlers
        service_server.register_handler("add_connection", handle_add_connection)
        service_server.register_handler("remove_connection", handle_remove_connection)

        # Transport control handlers
        service_server.register_handler("control_transport", handle_control_transport)
        service_server.register_handler("set_session_tempo", handle_set_session_tempo)
        service_server.register_handler("set_beats_per_bar", handle_set_beats_per_bar)

        # Recording handlers
        service_server.register_handler("recording_start", handle_recording_start)
        service_server.register_handler("recording_stop", handle_recording_stop)
        service_server.register_handler("recording_reset", handle_recording_reset)

        # Legacy compatibility handlers
        service_server.register_handler(
            "update_session_state", handle_update_session_state
        )
        service_server.register_handler("get_session_status", handle_get_session_status)
        service_server.register_handler("get_session_stats", handle_get_session_stats)
        service_server.register_handler("start_session", handle_start_session)
        service_server.register_handler("stop_session", handle_stop_session)
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
    global state_manager, session_manager, event_bus, service_server

    logger = logging.getLogger(__name__)
    logger.info("Shutting down Session Service v2...")

    # Close services
    if service_server:
        await service_server.stop()
        logger.info("ServiceServer stopped")

    # Close session manager
    if session_manager:
        await session_manager.shutdown()
        logger.info("Enhanced session manager shutdown")

    # Close state manager
    if state_manager:
        await state_manager.shutdown()
        logger.info("State manager shutdown")

    # Close event bus
    if event_bus:
        await event_bus.close()
        logger.info("Event bus closed")

    logger.info("Session Service v2 shutdown complete")


async def handle_get_session_state(request) -> dict:
    """Handler for getting current session state"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        # Get current session state from enhanced session manager
        state = await session_manager.get_session_state()
        return {
            "success": True,
            "session": {
                "session_id": str(state.session_id),
                "status": state.status.value,
                "transport_state": state.transport_state.value,
                "transport_rolling": state.transport_rolling,
                "tempo_bpm": state.tempo_bpm,
                "beats_per_bar": state.beats_per_bar,
                "sample_rate": state.sample_rate,
                "buffer_size": state.buffer_size,
                "audio_driver": state.audio_driver,
                "cpu_load": state.cpu_load,
                "xrun_count": state.xrun_count,
                "uptime_seconds": state.uptime_seconds,
                "websocket_clients": state.websocket_clients,
                "web_connected": state.web_connected,
                "hmi_connected": state.hmi_connected,
                "hardware_connected": state.hardware_connected,
                "audio_engine_connected": state.audio_engine_connected,
                "pedalboard_name": state.pedalboard_name,
                "pedalboard_path": state.pedalboard_path,
                "pedalboard_empty": state.pedalboard_empty,
                "pedalboard_modified": state.pedalboard_modified,
                "current_snapshot_id": state.current_snapshot_id,
                "recording": {
                    "is_recording": state.recording.is_recording,
                    "is_playing": state.recording.is_playing,
                    "has_recording": state.recording.has_recording,
                    "recording_length_seconds": state.recording.recording_length_seconds,
                },
                "created_at": state.created_at.isoformat(),
                "modified_at": state.modified_at.isoformat(),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_reset_session(request) -> dict:
    """Handler for resetting session"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        result = await session_manager.reset_session()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


# WebSocket Management Handlers


async def handle_websocket_connected(request) -> dict:
    """Handler for websocket connection"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        # Handle both HTTP requests (with .data attribute) and ServiceBus calls (dict directly)
        if hasattr(request, "data"):
            data = request.data
        else:
            data = request

        websocket_id = data.get("websocket_id", "unknown")

        result = await session_manager.websocket_connected(websocket_id)

        if result:
            state = await session_manager.get_session_state()
            return {
                "success": True,
                "websocket_clients": state.websocket_clients,
                "web_connected": state.web_connected,
            }
        else:
            return {"success": False, "error": "Failed to connect websocket"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_websocket_disconnected(request) -> dict:
    """Handler for websocket disconnection"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        data = request.data
        websocket_id = data.get("websocket_id", "unknown")

        result = await session_manager.websocket_disconnected(websocket_id)

        if result:
            state = await session_manager.get_session_state()
            return {
                "success": True,
                "websocket_clients": state.websocket_clients,
                "web_connected": state.web_connected,
            }
        else:
            return {"success": False, "error": "Failed to disconnect websocket"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# Plugin Management Handlers


async def handle_add_plugin(request) -> dict:
    """Handler for adding a plugin"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        from .models.plugin import PluginAddRequest

        # Handle both HTTP requests (with .data attribute) and ServiceBus calls (dict directly)
        if hasattr(request, "data"):
            data = request.data
        else:
            data = request

        plugin_request = PluginAddRequest(
            instance=data.get("instance"),
            uri=data.get("uri"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
        )

        result = await session_manager.add_plugin(plugin_request)
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_remove_plugin(request) -> dict:
    """Handler for removing a plugin"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        from .models.plugin import PluginRemoveRequest

        data = request.data
        plugin_request = PluginRemoveRequest(instance=data.get("instance"))

        result = await session_manager.remove_plugin(plugin_request)
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_set_plugin_parameter(request) -> dict:
    """Handler for setting plugin parameter"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        from .models.plugin import ParameterSetRequest

        data = request.data
        param_request = ParameterSetRequest(
            instance=data.get("instance"),
            parameter=data.get("parameter"),
            value=data.get("value"),
        )

        result = await session_manager.set_plugin_parameter(param_request)
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


# Connection Management Handlers


async def handle_add_connection(request) -> dict:
    """Handler for adding connection"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        from .models.plugin import ConnectionRequest

        data = request.data
        conn_request = ConnectionRequest(
            source=data.get("source"), target=data.get("target")
        )

        result = await session_manager.add_connection(conn_request)
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_remove_connection(request) -> dict:
    """Handler for removing connection"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        from .models.plugin import ConnectionRequest

        data = request.data
        conn_request = ConnectionRequest(
            source=data.get("source"), target=data.get("target")
        )

        result = await session_manager.remove_connection(conn_request)
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_set_beats_per_bar(request) -> dict:
    """Handler for setting beats per bar"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        data = request.data
        bpb = data.get("bpb", 4.0)

        result = await session_manager.set_beats_per_bar(bpb)
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


# Recording Handlers


async def handle_recording_start(request) -> dict:
    """Handler for starting recording"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        result = await session_manager.recording_start()
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_recording_stop(request) -> dict:
    """Handler for stopping recording"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        result = await session_manager.recording_stop()
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_recording_reset(request) -> dict:
    """Handler for resetting recording"""
    global session_manager

    if not session_manager:
        return {"error": "Session manager not initialized"}

    try:
        result = await session_manager.recording_reset()
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


# Legacy compatibility handlers using state_manager (for backward compatibility)
async def handle_get_session_state_legacy(request) -> dict:
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
