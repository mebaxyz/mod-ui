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

    # Phase 1 Critical mod-host commands
    service_bus.register_handler("activate_plugin", handle_activate_plugin)
    service_bus.register_handler("preload_plugin", handle_preload_plugin)
    service_bus.register_handler("bypass_plugin", handle_bypass_plugin)
    service_bus.register_handler("disconnect_all_ports", handle_disconnect_all_ports)
    service_bus.register_handler("get_cpu_load", handle_get_cpu_load)
    service_bus.register_handler("get_max_cpu_load", handle_get_max_cpu_load)

    # Phase 2 Preset Management
    service_bus.register_handler("load_preset", handle_load_preset)
    service_bus.register_handler("save_preset", handle_save_preset)
    service_bus.register_handler("show_presets", handle_show_presets)

    # Phase 3 Monitoring
    service_bus.register_handler("monitor_parameter", handle_monitor_parameter)
    service_bus.register_handler("monitor_output", handle_monitor_output)
    service_bus.register_handler("get_audio_levels", handle_get_audio_levels)
    service_bus.register_handler("flush_parameters", handle_flush_parameters)

    # Feedback Port Monitoring (New)
    service_bus.register_handler("monitor_audio_levels", handle_monitor_audio_levels)
    service_bus.register_handler("monitor_midi_control", handle_monitor_midi_control)
    service_bus.register_handler("monitor_midi_program", handle_monitor_midi_program)

    # Session Control Methods (Critical Missing)
    service_bus.register_handler("reset_session", handle_reset_session)
    service_bus.register_handler("mute_session", handle_mute_session)
    service_bus.register_handler("unmute_session", handle_unmute_session)
    service_bus.register_handler("get_session_state", handle_get_session_state)
    service_bus.register_handler("initialize_session", handle_initialize_session)

    # JACK Integration Methods (Critical Missing)
    service_bus.register_handler("get_jack_ports", handle_get_jack_ports)
    service_bus.register_handler("set_jack_buffer_size", handle_set_jack_buffer_size)
    service_bus.register_handler("jack_port_appeared", handle_jack_port_appeared)
    service_bus.register_handler("jack_port_deleted", handle_jack_port_deleted)
    service_bus.register_handler(
        "jack_buffer_size_changed", handle_jack_buffer_size_changed
    )

    # Phase 4 Patch Management
    service_bus.register_handler("set_patch_property", handle_set_patch_property)
    service_bus.register_handler("get_patch_property", handle_get_patch_property)

    # Phase 5 Bundle Management
    service_bus.register_handler("add_bundle", handle_add_bundle)
    service_bus.register_handler("remove_bundle", handle_remove_bundle)

    # Phase 6 MIDI Control
    service_bus.register_handler("midi_learn_parameter", handle_midi_learn_parameter)
    service_bus.register_handler("midi_map_parameter", handle_midi_map_parameter)
    service_bus.register_handler("midi_unmap_parameter", handle_midi_unmap_parameter)

    # Phase 7 Hardware Control
    service_bus.register_handler("cc_map_parameter", handle_cc_map_parameter)
    service_bus.register_handler("cc_unmap_parameter", handle_cc_unmap_parameter)
    service_bus.register_handler("cc_value_set", handle_cc_value_set)
    service_bus.register_handler("cv_map_parameter", handle_cv_map_parameter)
    service_bus.register_handler("cv_unmap_parameter", handle_cv_unmap_parameter)

    # Phase 8 Transport Control
    service_bus.register_handler("set_bpm", handle_set_bpm)
    service_bus.register_handler("set_beats_per_bar", handle_set_beats_per_bar)
    service_bus.register_handler("set_transport", handle_set_transport)
    service_bus.register_handler("transport_sync", handle_transport_sync)

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


# Phase 1 Critical mod-host command handlers
async def handle_activate_plugin(**_kwargs) -> Dict[str, Any]:
    """Activate a plugin instance"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    success = await plugin_manager.modhost.activate_plugin(instance_number)
    return {"success": success, "instance_number": instance_number}


async def handle_preload_plugin(**_kwargs) -> Dict[str, Any]:
    """Preload a plugin to reduce instantiation time"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    lv2_uri = _kwargs.get("lv2_uri")
    if not lv2_uri:
        raise ValueError("Missing required parameter: lv2_uri")

    success = await plugin_manager.modhost.preload_plugin(lv2_uri)
    return {"success": success, "lv2_uri": lv2_uri}


