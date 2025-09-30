"""
MOD UI - Audio Processing Service - Plugin Manager

Manages plugin instances, parameters, and state.
"""

import asyncio
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional, cast

logger = logging.getLogger(__name__)

# Localized pylint - best-effort publish calls use broad except handling
# pylint: disable=broad-except


@dataclass
class PluginInstance:
    """Represents a loaded plugin instance"""

    uri: str
    instance_id: str
    name: str
    brand: str
    version: str
    parameters: Dict[str, Any]
    ports: Dict[str, Any]
    x: float = 0.0
    y: float = 0.0
    enabled: bool = True
    preset: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class PluginManager:
    """Manages plugin loading, unloading, and parameter control"""

    def __init__(self, modhost_bridge, service_bus=None):
        self.modhost = modhost_bridge
        self.service_bus = service_bus
        self.instances: Dict[str, PluginInstance] = {}
        self.available_plugins: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize plugin manager"""
        logger.info("Initializing plugin manager")

        # Load available plugins
        await self._load_available_plugins()

        logger.info(
            "Plugin manager initialized with %s available plugins",
            len(self.available_plugins),
        )

    async def _safe_publish(self, event_name: str, payload: Dict[str, Any]):
        """Call publisher in a robust way supporting different ServiceBus APIs."""
        if not self.service_bus:
            return

        # Try both publish_event and publish to support different servicebus APIs
        for attr in ("publish_event", "publish"):
            publisher = getattr(self.service_bus, attr, None)
            if publisher is None:
                continue

            # At runtime publisher may be a coroutine function or a normal function.
            try:
                # Use typing.cast to convince the analyzer the object is callable
                if callable(publisher):
                    pub_callable = cast(Callable[..., Any], publisher)
                    # pylint: disable=not-callable
                    result = pub_callable(event_name, payload)
                    if hasattr(result, "__await__"):
                        await result
                else:
                    # Defensive fallback: retrieve attribute and try calling it
                    meth = getattr(self.service_bus, attr, None)
                    if callable(meth):
                        meth_callable = cast(Callable[..., Any], meth)
                        # pylint: disable=not-callable
                        res = meth_callable(event_name, payload)
                        if hasattr(res, "__await__"):
                            await res
            except Exception:
                logger.debug("Publish %s failed for %s", attr, event_name)

    async def _load_available_plugins(self):
        """Load list of available plugins"""
        # This would typically scan LV2 plugin directories
        # For MVP, we'll use a hardcoded list
        self.available_plugins = {
            "http://guitarix.sourceforge.net/plugins/gx_distortion": {
                "name": "GX Distortion",
                "brand": "Guitarix",
                "version": "1.0",
                "category": "Distortion",
                "ports": {
                    "input": {"type": "audio", "direction": "input"},
                    "output": {"type": "audio", "direction": "output"},
                    "drive": {
                        "type": "control",
                        "min": 0.0,
                        "max": 1.0,
                        "default": 0.5,
                    },
                },
            },
            "http://guitarix.sourceforge.net/plugins/gx_reverb": {
                "name": "GX Reverb",
                "brand": "Guitarix",
                "version": "1.0",
                "category": "Reverb",
                "ports": {
                    "input": {"type": "audio", "direction": "input"},
                    "output": {"type": "audio", "direction": "output"},
                    "roomsize": {
                        "type": "control",
                        "min": 0.0,
                        "max": 1.0,
                        "default": 0.5,
                    },
                    "wet": {"type": "control", "min": 0.0, "max": 1.0, "default": 0.3},
                },
            },
            "http://lv2plug.in/plugins/eg-amp": {
                "name": "Example Amplifier",
                "brand": "LV2",
                "version": "1.0",
                "category": "Amplifier",
                "ports": {
                    "input": {"type": "audio", "direction": "input"},
                    "output": {"type": "audio", "direction": "output"},
                    "gain": {"type": "control", "min": 0.0, "max": 2.0, "default": 1.0},
                },
            },
        }

    async def get_available_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available plugins"""
        return self.available_plugins.copy()

    async def load_plugin(
        self,
        uri: str,
        x: float = 0.0,
        y: float = 0.0,
        parameters: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Load a plugin instance"""
        async with self._lock:
            # Check if plugin exists
            if uri not in self.available_plugins:
                raise ValueError(f"Plugin not found: {uri}")

            plugin_info = self.available_plugins[uri]

            # Generate instance ID
            instance_id = f"plugin_{len(self.instances)}_{uuid.uuid4().hex[:8]}"

            # Add to mod-host
            success = await self.modhost.add_plugin(uri, instance_id)
            if not success:
                raise RuntimeError("Failed to add plugin to mod-host")

            # Create plugin instance
            instance = PluginInstance(
                uri=uri,
                instance_id=instance_id,
                name=plugin_info.get("name", "Unknown"),
                brand=plugin_info.get("brand", "Unknown"),
                version=plugin_info.get("version", "1.0"),
                parameters=parameters or {},
                ports=plugin_info.get("ports", {}),
                x=x,
                y=y,
            )

            # Set initial parameters
            if parameters:
                for param, value in parameters.items():
                    await self.modhost.set_parameter(instance_id, param, value)

            # Store instance
            self.instances[instance_id] = instance

            # Publish event (support service bus API compatibility)
            # Best-effort publish; don't fail the operation on publish errors
            await self._safe_publish(
                "plugin_loaded",
                {"instance_id": instance_id, "uri": uri, "name": instance.name},
            )

            logger.info("Loaded plugin %s as %s", uri, instance_id)

            # Convert to JSON-serializable dict (convert datetimes to isoformat)
            plugin_dict = asdict(instance)
            if plugin_dict.get("created_at") is not None:
                try:
                    plugin_dict["created_at"] = plugin_dict["created_at"].isoformat()
                except Exception:
                    plugin_dict["created_at"] = str(plugin_dict["created_at"])

            return {"instance_id": instance_id, "plugin": plugin_dict}

    async def unload_plugin(self, instance_id: str) -> Dict[str, Any]:
        """Unload a plugin instance"""
        async with self._lock:
            if instance_id not in self.instances:
                raise ValueError(f"Plugin instance not found: {instance_id}")

            instance = self.instances[instance_id]

            # Remove from mod-host
            success = await self.modhost.remove_plugin(instance_id)
            if not success:
                logger.warning("Failed to remove plugin %s from mod-host", instance_id)

            # Remove from instances
            del self.instances[instance_id]

            # Publish event (support service bus API compatibility)
            await self._safe_publish(
                "plugin_unloaded", {"instance_id": instance_id, "uri": instance.uri}
            )

            logger.info("Unloaded plugin %s", instance_id)

            return {"status": "ok", "instance_id": instance_id}

    async def set_parameter(
        self, instance_id: str, parameter: str, value: float
    ) -> Dict[str, Any]:
        """Set plugin parameter"""
        if instance_id not in self.instances:
            raise ValueError(f"Plugin instance not found: {instance_id}")

        instance = self.instances[instance_id]

        # Set in mod-host
        success = await self.modhost.set_parameter(instance_id, parameter, value)
        if not success:
            raise RuntimeError("Failed to set parameter in mod-host")

        # Update local state
        instance.parameters[parameter] = value

        # Publish event (support service bus API compatibility)
        await self._safe_publish(
            "parameter_changed",
            {"instance_id": instance_id, "parameter": parameter, "value": value},
        )

        logger.debug("Set parameter %s.%s = %s", instance_id, parameter, value)

        return {"status": "ok", "value": value}

    async def get_parameter(self, instance_id: str, parameter: str) -> Dict[str, Any]:
        """Get plugin parameter value"""
        if instance_id not in self.instances:
            raise ValueError(f"Plugin instance not found: {instance_id}")

        # Try to get from mod-host first
        value = await self.modhost.get_parameter(instance_id, parameter)

        if value is None:
            # Fallback to stored value
            instance = self.instances[instance_id]
            value = instance.parameters.get(parameter)

        return {"parameter": parameter, "value": value}

    async def get_plugin_info(self, instance_id: str) -> Dict[str, Any]:
        """Get plugin instance information"""
        if instance_id not in self.instances:
            raise ValueError(f"Plugin instance not found: {instance_id}")

        instance = self.instances[instance_id]
        return {"plugin": asdict(instance)}

    async def list_instances(self) -> Dict[str, Any]:
        """List all loaded plugin instances"""
        instances = {}
        for instance_id, instance in self.instances.items():
            inst = asdict(instance)
            if inst.get("created_at") is not None:
                try:
                    inst["created_at"] = inst["created_at"].isoformat()
                except Exception:
                    inst["created_at"] = str(inst["created_at"])
            instances[instance_id] = inst

        return {"instances": instances}

    async def clear_all(self):
        """Unload all plugin instances"""
        instance_ids = list(self.instances.keys())
        for instance_id in instance_ids:
            try:
                await self.unload_plugin(instance_id)
            except Exception as e:
                logger.error("Error unloading plugin %s: %s", instance_id, e)

        logger.info("Cleared all plugin instances")

    async def shutdown(self):
        """Shutdown plugin manager"""
        logger.info("Shutting down plugin manager")
        await self.clear_all()
        logger.info("Plugin manager shutdown complete")

    def get_status(self) -> Dict[str, Any]:
        """Get plugin manager status"""
        return {
            "loaded_instances": len(self.instances),
            "available_plugins": len(self.available_plugins),
            "instances": list(self.instances.keys()),
        }
