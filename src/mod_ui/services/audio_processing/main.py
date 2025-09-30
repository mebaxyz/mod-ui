"""
MOD UI - Audio Processing Service

Consolidated service handling audio engine management, plugin management, session management, and mod-host bridge.
This service consolidates the audio_engine, plugin_manager, session_service, and provides mod-host integration.

This service communicates exclusively via ZeroMQ ServiceBus (no HTTP endpoints).
"""

# Localized pylint - module requires use of global variables for runtime wiring
# pylint: disable=global-statement

import asyncio
import logging
import os
import signal
from typing import Any, Dict

from servicebus import Service

# Local components (use absolute imports so the module can run as __main__)
from mod_ui.services.audio_processing.modhost_bridge import ModHostBridge
from mod_ui.services.audio_processing.plugin_manager import PluginManager
from mod_ui.services.audio_processing.session_manager import SessionManager

# Configuration
SERVICE_NAME = "audio_processing"

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global components
modhost_bridge = None
plugin_manager = None
session_manager = None
service_bus = None
running = False


async def startup():
    """Service startup"""
    global service_bus, modhost_bridge, plugin_manager, session_manager, running

    logger.info("Starting %s service", SERVICE_NAME)

    # If already started, don't start again
    try:
        if (
            service_bus is not None
            and getattr(service_bus, "is_running", lambda: False)()
        ):
            logger.info("Service already started")
            return

        # Initialize service bus
        service_bus = Service(SERVICE_NAME)
        await service_bus.start()
        logger.info("ServiceBus started")

        # Initialize mod-host bridge
        modhost_bridge = ModHostBridge()

        # Optionally wait until mod-host is ready. Controlled by env var:
        # AUDIO_WAIT_FOR_MODHOST (true/false) and MODHOST_STARTUP_TIMEOUT (seconds or empty for indefinite)
        wait_for_modhost = os.getenv("AUDIO_WAIT_FOR_MODHOST", "true").lower() in (
            "1",
            "true",
            "yes",
        )
        timeout_env = os.getenv("MODHOST_STARTUP_TIMEOUT", "")
        timeout = None
        if timeout_env:
            try:
                timeout = float(timeout_env)
            except Exception:
                timeout = None

        if wait_for_modhost:
            logger.info(
                "Starting mod-host and waiting until ready (timeout=%s)", timeout
            )
            ok = await modhost_bridge.start_and_wait(timeout=timeout)
            if not ok:
                # Configurable fail-fast behavior: some deployments want the service
                # to abort startup if mod-host is not available. This is controlled
                # by AUDIO_WAIT_FOR_MODHOST_FAILFAST (true/false). Default: false
                # to preserve the current non-fatal behaviour.
                failfast = os.getenv(
                    "AUDIO_WAIT_FOR_MODHOST_FAILFAST", "false"
                ).lower() in (
                    "1",
                    "true",
                    "yes",
                )

                if failfast:
                    logger.error(
                        "mod-host failed to become ready within timeout=%s; failing startup because AUDIO_WAIT_FOR_MODHOST_FAILFAST=%s",
                        timeout,
                        failfast,
                    )
                    # Raise to trigger the outer exception handler which will perform
                    # cleanup (shutdown) and propagate the error to the caller.
                    raise RuntimeError("mod-host did not become ready within timeout")

                # Non-fatal: continue startup but warn the operator.
                logger.warning(
                    "mod-host failed to become ready within timeout=%s; continuing startup without mod-host",
                    timeout,
                )
            else:
                logger.info("ModHost bridge started and ready")
        else:
            # Start but do not wait
            await modhost_bridge.start()
            logger.info("ModHost bridge started (not waiting)")

        # Initialize plugin manager
        plugin_manager = PluginManager(modhost_bridge, service_bus)
        await plugin_manager.initialize()
        logger.info("Plugin manager initialized")

        # Initialize session manager
        session_manager = SessionManager(plugin_manager, modhost_bridge, service_bus)
        logger.info("Session manager initialized")

        # Register ServiceBus methods
        await register_service_methods()

        running = True
        logger.info("%s service started successfully", SERVICE_NAME)

    except Exception as e:
        logger.error("Failed to start %s service: %s", SERVICE_NAME, e)
        await shutdown()
        raise


async def shutdown():
    """Service shutdown"""
    global service_bus, modhost_bridge, plugin_manager, session_manager, running

    logger.info("Shutting down %s service", SERVICE_NAME)
    running = False

    if session_manager:
        logger.info("Shutting down session manager")

    if plugin_manager:
        await plugin_manager.shutdown()
        logger.info("Plugin manager shutdown")

    if modhost_bridge:
        await modhost_bridge.stop()
        logger.info("ModHost bridge stopped")

    if service_bus:
        await service_bus.stop()
        logger.info("ServiceBus stopped")

    # Clear globals so future startup attempts can rebind sockets
    service_bus = None
    modhost_bridge = None
    plugin_manager = None
    session_manager = None