async def handle_bypass_plugin(**_kwargs) -> Dict[str, Any]:
    """Bypass or enable a plugin instance"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    bypass = _kwargs.get("bypass", True)  # Default to bypass=True
    success = await plugin_manager.modhost.bypass_plugin(instance_number, bypass)

    return {"success": success, "instance_number": instance_number, "bypassed": bypass}


async def handle_disconnect_all_ports(**_kwargs) -> Dict[str, Any]:
    """Disconnect all audio connections"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    success = await plugin_manager.modhost.disconnect_all_ports()
    return {"success": success}


async def handle_get_cpu_load(**_kwargs) -> Dict[str, Any]:
    """Get current CPU load percentage"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    cpu_load = await plugin_manager.modhost.get_cpu_load()
    return {"cpu_load": cpu_load, "unit": "percent"}


async def handle_get_max_cpu_load(**_kwargs) -> Dict[str, Any]:
    """Get maximum CPU load since last check"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    max_cpu_load = await plugin_manager.modhost.get_max_cpu_load()
    return {"max_cpu_load": max_cpu_load, "unit": "percent"}


# Phase 2 Preset Management handlers
async def handle_load_preset(**_kwargs) -> Dict[str, Any]:
    """Load a preset for a plugin instance"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    preset_uri = _kwargs.get("preset_uri")
    if not preset_uri:
        raise ValueError("Missing required parameter: preset_uri")

    success = await plugin_manager.modhost.load_preset(instance_number, preset_uri)
    return {
        "success": success,
        "instance_number": instance_number,
        "preset_uri": preset_uri,
    }


async def handle_save_preset(**_kwargs) -> Dict[str, Any]:
    """Save current plugin state as preset"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    preset_name = _kwargs.get("preset_name")
    if not preset_name:
        raise ValueError("Missing required parameter: preset_name")

    directory = _kwargs.get("directory", "/tmp/presets")  # Default directory
    filename = _kwargs.get("filename", f"{preset_name}.ttl")  # Default filename

    success = await plugin_manager.modhost.save_preset(
        instance_number, preset_name, directory, filename
    )
    return {
        "success": success,
        "instance_number": instance_number,
        "preset_name": preset_name,
        "directory": directory,
        "filename": filename,
    }


async def handle_show_presets(**_kwargs) -> Dict[str, Any]:
    """Show available presets for plugin"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    presets = await plugin_manager.modhost.show_presets(instance_number)
    return {"presets": presets, "instance_number": instance_number}


# Phase 3 Monitoring handlers
async def handle_monitor_parameter(**_kwargs) -> Dict[str, Any]:
    """Monitor parameter changes with conditions"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    param_symbol = _kwargs.get("param_symbol")
    if not param_symbol:
        raise ValueError("Missing required parameter: param_symbol")

    condition = _kwargs.get("condition", "=")  # Default to equality
    value = _kwargs.get("value")
    if value is None:
        raise ValueError("Missing required parameter: value")

    success = await plugin_manager.modhost.monitor_parameter(
        instance_number, param_symbol, condition, float(value)
    )
    return {
        "success": success,
        "instance_number": instance_number,
        "param_symbol": param_symbol,
        "condition": condition,
        "value": value,
    }


async def handle_monitor_output(**_kwargs) -> Dict[str, Any]:
    """Monitor audio output levels"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    output_port = _kwargs.get("output_port")
    if not output_port:
        raise ValueError("Missing required parameter: output_port")

    enable = _kwargs.get("enable", True)  # Default to enable
    success = await plugin_manager.modhost.monitor_output(output_port, enable)
    return {"success": success, "output_port": output_port, "enabled": enable}


async def handle_get_audio_levels(**_kwargs) -> Dict[str, Any]:
    """Get current audio level meters"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    levels = await plugin_manager.modhost.get_audio_levels()
    return {"audio_levels": levels}


async def handle_flush_parameters(**_kwargs) -> Dict[str, Any]:
    """Flush all parameter changes"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    success = await plugin_manager.modhost.flush_parameters()
    return {"success": success}


# Phase 4 Patch Management handlers
async def handle_set_patch_property(**_kwargs) -> Dict[str, Any]:
    """Set plugin property/patch value"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    property_uri = _kwargs.get("property_uri")
    if not property_uri:
        raise ValueError("Missing required parameter: property_uri")

    value = _kwargs.get("value")
    if value is None:
        raise ValueError("Missing required parameter: value")

    success = await plugin_manager.modhost.set_patch_property(
        instance_number, property_uri, str(value)
    )
    return {
        "success": success,
        "instance_number": instance_number,
        "property_uri": property_uri,
        "value": value,
    }


