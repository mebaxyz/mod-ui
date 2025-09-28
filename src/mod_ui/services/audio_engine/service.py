"""
Audio Engine Service

High-level service for managing audio engine operations.
This service provides a clean async API for plugin management, transport control,
and audio routing while abstracting the low-level mod-host communication.
"""

import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException

from .connection import (
    AudioEngineCommand,
    AudioEngineResponse,
    ConnectionStatus,
    ModHostConnectionManager,
)
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
)

logger = logging.getLogger(__name__)


class AudioEngineService:
    """High-level audio engine service"""

    def __init__(self):
        self.connection = ModHostConnectionManager()
        self.state = AudioEngineState()
        self.parameter_change_handlers: List[
            Callable[[PluginParameterChange], None]
        ] = []

        # Register for real-time messages
        self.connection.add_message_handler(self._handle_realtime_message)

    async def start(self) -> bool:
        """Start the audio engine service"""
        logger.info("Starting audio engine service")
        success = await self.connection.connect()
        if success:
            await self._initialize_state()
        return success

    async def stop(self):
        """Stop the audio engine service"""
        logger.info("Stopping audio engine service")
        await self.connection.disconnect()

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
            raise HTTPException(status_code=503, detail="Audio engine not connected")

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
            raise HTTPException(
                status_code=500, detail=f"Failed to add plugin: {response.error}"
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
            raise HTTPException(status_code=503, detail="Audio engine not connected")

        if command.instance_id not in self.state.plugins:
            raise HTTPException(status_code=404, detail="Plugin not found")

        # Send remove_plugin command to mod-host
        audio_cmd = AudioEngineCommand(
            command="remove_plugin",
            parameters={"instance": command.instance_id},
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise HTTPException(
                status_code=500, detail=f"Failed to remove plugin: {response.error}"
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
            raise HTTPException(status_code=503, detail="Audio engine not connected")

        if command.instance_id not in self.state.plugins:
            raise HTTPException(status_code=404, detail="Plugin not found")

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
            raise HTTPException(
                status_code=500, detail=f"Failed to set parameter: {response.error}"
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
            raise HTTPException(status_code=503, detail="Audio engine not connected")

        # Send connect command to mod-host
        audio_cmd = AudioEngineCommand(
            command="connect",
            parameters={"from": command.from_port, "to": command.to_port},
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise HTTPException(
                status_code=500, detail=f"Failed to connect ports: {response.error}"
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
            raise HTTPException(status_code=503, detail="Audio engine not connected")

        # Send disconnect command to mod-host
        audio_cmd = AudioEngineCommand(
            command="disconnect",
            parameters={"from": command.from_port, "to": command.to_port},
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise HTTPException(
                status_code=500, detail=f"Failed to disconnect ports: {response.error}"
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
            raise HTTPException(status_code=503, detail="Audio engine not connected")

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
            raise HTTPException(status_code=503, detail="Audio engine not connected")

        if command.instance_id not in self.state.plugins:
            raise HTTPException(status_code=404, detail="Plugin not found")

        # Send preset_load command to mod-host
        audio_cmd = AudioEngineCommand(
            command="preset_load",
            parameters={"instance": command.instance_id, "uri": command.preset_uri},
            callback_id=str(uuid.uuid4()),
            modifies_pedalboard=True,
        )

        response = await self.connection.send_command(audio_cmd)

        if response.status != "success":
            raise HTTPException(
                status_code=500, detail=f"Failed to load preset: {response.error}"
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
            raise HTTPException(status_code=503, detail="Audio engine not connected")

        if command.instance_id not in self.state.plugins:
            raise HTTPException(status_code=404, detail="Plugin not found")

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
            raise HTTPException(
                status_code=500, detail=f"Failed to bypass plugin: {response.error}"
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
        pass

    async def _update_plugin_ports(self, plugin: PluginInstance):
        """Update plugin port information"""
        # TODO: Query plugin ports from mod-host
        # This would get parameter ranges, defaults, and audio/cv port info
        pass