async def register_service_methods():
    """Register ServiceBus RPC methods"""
    if not service_bus:
        return

    # Plugin management methods
    service_bus.register_handler("get_available_plugins", handle_get_available_plugins)
    service_bus.register_handler("load_plugin", handle_load_plugin)
    service_bus.register_handler("unload_plugin", handle_unload_plugin)
    service_bus.register_handler("get_plugin_info", handle_get_plugin_info)
    service_bus.register_handler("list_instances", handle_list_instances)

    # Parameter control methods
    service_bus.register_handler("set_parameter", handle_set_parameter)
    service_bus.register_handler("get_parameter", handle_get_parameter)

    # Session management methods
    service_bus.register_handler("create_pedalboard", handle_create_pedalboard)
    service_bus.register_handler("load_pedalboard", handle_load_pedalboard)
    service_bus.register_handler("save_pedalboard", handle_save_pedalboard)
    service_bus.register_handler(
        "get_current_pedalboard", handle_get_current_pedalboard
    )

    # Connection methods
    service_bus.register_handler("create_connection", handle_create_connection)
    service_bus.register_handler("remove_connection", handle_remove_connection)

    # Snapshot methods
    service_bus.register_handler("create_snapshot", handle_create_snapshot)
    service_bus.register_handler("apply_snapshot", handle_apply_snapshot)

    # Health check method
    service_bus.register_handler("health", handle_health_check)

    # Persistence RPCs
    service_bus.register_handler(
        "list_saved_pedalboards", handle_list_saved_pedalboards
    )
    service_bus.register_handler("load_saved_pedalboard", handle_load_saved_pedalboard)
    service_bus.register_handler(
        "delete_saved_pedalboard", handle_delete_saved_pedalboard
    )

    service_bus.register_handler(
        "export_saved_pedalboard", handle_export_saved_pedalboard
    )
    service_bus.register_handler("import_pedalboard", handle_import_pedalboard)

    # Echo for tests
    service_bus.register_handler("echo", handle_echo)

    logger.info("ServiceBus methods registered")


# ServiceBus method handlers
async def handle_get_available_plugins(**_kwargs) -> Dict[str, Any]:
    """Get available plugins"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")
    return await plugin_manager.get_available_plugins()


async def handle_load_plugin(**_kwargs) -> Dict[str, Any]:
    """Load plugin"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    uri = _kwargs.get("uri")
    if not uri:
        raise ValueError("Missing required parameter: uri")

    x = _kwargs.get("x", 0.0)
    y = _kwargs.get("y", 0.0)
    parameters = _kwargs.get("parameters")

    return await plugin_manager.load_plugin(uri, x, y, parameters)


async def handle_unload_plugin(**_kwargs) -> Dict[str, Any]:
    """Unload plugin"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_id = _kwargs.get("instance_id")
    if not instance_id:
        raise ValueError("Missing required parameter: instance_id")

    return await plugin_manager.unload_plugin(instance_id)


async def handle_get_plugin_info(**_kwargs) -> Dict[str, Any]:
    """Get plugin info"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_id = _kwargs.get("instance_id")
    if not instance_id:
        raise ValueError("Missing required parameter: instance_id")

    return await plugin_manager.get_plugin_info(instance_id)


async def handle_list_instances(**_kwargs) -> Dict[str, Any]:
    """List plugin instances"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    return await plugin_manager.list_instances()


async def handle_set_parameter(**_kwargs) -> Dict[str, Any]:
    """Set plugin parameter"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_id = _kwargs.get("instance_id")
    parameter = _kwargs.get("parameter")
    value = _kwargs.get("value")

    if not all([instance_id, parameter, value is not None]):
        raise ValueError("Missing required parameters: instance_id, parameter, value")

    return await plugin_manager.set_parameter(instance_id, parameter, value)


async def handle_get_parameter(**_kwargs) -> Dict[str, Any]:
    """Get plugin parameter"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_id = _kwargs.get("instance_id")
    parameter = _kwargs.get("parameter")

    if not all([instance_id, parameter]):
        raise ValueError("Missing required parameters: instance_id, parameter")

    return await plugin_manager.get_parameter(instance_id, parameter)


async def handle_create_pedalboard(**_kwargs) -> Dict[str, Any]:
    """Create pedalboard"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    name = _kwargs.get("name")
    if not name:
        raise ValueError("Missing required parameter: name")

    description = _kwargs.get("description", "")

    return await session_manager.create_pedalboard(name, description)


async def handle_load_pedalboard(**_kwargs) -> Dict[str, Any]:
    """Load pedalboard"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    pedalboard_data = _kwargs.get("pedalboard_data")
    if not pedalboard_data:
        raise ValueError("Missing required parameter: pedalboard_data")

    return await session_manager.load_pedalboard(pedalboard_data)


async def handle_save_pedalboard(**_kwargs) -> Dict[str, Any]:
    """Save pedalboard"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    return await session_manager.save_pedalboard()


