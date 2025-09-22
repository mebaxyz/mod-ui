#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2012-2023 MOD Audio UG
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Hardware service adapter to integrate standalone hardware service with existing MOD UI code.
This module provides backward-compatible interfaces while using the new hardware service architecture.
"""

import logging
from typing import Any, Dict, List, Optional

from mod import safe_json_load
from mod.hardware_client import get_hardware_client
from mod.settings import HARDWARE_DESC_FILE

logger = logging.getLogger(__name__)


class HardwareServiceAdapter:
    """Adapter that provides backward compatibility for hardware operations."""

    def __init__(self):
        self.client = get_hardware_client()
        self._fallback_descriptor = None

    def get_hardware_descriptor(self) -> Dict[str, Any]:
        """Get hardware descriptor with fallback to file-based descriptor."""
        try:
            # Try to get descriptor from hardware service first
            descriptor = self.client.get_hardware_descriptor()
            if descriptor and not descriptor.get("error"):
                return descriptor
        except Exception as e:
            logger.debug(f"Hardware service descriptor failed, using fallback: {e}")

        # Fallback to file-based descriptor
        if self._fallback_descriptor is None:
            self._fallback_descriptor = safe_json_load(HARDWARE_DESC_FILE, dict)
        return self._fallback_descriptor

    def get_hardware_actuators(self) -> List[Dict[str, Any]]:
        """Get hardware actuators from descriptor."""
        descriptor = self.get_hardware_descriptor()
        return descriptor.get("actuators", [])

    def get_hardware_status(self) -> Dict[str, Any]:
        """Get current hardware status."""
        try:
            return self.client.get_hardware_status()
        except Exception as e:
            logger.error(f"Failed to get hardware status: {e}")
            return {"device_connected": False, "device_type": "", "error": str(e)}

    def hmi_ping(self) -> bool:
        """Ping HMI device."""
        try:
            return self.client.hmi_ping()
        except Exception as e:
            logger.error(f"HMI ping failed: {e}")
            return False

    def hmi_reset_eeprom(self) -> bool:
        """Reset HMI EEPROM."""
        try:
            return self.client.hmi_reset_eeprom()
        except Exception as e:
            logger.error(f"HMI EEPROM reset failed: {e}")
            return False

    def scan_devices(self) -> List[Dict[str, Any]]:
        """Scan for hardware devices."""
        try:
            return self.client.scan_devices()
        except Exception as e:
            logger.error(f"Device scan failed: {e}")
            return []

    def control_chain_scan(self) -> List[Dict[str, Any]]:
        """Scan for Control Chain devices."""
        try:
            return self.client.control_chain_scan()
        except Exception as e:
            logger.error(f"Control Chain scan failed: {e}")
            return []

    def is_service_healthy(self) -> bool:
        """Check if hardware service is healthy."""
        try:
            health = self.client.health_check()
            return health.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global adapter instance
_hardware_adapter: Optional[HardwareServiceAdapter] = None


def get_hardware_adapter() -> HardwareServiceAdapter:
    """Get the global hardware service adapter."""
    global _hardware_adapter
    if _hardware_adapter is None:
        _hardware_adapter = HardwareServiceAdapter()
    return _hardware_adapter


# Backward compatibility functions that can replace existing functions
def get_hardware_descriptor_via_service() -> Dict[str, Any]:
    """Get hardware descriptor via service (backward compatible)."""
    return get_hardware_adapter().get_hardware_descriptor()


def get_hardware_actuators_via_service() -> List[Dict[str, Any]]:
    """Get hardware actuators via service (backward compatible)."""
    return get_hardware_adapter().get_hardware_actuators()
