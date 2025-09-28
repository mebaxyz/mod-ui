"""
Audio Engine ServiceBus Server

Provides ServiceBus (Redis pub/sub) endpoints for audio engine operations
instead of HTTP endpoints. This maintains pure pub/sub architecture.
"""

import asyncio
import logging
import os
import signal
from typing import Optional

# Import ServiceBus infrastructure
from servicebus import CommConfig, ServiceServer, set_config

from .models import (
    AddPluginCommand,
    BypassPluginCommand,
    ConnectPortsCommand,
    DisconnectPortsCommand,
    LoadPresetCommand,
    RemovePluginCommand,
    SetParameterCommand,
    SetTransportCommand,
)
from .service import AudioEngineService

logger = logging.getLogger(__name__)

# Global service instances
audio_service: Optional[AudioEngineService] = None
service_server: Optional[ServiceServer] = None


async def initialize_services():
    """Initialize audio engine service"""
    global audio_service, service_server

    logger.info("Starting Audio Engine Service...")

    try:
        # Initialize audio engine service
        audio_service = AudioEngineService()
        success = await audio_service.start()

        # Don't fail if mod-host is not available - this is expected in development
        if not success:
            logger.warning(
                "Could not connect to mod-host - continuing without audio engine connection"
            )
        else:
            logger.info("Audio engine service connected to mod-host")

        logger.info("Audio engine service initialized")

        # Initialize ServiceServer for Redis pub/sub communication
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # Configure ServiceBus
        config = CommConfig(redis_url=redis_url)
        set_config(config)

        # Create ServiceServer instance
        service_server = ServiceServer("audio-engine")

        # Register handlers
        service_server.register_handler("add_plugin", handle_add_plugin)
        service_server.register_handler("remove_plugin", handle_remove_plugin)
        service_server.register_handler("set_parameter", handle_set_parameter)
        service_server.register_handler("connect_ports", handle_connect_ports)
        service_server.register_handler("disconnect_ports", handle_disconnect_ports)
        service_server.register_handler("set_transport", handle_set_transport)
        service_server.register_handler("get_state", handle_get_state)
        service_server.register_handler("load_preset", handle_load_preset)
        service_server.register_handler("bypass_plugin", handle_bypass_plugin)
        service_server.register_handler("health", handle_health)

        logger.info("ServiceBus handlers registered")

    except Exception as e:
        logger.error("Failed to initialize services: %s", e)
        raise


async def cleanup_services():
    """Cleanup services"""
    global audio_service, service_server

    logger.info("Cleaning up services...")

    if service_server:
        await service_server.stop()
        service_server = None

    if audio_service:
        await audio_service.stop()
        audio_service = None

    logger.info("Services cleaned up")


# ServiceBus Message Handlers


async def handle_add_plugin(request):
    """Handler for adding plugin"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        data = request.data
        command = AddPluginCommand(
            instance_id=data.get("instance_id"),
            plugin_uri=data.get("plugin_uri"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
        )

        plugin = await audio_service.add_plugin(command)
        return {
            "success": True,
            "plugin": {
                "instance_id": plugin.instance_id,
                "plugin_uri": plugin.plugin_uri,
                "x": plugin.x,
                "y": plugin.y,
                "ports": plugin.ports,
            },
        }

    except Exception as e:
        logger.error("Error in add_plugin handler: %s", e)
        return {"error": str(e)}


async def handle_remove_plugin(request):
    """Handler for removing plugin"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        data = request.data
        command = RemovePluginCommand(instance_id=data.get("instance_id"))

        success = await audio_service.remove_plugin(command)
        return {"success": success}

    except Exception as e:
        logger.error("Error in remove_plugin handler: %s", e)
        return {"error": str(e)}


