#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2012-2023 MOD Audio UG
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from mod.settings import HARDWARE_SERVICE_URL, REDIS_HOST, REDIS_PORT

# Try to import redis if available
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning(
        "Redis library not available. Hardware events will not be accessible."
    )

# Try to import requests if available, fallback to urllib
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class HardwareServiceClient:
    """Client for communicating with the standalone hardware service."""

    def __init__(self, service_url: str = HARDWARE_SERVICE_URL):
        self.service_url = service_url.rstrip("/")
        self.logger = logging.getLogger(__name__)

        # Initialize HTTP client
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.use_requests = True
        else:
            self.session = None
            self.use_requests = False

        # Initialize Redis client if available
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
                )
            except Exception as e:
                self.logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
        else:
            self.redis_client = None

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request using either requests or urllib."""
        url = f"{self.service_url}{endpoint}"

        if self.use_requests:
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, timeout=kwargs.get("timeout", 5))
                elif method.upper() == "POST":
                    response = self.session.post(url, timeout=kwargs.get("timeout", 5))
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise e
        else:
            # Fallback to urllib
            try:
                if method.upper() == "POST":
                    req = urllib.request.Request(url, data=b"", method="POST")
                else:
                    req = urllib.request.Request(url)

                with urllib.request.urlopen(
                    req, timeout=kwargs.get("timeout", 5)
                ) as response:
                    return json.loads(response.read().decode())
            except Exception as e:
                raise e

    def health_check(self) -> Dict[str, Any]:
        """Check if the hardware service is healthy."""
        try:
            return self._make_request("GET", "/health")
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def get_hardware_status(self) -> Dict[str, Any]:
        """Get current hardware status."""
        try:
            return self._make_request("GET", "/hardware/status")
        except Exception as e:
            self.logger.error(f"Failed to get hardware status: {e}")
            return {"error": str(e)}

    def get_hardware_descriptor(self) -> Dict[str, Any]:
        """Get hardware descriptor information."""
        try:
            return self._make_request("GET", "/hardware/descriptor")
        except Exception as e:
            self.logger.error(f"Failed to get hardware descriptor: {e}")
            return {}

    def scan_devices(self) -> List[Dict[str, Any]]:
        """Trigger device scan and return discovered devices."""
        try:
            return self._make_request("POST", "/hardware/scan", timeout=10)
        except Exception as e:
            self.logger.error(f"Failed to scan devices: {e}")
            return []

    def hmi_ping(self) -> bool:
        """Send ping to HMI device."""
        try:
            result = self._make_request("POST", "/hardware/hmi/ping")
            return result.get("success", False)
        except Exception as e:
            self.logger.error(f"HMI ping failed: {e}")
            return False

    def hmi_reset_eeprom(self) -> bool:
        """Reset HMI EEPROM."""
        try:
            result = self._make_request(
                "POST", "/hardware/hmi/reset_eeprom", timeout=10
            )
            return result.get("success", False)
        except Exception as e:
            self.logger.error(f"HMI EEPROM reset failed: {e}")
            return False

    def control_chain_scan(self) -> List[Dict[str, Any]]:
        """Scan for Control Chain devices."""
        try:
            return self._make_request(
                "POST", "/hardware/control_chain/scan", timeout=10
            )
        except Exception as e:
            self.logger.error(f"Control Chain scan failed: {e}")
            return []

    def subscribe_to_events(
        self, event_types: Optional[List[str]] = None
    ) -> redis.client.PubSub:
        """Subscribe to hardware events from Redis.

        Args:
            event_types: List of event types to filter for. If None, subscribes to all hardware events.

        Returns:
            Redis PubSub object for listening to events
        """
        pubsub = self.redis_client.pubsub()

        if event_types:
            # Subscribe to specific event types
            patterns = [f"mod_ui:event:*:{event_type}" for event_type in event_types]
            for pattern in patterns:
                pubsub.psubscribe(pattern)
        else:
            # Subscribe to all hardware-related events
            pubsub.psubscribe("mod_ui:event:*:hardware_*")
            pubsub.psubscribe("mod_ui:event:*:control_chain_*")
            pubsub.psubscribe("mod_ui:event:*:hmi_*")

        return pubsub

    def get_latest_hardware_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent hardware events from Redis.

        Args:
            limit: Maximum number of events to retrieve

        Returns:
            List of event dictionaries
        """
        try:
            # Get all event keys
            event_keys = self.redis_client.keys("event:*")

            if not event_keys:
                return []

            # Sort by timestamp (Redis keys include UUIDs, so we'll get events and sort by timestamp)
            events = []
            for key in event_keys[-limit:]:  # Get recent keys
                event_data = self.redis_client.get(key)
                if event_data:
                    try:
                        event = json.loads(event_data)
                        # Filter for hardware-related events
                        if any(
                            hw_type in event.get("event_type", "")
                            for hw_type in ["hardware", "control_chain", "hmi"]
                        ):
                            events.append(event)
                    except json.JSONDecodeError:
                        continue

            # Sort by timestamp
            events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return events[:limit]

        except Exception as e:
            self.logger.error(f"Failed to get hardware events: {e}")
            return []


# Singleton instance for global use
_hardware_client: Optional[HardwareServiceClient] = None


def get_hardware_client() -> HardwareServiceClient:
    """Get the global hardware service client instance."""
    global _hardware_client
    if _hardware_client is None:
        _hardware_client = HardwareServiceClient()
    return _hardware_client


def cleanup_hardware_client():
    """Clean up the global hardware client."""
    global _hardware_client
    if _hardware_client:
        _hardware_client.session.close()
        _hardware_client = None
