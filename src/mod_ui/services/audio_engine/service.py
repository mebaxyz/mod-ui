"""
Audio Engine Service

High-level service for managing audio engine operations including mod-host communication,
JACK audio connection management, and LV2 plugin discovery.
This service provides a clean async API for plugin management, transport control,
audio routing, and system-level audio operations.
"""

import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from .connection import (
    AudioEngineCommand,
    AudioEngineResponse,
    ConnectionStatus,
    ModHostConnectionManager,
)
from .jack_lv2_utils import get_jack_manager, get_lv2_manager, cleanup_managers
from .models import (
    AddPluginCommand,
    AudioConnection,
    AudioEngineState,
    AudioPortInfo,
    BypassPluginCommand,
    ConnectPortsCommand,
    DisconnectPortsCommand,
    LoadPresetCommand,
    PluginInstance,
    PluginParameterChange,
    RemovePluginCommand,
    SetParameterCommand,
    SetTransportCommand,
    TransportState,
    # JACK and LV2 models
    ConnectJackPortsCommand,
    DisconnectJackPortsCommand,
    DisconnectAllJackPortsCommand,
    SetJackBufferSizeCommand,
    ScanPluginsCommand,
    AddBundleCommand,
    RemoveBundleCommand,
    GetPluginInfoCommand,
    JackData,
    JackPortInfo,
    JackConnectionInfo,
    LV2PluginInfo,
)

logger = logging.getLogger(__name__)


