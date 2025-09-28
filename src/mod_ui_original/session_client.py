"""
Session Service HTTP Client

HTTP client for communicating with the Session Service v2.
Provides fallback mechanisms and compatibility with the existing MOD UI.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from .settings import MOD_SESSION_SERVICE_TIMEOUT, MOD_SESSION_SERVICE_URL


class SessionServiceClient:
    """
    HTTP client for the Session Service v2

    Provides robust communication with the session service including:
    - Service health monitoring
    - Automatic retries with backoff
    - Multiple HTTP backend support (requests -> urllib)
    - Comprehensive error handling
    """

    def __init__(
        self,
        service_url: str = MOD_SESSION_SERVICE_URL,
        timeout: int = MOD_SESSION_SERVICE_TIMEOUT,
    ):
        self.logger = logging.getLogger(__name__)
        self.service_url = service_url.rstrip("/")
        self.timeout = timeout
        self._http_backend = None
        self._session = None

        self.logger.info(
            f"SessionServiceClient initialized: {self.service_url} (timeout={timeout}s)"
        )

    def _get_http_backend(self):
        """Get HTTP backend with fallback mechanism"""
        if self._http_backend is not None:
            return self._http_backend

        try:
            import requests

            self._http_backend = "requests"
            if self._session is None:
                self._session = requests.Session()
            self.logger.debug("Using requests backend")
            return self._http_backend
        except ImportError:
            self._http_backend = "urllib"
            self.logger.debug("Using urllib backend (requests not available)")
            return self._http_backend

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with fallback and error handling"""
        url = urljoin(self.service_url + "/", endpoint.lstrip("/"))
        headers = {"Content-Type": "application/json"}

        backend = self._get_http_backend()

        try:
            if backend == "requests":
                return self._make_requests_call(method, url, headers, data)
            else:
                return self._make_urllib_call(method, url, headers, data)

        except Exception as e:
            self.logger.error(f"Request failed: {method} {url} - {e}")
            raise SessionServiceError(f"Request failed: {e}")

    def _make_requests_call(
        self, method: str, url: str, headers: Dict, data: Optional[Dict]
    ) -> Dict[str, Any]:
        """Make request using requests library"""
        json_data = json.dumps(data) if data else None

        if self._session is None:
            raise SessionServiceError("Session object not initialized")

        response = self._session.request(
            method=method,
            url=url,
            headers=headers,
            data=json_data,
            timeout=self.timeout,
        )

        if response.status_code >= 400:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            raise SessionServiceError(error_msg)

        try:
            return response.json()
        except json.JSONDecodeError:
            return {"status": "ok", "data": response.text}

    def _make_urllib_call(
        self, method: str, url: str, headers: Dict, data: Optional[Dict]
    ) -> Dict[str, Any]:
        """Make request using urllib (fallback)"""
        import urllib.error
        import urllib.parse
        import urllib.request

        json_data = json.dumps(data).encode() if data else None

        request = urllib.request.Request(
            url, data=json_data, headers=headers, method=method
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_data = response.read().decode()
                try:
                    return json.loads(response_data)
                except json.JSONDecodeError:
                    return {"status": "ok", "data": response_data}

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.read().decode()}"
            raise SessionServiceError(error_msg)
        except urllib.error.URLError as e:
            raise SessionServiceError(f"Connection error: {e.reason}")

    def is_service_healthy(self) -> bool:
        """Check if the session service is healthy"""
        try:
            response = self._make_request("GET", "/ping")
            return response.get("status") == "ok"
        except Exception as e:
            self.logger.debug(f"Health check failed: {e}")
            return False

    def get_service_status(self) -> Dict[str, Any]:
        """Get detailed service status"""
        try:
            return self._make_request("GET", "/status")
        except Exception as e:
            self.logger.error(f"Failed to get service status: {e}")
            return {"error": str(e), "service": "session-v2", "status": "error"}

    # Session Management

    def get_session_status(self) -> Dict[str, Any]:
        """Get current session status"""
        return self._make_request("GET", "/api/session/status")

    def reset_session(self) -> Dict[str, Any]:
        """Reset session to initial state"""
        return self._make_request("POST", "/api/session/reset")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session performance statistics"""
        return self._make_request("GET", "/api/session/stats")

    def reset_session_stats(self) -> Dict[str, Any]:
        """Reset session performance counters"""
        return self._make_request("POST", "/api/session/stats/reset")

    # Transport Control

    def transport_play(self) -> Dict[str, Any]:
        """Start transport playback"""
        return self._make_request("POST", "/api/session/transport/play")

    def transport_stop(self) -> Dict[str, Any]:
        """Stop transport playback"""
        return self._make_request("POST", "/api/session/transport/stop")

    def transport_pause(self) -> Dict[str, Any]:
        """Pause transport playback"""
        return self._make_request("POST", "/api/session/transport/pause")

    def transport_rewind(self) -> Dict[str, Any]:
        """Rewind transport to beginning"""
        return self._make_request("POST", "/api/session/transport/rewind")

    def set_tempo(self, bpm: float) -> Dict[str, Any]:
        """Set session tempo"""
        return self._make_request("POST", "/api/session/tempo", {"bpm": bpm})

    def get_tempo(self) -> Dict[str, Any]:
        """Get current session tempo"""
        return self._make_request("GET", "/api/session/tempo")

    # System Configuration

    def set_system_config(
        self,
        sample_rate: Optional[int] = None,
        buffer_size: Optional[int] = None,
        audio_driver: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update system configuration"""
        data: Dict[str, Any] = {}
        if sample_rate is not None:
            data["sample_rate"] = sample_rate
        if buffer_size is not None:
            data["buffer_size"] = buffer_size
        if audio_driver is not None:
            data["audio_driver"] = audio_driver

        return self._make_request("POST", "/api/session/config", data)

    def get_system_config(self) -> Dict[str, Any]:
        """Get current system configuration"""
        return self._make_request("GET", "/api/session/config")

    # Pedalboard Management

    def list_pedalboards(self) -> Dict[str, Any]:
        """List all available pedalboards"""
        return self._make_request("GET", "/api/pedalboard/list")

    def get_current_pedalboard(self) -> Dict[str, Any]:
        """Get currently loaded pedalboard"""
        return self._make_request("GET", "/api/pedalboard/current")

    def create_pedalboard(
        self, title: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new empty pedalboard"""
        data = {"title": title}
        if description:
            data["description"] = description
        return self._make_request("POST", "/api/pedalboard/create", data)

    def load_pedalboard(self, bundle_path: str) -> Dict[str, Any]:
        """Load a pedalboard from file system"""
        return self._make_request("POST", f"/api/pedalboard/load/{bundle_path}")

    def save_pedalboard(
        self, title: Optional[str] = None, bundle_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save current pedalboard"""
        data = {}
        if title:
            data["title"] = title
        if bundle_path:
            data["bundle_path"] = bundle_path
        return self._make_request("POST", "/api/pedalboard/save", data)

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
        data = {
            "instance_id": instance_id,
            "plugin_uri": plugin_uri,
            "x": x,
            "y": y,
            "enabled": enabled,
        }
        return self._make_request("POST", "/api/pedalboard/plugin/add", data)

    def remove_plugin(self, instance_id: str) -> Dict[str, Any]:
        """Remove a plugin from the current pedalboard"""
        return self._make_request("DELETE", f"/api/pedalboard/plugin/{instance_id}")

    def move_plugin(self, instance_id: str, x: float, y: float) -> Dict[str, Any]:
        """Move a plugin on the pedalboard canvas"""
        data = {"x": x, "y": y}
        return self._make_request(
            "PATCH", f"/api/pedalboard/plugin/{instance_id}/move", data
        )

    def set_plugin_parameter(
        self, instance_id: str, parameter_symbol: str, value: float
    ) -> Dict[str, Any]:
        """Set a plugin parameter value"""
        data = {"value": value}
        return self._make_request(
            "PATCH",
            f"/api/pedalboard/plugin/{instance_id}/parameter/{parameter_symbol}",
            data,
        )

    def enable_plugin(self, instance_id: str) -> Dict[str, Any]:
        """Enable a plugin (remove bypass)"""
        return self._make_request(
            "PATCH", f"/api/pedalboard/plugin/{instance_id}/enable"
        )

    def disable_plugin(self, instance_id: str) -> Dict[str, Any]:
        """Disable a plugin (bypass)"""
        return self._make_request(
            "PATCH", f"/api/pedalboard/plugin/{instance_id}/disable"
        )

    # Connection Management

    def add_connection(self, source_port: str, destination_port: str) -> Dict[str, Any]:
        """Add a connection between plugin ports"""
        data = {"source_port": source_port, "destination_port": destination_port}
        return self._make_request("POST", "/api/pedalboard/connection/add", data)

    def remove_connection(
        self, source_port: str, destination_port: str
    ) -> Dict[str, Any]:
        """Remove a connection between plugin ports"""
        params = f"source_port={source_port}&destination_port={destination_port}"
        return self._make_request(
            "DELETE", f"/api/pedalboard/connection/remove?{params}"
        )

    def list_connections(self) -> Dict[str, Any]:
        """List all connections in current pedalboard"""
        return self._make_request("GET", "/api/pedalboard/connections")

    # Snapshot Management

    def save_snapshot(self, name: str) -> Dict[str, Any]:
        """Save current session state as a named snapshot"""
        return self._make_request("POST", f"/api/session/snapshot/save?name={name}")

    def load_snapshot(self, name: str) -> Dict[str, Any]:
        """Load a saved session snapshot"""
        return self._make_request("POST", f"/api/session/snapshot/load/{name}")

    def list_snapshots(self) -> Dict[str, Any]:
        """List all available session snapshots"""
        return self._make_request("GET", "/api/session/snapshots")

    # Advanced Features

    def test_connection(self, retries: int = 3, delay: float = 1.0) -> bool:
        """Test connection to session service with retries"""
        for attempt in range(retries):
            if self.is_service_healthy():
                return True

            if attempt < retries - 1:
                self.logger.debug(f"Connection test failed, retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff

        return False

    def wait_for_service(
        self, timeout: float = 30.0, check_interval: float = 1.0
    ) -> bool:
        """Wait for session service to become available"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.is_service_healthy():
                self.logger.info("Session service is now available")
                return True

            time.sleep(check_interval)

        self.logger.warning(f"Session service not available after {timeout}s")
        return False


class SessionServiceError(Exception):
    """Exception raised by session service operations"""

    pass


# Global client instance
_session_client_instance: Optional[SessionServiceClient] = None


def get_session_client() -> SessionServiceClient:
    """Get the global session service client instance"""
    global _session_client_instance
    if _session_client_instance is None:
        _session_client_instance = SessionServiceClient()
    return _session_client_instance


def is_session_service_available() -> bool:
    """Check if session service is available"""
    try:
        client = get_session_client()
        return client.is_service_healthy()
    except Exception:
        return False