async def handle_get_patch_property(**_kwargs) -> Dict[str, Any]:
    """Get plugin property/patch value"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    property_uri = _kwargs.get("property_uri")
    if not property_uri:
        raise ValueError("Missing required parameter: property_uri")

    value = await plugin_manager.modhost.get_patch_property(
        instance_number, property_uri
    )
    return {
        "value": value,
        "instance_number": instance_number,
        "property_uri": property_uri,
    }


# Phase 5 Bundle Management handlers
async def handle_add_bundle(**_kwargs) -> Dict[str, Any]:
    """Add plugin bundle to available plugins"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    bundle_path = _kwargs.get("bundle_path")
    if not bundle_path:
        raise ValueError("Missing required parameter: bundle_path")

    success = await plugin_manager.modhost.add_bundle(bundle_path)
    return {"success": success, "bundle_path": bundle_path}


async def handle_remove_bundle(**_kwargs) -> Dict[str, Any]:
    """Remove plugin bundle"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    bundle_path = _kwargs.get("bundle_path")
    if not bundle_path:
        raise ValueError("Missing required parameter: bundle_path")

    success = await plugin_manager.modhost.remove_bundle(bundle_path)
    return {"success": success, "bundle_path": bundle_path}


# Phase 6 MIDI Control handlers
async def handle_midi_learn_parameter(**_kwargs) -> Dict[str, Any]:
    """Enable MIDI learning for parameter"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    param_symbol = _kwargs.get("param_symbol")
    if not param_symbol:
        raise ValueError("Missing required parameter: param_symbol")

    min_val = _kwargs.get("min_val", 0.0)
    max_val = _kwargs.get("max_val", 1.0)

    success = await plugin_manager.modhost.midi_learn_parameter(
        instance_number, param_symbol, float(min_val), float(max_val)
    )
    return {
        "success": success,
        "instance_number": instance_number,
        "param_symbol": param_symbol,
        "min_val": min_val,
        "max_val": max_val,
    }


async def handle_midi_map_parameter(**_kwargs) -> Dict[str, Any]:
    """Map MIDI CC to parameter"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    param_symbol = _kwargs.get("param_symbol")
    if not param_symbol:
        raise ValueError("Missing required parameter: param_symbol")

    channel = _kwargs.get("channel")
    if channel is None:
        raise ValueError("Missing required parameter: channel")

    cc = _kwargs.get("cc")
    if cc is None:
        raise ValueError("Missing required parameter: cc")

    min_val = _kwargs.get("min_val", 0.0)
    max_val = _kwargs.get("max_val", 1.0)

    success = await plugin_manager.modhost.midi_map_parameter(
        instance_number,
        param_symbol,
        int(channel),
        int(cc),
        float(min_val),
        float(max_val),
    )
    return {
        "success": success,
        "instance_number": instance_number,
        "param_symbol": param_symbol,
        "channel": channel,
        "cc": cc,
        "min_val": min_val,
        "max_val": max_val,
    }


async def handle_midi_unmap_parameter(**_kwargs) -> Dict[str, Any]:
    """Remove MIDI mapping from parameter"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    param_symbol = _kwargs.get("param_symbol")
    if not param_symbol:
        raise ValueError("Missing required parameter: param_symbol")

    success = await plugin_manager.modhost.midi_unmap_parameter(
        instance_number, param_symbol
    )
    return {
        "success": success,
        "instance_number": instance_number,
        "param_symbol": param_symbol,
    }


# Phase 7 Hardware Control handlers
async def handle_cc_map_parameter(**_kwargs) -> Dict[str, Any]:
    """Map Control Chain actuator to parameter"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    device_id = _kwargs.get("device_id")
    if device_id is None:
        raise ValueError("Missing required parameter: device_id")

    actuator_id = _kwargs.get("actuator_id")
    if actuator_id is None:
        raise ValueError("Missing required parameter: actuator_id")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    param_symbol = _kwargs.get("param_symbol")
    if not param_symbol:
        raise ValueError("Missing required parameter: param_symbol")

    min_val = _kwargs.get("min_val", 0.0)
    max_val = _kwargs.get("max_val", 1.0)

    success = await plugin_manager.modhost.cc_map_parameter(
        int(device_id),
        int(actuator_id),
        instance_number,
        param_symbol,
        float(min_val),
        float(max_val),
    )
    return {
        "success": success,
        "device_id": device_id,
        "actuator_id": actuator_id,
        "instance_number": instance_number,
        "param_symbol": param_symbol,
        "min_val": min_val,
        "max_val": max_val,
    }


async def handle_cc_unmap_parameter(**_kwargs) -> Dict[str, Any]:
    """Remove Control Chain mapping"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    device_id = _kwargs.get("device_id")
    if device_id is None:
        raise ValueError("Missing required parameter: device_id")

    actuator_id = _kwargs.get("actuator_id")
    if actuator_id is None:
        raise ValueError("Missing required parameter: actuator_id")

    success = await plugin_manager.modhost.cc_unmap_parameter(
        int(device_id), int(actuator_id)
    )
    return {"success": success, "device_id": device_id, "actuator_id": actuator_id}


