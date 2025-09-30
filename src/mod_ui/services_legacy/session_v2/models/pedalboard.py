"""
Pedalboard and Plugin Models

Defines data models for pedalboards, plugins, connections,
and related audio processing components.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PluginParameter(BaseModel):
    """Individual plugin parameter"""

    symbol: str = Field(..., min_length=1)
    value: float
    minimum: float = 0.0
    maximum: float = 1.0
    default: float = 0.0
    unit: Optional[str] = None
    scale_points: Optional[Dict[str, float]] = None

    class Config:
        # Allow arbitrary field names for flexibility
        extra = "allow"


class PluginPort(BaseModel):
    """Plugin input/output port"""

    symbol: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    port_type: str = Field(..., pattern=r"^(audio|control|cv|midi)$")
    direction: str = Field(..., pattern=r"^(input|output)$")

    # Port properties
    is_integer: bool = False
    is_enumeration: bool = False
    is_logarithmic: bool = False
    is_trigger: bool = False

    class Config:
        extra = "allow"


class PluginModel(BaseModel):
    """Individual plugin instance"""

    # Plugin identification
    instance_id: str = Field(..., min_length=1)
    plugin_uri: str = Field(..., min_length=1)

    # Plugin metadata
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None

    # Canvas position
    x: float = 0.0
    y: float = 0.0

    # Plugin state
    enabled: bool = True
    parameters: Dict[str, PluginParameter] = Field(default_factory=dict)
    ports: Dict[str, PluginPort] = Field(default_factory=dict)

    # Plugin-specific data
    preset_uri: Optional[str] = None
    plugin_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class ConnectionModel(BaseModel):
    """Audio/CV connection between plugin ports"""

    # Connection identification
    connection_id: str = Field(default_factory=lambda: str(uuid4()))

    # Connection endpoints
    source_port: str = Field(..., min_length=1)
    destination_port: str = Field(..., min_length=1)

    # Connection properties
    enabled: bool = True
    gain: float = Field(default=1.0, ge=0.0, le=2.0)

    class Config:
        extra = "allow"


class PedalboardMetadata(BaseModel):
    """Pedalboard metadata and information"""

    # Basic information
    title: str = Field(default="Untitled Pedalboard", min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    # Authorship
    author: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = None
    homepage: Optional[str] = None

    # Categorization
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Version information
    version: str = Field(default="1.0.0")

    class Config:
        extra = "allow"


class PedalboardModel(BaseModel):
    """Complete pedalboard representation"""

    # Pedalboard identification
    bundle_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)

    # Pedalboard content
    metadata: PedalboardMetadata = PedalboardMetadata()
    plugins: Dict[str, PluginModel] = Field(default_factory=dict)
    connections: List[ConnectionModel] = Field(default_factory=list)

    # Canvas properties
    canvas_width: int = Field(default=1200, ge=800)
    canvas_height: int = Field(default=800, ge=600)
    zoom_level: float = Field(default=1.0, ge=0.1, le=3.0)

    # Hardware mappings
    hardware_mappings: Dict[str, Any] = Field(default_factory=dict)

    def get_plugin(self, instance_id: str) -> Optional[PluginModel]:
        """Get plugin by instance ID"""
        return self.plugins.get(instance_id)

    def add_plugin(self, plugin: PluginModel) -> None:
        """Add plugin to pedalboard"""
        self.plugins[plugin.instance_id] = plugin
        self.modified_at = datetime.now()

    def remove_plugin(self, instance_id: str) -> bool:
        """Remove plugin from pedalboard"""
        if instance_id in self.plugins:
            del self.plugins[instance_id]
            # Remove connections involving this plugin
            self.connections = [
                conn
                for conn in self.connections
                if not (
                    conn.source_port.startswith(f"{instance_id}:")
                    or conn.destination_port.startswith(f"{instance_id}:")
                )
            ]
            self.modified_at = datetime.now()
            return True
        return False

    def add_connection(self, connection: ConnectionModel) -> None:
        """Add connection to pedalboard"""
        self.connections.append(connection)
        self.modified_at = datetime.now()

    def remove_connection(self, source_port: str, destination_port: str) -> bool:
        """Remove connection from pedalboard"""
        original_count = len(self.connections)
        self.connections = [
            conn
            for conn in self.connections
            if not (
                conn.source_port == source_port
                and conn.destination_port == destination_port
            )
        ]

        if len(self.connections) < original_count:
            self.modified_at = datetime.now()
            return True
        return False

    def get_plugin_count(self) -> int:
        """Get total number of plugins"""
        return len(self.plugins)

    def get_connection_count(self) -> int:
        """Get total number of connections"""
        return len(self.connections)

    class Config:
        extra = "allow"


class PedalboardList(BaseModel):
    """List of available pedalboards"""

    pedalboards: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0

    class Config:
        extra = "allow"