class AudioEngineService:
    """High-level audio engine service with mod-host, JACK, and LV2 support"""

    def __init__(self):
        self.connection = ModHostConnectionManager()
        self.state = AudioEngineState()
        self.parameter_change_handlers: List[
            Callable[[PluginParameterChange], None]
        ] = []

        # JACK and LV2 managers
        self.jack_manager = get_jack_manager()
        self.lv2_manager = get_lv2_manager()

        # Register for real-time messages
        self.connection.add_message_handler(self._handle_realtime_message)

    async def start(self) -> bool:
        """Start the audio engine service"""
        logger.info("Starting audio engine service with JACK and LV2 support")
        success = await self.connection.connect()
        if success:
            await self._initialize_state()
        
        # Initialize JACK data in state
        await self._update_jack_state()
        
        return success

    async def stop(self):
        """Stop the audio engine service"""
        logger.info("Stopping audio engine service")
        await self.connection.disconnect()
        cleanup_managers()

    @property
    def is_connected(self) -> bool:
        """Check if connected to mod-host"""
        return self.connection.status == ConnectionStatus.CONNECTED

    async def get_state(self) -> AudioEngineState:
        """Get current audio engine state"""
        return self.state.copy()

    # Plugin Management
    async def add_plugin(self, command: AddPluginCommand) -> PluginInstance:
        """Add a plugin instance to the audio engine"""
        if not self.is_connected:
            raise RuntimeError("Audio engine not connected")

        # Send add_plugin command to mod-host
        audio_cmd = AudioEngineCommand(
            command="add_plugin",
            parameters={
                "uri": command.plugin_uri,
                "instance": command.instance_id,
                "x": command.x,
                "y": command.y,
            },
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise RuntimeError(
                f"Failed to add plugin: {response.error}"
            )

        # Create plugin instance
        plugin = PluginInstance(
            instance_id=command.instance_id,
            plugin_uri=command.plugin_uri,
            x=command.x,
            y=command.y,
        )

        # Update local state
        self.state.plugins[command.instance_id] = plugin

        # TODO: Query plugin ports and parameters
        await self._update_plugin_ports(plugin)

        logger.info("Added plugin %s (%s)", command.instance_id, command.plugin_uri)
        return plugin

    async def remove_plugin(self, command: RemovePluginCommand) -> bool:
        """Remove a plugin instance from the audio engine"""
        if not self.is_connected:
            raise RuntimeError("Audio engine not connected")

        if command.instance_id not in self.state.plugins:
            raise ValueError("Plugin not found")

        # Send remove_plugin command to mod-host
        audio_cmd = AudioEngineCommand(
            command="remove_plugin",
            parameters={"instance": command.instance_id},
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise RuntimeError(
                f"Failed to remove plugin: {response.error}"
            )

        # Remove from local state
        del self.state.plugins[command.instance_id]

        # Remove connections involving this plugin
        self.state.connections = [
            conn
            for conn in self.state.connections
            if not (
                conn.from_port.startswith(command.instance_id)
                or conn.to_port.startswith(command.instance_id)
            )
        ]

        logger.info("Removed plugin %s", command.instance_id)
        return True

    async def set_parameter(self, command: SetParameterCommand) -> bool:
        """Set a plugin parameter value"""
        if not self.is_connected:
            raise RuntimeError("Audio engine not connected")

        if command.instance_id not in self.state.plugins:
            raise ValueError("Plugin not found")

        # Send param_set command to mod-host
        audio_cmd = AudioEngineCommand(
            command="param_set",
            parameters={
                "instance": command.instance_id,
                "symbol": command.port_symbol,
                "value": command.value,
            },
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise RuntimeError(
                f"Failed to set parameter: {response.error}"
            )

        # Update local state
        plugin = self.state.plugins[command.instance_id]
        plugin.ports[command.port_symbol] = command.value

        logger.debug(
            "Set parameter %s:%s = %f",
            command.instance_id,
            command.port_symbol,
            command.value,
        )
        return True

    # Audio Routing
    async def connect_ports(self, command: ConnectPortsCommand) -> AudioConnection:
        """Connect two audio ports"""
        if not self.is_connected:
            raise RuntimeError("Audio engine not connected")

        # Send connect command to mod-host
        audio_cmd = AudioEngineCommand(
            command="connect",
            parameters={"from": command.from_port, "to": command.to_port},
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise RuntimeError(
                f"Failed to connect ports: {response.error}"
            )

        # Create connection
        connection = AudioConnection(
            from_port=command.from_port,
            to_port=command.to_port,
            connection_id=f"{command.from_port}:{command.to_port}",
        )

        # Update local state
        self.state.connections.append(connection)

        logger.info("Connected %s -> %s", command.from_port, command.to_port)
        return connection

    async def disconnect_ports(self, command: DisconnectPortsCommand) -> bool:
        """Disconnect two audio ports"""
        if not self.is_connected:
            raise RuntimeError("Audio engine not connected")

        # Send disconnect command to mod-host
        audio_cmd = AudioEngineCommand(
            command="disconnect",
            parameters={"from": command.from_port, "to": command.to_port},
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise RuntimeError(
                f"Failed to disconnect ports: {response.error}"
            )

        # Remove from local state
        self.state.connections = [
            conn
            for conn in self.state.connections
            if not (
                conn.from_port == command.from_port and conn.to_port == command.to_port
            )
        ]

        logger.info("Disconnected %s -> %s", command.from_port, command.to_port)
        return True

    # Transport Control
    async def set_transport(self, command: SetTransportCommand) -> TransportState:
        """Set transport state"""
        if not self.is_connected:
            raise RuntimeError("Audio engine not connected")

        current_transport = self.state.transport

        # Update individual transport parameters
        if command.bpm is not None:
            audio_cmd = AudioEngineCommand(
                command="bpm",
                parameters={"value": command.bpm},
                callback_id=str(uuid.uuid4()),
            )
            response = await self.connection.send_command(audio_cmd)
            if response.status == "success":
                current_transport.bpm = command.bpm

        if command.bpb is not None:
            audio_cmd = AudioEngineCommand(
                command="bpb",
                parameters={"value": command.bpb},
                callback_id=str(uuid.uuid4()),
            )
            response = await self.connection.send_command(audio_cmd)
            if response.status == "success":
                current_transport.bpb = command.bpb

        if command.rolling is not None:
            audio_cmd = AudioEngineCommand(
                command="transport" if command.rolling else "transport_stop",
                parameters={},
                callback_id=str(uuid.uuid4()),
            )
            response = await self.connection.send_command(audio_cmd)
            if response.status == "success":
                current_transport.rolling = command.rolling
                current_transport.speed = 1.0 if command.rolling else 0.0

        return current_transport

    async def get_transport(self) -> TransportState:
        """Get current transport state"""
        return self.state.transport.copy()

    # Plugin Presets
    async def load_preset(self, command: LoadPresetCommand) -> bool:
        """Load a plugin preset"""
        if not self.is_connected:
            raise RuntimeError("Audio engine not connected")

        if command.instance_id not in self.state.plugins:
            raise ValueError("Plugin not found")

        # Send preset_load command to mod-host
        audio_cmd = AudioEngineCommand(
            command="preset_load",
            parameters={"instance": command.instance_id, "uri": command.preset_uri},
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise RuntimeError(
                f"Failed to load preset: {response.error}"
            )

        # Update local state
        plugin = self.state.plugins[command.instance_id]
        plugin.preset_uri = command.preset_uri

        # TODO: Update plugin parameter values after preset load

        logger.info(
            "Loaded preset %s for plugin %s", command.preset_uri, command.instance_id
        )
        return True

    async def bypass_plugin(self, command: BypassPluginCommand) -> bool:
        """Bypass or enable a plugin"""
        if not self.is_connected:
            raise RuntimeError("Audio engine not connected")

        if command.instance_id not in self.state.plugins:
            raise ValueError("Plugin not found")

        # Send bypass command to mod-host
        audio_cmd = AudioEngineCommand(
            command="bypass",
            parameters={
                "instance": command.instance_id,
                "bypass": 1 if command.bypass else 0,
            },
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise RuntimeError(
                f"Failed to bypass plugin: {response.error}"
            )

        # Update local state
        plugin = self.state.plugins[command.instance_id]
        plugin.bypass = command.bypass

        logger.info("Set plugin %s bypass = %s", command.instance_id, command.bypass)
        return True

    # Event Handling
    def add_parameter_change_handler(
        self, handler: Callable[[PluginParameterChange], None]
    ):
        """Add a handler for parameter change events"""
        self.parameter_change_handlers.append(handler)

    def remove_parameter_change_handler(
        self, handler: Callable[[PluginParameterChange], None]
    ):
        """Remove a parameter change handler"""
        if handler in self.parameter_change_handlers:
            self.parameter_change_handlers.remove(handler)

    async def _handle_realtime_message(self, cmd: str, data: str):
        """Handle real-time messages from mod-host"""
        try:
            if cmd == "param_set":
                # Parse parameter change message
                parts = data.split(" ", 2)
                if len(parts) >= 3:
                    instance_id, port_symbol, value_str = parts
                    value = float(value_str)

                    # Update local state
                    if instance_id in self.state.plugins:
                        self.state.plugins[instance_id].ports[port_symbol] = value

                    # Notify handlers
                    change = PluginParameterChange(
                        instance_id=instance_id, port_symbol=port_symbol, value=value
                    )

                    for handler in self.parameter_change_handlers:
                        try:
                            handler(change)
                        except Exception as e:
                            logger.error("Error in parameter change handler: %s", e)

            elif cmd == "transport":
                # Parse transport message
                parts = data.split(" ")
                if len(parts) >= 3:
                    rolling = bool(int(parts[0]))
                    bpb = float(parts[1])
                    bpm = float(parts[2])

                    self.state.transport.rolling = rolling
                    self.state.transport.bpb = bpb
                    self.state.transport.bpm = bpm
                    self.state.transport.speed = 1.0 if rolling else 0.0

            # TODO: Handle other real-time messages (plugin_add, plugin_remove, etc.)

        except Exception as e:
            logger.error("Error handling real-time message %s:%s - %s", cmd, data, e)

    async def _initialize_state(self):
        """Initialize audio engine state after connection"""
        # TODO: Query current state from mod-host
        # This would involve sending commands to get:
        # - Current plugins and their parameters
        # - Current connections
        # - Transport state
        # - Available ports
        
        # Initialize JACK and LV2 data
        await self._update_jack_state()

    async def _update_plugin_ports(self, plugin: PluginInstance):
        """Update plugin port information"""
        # TODO: Query plugin ports from mod-host
        # This would get parameter ranges, defaults, and audio/cv port info
        pass

    async def _update_jack_state(self):
        """Update JACK system state in audio engine state"""
        try:
            # Get current JACK data
            jack_data = self.jack_manager.get_jack_data()
            self.state.jack_data = jack_data
            
            # Get hardware ports
            audio_in_ports = self.jack_manager.get_hardware_ports(is_audio=True, is_output=False)
            audio_out_ports = self.jack_manager.get_hardware_ports(is_audio=True, is_output=True)
            
            self.state.jack_hardware_ports = audio_in_ports + audio_out_ports
            
        except Exception as e:
            logger.warning(f"Failed to update JACK state: {e}")

    # =============================================================================
    # JACK Audio Connection Management Methods  
    # =============================================================================

    async def get_jack_data(self) -> JackData:
        """Get current JACK system data"""
        return self.jack_manager.get_jack_data()

    async def get_jack_hardware_ports(self, is_audio: bool = True, is_output: bool = False) -> List[JackPortInfo]:
        """Get JACK hardware ports"""
        return self.jack_manager.get_hardware_ports(is_audio, is_output)

    async def connect_jack_ports(self, command: ConnectJackPortsCommand) -> JackConnectionInfo:
        """Connect two JACK ports"""
        success = self.jack_manager.connect_ports(command.output_port, command.input_port)
        if not success:
            raise RuntimeError(
                status_code=500, 
                detail=f"Failed to connect JACK ports {command.output_port} -> {command.input_port}"
            )
        
        connection = JackConnectionInfo(
            output_port=command.output_port,
            input_port=command.input_port,
            connection_id=f"{command.output_port}:{command.input_port}"
        )
        
        # Update local state
        self.state.jack_connections.append(connection)
        
        logger.info("Connected JACK ports %s -> %s", command.output_port, command.input_port)
        return connection

    async def disconnect_jack_ports(self, command: DisconnectJackPortsCommand) -> bool:
        """Disconnect two JACK ports"""
        success = self.jack_manager.disconnect_ports(command.output_port, command.input_port)
        if not success:
            raise RuntimeError(
                status_code=500,
                detail=f"Failed to disconnect JACK ports {command.output_port} -> {command.input_port}"
            )
        
        # Update local state
        self.state.jack_connections = [
            conn for conn in self.state.jack_connections
            if not (conn.output_port == command.output_port and conn.input_port == command.input_port)
        ]
        
        logger.info("Disconnected JACK ports %s -> %s", command.output_port, command.input_port)
        return True

    async def disconnect_all_jack_ports(self, command: DisconnectAllJackPortsCommand) -> bool:
        """Disconnect all connections from a JACK port"""
        success = self.jack_manager.disconnect_all_ports(command.port_name)
        if not success:
            raise RuntimeError(
                status_code=500,
                detail=f"Failed to disconnect all ports from {command.port_name}"
            )
        
        # Update local state
        self.state.jack_connections = [
            conn for conn in self.state.jack_connections
            if not (conn.output_port == command.port_name or conn.input_port == command.port_name)
        ]
        
        logger.info("Disconnected all ports from %s", command.port_name)
        return True

    async def reset_jack_xruns(self) -> bool:
        """Reset JACK xrun counter"""
        try:
            self.jack_manager.reset_xruns()
            logger.info("Reset JACK xruns")
            return True
        except Exception as e:
            logger.error(f"Failed to reset JACK xruns: {e}")
            return False

    async def set_jack_buffer_size(self, command: SetJackBufferSizeCommand) -> bool:
        """Set JACK buffer size"""
        success = self.jack_manager.set_buffer_size(command.buffer_size)
        if not success:
            raise RuntimeError(
                status_code=500,
                detail=f"Failed to set JACK buffer size to {command.buffer_size}"
            )
        
        logger.info("Set JACK buffer size to %d", command.buffer_size)
        return True

    # =============================================================================
    # LV2 Plugin Management Methods
    # =============================================================================

    async def get_plugin_list(self) -> List[str]:
        """Get list of all available LV2 plugin URIs"""
        return self.lv2_manager.get_plugin_list()

    async def get_all_plugins(self) -> List[Dict[str, Any]]:
        """Get all available LV2 plugins (lightweight info)"""
        return self.lv2_manager.get_all_plugins()

    async def get_plugin_info(self, command: GetPluginInfoCommand) -> Optional[LV2PluginInfo]:
        """Get detailed information about an LV2 plugin"""
        plugin_info = self.lv2_manager.get_plugin_info(command.plugin_uri)
        if not plugin_info:
            raise RuntimeError(
                status_code=404,
                detail=f"Plugin not found: {command.plugin_uri}"
            )
        return plugin_info

    async def scan_plugins(self, command: ScanPluginsCommand) -> int:
        """Rescan all LV2 plugins"""
        try:
            plugins = self.lv2_manager.get_all_plugins()
            count = len(plugins)
            logger.info("Scanned %d LV2 plugins", count)
            return count
        except Exception as e:
            logger.error(f"Failed to scan plugins: {e}")
            raise RuntimeError(
                status_code=500,
                detail=f"Failed to scan plugins: {e}"
            )

    async def add_bundle(self, command: AddBundleCommand) -> List[str]:
        """Add an LV2 bundle to the plugin world"""
        try:
            added_plugins = self.lv2_manager.add_bundle(command.bundle_path)
            logger.info("Added bundle %s with %d plugins", command.bundle_path, len(added_plugins))
            return added_plugins
        except Exception as e:
            logger.error(f"Failed to add bundle {command.bundle_path}: {e}")
            raise RuntimeError(
                status_code=500,
                detail=f"Failed to add bundle: {e}"
            )

    async def remove_bundle(self, command: RemoveBundleCommand) -> List[str]:
        """Remove an LV2 bundle from the plugin world"""
        try:
            removed_plugins = self.lv2_manager.remove_bundle(command.bundle_path, command.resource)
            logger.info("Removed bundle %s with %d plugins", command.bundle_path, len(removed_plugins))
            return removed_plugins
        except Exception as e:
            logger.error(f"Failed to remove bundle {command.bundle_path}: {e}")
            raise RuntimeError(
                status_code=500,
                detail=f"Failed to remove bundle: {e}"
            )