async def handle_cc_value_set(**_kwargs) -> Dict[str, Any]:
    """Set Control Chain actuator value"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    device_id = _kwargs.get("device_id")
    if device_id is None:
        raise ValueError("Missing required parameter: device_id")

    actuator_id = _kwargs.get("actuator_id")
    if actuator_id is None:
        raise ValueError("Missing required parameter: actuator_id")

    value = _kwargs.get("value")
    if value is None:
        raise ValueError("Missing required parameter: value")

    success = await plugin_manager.modhost.cc_value_set(
        int(device_id), int(actuator_id), float(value)
    )
    return {
        "success": success,
        "device_id": device_id,
        "actuator_id": actuator_id,
        "value": value,
    }


async def handle_cv_map_parameter(**_kwargs) -> Dict[str, Any]:
    """Map CV input to parameter"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    param_symbol = _kwargs.get("param_symbol")
    if not param_symbol:
        raise ValueError("Missing required parameter: param_symbol")

    min_val = _kwargs.get("min_val", 0.0)
    max_val = _kwargs.get("max_val", 1.0)

    success = await plugin_manager.modhost.cv_map_parameter(
        instance_number, param_symbol, float(min_val), float(max_val)
    )
    return {
        "success": success,
        "instance_number": instance_number,
        "param_symbol": param_symbol,
        "min_val": min_val,
        "max_val": max_val,
    }


async def handle_cv_unmap_parameter(**_kwargs) -> Dict[str, Any]:
    """Remove CV mapping from parameter"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    instance_number = _kwargs.get("instance_number")
    if instance_number is None:
        raise ValueError("Missing required parameter: instance_number")

    param_symbol = _kwargs.get("param_symbol")
    if not param_symbol:
        raise ValueError("Missing required parameter: param_symbol")

    success = await plugin_manager.modhost.cv_unmap_parameter(
        instance_number, param_symbol
    )
    return {
        "success": success,
        "instance_number": instance_number,
        "param_symbol": param_symbol,
    }


# Phase 8 Transport Control handlers
async def handle_set_bpm(**_kwargs) -> Dict[str, Any]:
    """Set transport BPM"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    bpm = _kwargs.get("bpm")
    if bpm is None:
        raise ValueError("Missing required parameter: bpm")

    success = await plugin_manager.modhost.set_bpm(float(bpm))
    return {"success": success, "bpm": bpm}


async def handle_set_beats_per_bar(**_kwargs) -> Dict[str, Any]:
    """Set beats per bar"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    beats_per_bar = _kwargs.get("beats_per_bar")
    if beats_per_bar is None:
        raise ValueError("Missing required parameter: beats_per_bar")

    success = await plugin_manager.modhost.set_beats_per_bar(int(beats_per_bar))
    return {"success": success, "beats_per_bar": beats_per_bar}


async def handle_set_transport(**_kwargs) -> Dict[str, Any]:
    """Control transport state"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    rolling = _kwargs.get("rolling", False)
    beats_per_bar = _kwargs.get("beats_per_bar", 4)
    beat_type = _kwargs.get("beat_type", 4)

    success = await plugin_manager.modhost.set_transport(
        bool(rolling), int(beats_per_bar), int(beat_type)
    )
    return {
        "success": success,
        "rolling": rolling,
        "beats_per_bar": beats_per_bar,
        "beat_type": beat_type,
    }


async def handle_transport_sync(**_kwargs) -> Dict[str, Any]:
    """Set transport sync mode"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    sync_mode = _kwargs.get("sync_mode", "none")
    if not sync_mode:
        raise ValueError("Missing required parameter: sync_mode")

    success = await plugin_manager.modhost.transport_sync(str(sync_mode))
    return {"success": success, "sync_mode": sync_mode}

    return {"success": success, "midi_channel": midi_channel, "monitoring": enable}


# Session Control handlers (Critical Missing Functionality)
async def handle_reset_session(**_kwargs) -> Dict[str, Any]:
    """Reset entire session state"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    bank_id = _kwargs.get("bank_id")
    return await session_manager.reset_session(bank_id)


