"""
JACK and LV2 Utilities for Audio Engine Service

This module provides Python wrappers for JACK audio connection management
and LV2 plugin discovery/management functionality, integrating with the
existing MOD UI C++ utilities.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    JackConnectionInfo,
    JackData,
    JackPortInfo,
    LV2PluginInfo,
    LV2PluginPort,
)

logger = logging.getLogger(__name__)

# Try to import the mod utils if available (for production)
try:
    from modtools.utils import (
        add_bundle_to_lilv_world,
        close_jack,
        connect_jack_ports,
        disconnect_all_jack_ports,
        disconnect_jack_ports,
        get_all_plugins,
        get_jack_buffer_size,
        get_jack_data,
        get_jack_hardware_ports,
        get_jack_sample_rate,
        get_plugin_info,
        get_plugin_list,
        init_jack,
        remove_bundle_from_lilv_world,
        reset_xruns,
        set_jack_buffer_size,
    )

    HAVE_MOD_UTILS = True
    logger.info("MOD utilities available - using native implementation")
except ImportError:
    logger.warning("MOD utilities not available - using fallback implementations")
    HAVE_MOD_UTILS = False


class JackManager:
    """JACK audio connection manager"""

    def __init__(self):
        self.initialized = False
        self._try_init_jack()

    def _try_init_jack(self) -> bool:
        """Try to initialize JACK"""
        try:
            if HAVE_MOD_UTILS:
                self.initialized = init_jack()
            else:
                # Fallback: check if JACK is running by trying to connect to it
                result = subprocess.run(
                    ["jack_connect", "--help"], capture_output=True, timeout=2
                )
                self.initialized = result.returncode == 0
        except Exception as e:
            logger.warning(f"JACK initialization failed: {e}")
            self.initialized = False

        logger.info(f"JACK initialized: {self.initialized}")
        return self.initialized

    def get_jack_data(self, with_transport: bool = True) -> JackData:
        """Get current JACK system data"""
        if not self.initialized:
            return JackData()

        try:
            if HAVE_MOD_UTILS:
                data = get_jack_data(with_transport)
                return JackData(
                    cpu_load=data.get("cpuLoad", 0.0),
                    xruns=data.get("xruns", 0),
                    rolling=data.get("rolling", False),
                    bpb=data.get("bpb", 4.0),
                    bpm=data.get("bpm", 120.0),
                    buffer_size=get_jack_buffer_size(),
                    sample_rate=get_jack_sample_rate(),
                )
            else:
                # Fallback implementation
                return self._get_jack_data_fallback()
        except Exception as e:
            logger.error(f"Failed to get JACK data: {e}")
            return JackData()

    def _get_jack_data_fallback(self) -> JackData:
        """Fallback JACK data retrieval using command-line tools"""
        try:
            # Get sample rate
            result = subprocess.run(
                ["jack_sample_rate"], capture_output=True, text=True, timeout=2
            )
            sample_rate = (
                float(result.stdout.strip()) if result.returncode == 0 else 48000.0
            )

            # Get buffer size
            result = subprocess.run(
                ["jack_buffer_size"], capture_output=True, text=True, timeout=2
            )
            buffer_size = int(result.stdout.strip()) if result.returncode == 0 else 512

            return JackData(
                sample_rate=sample_rate,
                buffer_size=buffer_size,
            )
        except Exception as e:
            logger.warning(f"Fallback JACK data retrieval failed: {e}")
            return JackData()

    def get_hardware_ports(
        self, is_audio: bool = True, is_output: bool = False
    ) -> List[JackPortInfo]:
        """Get JACK hardware ports"""
        if not self.initialized:
            return []

        try:
            if HAVE_MOD_UTILS:
                ports = get_jack_hardware_ports(is_audio, is_output)
                return [
                    JackPortInfo(
                        name=port,
                        is_audio=is_audio,
                        is_output=is_output,
                    )
                    for port in ports
                ]
            else:
                return self._get_hardware_ports_fallback(is_audio, is_output)
        except Exception as e:
            logger.error(f"Failed to get hardware ports: {e}")
            return []

    def _get_hardware_ports_fallback(
        self, is_audio: bool, is_output: bool
    ) -> List[JackPortInfo]:
        """Fallback hardware ports retrieval using jack_lsp"""
        try:
            args = ["jack_lsp"]
            if is_audio:
                args.append("-A")  # Audio ports only
            if is_output:
                args.append("-o")  # Output ports only
            else:
                args.append("-i")  # Input ports only

            result = subprocess.run(args, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return []

            ports = []
            for line in result.stdout.strip().split("\n"):
                if (
                    line and "system:" in line
                ):  # Hardware ports typically start with system:
                    ports.append(
                        JackPortInfo(
                            name=line.strip(),
                            is_audio=is_audio,
                            is_output=is_output,
                        )
                    )

            return ports
        except Exception as e:
            logger.warning(f"Fallback hardware ports retrieval failed: {e}")
            return []

    def connect_ports(self, output_port: str, input_port: str) -> bool:
        """Connect two JACK ports"""
        if not self.initialized:
            return False

        try:
            if HAVE_MOD_UTILS:
                return connect_jack_ports(output_port, input_port)
            else:
                return self._connect_ports_fallback(output_port, input_port)
        except Exception as e:
            logger.error(f"Failed to connect ports {output_port} -> {input_port}: {e}")
            return False

    def _connect_ports_fallback(self, output_port: str, input_port: str) -> bool:
        """Fallback port connection using jack_connect"""
        try:
            result = subprocess.run(
                ["jack_connect", output_port, input_port],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Fallback port connection failed: {e}")
            return False

    def disconnect_ports(self, output_port: str, input_port: str) -> bool:
        """Disconnect two JACK ports"""
        if not self.initialized:
            return False

        try:
            if HAVE_MOD_UTILS:
                return disconnect_jack_ports(output_port, input_port)
            else:
                return self._disconnect_ports_fallback(output_port, input_port)
        except Exception as e:
            logger.error(
                f"Failed to disconnect ports {output_port} -> {input_port}: {e}"
            )
            return False

    def _disconnect_ports_fallback(self, output_port: str, input_port: str) -> bool:
        """Fallback port disconnection using jack_disconnect"""
        try:
            result = subprocess.run(
                ["jack_disconnect", output_port, input_port],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Fallback port disconnection failed: {e}")
            return False

    def disconnect_all_ports(self, port_name: str) -> bool:
        """Disconnect all connections from a JACK port"""
        if not self.initialized:
            return False

        try:
            if HAVE_MOD_UTILS:
                return disconnect_all_jack_ports(port_name)
            else:
                return self._disconnect_all_ports_fallback(port_name)
        except Exception as e:
            logger.error(f"Failed to disconnect all ports from {port_name}: {e}")
            return False

    def _disconnect_all_ports_fallback(self, port_name: str) -> bool:
        """Fallback disconnect all using jack_lsp and jack_disconnect"""
        try:
            # Get all connections for this port
            result = subprocess.run(
                ["jack_lsp", "-c", port_name], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return False

            # Parse connections and disconnect them
            success = True
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and line != port_name:
                    if not self._disconnect_ports_fallback(port_name, line):
                        success = False

            return success
        except Exception as e:
            logger.warning(f"Fallback disconnect all failed: {e}")
            return False

    def reset_xruns(self):
        """Reset JACK xrun counter"""
        if not self.initialized:
            return

        try:
            if HAVE_MOD_UTILS:
                reset_xruns()
            else:
                logger.warning("XRUN reset not available in fallback mode")
        except Exception as e:
            logger.error(f"Failed to reset xruns: {e}")

    def set_buffer_size(self, size: int) -> bool:
        """Set JACK buffer size"""
        if not self.initialized:
            return False

        try:
            if HAVE_MOD_UTILS:
                new_size = set_jack_buffer_size(size)
                return new_size == size
            else:
                logger.warning("Buffer size setting not available in fallback mode")
                return False
        except Exception as e:
            logger.error(f"Failed to set buffer size: {e}")
            return False

    def cleanup(self):
        """Cleanup JACK resources"""
        if self.initialized and HAVE_MOD_UTILS:
            try:
                close_jack()
                self.initialized = False
            except Exception as e:
                logger.error(f"Failed to cleanup JACK: {e}")


class LV2Manager:
    """LV2 plugin discovery and management"""

    def __init__(self):
        self.initialized = HAVE_MOD_UTILS
        logger.info(f"LV2Manager initialized with native support: {self.initialized}")

    def get_plugin_list(self) -> List[str]:
        """Get list of all available LV2 plugin URIs"""
        try:
            if HAVE_MOD_UTILS:
                return get_plugin_list() or []
            else:
                return self._get_plugin_list_fallback()
        except Exception as e:
            logger.error(f"Failed to get plugin list: {e}")
            return []

    def _get_plugin_list_fallback(self) -> List[str]:
        """Fallback plugin list using lv2ls command"""
        try:
            result = subprocess.run(
                ["lv2ls"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return []

            return [
                line.strip()
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
        except Exception as e:
            logger.warning(f"Fallback plugin list retrieval failed: {e}")
            return []

    def get_all_plugins(self) -> List[Dict[str, Any]]:
        """Get all plugin information (lightweight)"""
        try:
            if HAVE_MOD_UTILS:
                plugins = get_all_plugins()
                return (
                    [self._convert_plugin_mini_to_dict(p) for p in plugins]
                    if plugins
                    else []
                )
            else:
                # Fallback: get basic info for each plugin
                plugin_uris = self.get_plugin_list()
                return [
                    {"uri": uri, "name": uri.split("/")[-1]} for uri in plugin_uris[:50]
                ]  # Limit for performance
        except Exception as e:
            logger.error(f"Failed to get all plugins: {e}")
            return []

    def _convert_plugin_mini_to_dict(self, plugin_mini) -> Dict[str, Any]:
        """Convert PluginInfo_Mini C struct to dict"""
        # This is a placeholder - actual implementation would depend on the exact structure
        return {
            "uri": getattr(plugin_mini, "uri", ""),
            "name": getattr(plugin_mini, "name", ""),
            "brand": getattr(plugin_mini, "brand", ""),
            "category": getattr(plugin_mini, "category", []),
        }

    def get_plugin_info(self, plugin_uri: str) -> Optional[LV2PluginInfo]:
        """Get detailed plugin information"""
        try:
            if HAVE_MOD_UTILS:
                info = get_plugin_info(plugin_uri)
                return self._convert_plugin_info_to_model(info) if info else None
            else:
                return self._get_plugin_info_fallback(plugin_uri)
        except Exception as e:
            logger.error(f"Failed to get plugin info for {plugin_uri}: {e}")
            return None

    def _convert_plugin_info_to_model(self, plugin_info) -> LV2PluginInfo:
        """Convert PluginInfo C struct to Pydantic model"""
        # This is a placeholder - actual implementation would depend on the exact structure
        ports = []
        if hasattr(plugin_info, "ports") and plugin_info.ports:
            # Convert port information
            for port in plugin_info.ports:
                ports.append(
                    LV2PluginPort(
                        symbol=getattr(port, "symbol", ""),
                        name=getattr(port, "name", ""),
                        is_input=getattr(port, "is_input", False),
                        is_audio=getattr(port, "is_audio", False),
                        is_cv=getattr(port, "is_cv", False),
                        is_midi=getattr(port, "is_midi", False),
                        is_control=getattr(port, "is_control", False),
                        default_value=getattr(port, "default_value", None),
                        minimum_value=getattr(port, "minimum_value", None),
                        maximum_value=getattr(port, "maximum_value", None),
                    )
                )

        return LV2PluginInfo(
            uri=getattr(plugin_info, "uri", ""),
            name=getattr(plugin_info, "name", ""),
            brand=getattr(plugin_info, "brand", ""),
            comment=getattr(plugin_info, "comment", ""),
            version=getattr(plugin_info, "version", ""),
            license=getattr(plugin_info, "license", ""),
            author=getattr(plugin_info, "author", ""),
            category=getattr(plugin_info, "category", []),
            bundle_path=getattr(plugin_info, "bundle", ""),
            binary=getattr(plugin_info, "binary", ""),
            ports=ports,
            has_gui=getattr(plugin_info, "has_gui", False),
        )

    def _get_plugin_info_fallback(self, plugin_uri: str) -> Optional[LV2PluginInfo]:
        """Fallback plugin info using lv2info command"""
        try:
            result = subprocess.run(
                ["lv2info", plugin_uri], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return None

            # Parse lv2info output (basic implementation)
            info = LV2PluginInfo(uri=plugin_uri, name=plugin_uri.split("/")[-1])

            for line in result.stdout.split("\n"):
                line = line.strip()
                if "Name:" in line:
                    info.name = line.split("Name:", 1)[1].strip()
                elif "Class:" in line:
                    info.category = [line.split("Class:", 1)[1].strip()]

            return info
        except Exception as e:
            logger.warning(
                f"Fallback plugin info retrieval failed for {plugin_uri}: {e}"
            )
            return None

    def add_bundle(self, bundle_path: str) -> List[str]:
        """Add an LV2 bundle to the world"""
        try:
            if HAVE_MOD_UTILS:
                result = add_bundle_to_lilv_world(bundle_path)
                return result or []
            else:
                logger.warning("Bundle management not available in fallback mode")
                return []
        except Exception as e:
            logger.error(f"Failed to add bundle {bundle_path}: {e}")
            return []

    def remove_bundle(
        self, bundle_path: str, resource: Optional[str] = None
    ) -> List[str]:
        """Remove an LV2 bundle from the world"""
        try:
            if HAVE_MOD_UTILS:
                result = remove_bundle_from_lilv_world(bundle_path, resource)
                return result or []
            else:
                logger.warning("Bundle management not available in fallback mode")
                return []
        except Exception as e:
            logger.error(f"Failed to remove bundle {bundle_path}: {e}")
            return []


# Global instances (singletons)
_jack_manager: Optional[JackManager] = None
_lv2_manager: Optional[LV2Manager] = None


def get_jack_manager() -> JackManager:
    """Get the global JACK manager instance"""
    global _jack_manager
    if _jack_manager is None:
        _jack_manager = JackManager()
    return _jack_manager


def get_lv2_manager() -> LV2Manager:
    """Get the global LV2 manager instance"""
    global _lv2_manager
    if _lv2_manager is None:
        _lv2_manager = LV2Manager()
    return _lv2_manager


def cleanup_managers():
    """Cleanup all manager instances"""
    global _jack_manager, _lv2_manager

    if _jack_manager:
        _jack_manager.cleanup()
        _jack_manager = None

    if _lv2_manager:
        _lv2_manager = None
