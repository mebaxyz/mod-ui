"""
MOD UI - Audio Processing Service - Session Manager

Manages pedalboard sessions, snapshots, and state persistence.
"""

import asyncio
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    """Represents an audio connection between plugins"""

    source_plugin: str
    source_port: str
    target_plugin: str
    target_port: str
    connection_id: str = None

    def __post_init__(self):
        if not self.connection_id:
            self.connection_id = str(uuid.uuid4())


@dataclass
class Pedalboard:
    """Represents a complete pedalboard configuration"""

    id: str
    name: str
    description: str
    plugins: List[Dict[str, Any]]
    connections: List[Connection]
    created_at: datetime
    modified_at: datetime
    metadata: Dict[str, Any]


class SessionManager:
    """Manages pedalboard sessions and state"""

    def __init__(self, plugin_manager, modhost_bridge, service_bus=None):
        self.plugin_manager = plugin_manager
        self.modhost = modhost_bridge
        self.service_bus = service_bus

        self.current_pedalboard: Optional[Pedalboard] = None
        self.connections: List[Connection] = []
        self._lock = asyncio.Lock()

    def _serialize_pedalboard(self, pedalboard: Pedalboard) -> Dict[str, Any]:
        """Return a JSON-serializable dict for a Pedalboard (datetimes -> isoformat)."""
        pb = asdict(pedalboard)
        # convert datetime fields to ISO strings
        if isinstance(pedalboard.created_at, datetime):
            pb["created_at"] = pedalboard.created_at.isoformat()
        if isinstance(pedalboard.modified_at, datetime):
            pb["modified_at"] = pedalboard.modified_at.isoformat()

        # ensure connections are basic dicts
        if "connections" in pb:
            serialized_conns = []
            for c in pb["connections"]:
                # dataclass->dict should already be fine but ensure nested ids are strings
                if isinstance(c, dict):
                    serialized_conns.append(c)
                else:
                    try:
                        serialized_conns.append(asdict(c))
                    except Exception:
                        serialized_conns.append({})
            pb["connections"] = serialized_conns

        return pb

    async def create_pedalboard(
        self, name: str, description: str = ""
    ) -> Dict[str, Any]:
        """Create a new empty pedalboard"""
        async with self._lock:
            pedalboard_id = str(uuid.uuid4())

            pedalboard = Pedalboard(
                id=pedalboard_id,
                name=name,
                description=description,
                plugins=[],
                connections=[],
                created_at=datetime.now(),
                modified_at=datetime.now(),
                metadata={},
            )

            # Clear current audio state
            await self._clear_audio_state()

            self.current_pedalboard = pedalboard
            self.connections = []

            # Publish event
            if self.service_bus:
                await self.service_bus.publish_event(
                    "pedalboard_created",
                    {"id": pedalboard_id, "name": name, "description": description},
                )

            logger.info("Created pedalboard: %s (%s)", name, pedalboard_id)

            return {
                "pedalboard_id": pedalboard_id,
                "pedalboard": self._serialize_pedalboard(pedalboard),
            }

    async def load_pedalboard(self, pedalboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load a pedalboard from configuration data"""
        async with self._lock:
            # Clear current state
            await self._clear_audio_state()

            # Create pedalboard object
            pedalboard = Pedalboard(
                id=pedalboard_data.get("id", str(uuid.uuid4())),
                name=pedalboard_data.get("name", "Untitled"),
                description=pedalboard_data.get("description", ""),
                plugins=pedalboard_data.get("plugins", []),
                connections=[
                    Connection(**conn) if isinstance(conn, dict) else conn
                    for conn in pedalboard_data.get("connections", [])
                ],
                created_at=datetime.fromisoformat(
                    pedalboard_data.get("created_at", datetime.now().isoformat())
                ),
                modified_at=datetime.now(),
                metadata=pedalboard_data.get("metadata", {}),
            )

            # Load plugins
            loaded_plugins = []
            plugin_mapping = {}  # old_id -> new_id

            for plugin_config in pedalboard.plugins:
                try:
                    result = await self.plugin_manager.load_plugin(
                        uri=plugin_config["uri"],
                        x=plugin_config.get("x", 0.0),
                        y=plugin_config.get("y", 0.0),
                        parameters=plugin_config.get("parameters", {}),
                    )

                    old_id = plugin_config.get("instance_id")
                    new_id = result["instance_id"]

                    if old_id:
                        plugin_mapping[old_id] = new_id

                    loaded_plugins.append({**plugin_config, "instance_id": new_id})

                except Exception as e:
                    logger.error(
                        "Failed to load plugin %s: %s",
                        plugin_config.get("uri"),
                        e,
                    )

            # Create connections
            loaded_connections = []
            for connection in pedalboard.connections:
                try:
                    # Map old instance IDs to new ones
                    source_plugin = plugin_mapping.get(
                        connection.source_plugin, connection.source_plugin
                    )
                    target_plugin = plugin_mapping.get(
                        connection.target_plugin, connection.target_plugin
                    )

                    success = await self.modhost.connect_ports(
                        f"{source_plugin}:{connection.source_port}",
                        f"{target_plugin}:{connection.target_port}",
                    )

                    if success:
                        new_connection = Connection(
                            source_plugin=source_plugin,
                            source_port=connection.source_port,
                            target_plugin=target_plugin,
                            target_port=connection.target_port,
                        )
                        loaded_connections.append(new_connection)

                except Exception as e:
                    logger.error("Failed to create connection: %s", e)

            # Update pedalboard with loaded state
            pedalboard.plugins = loaded_plugins
            pedalboard.connections = loaded_connections

            self.current_pedalboard = pedalboard
            self.connections = loaded_connections

            # Publish event
            if self.service_bus:
                await self.service_bus.publish_event(
                    "pedalboard_loaded",
                    {
                        "id": pedalboard.id,
                        "name": pedalboard.name,
                        "plugins_loaded": len(loaded_plugins),
                        "connections_created": len(loaded_connections),
                    },
                )

            logger.info("Loaded pedalboard: %s (%s)", pedalboard.name, pedalboard.id)

            return {
                "status": "ok",
                "pedalboard": self._serialize_pedalboard(pedalboard),
                "plugins_loaded": len(loaded_plugins),
                "connections_created": len(loaded_connections),
            }

    async def save_pedalboard(self) -> Dict[str, Any]:
        """Save current pedalboard state"""
        if not self.current_pedalboard:
            raise ValueError("No pedalboard currently loaded")

        # Update modified time
        self.current_pedalboard.modified_at = datetime.now()

        # Get current plugin states
        current_plugins = []
        for instance_id, instance in self.plugin_manager.instances.items():
            current_plugins.append(asdict(instance))

        # Update pedalboard with current state
        self.current_pedalboard.plugins = current_plugins
        self.current_pedalboard.connections = self.connections

        # Publish event
        if self.service_bus:
            await self.service_bus.publish_event(
                "pedalboard_saved",
                {
                    "id": self.current_pedalboard.id,
                    "name": self.current_pedalboard.name,
                },
            )

        logger.info("Saved pedalboard: %s", self.current_pedalboard.name)

        return {
            "status": "ok",
            "pedalboard": self._serialize_pedalboard(self.current_pedalboard),
        }

    async def get_current_pedalboard(self) -> Dict[str, Any]:
        """Get current pedalboard state"""
        if not self.current_pedalboard:
            return {"pedalboard": None}

        # Update with current plugin states
        await self.save_pedalboard()

        return {"pedalboard": self._serialize_pedalboard(self.current_pedalboard)}

    async def create_connection(
        self, source_plugin: str, source_port: str, target_plugin: str, target_port: str
    ) -> Dict[str, Any]:
        """Create a connection between plugins"""
        async with self._lock:
            # Validate plugins exist
            if source_plugin not in self.plugin_manager.instances:
                raise ValueError(f"Source plugin not found: {source_plugin}")
            if target_plugin not in self.plugin_manager.instances:
                raise ValueError(f"Target plugin not found: {target_plugin}")

            # Create connection
            connection = Connection(
                source_plugin=source_plugin,
                source_port=source_port,
                target_plugin=target_plugin,
                target_port=target_port,
            )

            # Connect in mod-host
            success = await self.modhost.connect_ports(
                f"{source_plugin}:{source_port}", f"{target_plugin}:{target_port}"
            )

            if not success:
                raise RuntimeError("Failed to create connection in mod-host")

            # Store connection
            self.connections.append(connection)

            # Update pedalboard if loaded
            if self.current_pedalboard:
                self.current_pedalboard.connections.append(connection)
                self.current_pedalboard.modified_at = datetime.now()

            # Publish event
            if self.service_bus:
                await self.service_bus.publish_event(
                    "connection_created",
                    {
                        "connection_id": connection.connection_id,
                        "source": f"{source_plugin}:{source_port}",
                        "target": f"{target_plugin}:{target_port}",
                    },
                )

            logger.info(
                "Created connection: %s:%s -> %s:%s",
                source_plugin,
                source_port,
                target_plugin,
                target_port,
            )

            return {
                "connection_id": connection.connection_id,
                "connection": asdict(connection),
            }

    async def remove_connection(self, connection_id: str) -> Dict[str, Any]:
        """Remove a connection"""
        async with self._lock:
            # Find connection
            connection = None
            for conn in self.connections:
                if conn.connection_id == connection_id:
                    connection = conn
                    break

            if not connection:
                raise ValueError(f"Connection not found: {connection_id}")

            # Disconnect in mod-host
            success = await self.modhost.disconnect_ports(
                f"{connection.source_plugin}:{connection.source_port}",
                f"{connection.target_plugin}:{connection.target_port}",
            )

            if not success:
                logger.warning("Failed to disconnect in mod-host: %s", connection_id)

            # Remove from connections
            self.connections.remove(connection)

            # Update pedalboard if loaded
            if self.current_pedalboard:
                self.current_pedalboard.connections = [
                    c
                    for c in self.current_pedalboard.connections
                    if c.connection_id != connection_id
                ]
                self.current_pedalboard.modified_at = datetime.now()

            # Publish event
            if self.service_bus:
                await self.service_bus.publish_event(
                    "connection_removed", {"connection_id": connection_id}
                )

            logger.info("Removed connection %s", connection_id)

            return {"status": "ok", "connection_id": connection_id}

    async def create_snapshot(self, name: str) -> Dict[str, Any]:
        """Create a snapshot of current state"""
        if not self.current_pedalboard:
            raise ValueError("No pedalboard currently loaded")

        snapshot = {
            "id": str(uuid.uuid4()),
            "name": name,
            "created_at": datetime.now().isoformat(),
            "pedalboard_id": self.current_pedalboard.id,
            "plugin_states": {},
        }

        # Capture current parameter values
        for instance_id, instance in self.plugin_manager.instances.items():
            snapshot["plugin_states"][instance_id] = instance.parameters.copy()

        logger.info("Created snapshot: %s", name)

        return {"status": "ok", "snapshot": snapshot}

    async def apply_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a snapshot to current state"""
        if not self.current_pedalboard:
            raise ValueError("No pedalboard currently loaded")

        applied_params = 0

        # Apply parameter values
        for instance_id, parameters in snapshot.get("plugin_states", {}).items():
            if instance_id in self.plugin_manager.instances:
                for param, value in parameters.items():
                    try:
                        await self.plugin_manager.set_parameter(
                            instance_id, param, value
                        )
                        applied_params += 1
                    except Exception as e:
                        logger.error(
                            "Failed to apply parameter %s.%s: %s",
                            instance_id,
                            param,
                            e,
                        )

        # Publish event
        if self.service_bus:
            await self.service_bus.publish_event(
                "snapshot_applied",
                {
                    "snapshot_id": snapshot.get("id"),
                    "snapshot_name": snapshot.get("name"),
                    "parameters_applied": applied_params,
                },
            )

        logger.info(
            "Applied snapshot: %s (%s parameters)", snapshot.get("name"), applied_params
        )

        return {"status": "ok", "parameters_applied": applied_params}

    async def _clear_audio_state(self):
        """Clear all audio state (plugins and connections)"""
        # Clear connections
        self.connections = []

        # Clear plugins
        await self.plugin_manager.clear_all()

        logger.debug("Cleared audio state")

    def get_status(self) -> Dict[str, Any]:
        """Get session manager status"""
        return {
            "current_pedalboard": (
                self.current_pedalboard.name if self.current_pedalboard else None
            ),
            "pedalboard_id": (
                self.current_pedalboard.id if self.current_pedalboard else None
            ),
            "active_connections": len(self.connections),
            "loaded_plugins": len(self.plugin_manager.instances),
        }