async def handle_mute_session(**_kwargs) -> Dict[str, Any]:
    """Mute audio output"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    return await session_manager.mute_session()


async def handle_unmute_session(**_kwargs) -> Dict[str, Any]:
    """Unmute audio output"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    return await session_manager.unmute_session()


async def handle_get_session_state(**_kwargs) -> Dict[str, Any]:
    """Get comprehensive session state"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    return await session_manager.get_session_state()


async def handle_initialize_session(**_kwargs) -> Dict[str, Any]:
    """Initialize session"""
    if not session_manager:
        raise RuntimeError("Session manager not initialized")

    return await session_manager.initialize_session()


# JACK Integration handlers (Critical Missing Functionality)
async def handle_get_jack_ports(**_kwargs) -> Dict[str, Any]:
    """Get available JACK ports"""
    if not modhost_bridge:
        raise RuntimeError("ModHost bridge not initialized")

    ports = await modhost_bridge.get_jack_ports()
    return {"ports": ports}


async def handle_set_jack_buffer_size(**_kwargs) -> Dict[str, Any]:
    """Set JACK buffer size"""
    if not modhost_bridge:
        raise RuntimeError("ModHost bridge not initialized")

    buffer_size = _kwargs.get("buffer_size")
    if buffer_size is None:
        raise ValueError("Missing required parameter: buffer_size")

    success = await modhost_bridge.set_buffer_size(int(buffer_size))
    return {"success": success, "buffer_size": buffer_size}


async def handle_jack_port_appeared(**_kwargs) -> Dict[str, Any]:
    """Handle JACK port appearance"""
    if not modhost_bridge:
        raise RuntimeError("ModHost bridge not initialized")

    port_name = _kwargs.get("port_name")
    if not port_name:
        raise ValueError("Missing required parameter: port_name")

    is_output = _kwargs.get("is_output", False)
    return await modhost_bridge.handle_port_appeared(port_name, bool(is_output))


async def handle_jack_port_deleted(**_kwargs) -> Dict[str, Any]:
    """Handle JACK port deletion"""
    if not modhost_bridge:
        raise RuntimeError("ModHost bridge not initialized")

    port_name = _kwargs.get("port_name")
    if not port_name:
        raise ValueError("Missing required parameter: port_name")

    return await modhost_bridge.handle_port_deleted(port_name)


async def handle_jack_buffer_size_changed(**_kwargs) -> Dict[str, Any]:
    """Handle JACK buffer size change"""
    if not modhost_bridge:
        raise RuntimeError("ModHost bridge not initialized")

    buffer_size = _kwargs.get("buffer_size")
    if buffer_size is None:
        raise ValueError("Missing required parameter: buffer_size")

    return await modhost_bridge.handle_buffer_size_changed(int(buffer_size))


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


# Feedback Port Monitoring handlers
async def handle_monitor_audio_levels(**_kwargs) -> Dict[str, Any]:
    """Monitor audio levels for a JACK port (sends data to feedback port)"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    port_name = _kwargs.get("port_name")
    if not port_name:
        raise ValueError("Missing required parameter: port_name")

    enable = _kwargs.get("enable", True)
    success = await plugin_manager.modhost.monitor_audio_levels(port_name, enable)

    return {"success": success, "port_name": port_name, "monitoring": enable}


async def handle_monitor_midi_control(**_kwargs) -> Dict[str, Any]:
    """Monitor MIDI control change messages (sends data to feedback port)"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    midi_channel = _kwargs.get("midi_channel")
    if midi_channel is None:
        raise ValueError("Missing required parameter: midi_channel")

    enable = _kwargs.get("enable", True)
    success = await plugin_manager.modhost.monitor_midi_control(midi_channel, enable)

    return {"success": success, "midi_channel": midi_channel, "monitoring": enable}


async def handle_monitor_midi_program(**_kwargs) -> Dict[str, Any]:
    """Monitor MIDI program change messages (sends data to feedback port)"""
    if not plugin_manager:
        raise RuntimeError("Plugin manager not initialized")

    midi_channel = _kwargs.get("midi_channel")
    if midi_channel is None:
        raise ValueError("Missing required parameter: midi_channel")

    enable = _kwargs.get("enable", True)
    success = await plugin_manager.modhost.monitor_midi_program(midi_channel, enable)

    return {"success": success, "midi_channel": midi_channel, "monitoring": enable}


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