async def handle_set_parameter(request):
    """Handler for setting parameter"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        data = request.data
        command = SetParameterCommand(
            instance_id=data.get("instance_id"),
            port_symbol=data.get("port_symbol"),
            value=data.get("value"),
        )

        success = await audio_service.set_parameter(command)
        return {"success": success}

    except Exception as e:
        logger.error("Error in set_parameter handler: %s", e)
        return {"error": str(e)}


async def handle_connect_ports(request):
    """Handler for connecting ports"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        data = request.data
        command = ConnectPortsCommand(
            from_port=data.get("from_port"), to_port=data.get("to_port")
        )

        connection = await audio_service.connect_ports(command)
        return {
            "success": True,
            "connection": {
                "from_port": connection.from_port,
                "to_port": connection.to_port,
                "connection_id": connection.connection_id,
            },
        }

    except Exception as e:
        logger.error("Error in connect_ports handler: %s", e)
        return {"error": str(e)}


async def handle_disconnect_ports(request):
    """Handler for disconnecting ports"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        data = request.data
        command = DisconnectPortsCommand(
            from_port=data.get("from_port"), to_port=data.get("to_port")
        )

        success = await audio_service.disconnect_ports(command)
        return {"success": success}

    except Exception as e:
        logger.error("Error in disconnect_ports handler: %s", e)
        return {"error": str(e)}


async def handle_set_transport(request):
    """Handler for setting transport"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        data = request.data
        command = SetTransportCommand(
            rolling=data.get("rolling"), bpm=data.get("bpm"), bpb=data.get("bpb")
        )

        transport = await audio_service.set_transport(command)
        return {
            "success": True,
            "transport": {
                "rolling": transport.rolling,
                "bpm": transport.bpm,
                "bpb": transport.bpb,
                "speed": transport.speed,
            },
        }

    except Exception as e:
        logger.error("Error in set_transport handler: %s", e)
        return {"error": str(e)}


async def handle_get_state(request):
    """Handler for getting state"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        state = await audio_service.get_state()
        return {
            "success": True,
            "state": {
                "plugins": {k: v.dict() for k, v in state.plugins.items()},
                "connections": [conn.dict() for conn in state.connections],
                "transport": state.transport.dict(),
            },
        }

    except Exception as e:
        logger.error("Error in get_state handler: %s", e)
        return {"error": str(e)}


async def handle_load_preset(request):
    """Handler for loading preset"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        data = request.data
        command = LoadPresetCommand(
            instance_id=data.get("instance_id"), preset_uri=data.get("preset_uri")
        )

        success = await audio_service.load_preset(command)
        return {"success": success}

    except Exception as e:
        logger.error("Error in load_preset handler: %s", e)
        return {"error": str(e)}


async def handle_bypass_plugin(request):
    """Handler for bypassing plugin"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        data = request.data
        command = BypassPluginCommand(
            instance_id=data.get("instance_id"), bypass=data.get("bypass")
        )

        success = await audio_service.bypass_plugin(command)
        return {"success": success}

    except Exception as e:
        logger.error("Error in bypass_plugin handler: %s", e)
        return {"error": str(e)}


async def handle_health(request):
    """Handler for health check"""
    if not audio_service:
        return {"status": "unhealthy", "error": "Audio service not initialized"}

    try:
        return {
            "status": "healthy" if audio_service.is_connected else "unhealthy",
            "connected": audio_service.is_connected,
            "connection_status": audio_service.connection.status.value,
        }

    except Exception as e:
        logger.error("Error in health handler: %s", e)
        return {"status": "unhealthy", "error": str(e)}


async def main():
    """Main service loop"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize services
    await initialize_services()

    # Setup signal handlers for graceful shutdown
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(shutdown())

    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, lambda s, f: signal_handler())

    try:
        # Start ServiceServer
        if service_server:
            await service_server.start()
            logger.info(
                "Audio Engine Service started and listening for ServiceBus messages"
            )

            # Keep running
            while True:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    except Exception as e:
        logger.error("Service error: %s", e)
        raise
    finally:
        await cleanup_services()


async def shutdown():
    """Graceful shutdown"""
    logger.info("Shutting down...")
    await cleanup_services()


if __name__ == "__main__":
    asyncio.run(main())
