"""
Session Service Adapter

Provides backward compatibility layer for integrating the Session Service v2
with the existing MOD UI. This adapter enables seamless migration from the
legacy session management to the new service-based architecture.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from .session_client import SessionServiceClient, SessionServiceError


class SessionServiceAdapter:
    """
    Backward compatibility adapter for Session Service v2

    Features:
    - Seamless fallback between service and legacy implementations
    - Graceful error handling and service health monitoring
    - Compatible API with existing MOD UI session management
    - Automatic service discovery and reconnection
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._client = None
        self._service_available = False
        self._use_service = os.environ.get("MOD_USE_SESSION_SERVICE", "0") == "1"

        # Initialize client if service should be used
        if self._use_service:
            try:
                self._client = SessionServiceClient()
                self._service_available = self._client.is_service_healthy()
                if self._service_available:
                    self.logger.info("Session service is available and will be used")
                else:
                    self.logger.warning(
                        "Session service is not available, using fallback"
                    )
            except Exception as e:
                self.logger.warning(f"Failed to initialize session service client: {e}")
                self._service_available = False
        else:
            self.logger.info("Session service disabled via environment variable")

    def _ensure_client(self) -> SessionServiceClient:
        """Ensure client is available and service is healthy"""
        if not self._use_service:
            raise SessionServiceError("Session service is disabled")

        if self._client is None:
            self._client = SessionServiceClient()

        # Re-check service health periodically
        if not self._service_available:
            self._service_available = self._client.is_service_healthy()
            if self._service_available:
                self.logger.info("Session service is now available")

        if not self._service_available:
            raise SessionServiceError("Session service is not available")

        return self._client

    def is_service_available(self) -> bool:
        """Check if session service is available"""
        if not self._use_service:
            return False

        try:
            client = self._ensure_client()
            self._service_available = client.is_service_healthy()
            return self._service_available
        except Exception:
            self._service_available = False
            return False

    def is_service_healthy(self) -> bool:
        """Check if session service is healthy"""
        return self.is_service_available()

    def get_service_status(self) -> Dict[str, Any]:
        """Get session service status"""
        try:
            client = self._ensure_client()
            return client.get_service_status()
        except Exception as e:
            self.logger.debug(f"Failed to get service status: {e}")
            return {"error": str(e), "service": "session-v2", "status": "unavailable"}

    # Session Management

    def get_session_status(self) -> Dict[str, Any]:
        """Get current session status"""
        try:
            client = self._ensure_client()
            return client.get_session_status()
        except Exception as e:
            self.logger.debug(f"Failed to get session status via service: {e}")
            # Return fallback status
            return {
                "success": True,
                "session": {
                    "transport_state": "stopped",
                    "tempo_bpm": 120.0,
                    "sample_rate": 48000,
                    "buffer_size": 256,
                    "audio_driver": "jack",
                    "cpu_load": 0.0,
                    "xrun_count": 0,
                    "uptime_seconds": 0,
                },
                "fallback": True,
            }

    def reset_session(self) -> Dict[str, Any]:
        """Reset session to initial state"""
        try:
            client = self._ensure_client()
            return client.reset_session()
        except Exception as e:
            self.logger.warning(f"Failed to reset session via service: {e}")
            # Return fallback response
            return {
                "success": True,
                "message": "Session reset (fallback mode)",
                "fallback": True,
            }

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session performance statistics"""
        try:
            client = self._ensure_client()
            return client.get_session_stats()
        except Exception as e:
            self.logger.debug(f"Failed to get session stats via service: {e}")
            # Return fallback stats
            return {
                "success": True,
                "stats": {
                    "cpu_load": 0.0,
                    "xrun_count": 0,
                    "uptime_seconds": 0,
                    "sample_rate": 48000,
                    "buffer_size": 256,
                    "transport_state": "stopped",
                },
                "fallback": True,
            }

    # Transport Control

    def transport_play(self) -> Dict[str, Any]:
        """Start transport playback"""
        try:
            client = self._ensure_client()
            return client.transport_play()
        except Exception as e:
            self.logger.warning(f"Failed to start transport via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Transport control not available",
                "fallback": True,
            }

    def transport_stop(self) -> Dict[str, Any]:
        """Stop transport playback"""
        try:
            client = self._ensure_client()
            return client.transport_stop()
        except Exception as e:
            self.logger.warning(f"Failed to stop transport via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Transport control not available",
                "fallback": True,
            }

    def transport_pause(self) -> Dict[str, Any]:
        """Pause transport playback"""
        try:
            client = self._ensure_client()
            return client.transport_pause()
        except Exception as e:
            self.logger.warning(f"Failed to pause transport via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Transport control not available",
                "fallback": True,
            }

    def set_tempo(self, bpm: float) -> Dict[str, Any]:
        """Set session tempo"""
        try:
            client = self._ensure_client()
            return client.set_tempo(bpm)
        except Exception as e:
            self.logger.warning(f"Failed to set tempo via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Tempo control not available",
                "fallback": True,
            }

    def get_tempo(self) -> Dict[str, Any]:
        """Get current session tempo"""
        try:
            client = self._ensure_client()
            return client.get_tempo()
        except Exception as e:
            self.logger.debug(f"Failed to get tempo via service: {e}")
            return {"success": True, "tempo_bpm": 120.0, "fallback": True}

    # System Configuration

    def set_system_config(
        self,
        sample_rate: Optional[int] = None,
        buffer_size: Optional[int] = None,
        audio_driver: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update system configuration"""
        try:
            client = self._ensure_client()
            return client.set_system_config(sample_rate, buffer_size, audio_driver)
        except Exception as e:
            self.logger.warning(f"Failed to set system config via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "System configuration not available",
                "fallback": True,
            }

    def get_system_config(self) -> Dict[str, Any]:
        """Get current system configuration"""
        try:
            client = self._ensure_client()
            return client.get_system_config()
        except Exception as e:
            self.logger.debug(f"Failed to get system config via service: {e}")
            return {
                "success": True,
                "config": {
                    "sample_rate": 48000,
                    "buffer_size": 256,
                    "audio_driver": "jack",
                },
                "fallback": True,
            }

    # Pedalboard Management

    def list_pedalboards(self) -> Dict[str, Any]:
        """List all available pedalboards"""
        try:
            client = self._ensure_client()
            return client.list_pedalboards()
        except Exception as e:
            self.logger.debug(f"Failed to list pedalboards via service: {e}")
            return {"success": True, "pedalboards": [], "count": 0, "fallback": True}

    def get_current_pedalboard(self) -> Dict[str, Any]:
        """Get currently loaded pedalboard"""
        try:
            client = self._ensure_client()
            return client.get_current_pedalboard()
        except Exception as e:
            self.logger.debug(f"Failed to get current pedalboard via service: {e}")
            return {"success": True, "pedalboard": None, "fallback": True}

    def create_pedalboard(
        self, title: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new empty pedalboard"""
        try:
            client = self._ensure_client()
            return client.create_pedalboard(title, description)
        except Exception as e:
            self.logger.warning(f"Failed to create pedalboard via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Pedalboard creation not available",
                "fallback": True,
            }

    def load_pedalboard(self, bundle_path: str) -> Dict[str, Any]:
        """Load a pedalboard from file system"""
        try:
            client = self._ensure_client()
            return client.load_pedalboard(bundle_path)
        except Exception as e:
            self.logger.warning(f"Failed to load pedalboard via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Pedalboard loading not available",
                "fallback": True,
            }

    def save_pedalboard(
        self, title: Optional[str] = None, bundle_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save current pedalboard"""
        try:
            client = self._ensure_client()
            return client.save_pedalboard(title, bundle_path)
        except Exception as e:
            self.logger.warning(f"Failed to save pedalboard via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Pedalboard saving not available",
                "fallback": True,
            }

    # Plugin Management

    def add_plugin(
        self,
        instance_id: str,
        plugin_uri: str,
        x: float,
        y: float,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """Add a plugin to the current pedalboard"""
        try:
            client = self._ensure_client()
            return client.add_plugin(instance_id, plugin_uri, x, y, enabled)
        except Exception as e:
            self.logger.warning(f"Failed to add plugin via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Plugin management not available",
                "fallback": True,
            }

    def remove_plugin(self, instance_id: str) -> Dict[str, Any]:
        """Remove a plugin from the current pedalboard"""
        try:
            client = self._ensure_client()
            return client.remove_plugin(instance_id)
        except Exception as e:
            self.logger.warning(f"Failed to remove plugin via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Plugin management not available",
                "fallback": True,
            }

    def set_plugin_parameter(
        self, instance_id: str, parameter_symbol: str, value: float
    ) -> Dict[str, Any]:
        """Set a plugin parameter value"""
        try:
            client = self._ensure_client()
            return client.set_plugin_parameter(instance_id, parameter_symbol, value)
        except Exception as e:
            self.logger.warning(f"Failed to set plugin parameter via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Parameter control not available",
                "fallback": True,
            }

    # Connection Management

    def add_connection(self, source_port: str, destination_port: str) -> Dict[str, Any]:
        """Add a connection between plugin ports"""
        try:
            client = self._ensure_client()
            return client.add_connection(source_port, destination_port)
        except Exception as e:
            self.logger.warning(f"Failed to add connection via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Connection management not available",
                "fallback": True,
            }

    def remove_connection(
        self, source_port: str, destination_port: str
    ) -> Dict[str, Any]:
        """Remove a connection between plugin ports"""
        try:
            client = self._ensure_client()
            return client.remove_connection(source_port, destination_port)
        except Exception as e:
            self.logger.warning(f"Failed to remove connection via service: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Connection management not available",
                "fallback": True,
            }

    def list_connections(self) -> Dict[str, Any]:
        """List all connections in current pedalboard"""
        try:
            client = self._ensure_client()
            return client.list_connections()
        except Exception as e:
            self.logger.debug(f"Failed to list connections via service: {e}")
            return {"success": True, "connections": [], "count": 0, "fallback": True}

    # Advanced Features

    def wait_for_service(self, timeout: float = 10.0) -> bool:
        """Wait for session service to become available"""
        if not self._use_service:
            return False

        try:
            client = self._ensure_client()
            result = client.wait_for_service(timeout)
            if result:
                self._service_available = True
            return result
        except Exception as e:
            self.logger.debug(f"Failed to wait for service: {e}")
            return False

    def reconnect_service(self) -> bool:
        """Attempt to reconnect to session service"""
        if not self._use_service:
            return False

        try:
            self._client = SessionServiceClient()
            self._service_available = self._client.is_service_healthy()
            if self._service_available:
                self.logger.info("Successfully reconnected to session service")
            return self._service_available
        except Exception as e:
            self.logger.warning(f"Failed to reconnect to session service: {e}")
            self._service_available = False
            return False


# Global adapter instance
_session_adapter_instance: Optional[SessionServiceAdapter] = None


def get_session_adapter() -> SessionServiceAdapter:
    """Get the global session service adapter instance"""
    global _session_adapter_instance
    if _session_adapter_instance is None:
        _session_adapter_instance = SessionServiceAdapter()
    return _session_adapter_instance


def is_session_service_enabled() -> bool:
    """Check if session service is enabled via environment variable"""
    return os.environ.get("MOD_USE_SESSION_SERVICE", "0") == "1"


def is_session_service_available() -> bool:
    """Check if session service is available and healthy"""
    try:
        adapter = get_session_adapter()
        return adapter.is_service_available()
    except Exception:
        return False