async def handle_get_current_pedalboard(**_kwargs) -> Dict[str, Any]:
    """Get current pedalboard"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    return await session_manager.get_current_pedalboard()


async def handle_create_connection(**_kwargs) -> Dict[str, Any]:
    """Create connection"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    source_plugin = _kwargs.get("source_plugin")
    source_port = _kwargs.get("source_port")
    target_plugin = _kwargs.get("target_plugin")
    target_port = _kwargs.get("target_port")

    if not all([source_plugin, source_port, target_plugin, target_port]):
        raise ValueError(
            "Missing required parameters: source_plugin, source_port, target_plugin, target_port"
        )

    return await session_manager.create_connection(
        source_plugin, source_port, target_plugin, target_port
    )


async def handle_remove_connection(**_kwargs) -> Dict[str, Any]:
    """Remove connection"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    connection_id = _kwargs.get("connection_id")
    if not connection_id:
        raise ValueError("Missing required parameter: connection_id")

    return await session_manager.remove_connection(connection_id)


async def handle_create_snapshot(**_kwargs) -> Dict[str, Any]:
    """Create snapshot"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    name = _kwargs.get("name")
    if not name:
        raise ValueError("Missing required parameter: name")

    return await session_manager.create_snapshot(name)


async def handle_apply_snapshot(**_kwargs) -> Dict[str, Any]:
    """Apply snapshot"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    snapshot = _kwargs.get("snapshot")
    if not snapshot:
        raise ValueError("Missing required parameter: snapshot")

    return await session_manager.apply_snapshot(snapshot)


async def handle_health_check(**_kwargs) -> Dict[str, Any]:
    """Health check via ServiceBus"""
    modhost_status = modhost_bridge.get_status() if modhost_bridge else None

    return {
        "service": SERVICE_NAME,
        "status": "healthy" if running else "stopped",
        "details": {
            "modhost": modhost_status,
            "plugin_manager_ready": plugin_manager is not None,
            "session_manager_ready": session_manager is not None,
            "service_bus_connected": service_bus.is_running() if service_bus else False,
            "loaded_plugins": len(plugin_manager.instances) if plugin_manager else 0,
            "active_connections": (
                len(session_manager.connections) if session_manager else 0
            ),
        },
    }


async def handle_echo(**_kwargs) -> Dict[str, Any]:
    """Echo method for testing"""
    message = _kwargs.get("message", "")
    return {"echo": message}


async def handle_list_saved_pedalboards(**_kwargs) -> Dict[str, Any]:
    from mod_ui.services.audio_processing import storage

    items = storage.list_pedalboards()
    return {"saved": items}


async def handle_load_saved_pedalboard(**_kwargs) -> Dict[str, Any]:
    pb_id = _kwargs.get("id")
    if not pb_id:
        raise ValueError("Missing required parameter: id")

    from mod_ui.services.audio_processing import storage

    data = storage.load_pedalboard(pb_id)
    if data is None:
        raise ValueError(f"Pedalboard not found: {pb_id}")

    return {"pedalboard": data}


async def handle_delete_saved_pedalboard(**_kwargs) -> Dict[str, Any]:
    pb_id = _kwargs.get("id")
    if not pb_id:
        raise ValueError("Missing required parameter: id")

    from mod_ui.services.audio_processing import storage

    ok = storage.delete_pedalboard(pb_id)
    return {"deleted": ok}


async def handle_export_saved_pedalboard(**_kwargs) -> Dict[str, Any]:
    pb_id = _kwargs.get("id")
    out_path = _kwargs.get("out_path")
    if not pb_id or not out_path:
        raise ValueError("Missing required parameters: id, out_path")

    from mod_ui.services.audio_processing import storage

    ok = storage.export_pedalboard(pb_id, out_path)
    return {"exported": ok, "out_path": out_path}


async def handle_import_pedalboard(**_kwargs) -> Dict[str, Any]:
    file_path = _kwargs.get("file_path")
    if not file_path:
        raise ValueError("Missing required parameter: file_path")

    from mod_ui.services.audio_processing import storage

    res = storage.import_pedalboard(file_path)
    if not res:
        raise ValueError("Import failed or file invalid")

    pb_id, path = res
    return {"imported_id": pb_id, "path": path}


async def main():
    """Main service entry point"""
    try:
        # Start the service
        await startup()

        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, _frame):
            logger.info("Received signal %s, shutting down...", signum)
            asyncio.create_task(shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Keep the service running
        while running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error("Service failed: %s", e)
        raise
    finally:
        await shutdown()


if __name__ == "__main__":
    asyncio.run(main())
