"""
Enhanced Session Manager Service

Comprehensive session management incorporating all functionality from the original
MOD UI session system, including pedalboard management, plugin control, hardware
integration, and transport control.
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.events import (
    EventType,
    SessionEvent,
    create_connection_event,
    create_parameter_event,
    create_pedalboard_event,
    create_plugin_event,
)
from ..models.plugin import (
    Connection,
    ConnectionRequest,
    ParameterSetRequest,
    PedalboardInfo,
    PluginAddRequest,
    PluginInfo,
    PluginInstance,
    PluginRemoveRequest,
)
from ..models.session import (
    AddressingInfo,
    BankInfo,
    MidiMapping,
    RecordingState,
    SessionState,
    SessionStatus,
    SnapshotData,
    TransportState,
    TransportSyncMode,
)


class SessionManager:
    """
    Enhanced session management service that replaces the original Session class
    from mod/session.py with modern async architecture and comprehensive functionality.
    """

    def __init__(self, data_dir: str = None, event_publisher=None):
        self.logger = logging.getLogger(__name__)

        # Set default data directory
        if data_dir is None:
            if os.getenv("MOD_DEV_ENVIRONMENT"):
                data_dir = str(Path.cwd() / "data")
            else:
                data_dir = "/app/data"

        self.data_dir = Path(data_dir)
        self.pedalboards_dir = self.data_dir / "pedalboards"
        self.banks_file = self.data_dir / "banks.json"
        self.preferences_file = self.data_dir / "preferences.json"

        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pedalboards_dir.mkdir(parents=True, exist_ok=True)

        # Initialize session state
        self.session_state = SessionState()
        self.event_publisher = event_publisher

        # WebSocket connections (similar to original SESSION.websockets)
        self.websocket_clients = []

        # Audio engine connection status
        self._audio_engine_connected = False
        self._hmi_connected = False

        # Recording state
        self._recording_handle = None

        self.logger.info(f"SessionManager initialized with data_dir: {data_dir}")

    async def initialize(self) -> None:
        """Initialize the session manager (replaces original Session.__init__)"""
        try:
            self.logger.info("Initializing Enhanced Session Manager...")

            # Load user preferences
            await self._load_preferences()

            # Load banks
            await self._load_banks()

            # Load last session if it exists
            await self._load_last_session()

            # Set status to ready
            self.session_state.status = SessionStatus.READY
            self.session_state.update_activity()

            # Publish session started event
            if self.event_publisher:
                event = SessionEvent(
                    event_type=EventType.SESSION_STARTED,
                    source_service="session_manager",
                    session_id=str(self.session_state.session_id),
                    data={"status": self.session_state.status.value},
                )
                await self.event_publisher.publish(event)

            self.logger.info("Enhanced Session Manager initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize Session Manager: {e}")
            self.session_state.set_error(f"Initialization failed: {e}")
            raise

    async def shutdown(self) -> None:
        """Graceful shutdown of the session manager"""
        self.logger.info("Shutting down Enhanced Session Manager...")

        try:
            # Save current session state
            await self._save_session_state()

            # Stop any recording
            await self.recording_stop()

            # Clear WebSocket connections
            self.websocket_clients.clear()
            self.session_state.websocket_clients = 0

            self.session_state.status = SessionStatus.SHUTTING_DOWN
            self.session_state.update_activity()

            self.logger.info("Enhanced Session Manager shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    # -------------------------------------------------------------------------
    # WebSocket Management (replaces original websocket_opened/closed methods)
    # -------------------------------------------------------------------------

    async def websocket_connected(self, websocket_id: str) -> bool:
        """Handle new websocket connection"""
        try:
            self.websocket_clients.append(websocket_id)
            self.session_state.websocket_clients = len(self.websocket_clients)
            self.session_state.web_connected = len(self.websocket_clients) > 0
            self.session_state.update_activity()

            # If this is the first connection, start UI session
            if len(self.websocket_clients) == 1:
                await self._start_ui_session()

            self.logger.info(
                f"WebSocket connected: {websocket_id} (total: {len(self.websocket_clients)})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error handling websocket connection: {e}")
            return False

    async def websocket_disconnected(self, websocket_id: str) -> bool:
        """Handle websocket disconnection"""
        try:
            if websocket_id in self.websocket_clients:
                self.websocket_clients.remove(websocket_id)

            self.session_state.websocket_clients = len(self.websocket_clients)
            self.session_state.web_connected = len(self.websocket_clients) > 0
            self.session_state.update_activity()

            # If this was the last connection, end UI session
            if len(self.websocket_clients) == 0:
                await self._end_ui_session()

            self.logger.info(
                f"WebSocket disconnected: {websocket_id} (total: {len(self.websocket_clients)})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error handling websocket disconnection: {e}")
            return False

    # -------------------------------------------------------------------------
    # Plugin Management (replaces original web_add, web_remove methods)
    # -------------------------------------------------------------------------

    async def add_plugin(self, request: PluginAddRequest) -> Dict[str, Any]:
        """Add plugin to current pedalboard (replaces SESSION.web_add)"""
        try:
            self.logger.info(f"Adding plugin: {request.instance} ({request.uri})")

            # TODO: Integration with effects service to get plugin info
            # For now, create basic plugin instance
            plugin = PluginInstance(
                instance=request.instance, uri=request.uri, x=request.x, y=request.y
            )

            # Add to session state
            self.session_state.plugins_data[request.instance] = {
                "instance": request.instance,
                "uri": request.uri,
                "x": request.x,
                "y": request.y,
                "bypassed": False,
                "enabled": True,
                "ports": {},
                "addressings": {},
                "midiCCs": {},
                "ranges": {},
                "designations": (None, None, None, None, None),
                "preset": "",
                "mapPresets": [],
                "outputs": {},
                "parameters": {},
            }

            self.session_state.pedalboard_empty = (
                len(self.session_state.plugins_data) == 0
            )
            self.session_state.pedalboard_modified = True
            self.session_state.update_activity()

            # Publish plugin added event
            if self.event_publisher:
                event = create_plugin_event(
                    EventType.PLUGIN_ADDED,
                    "session_manager",
                    request.instance,
                    request.uri,
                    str(self.session_state.session_id),
                    x=request.x,
                    y=request.y,
                    enabled=True,
                )
                await self.event_publisher.publish(event)

            # TODO: Return actual plugin info from effects service
            return {
                "success": True,
                "instance": request.instance,
                "uri": request.uri,
                "plugin_info": {},  # Would come from effects service
            }

        except Exception as e:
            self.logger.error(f"Failed to add plugin: {e}")
            return {"success": False, "error": str(e)}

    async def remove_plugin(self, request: PluginRemoveRequest) -> Dict[str, Any]:
        """Remove plugin from current pedalboard (replaces SESSION.web_remove)"""
        try:
            instance = request.instance

            if instance not in self.session_state.plugins_data:
                return {"success": False, "error": f"Plugin not found: {instance}"}

            plugin_data = self.session_state.plugins_data[instance]
            plugin_uri = plugin_data.get("uri", "")

            # Remove plugin
            del self.session_state.plugins_data[instance]

            # Remove connections involving this plugin
            self.session_state.connections = [
                conn
                for conn in self.session_state.connections
                if not (
                    conn.get("source", "").startswith(f"{instance}/")
                    or conn.get("target", "").startswith(f"{instance}/")
                )
            ]

            self.session_state.pedalboard_empty = (
                len(self.session_state.plugins_data) == 0
            )
            self.session_state.pedalboard_modified = True
            self.session_state.update_activity()

            # Publish plugin removed event
            if self.event_publisher:
                event = create_plugin_event(
                    EventType.PLUGIN_REMOVED,
                    "session_manager",
                    instance,
                    plugin_uri,
                    str(self.session_state.session_id),
                )
                await self.event_publisher.publish(event)

            self.logger.info(f"Removed plugin: {instance}")
            return {"success": True}

        except Exception as e:
            self.logger.error(f"Failed to remove plugin: {e}")
            return {"success": False, "error": str(e)}

    async def set_plugin_parameter(
        self, request: ParameterSetRequest
    ) -> Dict[str, Any]:
        """Set plugin parameter value (replaces param_set functionality)"""
        try:
            instance = request.instance
            parameter = request.parameter
            value = request.value

            if instance not in self.session_state.plugins_data:
                return {"success": False, "error": f"Plugin not found: {instance}"}

            plugin_data = self.session_state.plugins_data[instance]

            # Handle special parameters
            if parameter == ":bypass":
                plugin_data["bypassed"] = bool(value)
            else:
                plugin_data["ports"][parameter] = value

            self.session_state.pedalboard_modified = True
            self.session_state.update_activity()

            # Publish parameter changed event
            if self.event_publisher:
                event = create_parameter_event(
                    EventType.PARAMETER_CHANGED,
                    "session_manager",
                    instance,
                    parameter,
                    value,
                    str(self.session_state.session_id),
                )
                await self.event_publisher.publish(event)

            # Broadcast to WebSocket clients (similar to original msg_callback)
            await self._broadcast_message(f"param_set {instance} {parameter} {value}")

            self.logger.debug(f"Set parameter: {instance}/{parameter} = {value}")
            return {"success": True}

        except Exception as e:
            self.logger.error(f"Failed to set parameter: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Connection Management (replaces web_connect, web_disconnect)
    # -------------------------------------------------------------------------

    async def add_connection(self, request: ConnectionRequest) -> Dict[str, Any]:
        """Add audio/MIDI/CV connection (replaces SESSION.web_connect)"""
        try:
            source = request.source
            target = request.target

            # Check if connection already exists
            for conn in self.session_state.connections:
                if conn.get("source") == source and conn.get("target") == target:
                    return {"success": False, "error": "Connection already exists"}

            # Add connection
            connection = {"source": source, "target": target}
            self.session_state.connections.append(connection)

            self.session_state.pedalboard_modified = True
            self.session_state.update_activity()

            # Publish connection added event
            if self.event_publisher:
                event = create_connection_event(
                    EventType.CONNECTION_ADDED,
                    "session_manager",
                    source,
                    target,
                    f"{source}->{target}",
                    str(self.session_state.session_id),
                )
                await self.event_publisher.publish(event)

            # Broadcast to WebSocket clients
            await self._broadcast_message(f"connect {source} {target}")

            self.logger.info(f"Added connection: {source} -> {target}")
            return {"success": True}

        except Exception as e:
            self.logger.error(f"Failed to add connection: {e}")
            return {"success": False, "error": str(e)}

    async def remove_connection(self, request: ConnectionRequest) -> Dict[str, Any]:
        """Remove audio/MIDI/CV connection (replaces SESSION.web_disconnect)"""
        try:
            source = request.source
            target = request.target

            # Find and remove connection
            for i, conn in enumerate(self.session_state.connections):
                if conn.get("source") == source and conn.get("target") == target:
                    del self.session_state.connections[i]

                    self.session_state.pedalboard_modified = True
                    self.session_state.update_activity()

                    # Publish connection removed event
                    if self.event_publisher:
                        event = create_connection_event(
                            EventType.CONNECTION_REMOVED,
                            "session_manager",
                            source,
                            target,
                            f"{source}->{target}",
                            str(self.session_state.session_id),
                        )
                        await self.event_publisher.publish(event)

                    # Broadcast to WebSocket clients
                    await self._broadcast_message(f"disconnect {source} {target}")

                    self.logger.info(f"Removed connection: {source} -> {target}")
                    return {"success": True}

            return {"success": False, "error": "Connection not found"}

        except Exception as e:
            self.logger.error(f"Failed to remove connection: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Transport Control (replaces original transport methods)
    # -------------------------------------------------------------------------

    async def set_transport_state(self, state: TransportState) -> Dict[str, Any]:
        """Set transport state (play/pause/stop)"""
        try:
            old_state = self.session_state.transport_state
            self.session_state.transport_state = state
            self.session_state.transport_rolling = state == TransportState.PLAYING
            self.session_state.update_activity()

            # Publish transport state changed event
            if self.event_publisher:
                event = SessionEvent(
                    event_type=EventType.SESSION_TRANSPORT_CHANGED,
                    source_service="session_manager",
                    session_id=str(self.session_state.session_id),
                    data={
                        "transport_state": state.value,
                        "rolling": self.session_state.transport_rolling,
                    },
                )
                await self.event_publisher.publish(event)

            # Broadcast transport state to WebSocket clients
            await self._broadcast_message(
                f"transport {int(self.session_state.transport_rolling)} "
                f"{self.session_state.beats_per_bar} {self.session_state.tempo_bpm} "
                f"{self.session_state.transport_sync.value}"
            )

            self.logger.info(
                f"Transport state changed: {old_state.value} -> {state.value}"
            )
            return {"success": True, "state": state.value}

        except Exception as e:
            self.logger.error(f"Failed to set transport state: {e}")
            return {"success": False, "error": str(e)}

    async def set_tempo(self, bpm: float) -> Dict[str, Any]:
        """Set session tempo"""
        try:
            if not 30.0 <= bpm <= 300.0:
                return {
                    "success": False,
                    "error": f"Invalid tempo: {bpm}. Must be between 30 and 300 BPM",
                }

            old_bpm = self.session_state.tempo_bpm
            self.session_state.tempo_bpm = bpm
            self.session_state.update_activity()

            # Broadcast transport update to WebSocket clients
            await self._broadcast_message(
                f"transport {int(self.session_state.transport_rolling)} "
                f"{self.session_state.beats_per_bar} {bpm} "
                f"{self.session_state.transport_sync.value}"
            )

            self.logger.info(f"Tempo changed: {old_bpm} -> {bpm} BPM")
            return {"success": True, "tempo_bpm": bpm}

        except Exception as e:
            self.logger.error(f"Failed to set tempo: {e}")
            return {"success": False, "error": str(e)}

    async def set_beats_per_bar(self, bpb: float) -> Dict[str, Any]:
        """Set beats per bar (time signature)"""
        try:
            if not 1.0 <= bpb <= 16.0:
                return {
                    "success": False,
                    "error": f"Invalid beats per bar: {bpb}. Must be between 1 and 16",
                }

            old_bpb = self.session_state.beats_per_bar
            self.session_state.beats_per_bar = bpb
            self.session_state.update_activity()

            # Broadcast transport update to WebSocket clients
            await self._broadcast_message(
                f"transport {int(self.session_state.transport_rolling)} "
                f"{bpb} {self.session_state.tempo_bpm} "
                f"{self.session_state.transport_sync.value}"
            )

            self.logger.info(f"Beats per bar changed: {old_bpb} -> {bpb}")
            return {"success": True, "beats_per_bar": bpb}

        except Exception as e:
            self.logger.error(f"Failed to set beats per bar: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Recording functionality (replaces original recording methods)
    # -------------------------------------------------------------------------

    async def recording_start(self) -> Dict[str, Any]:
        """Start audio recording (replaces SESSION.web_recording_start)"""
        try:
            # Stop any existing recording/playback
            await self.recording_stop()

            self.session_state.recording.is_recording = True
            self.session_state.recording.is_playing = False
            self.session_state.recording.has_recording = False
            self.session_state.update_activity()

            self.logger.info("Recording started")
            return {"success": True, "recording": True}

        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            return {"success": False, "error": str(e)}

    async def recording_stop(self) -> Dict[str, Any]:
        """Stop audio recording (replaces SESSION.web_recording_stop)"""
        try:
            was_recording = self.session_state.recording.is_recording

            self.session_state.recording.is_recording = False
            self.session_state.recording.is_playing = False

            if was_recording:
                self.session_state.recording.has_recording = True
                # TODO: Calculate actual recording length
                self.session_state.recording.recording_length_seconds = 0.0

            self.session_state.update_activity()

            if self._recording_handle:
                self._recording_handle = None

            self.logger.info("Recording stopped")
            return {"success": True, "recording": False}

        except Exception as e:
            self.logger.error(f"Failed to stop recording: {e}")
            return {"success": False, "error": str(e)}

    async def recording_reset(self) -> Dict[str, Any]:
        """Reset/delete recording (replaces SESSION.web_recording_delete)"""
        try:
            self.session_state.recording = RecordingState()
            self._recording_handle = None
            self.session_state.update_activity()

            self.logger.info("Recording reset")
            return {"success": True}

        except Exception as e:
            self.logger.error(f"Failed to reset recording: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Session State Management
    # -------------------------------------------------------------------------

    async def get_session_state(self) -> SessionState:
        """Get current session state"""
        self.session_state.update_activity()
        return self.session_state

    async def reset_session(self) -> Dict[str, Any]:
        """Reset session to empty state (replaces SESSION.reset)"""
        try:
            self.logger.info("Resetting session to empty state")

            # Save current session ID for event
            old_session_id = self.session_state.session_id

            # Create new session state, preserving some settings
            new_state = SessionState()
            new_state.sample_rate = self.session_state.sample_rate
            new_state.buffer_size = self.session_state.buffer_size
            new_state.audio_driver = self.session_state.audio_driver
            new_state.tempo_bpm = self.session_state.tempo_bpm
            new_state.websocket_clients = self.session_state.websocket_clients
            new_state.web_connected = self.session_state.web_connected
            new_state.hmi_connected = self.session_state.hmi_connected
            new_state.hardware_connected = self.session_state.hardware_connected
            new_state.audio_engine_connected = self.session_state.audio_engine_connected

            self.session_state = new_state
            self.session_state.status = SessionStatus.READY
            self.session_state.pedalboard_name = None
            self.session_state.pedalboard_path = None
            self.session_state.pedalboard_empty = True
            self.session_state.pedalboard_modified = False
            self.session_state.update_activity()

            # Publish session reset event
            if self.event_publisher:
                event = SessionEvent(
                    event_type=EventType.SESSION_RESET,
                    source_service="session_manager",
                    session_id=str(self.session_state.session_id),
                    data={
                        "old_session_id": str(old_session_id),
                        "new_session_id": str(self.session_state.session_id),
                    },
                )
                await self.event_publisher.publish(event)

            # Broadcast reset to WebSocket clients
            await self._broadcast_message("reset")

            self.logger.info("Session reset successfully")
            return {"success": True, "session_id": str(self.session_state.session_id)}

        except Exception as e:
            self.logger.error(f"Failed to reset session: {e}")
            self.session_state.set_error(f"Failed to reset session: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    async def _start_ui_session(self) -> None:
        """Start UI session when first client connects"""
        self.logger.info("Starting UI session")
        # TODO: Initialize UI-specific state
        pass

    async def _end_ui_session(self) -> None:
        """End UI session when last client disconnects"""
        self.logger.info("Ending UI session")
        # TODO: Cleanup UI-specific state
        pass

    async def _broadcast_message(self, message: str) -> None:
        """Broadcast message to all WebSocket clients (replaces msg_callback)"""
        if self.event_publisher:
            # Publish as WebSocket message event
            event = SessionEvent(
                event_type=EventType.SESSION_WEBSOCKET_MESSAGE,
                source_service="session_manager",
                session_id=str(self.session_state.session_id),
                data={"message": message},
            )
            await self.event_publisher.publish(event)

    async def _load_preferences(self) -> None:
        """Load user preferences"""
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file, "r") as f:
                    preferences = json.load(f)
                    # TODO: Apply preferences to session state
                self.logger.info("Loaded user preferences")
        except Exception as e:
            self.logger.warning(f"Failed to load preferences: {e}")

    async def _load_banks(self) -> None:
        """Load pedalboard banks"""
        try:
            if self.banks_file.exists():
                with open(self.banks_file, "r") as f:
                    banks_data = json.load(f)
                    self.session_state.banks = [BankInfo(**bank) for bank in banks_data]
                self.logger.info(f"Loaded {len(self.session_state.banks)} banks")
        except Exception as e:
            self.logger.warning(f"Failed to load banks: {e}")

    async def _load_last_session(self) -> None:
        """Load the last session state if available"""
        try:
            session_file = self.data_dir / "last_session.json"
            if session_file.exists():
                with open(session_file, "r") as f:
                    session_data = json.load(f)

                # Restore basic session info
                if "tempo_bpm" in session_data:
                    self.session_state.tempo_bpm = session_data["tempo_bpm"]
                if "pedalboard_path" in session_data:
                    self.session_state.pedalboard_path = session_data["pedalboard_path"]
                if "pedalboard_name" in session_data:
                    self.session_state.pedalboard_name = session_data["pedalboard_name"]

                self.logger.info("Loaded last session state")
        except Exception as e:
            self.logger.warning(f"Failed to load last session: {e}")

    async def _save_session_state(self) -> None:
        """Save current session state"""
        try:
            session_file = self.data_dir / "last_session.json"
            session_data = {
                "session_id": str(self.session_state.session_id),
                "tempo_bpm": self.session_state.tempo_bpm,
                "pedalboard_name": self.session_state.pedalboard_name,
                "pedalboard_path": self.session_state.pedalboard_path,
                "transport_state": self.session_state.transport_state.value,
                "last_activity": self.session_state.modified_at.isoformat(),
            }

            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)

            self.logger.debug("Saved session state")

        except Exception as e:
            self.logger.error(f"Failed to save session state: {e}")
