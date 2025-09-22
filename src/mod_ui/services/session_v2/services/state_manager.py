"""
State Manager Service for Session System

Handles all state management including pedalboard persistence, session state,
and coordination between different services. This service is the single source
of truth for session state.
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import (
    ConnectionModel,
    PedalboardMetadata,
    PedalboardModel,
    PluginModel,
    SessionState,
    SessionStatus,
    SystemStats,
)
from ..models.events import (
    EventType,
    SessionEvent,
    create_connection_event,
    create_parameter_event,
    create_pedalboard_event,
    create_plugin_event,
)


class StateManagerService:
    """
    Central state management service for MOD UI sessions

    Responsibilities:
    - Pedalboard CRUD operations
    - Session state management
    - File system persistence
    - State change event generation
    """

    def __init__(self, data_dir: str = None, event_publisher=None):
        self.logger = logging.getLogger(__name__)

        # Set default data directory based on environment
        if data_dir is None:
            if os.getenv("MOD_DEV_ENVIRONMENT"):
                # Development environment - use project directory
                data_dir = str(Path.cwd() / "data")
            else:
                # Production environment - use container path
                data_dir = "/app/data"

        self.data_dir = Path(data_dir)
        self.pedalboards_dir = self.data_dir / "pedalboards"
        self.session_state = SessionState()
        self.event_publisher = event_publisher

        # Ensure directories exist
        self.pedalboards_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"StateManagerService initialized with data_dir: {data_dir}")

    async def initialize(self) -> None:
        """Initialize the state manager service"""
        try:
            self.logger.info("Initializing State Manager Service...")

            # Load last session if it exists
            await self._load_last_session()

            # Set status to ready
            self.session_state.status = SessionStatus.READY
            self.session_state.update_activity()

            # Publish session started event
            if self.event_publisher:
                event = SessionEvent(
                    event_type=EventType.SESSION_STARTED,
                    source_service="state_manager",
                    session_id=self.session_state.session_id,
                    data={"status": self.session_state.status.value},
                )
                await self.event_publisher.publish(event)

            self.logger.info("State Manager Service initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize State Manager Service: {e}")
            self.session_state.set_error(f"Initialization failed: {e}")
            raise

    async def get_session_state(self) -> SessionState:
        """Get current session state"""
        self.session_state.update_activity()
        return self.session_state

    async def get_current_pedalboard(self) -> Optional[PedalboardModel]:
        """Get currently loaded pedalboard"""
        return self.session_state.current_pedalboard

    async def list_pedalboards(self) -> List[Dict[str, Any]]:
        """List all available pedalboards"""
        try:
            pedalboards = []

            for bundle_dir in self.pedalboards_dir.glob("*.pedalboard"):
                if bundle_dir.is_dir():
                    try:
                        pedalboard = await self._load_pedalboard_metadata(
                            str(bundle_dir)
                        )
                        pedalboards.append(
                            {
                                "bundle_path": str(bundle_dir),
                                "title": pedalboard.metadata.title,
                                "description": pedalboard.metadata.description,
                                "author": pedalboard.metadata.author,
                                "version": pedalboard.metadata.version,
                                "tags": pedalboard.metadata.tags,
                                "plugin_count": len(pedalboard.plugins),
                                "connection_count": len(pedalboard.connections),
                                "created_at": pedalboard.created_at.isoformat(),
                                "modified_at": pedalboard.modified_at.isoformat(),
                            }
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to load pedalboard metadata from {bundle_dir}: {e}"
                        )

            return sorted(pedalboards, key=lambda x: x["modified_at"], reverse=True)

        except Exception as e:
            self.logger.error(f"Failed to list pedalboards: {e}")
            return []

    async def load_pedalboard(self, bundle_path: str) -> PedalboardModel:
        """Load a pedalboard from file system"""
        try:
            self.session_state.status = SessionStatus.LOADING_PEDALBOARD
            self.session_state.update_activity()

            self.logger.info(f"Loading pedalboard: {bundle_path}")

            pedalboard_path = Path(bundle_path)
            if not pedalboard_path.exists():
                raise FileNotFoundError(f"Pedalboard not found: {bundle_path}")

            pedalboard = await self._load_pedalboard_from_bundle(str(pedalboard_path))

            # Set as current pedalboard
            self.session_state.current_pedalboard = pedalboard
            self.session_state.status = SessionStatus.READY
            self.session_state.update_activity()

            # Publish pedalboard loaded event
            if self.event_publisher:
                event = create_pedalboard_event(
                    EventType.PEDALBOARD_LOADED,
                    "state_manager",
                    pedalboard.bundle_path,
                    pedalboard.metadata.title,
                    len(pedalboard.plugins),
                    len(pedalboard.connections),
                    self.session_state.session_id,
                )
                await self.event_publisher.publish(event)

            self.logger.info(
                f"Pedalboard loaded successfully: {pedalboard.metadata.title}"
            )
            return pedalboard

        except Exception as e:
            self.logger.error(f"Failed to load pedalboard {bundle_path}: {e}")
            self.session_state.set_error(f"Failed to load pedalboard: {e}")
            raise

    async def save_pedalboard(
        self, pedalboard: PedalboardModel, bundle_path: Optional[str] = None
    ) -> str:
        """Save a pedalboard to file system"""
        try:
            self.session_state.status = SessionStatus.SAVING_PEDALBOARD
            self.session_state.update_activity()

            # Use provided path or current pedalboard path
            if bundle_path is None:
                if self.session_state.current_pedalboard is None:
                    raise ValueError("No current pedalboard to save")
                bundle_path = self.session_state.current_pedalboard.bundle_path

            # Ensure bundle path is in our pedalboards directory
            bundle_path = str(self.pedalboards_dir / Path(bundle_path).name)
            if not bundle_path.endswith(".pedalboard"):
                bundle_path += ".pedalboard"

            self.logger.info(f"Saving pedalboard: {bundle_path}")

            # Update pedalboard metadata
            pedalboard.bundle_path = bundle_path
            pedalboard.modified_at = datetime.now()

            # Save to file system
            await self._save_pedalboard_to_bundle(pedalboard, bundle_path)

            # Update current pedalboard
            self.session_state.current_pedalboard = pedalboard
            self.session_state.status = SessionStatus.READY
            self.session_state.update_activity()

            # Publish pedalboard saved event
            if self.event_publisher:
                event = create_pedalboard_event(
                    EventType.PEDALBOARD_SAVED,
                    "state_manager",
                    pedalboard.bundle_path,
                    pedalboard.metadata.title,
                    len(pedalboard.plugins),
                    len(pedalboard.connections),
                    self.session_state.session_id,
                )
                await self.event_publisher.publish(event)

            self.logger.info(f"Pedalboard saved successfully: {bundle_path}")
            return bundle_path

        except Exception as e:
            self.logger.error(f"Failed to save pedalboard: {e}")
            self.session_state.set_error(f"Failed to save pedalboard: {e}")
            raise

    async def create_new_pedalboard(
        self, title: str, description: Optional[str] = None
    ) -> PedalboardModel:
        """Create a new empty pedalboard"""
        try:
            # Generate unique bundle path
            safe_title = "".join(
                c for c in title if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            bundle_name = safe_title.replace(" ", "_").lower()
            bundle_path = str(self.pedalboards_dir / f"{bundle_name}.pedalboard")

            # Ensure unique path
            counter = 1
            while Path(bundle_path).exists():
                bundle_path = str(
                    self.pedalboards_dir / f"{bundle_name}_{counter}.pedalboard"
                )
                counter += 1

            # Create pedalboard
            pedalboard = PedalboardModel(
                bundle_path=bundle_path,
                metadata=PedalboardMetadata(title=title, description=description),
            )

            # Save and set as current
            await self.save_pedalboard(pedalboard)

            self.logger.info(f"Created new pedalboard: {title}")
            return pedalboard

        except Exception as e:
            self.logger.error(f"Failed to create new pedalboard: {e}")
            raise

    async def add_plugin(self, plugin: PluginModel) -> None:
        """Add plugin to current pedalboard"""
        try:
            if self.session_state.current_pedalboard is None:
                raise ValueError("No current pedalboard")

            self.session_state.current_pedalboard.add_plugin(plugin)

            # Publish plugin added event
            if self.event_publisher:
                event = create_plugin_event(
                    EventType.PLUGIN_ADDED,
                    "state_manager",
                    plugin.instance_id,
                    plugin.plugin_uri,
                    self.session_state.session_id,
                    x=plugin.x,
                    y=plugin.y,
                    enabled=plugin.enabled,
                )
                await self.event_publisher.publish(event)

            self.logger.info(
                f"Added plugin: {plugin.instance_id} ({plugin.plugin_uri})"
            )

        except Exception as e:
            self.logger.error(f"Failed to add plugin: {e}")
            raise

    async def remove_plugin(self, instance_id: str) -> bool:
        """Remove plugin from current pedalboard"""
        try:
            if self.session_state.current_pedalboard is None:
                raise ValueError("No current pedalboard")

            plugin = self.session_state.current_pedalboard.get_plugin(instance_id)
            if plugin is None:
                return False

            success = self.session_state.current_pedalboard.remove_plugin(instance_id)

            if success and self.event_publisher:
                event = create_plugin_event(
                    EventType.PLUGIN_REMOVED,
                    "state_manager",
                    instance_id,
                    plugin.plugin_uri,
                    self.session_state.session_id,
                )
                await self.event_publisher.publish(event)

            self.logger.info(f"Removed plugin: {instance_id}")
            return success

        except Exception as e:
            self.logger.error(f"Failed to remove plugin: {e}")
            raise

    async def set_plugin_parameter(
        self, instance_id: str, parameter_symbol: str, value: float
    ) -> None:
        """Set plugin parameter value"""
        try:
            if self.session_state.current_pedalboard is None:
                raise ValueError("No current pedalboard")

            plugin = self.session_state.current_pedalboard.get_plugin(instance_id)
            if plugin is None:
                raise ValueError(f"Plugin not found: {instance_id}")

            if parameter_symbol not in plugin.parameters:
                raise ValueError(f"Parameter not found: {parameter_symbol}")

            # Update parameter value
            plugin.parameters[parameter_symbol].value = value
            self.session_state.current_pedalboard.modified_at = datetime.now()

            # Publish parameter changed event
            if self.event_publisher:
                event = create_parameter_event(
                    EventType.PARAMETER_CHANGED,
                    "state_manager",
                    instance_id,
                    parameter_symbol,
                    value,
                    self.session_state.session_id,
                )
                await self.event_publisher.publish(event)

            self.logger.debug(
                f"Set parameter: {instance_id}/{parameter_symbol} = {value}"
            )

        except Exception as e:
            self.logger.error(f"Failed to set parameter: {e}")
            raise

    async def add_connection(self, connection: ConnectionModel) -> None:
        """Add connection to current pedalboard"""
        try:
            if self.session_state.current_pedalboard is None:
                raise ValueError("No current pedalboard")

            self.session_state.current_pedalboard.add_connection(connection)

            # Publish connection added event
            if self.event_publisher:
                event = create_connection_event(
                    EventType.CONNECTION_ADDED,
                    "state_manager",
                    connection.source_port,
                    connection.destination_port,
                    connection.connection_id,
                    self.session_state.session_id,
                )
                await self.event_publisher.publish(event)

            self.logger.info(
                f"Added connection: {connection.source_port} -> {connection.destination_port}"
            )

        except Exception as e:
            self.logger.error(f"Failed to add connection: {e}")
            raise

    async def remove_connection(self, source_port: str, destination_port: str) -> bool:
        """Remove connection from current pedalboard"""
        try:
            if self.session_state.current_pedalboard is None:
                raise ValueError("No current pedalboard")

            # Find connection for event
            connection_id = None
            for conn in self.session_state.current_pedalboard.connections:
                if (
                    conn.source_port == source_port
                    and conn.destination_port == destination_port
                ):
                    connection_id = conn.connection_id
                    break

            success = self.session_state.current_pedalboard.remove_connection(
                source_port, destination_port
            )

            if success and self.event_publisher and connection_id:
                event = create_connection_event(
                    EventType.CONNECTION_REMOVED,
                    "state_manager",
                    source_port,
                    destination_port,
                    connection_id,
                    self.session_state.session_id,
                )
                await self.event_publisher.publish(event)

            self.logger.info(f"Removed connection: {source_port} -> {destination_port}")
            return success

        except Exception as e:
            self.logger.error(f"Failed to remove connection: {e}")
            raise

    async def update_websocket_clients(self, count: int) -> None:
        """Update WebSocket client count"""
        self.session_state.websocket_clients = count
        self.session_state.update_activity()

    async def update_hardware_status(self, connected: bool) -> None:
        """Update hardware connection status"""
        self.session_state.hardware_connected = connected
        self.session_state.update_activity()

    async def update_audio_engine_status(self, connected: bool) -> None:
        """Update audio engine connection status"""
        self.session_state.audio_engine_connected = connected
        self.session_state.update_activity()

    async def set_transport_state(self, state) -> None:
        """Set transport state (play/pause/stop)"""
        from ..models import TransportState

        if isinstance(state, str):
            # Convert string to enum
            state = TransportState(state)

        self.session_state.transport_state = state
        self.session_state.update_activity()

        # Publish transport state changed event
        if self.event_publisher:
            from ..models.events import EventType, SessionEvent

            event = SessionEvent(
                event_type=EventType.SESSION_TRANSPORT_CHANGED,
                source_service="state_manager",
                session_id=self.session_state.session_id,
                data={"transport_state": state.value},
            )
            await self.event_publisher.publish(event)

        self.logger.debug(f"Transport state changed to: {state.value}")

    async def set_tempo(self, bpm: float) -> None:
        """Set session tempo"""
        if not 30.0 <= bpm <= 300.0:
            raise ValueError(f"Invalid tempo: {bpm}. Must be between 30 and 300 BPM")

        self.session_state.tempo_bpm = bpm
        self.session_state.update_activity()

        # Publish tempo changed event
        if self.event_publisher:
            from ..models.events import EventType, SessionEvent

            event = SessionEvent(
                event_type=EventType.SESSION_CONFIG_CHANGED,
                source_service="state_manager",
                session_id=self.session_state.session_id,
                data={"tempo": bpm},
            )
            await self.event_publisher.publish(event)

        self.logger.debug(f"Tempo changed to: {bpm} BPM")

    async def set_sample_rate(self, sample_rate: int) -> None:
        """Set audio sample rate"""
        valid_rates = [22050, 44100, 48000, 88200, 96000, 176400, 192000]
        if sample_rate not in valid_rates:
            raise ValueError(
                f"Invalid sample rate: {sample_rate}. Must be one of {valid_rates}"
            )

        self.session_state.sample_rate = sample_rate
        self.session_state.update_activity()

        # Publish sample rate changed event
        if self.event_publisher:
            from ..models.events import EventType, SessionEvent

            event = SessionEvent(
                event_type=EventType.SESSION_CONFIG_CHANGED,
                source_service="state_manager",
                session_id=self.session_state.session_id,
                data={"sample_rate": sample_rate},
            )
            await self.event_publisher.publish(event)

        self.logger.debug(f"Sample rate changed to: {sample_rate} Hz")

    async def set_buffer_size(self, buffer_size: int) -> None:
        """Set audio buffer size"""
        valid_sizes = [32, 64, 128, 256, 512, 1024, 2048]
        if buffer_size not in valid_sizes:
            raise ValueError(
                f"Invalid buffer size: {buffer_size}. Must be one of {valid_sizes}"
            )

        self.session_state.buffer_size = buffer_size
        self.session_state.update_activity()

        # Publish buffer size changed event
        if self.event_publisher:
            from ..models.events import EventType, SessionEvent

            event = SessionEvent(
                event_type=EventType.SESSION_CONFIG_CHANGED,
                source_service="state_manager",
                session_id=self.session_state.session_id,
                data={"buffer_size": buffer_size},
            )
            await self.event_publisher.publish(event)

        self.logger.debug(f"Buffer size changed to: {buffer_size} samples")

    # Private helper methods

    async def _load_last_session(self) -> None:
        """Load the last session state if available"""
        try:
            session_file = self.data_dir / "last_session.json"
            if session_file.exists():
                with open(session_file, "r") as f:
                    session_data = json.load(f)

                # Load last pedalboard if specified
                if "current_pedalboard" in session_data:
                    bundle_path = session_data["current_pedalboard"]
                    if Path(bundle_path).exists():
                        await self.load_pedalboard(bundle_path)

                self.logger.info("Loaded last session state")
        except Exception as e:
            self.logger.warning(f"Failed to load last session: {e}")

    async def _save_session_state(self) -> None:
        """Save current session state"""
        try:
            session_file = self.data_dir / "last_session.json"
            session_data = {
                "session_id": self.session_state.session_id,
                "current_pedalboard": (
                    self.session_state.current_pedalboard.bundle_path
                    if self.session_state.current_pedalboard
                    else None
                ),
                "last_activity": self.session_state.last_activity.isoformat(),
            }

            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save session state: {e}")

    async def _load_pedalboard_metadata(self, bundle_path: str) -> PedalboardModel:
        """Load pedalboard metadata only (for listing)"""
        manifest_file = Path(bundle_path) / "manifest.ttl"
        if not manifest_file.exists():
            raise FileNotFoundError(f"No manifest.ttl found in {bundle_path}")

        # For now, create a basic pedalboard with default metadata
        # TODO: Implement proper TTL parsing
        bundle_name = Path(bundle_path).stem

        return PedalboardModel(
            bundle_path=bundle_path,
            metadata=PedalboardMetadata(title=bundle_name.replace("_", " ").title()),
        )

    async def _load_pedalboard_from_bundle(self, bundle_path: str) -> PedalboardModel:
        """Load complete pedalboard from bundle directory"""
        # TODO: Implement proper TTL/RDF parsing for pedalboard files
        # For now, load from JSON if available, otherwise create empty

        bundle_dir = Path(bundle_path)
        json_file = bundle_dir / "pedalboard.json"

        if json_file.exists():
            with open(json_file, "r") as f:
                data = json.load(f)

            # Convert JSON data to PedalboardModel
            # This is a simplified implementation
            pedalboard = PedalboardModel(
                bundle_path=bundle_path,
                metadata=PedalboardMetadata(
                    **data.get("metadata", {"title": "Untitled"})
                ),
                plugins={},
                connections=[],
            )

            return pedalboard
        else:
            # Create empty pedalboard
            return await self._load_pedalboard_metadata(bundle_path)

    async def _save_pedalboard_to_bundle(
        self, pedalboard: PedalboardModel, bundle_path: str
    ) -> None:
        """Save pedalboard to bundle directory"""
        bundle_dir = Path(bundle_path)
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON for now (TODO: implement proper TTL generation)
        json_file = bundle_dir / "pedalboard.json"

        pedalboard_data = {
            "metadata": pedalboard.metadata.dict(),
            "plugins": {k: v.dict() for k, v in pedalboard.plugins.items()},
            "connections": [conn.dict() for conn in pedalboard.connections],
            "created_at": pedalboard.created_at.isoformat(),
            "modified_at": pedalboard.modified_at.isoformat(),
        }

        with open(json_file, "w") as f:
            json.dump(pedalboard_data, f, indent=2)

        # Create basic manifest.ttl
        manifest_file = bundle_dir / "manifest.ttl"
        with open(manifest_file, "w") as f:
            f.write(
                f"""@prefix lv2: <http://lv2plug.in/ns/lv2core#> .
@prefix mod: <http://moddevices.com/ns/mod#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<{bundle_path}>
    a mod:Pedalboard ;
    lv2:name "{pedalboard.metadata.title}" ;
    rdfs:comment "{pedalboard.metadata.description or ''}" .
"""
            )

    async def shutdown(self) -> None:
        """Graceful shutdown of the state manager"""
        self.logger.info("Shutting down State Manager Service...")

        # Save current session state
        try:
            await self._save_session_state()
            self.logger.info("Session state saved successfully")
        except Exception as e:
            self.logger.error("Failed to save session state: %s", str(e))

        self.logger.info("State Manager Service shutdown complete")
