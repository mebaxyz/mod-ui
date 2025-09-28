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
    # JACK and LV2 command imports are done dynamically in handlers
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

        # Register mod-host handlers
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

        # Register JACK handlers
        service_server.register_handler("get_jack_data", handle_get_jack_data)
        service_server.register_handler("get_jack_hardware_ports", handle_get_jack_hardware_ports)
        service_server.register_handler("connect_jack_ports", handle_connect_jack_ports)
        service_server.register_handler("disconnect_jack_ports", handle_disconnect_jack_ports)
        service_server.register_handler("disconnect_all_jack_ports", handle_disconnect_all_jack_ports)
        service_server.register_handler("reset_jack_xruns", handle_reset_jack_xruns)
        service_server.register_handler("set_jack_buffer_size", handle_set_jack_buffer_size)

        # Register LV2 handlers  
        service_server.register_handler("get_plugin_list", handle_get_plugin_list)
        service_server.register_handler("get_all_plugins", handle_get_all_plugins)
        service_server.register_handler("get_plugin_info", handle_get_plugin_info)
        service_server.register_handler("scan_plugins", handle_scan_plugins)
        service_server.register_handler("add_bundle", handle_add_bundle)
        service_server.register_handler("remove_bundle", handle_remove_bundle)

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


# =============================================================================
# JACK ServiceBus Message Handlers  
# =============================================================================

async def handle_get_jack_data(request):
    """Handler for getting JACK system data"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        # Handle both HTTP requests and ServiceBus calls
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request
        
        with_transport = data.get("with_transport", True)
        jack_data = await audio_service.get_jack_data()
        
        return {
            "success": True,
            "jack_data": jack_data.dict()
        }

    except Exception as e:
        logger.error("Error in get_jack_data handler: %s", e)
        return {"error": str(e)}


async def handle_get_jack_hardware_ports(request):
    """Handler for getting JACK hardware ports"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        # Handle both HTTP requests and ServiceBus calls
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request
        
        is_audio = data.get("is_audio", True)
        is_output = data.get("is_output", False)
        
        ports = await audio_service.get_jack_hardware_ports(is_audio, is_output)
        
        return {
            "success": True,
            "ports": [port.dict() for port in ports]
        }

    except Exception as e:
        logger.error("Error in get_jack_hardware_ports handler: %s", e)
        return {"error": str(e)}


async def handle_connect_jack_ports(request):
    """Handler for connecting JACK ports"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        # Handle both HTTP requests and ServiceBus calls
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request
            
        from .models import ConnectJackPortsCommand
        command = ConnectJackPortsCommand(
            output_port=data.get("output_port"),
            input_port=data.get("input_port")
        )

        connection = await audio_service.connect_jack_ports(command)
        return {
            "success": True,
            "connection": connection.dict()
        }

    except Exception as e:
        logger.error("Error in connect_jack_ports handler: %s", e)
        return {"error": str(e)}


async def handle_disconnect_jack_ports(request):
    """Handler for disconnecting JACK ports"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        # Handle both HTTP requests and ServiceBus calls
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request
            
        from .models import DisconnectJackPortsCommand
        command = DisconnectJackPortsCommand(
            output_port=data.get("output_port"),
            input_port=data.get("input_port")
        )

        success = await audio_service.disconnect_jack_ports(command)
        return {"success": success}

    except Exception as e:
        logger.error("Error in disconnect_jack_ports handler: %s", e)
        return {"error": str(e)}


async def handle_disconnect_all_jack_ports(request):
    """Handler for disconnecting all JACK port connections"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        # Handle both HTTP requests and ServiceBus calls
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request
            
        from .models import DisconnectAllJackPortsCommand
        command = DisconnectAllJackPortsCommand(
            port_name=data.get("port_name")
        )

        success = await audio_service.disconnect_all_jack_ports(command)
        return {"success": success}

    except Exception as e:
        logger.error("Error in disconnect_all_jack_ports handler: %s", e)
        return {"error": str(e)}


async def handle_reset_jack_xruns(request):
    """Handler for resetting JACK xrun counter"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        success = await audio_service.reset_jack_xruns()
        return {"success": success}

    except Exception as e:
        logger.error("Error in reset_jack_xruns handler: %s", e)
        return {"error": str(e)}


async def handle_set_jack_buffer_size(request):
    """Handler for setting JACK buffer size"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        # Handle both HTTP requests and ServiceBus calls
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request
            
        from .models import SetJackBufferSizeCommand
        command = SetJackBufferSizeCommand(
            buffer_size=data.get("buffer_size")
        )

        success = await audio_service.set_jack_buffer_size(command)
        return {"success": success}

    except Exception as e:
        logger.error("Error in set_jack_buffer_size handler: %s", e)
        return {"error": str(e)}


# =============================================================================
# LV2 Plugin ServiceBus Message Handlers
# =============================================================================

async def handle_get_plugin_list(request):
    """Handler for getting LV2 plugin list"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        plugins = await audio_service.get_plugin_list()
        return {
            "success": True,
            "plugins": plugins
        }

    except Exception as e:
        logger.error("Error in get_plugin_list handler: %s", e)
        return {"error": str(e)}


async def handle_get_all_plugins(request):
    """Handler for getting all LV2 plugins"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        plugins = await audio_service.get_all_plugins()
        return {
            "success": True,
            "plugins": plugins
        }

    except Exception as e:
        logger.error("Error in get_all_plugins handler: %s", e)
        return {"error": str(e)}


async def handle_get_plugin_info(request):
    """Handler for getting detailed plugin information"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        # Handle both HTTP requests and ServiceBus calls
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request
            
        from .models import GetPluginInfoCommand
        command = GetPluginInfoCommand(
            plugin_uri=data.get("plugin_uri")
        )

        plugin_info = await audio_service.get_plugin_info(command)
        return {
            "success": True,
            "plugin_info": plugin_info.dict() if plugin_info else None
        }

    except Exception as e:
        logger.error("Error in get_plugin_info handler: %s", e)
        return {"error": str(e)}


async def handle_scan_plugins(request):
    """Handler for scanning LV2 plugins"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        # Handle both HTTP requests and ServiceBus calls
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request
            
        from .models import ScanPluginsCommand
        command = ScanPluginsCommand(
            force_refresh=data.get("force_refresh", False)
        )

        count = await audio_service.scan_plugins(command)
        return {
            "success": True,
            "plugin_count": count
        }

    except Exception as e:
        logger.error("Error in scan_plugins handler: %s", e)
        return {"error": str(e)}


async def handle_add_bundle(request):
    """Handler for adding LV2 bundle"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        # Handle both HTTP requests and ServiceBus calls
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request
            
        from .models import AddBundleCommand
        command = AddBundleCommand(
            bundle_path=data.get("bundle_path")
        )

        added_plugins = await audio_service.add_bundle(command)
        return {
            "success": True,
            "added_plugins": added_plugins
        }

    except Exception as e:
        logger.error("Error in add_bundle handler: %s", e)
        return {"error": str(e)}


async def handle_remove_bundle(request):
    """Handler for removing LV2 bundle"""
    if not audio_service:
        return {"error": "Audio service not initialized"}

    try:
        # Handle both HTTP requests and ServiceBus calls
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = request
            
        from .models import RemoveBundleCommand
        command = RemoveBundleCommand(
            bundle_path=data.get("bundle_path"),
            resource=data.get("resource")
        )

        removed_plugins = await audio_service.remove_bundle(command)
        return {
            "success": True,
            "removed_plugins": removed_plugins
        }

    except Exception as e:
        logger.error("Error in remove_bundle handler: %s", e)
        return {"error": str(e)}


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
