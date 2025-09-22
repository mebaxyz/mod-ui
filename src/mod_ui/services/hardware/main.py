"""
Standalone Hardware Service - Manages MOD device hardware interfaces

This service provides isolated hardware communication with Redis event bus integration.
It handles:
- Serial communication with MOD devices
- HMI (Human Machine Interface) protocol
- Control Chain device management
- JACK audio system integration
- Hardware monitoring and diagnostics

Communicates with other services via Redis events for loose coupling.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import serial
import serial.tools.list_ports
import uvicorn
from fastapi import FastAPI

try:
    from mod.control_chain import ControlChainDeviceListener
    from mod.hmi import HMI
except ImportError:
    # Mock for development/testing
    class HMI:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            pass

    class ControlChainDeviceListener:
        def __init__(self, *args, **kwargs):
            pass

        def wait_initialized(self, callback):
            pass

        crashed = False


try:
    from mod_ui.services.session_v2.models.events import EventType
    from mod_ui.services.session_v2.models.hardware_events import (
        ControlChainDeviceStatus,
        HMIMessageType,
        create_control_chain_event,
        create_hardware_status_event,
        create_hmi_event,
    )
    from mod_ui.services.session_v2.utils.event_bus import EventBus, RedisEventBus
except ImportError as e:
    print(f"Warning: Could not import session_v2 modules: {e}")

    # Mock the classes for standalone operation
    class EventType:
        pass

    class ControlChainDeviceStatus:
        ADDED = "added"
        REMOVED = "removed"
        CONNECTED = "connected"
        DISCONNECTED = "disconnected"
        ACTUATOR_ADDED = "actuator_added"

    class HMIMessageType:
        HEARTBEAT = "heartbeat"
        DISCONNECT = "disconnect"
        CONTROL_ADD = "control_add"
        CONTROL_REMOVE = "control_remove"
        MESSAGE = "message"

    def create_hardware_status_event(*args, **kwargs):
        return {"type": "hardware_status", "data": kwargs}

    def create_control_chain_event(*args, **kwargs):
        return {"type": "control_chain", "data": kwargs}

    def create_hmi_event(*args, **kwargs):
        return {"type": "hmi", "data": kwargs}

    class EventBus:
        async def connect(self):
            pass

        async def disconnect(self):
            pass

        async def publish(self, event):
            pass

    class RedisEventBus(EventBus):
        def __init__(self, *args, **kwargs):
            pass


@dataclass
class HardwareState:
    """Represents the current state of connected hardware"""

    device_connected: bool = False
    device_type: str = ""
    serial_port: Optional[str] = None
    hmi_version: Optional[str] = None
    last_heartbeat: datetime = field(default_factory=datetime.now)
    control_chain_devices: List[Dict[str, Any]] = field(default_factory=list)


class HardwareService:
    """
    Service for managing hardware interfaces with MOD devices.

    This service handles:
    - Serial communication with MOD Duo/Duo X devices
    - HMI (Human Machine Interface) protocol communication
    - Control Chain device management for external hardware
    - Jack audio system integration
    - Real-time hardware monitoring and status reporting
    """

    def __init__(self, device_path: str = "/dev/ttyACM0"):
        """Initialize the hardware service."""
        self.device_path = device_path
        self.serial_port: Optional[serial.Serial] = None
        self.hmi: Optional[HMI] = None
        self.control_chain: Optional[ControlChainDeviceListener] = None
        self.hardware_state = HardwareState()
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self.event_bus: Optional[EventBus] = None

        self.setup_logging()

    def setup_logging(self):
        """Setup logging for the hardware service."""
        self.logger = logging.getLogger(f"{__name__}.HardwareService")

    async def initialize(self):
        """Initialize the hardware service"""
        try:
            self.logger.info("Initializing hardware service...")

            # Detect MOD devices
            await self._detect_devices()

            # Initialize HMI if device found
            if self.hardware_state.device_connected:
                await self._initialize_hmi()
                await self._initialize_control_chain()

            self.logger.info("Hardware service initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize hardware service: {e}")
            raise

    async def _detect_devices(self):
        """Detect connected MOD devices"""
        try:
            self.logger.info("Scanning for MOD devices...")

            # List all available serial ports
            ports = serial.tools.list_ports.comports()

            for port in ports:
                self.logger.debug(f"Checking port: {port.device}")

                # Check for MOD device signatures
                if self._is_mod_device(port):
                    self.hardware_state.device_connected = True
                    self.hardware_state.serial_port = port.device
                    self.hardware_state.device_type = self._detect_device_type(port)
                    self.logger.info(
                        f"Found MOD device: {self.hardware_state.device_type} on {port.device}"
                    )
                    break

            if not self.hardware_state.device_connected:
                self.logger.warning("No MOD devices detected")

        except Exception as e:
            self.logger.error(f"Device detection failed: {e}")

    def _is_mod_device(self, port) -> bool:
        """Check if the port is a MOD device"""
        try:
            # Check vendor ID and product ID for MOD devices
            if hasattr(port, "vid") and hasattr(port, "pid"):
                # MOD Devices vendor/product IDs (these would be the actual values)
                mod_devices = [
                    (0x0525, 0xA4A2),  # Example MOD Duo
                    (0x0525, 0xA4A3),  # Example MOD Duo X
                ]

                for vid, pid in mod_devices:
                    if port.vid == vid and port.pid == pid:
                        return True

            # Alternative: Check device description
            if hasattr(port, "description"):
                mod_descriptions = ["MOD", "Audio Injector"]
                for desc in mod_descriptions:
                    if desc.lower() in port.description.lower():
                        return True

        except Exception as e:
            self.logger.debug(f"Error checking device {port.device}: {e}")

        return False

    def _detect_device_type(self, port) -> str:
        """Detect specific MOD device type"""
        try:
            if hasattr(port, "pid"):
                if port.pid == 0xA4A2:
                    return "MOD Duo"
                elif port.pid == 0xA4A3:
                    return "MOD Duo X"

            # Fallback to generic
            return "MOD Device"

        except Exception:
            return "Unknown MOD Device"

    async def _initialize_hmi(self):
        """Initialize HMI communication"""
        try:
            if not self.hardware_state.serial_port:
                raise ValueError("No serial port available for HMI")

            self.logger.info("Initializing HMI communication...")

            # Initialize HMI with callback
            self.hmi = HMI(
                host_callback=self._hmi_callback, msg_callback=self._msg_callback
            )

            # Start HMI in executor for backward compatibility
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.hmi.start)

            # Get HMI version
            self.hardware_state.hmi_version = await self._get_hmi_version()

            self.logger.info(
                f"HMI initialized, version: {self.hardware_state.hmi_version}"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize HMI: {e}")
            raise

    async def _initialize_control_chain(self):
        """Initialize Control Chain communication"""
        try:
            self.logger.info("Initializing Control Chain...")

            # Initialize ControlChainDeviceListener with callbacks
            self.control_chain = ControlChainDeviceListener(
                hw_added_cb=self._hw_added_callback,
                hw_removed_cb=self._hw_removed_callback,
                hw_connected_cb=self._hw_connected_callback,
                hw_disconnected_cb=self._hw_disconnected_callback,
                act_added_cb=self._act_added_callback,
            )

            # Scan for Control Chain devices
            await self._scan_control_chain_devices()

            self.logger.info("Control Chain initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize Control Chain: {e}")
            # Control Chain is optional, don't raise

    async def _get_hmi_version(self) -> Optional[str]:
        """Get HMI version from device"""
        try:
            if self.hmi:
                # Request version info from HMI
                loop = asyncio.get_event_loop()
                version_info = await loop.run_in_executor(
                    None, lambda: getattr(self.hmi, "get_version", lambda: None)()
                )
                return version_info
        except Exception as e:
            self.logger.error(f"Failed to get HMI version: {e}")

        return None

    async def setup_event_bus(self):
        """Set up Redis event bus connection."""
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_url = f"redis://{redis_host}:{redis_port}"

        self.event_bus = RedisEventBus(redis_url=redis_url)
        await self.event_bus.initialize()
        self.logger.info(f"Connected to Redis event bus at {redis_url}")

    async def cleanup_event_bus(self):
        """Clean up event bus connection."""
        if self.event_bus:
            await self.event_bus.close()
            self.logger.info("Disconnected from Redis event bus")

    async def publish_hardware_status(self):
        """Publish current hardware status to event bus."""
        if not self.event_bus:
            return

        event = create_hardware_status_event(
            event_type=EventType.HARDWARE_STATUS_UPDATED,
            source_service="hardware",
            device_connected=self.hardware_state.device_connected,
            device_type=self.hardware_state.device_type,
            serial_port=self.device_path,
            hmi_version=self.hardware_state.hmi_version,
        )
        await self.event_bus.publish(event)

    async def publish_control_chain_event(
        self,
        device_id: str,
        status: ControlChainDeviceStatus,
        device_type: Optional[str] = None,
        name: Optional[str] = None,
    ):
        """Publish Control Chain device event."""
        if not self.event_bus:
            return

        # Use the right event type based on status
        if status == ControlChainDeviceStatus.ADDED:
            event_type = EventType.CONTROL_CHAIN_DEVICE_ADDED
        elif status == ControlChainDeviceStatus.REMOVED:
            event_type = EventType.CONTROL_CHAIN_DEVICE_REMOVED
        elif status == ControlChainDeviceStatus.CONNECTED:
            event_type = EventType.CONTROL_CHAIN_DEVICE_CONNECTED
        elif status == ControlChainDeviceStatus.DISCONNECTED:
            event_type = EventType.CONTROL_CHAIN_DEVICE_DISCONNECTED
        else:
            event_type = EventType.CONTROL_CHAIN_DEVICE_ADDED  # fallback

        event = create_control_chain_event(
            event_type=event_type,
            source_service="hardware",
            device_id=device_id,
            status=status,
            device_type=device_type,
            label=name,
        )
        await self.event_bus.publish(event)

    async def publish_hmi_event(
        self, message_type: HMIMessageType, data: Dict[str, Any]
    ):
        """Publish HMI message event."""
        if not self.event_bus:
            return

        # Use appropriate event type based on message type
        if message_type == HMIMessageType.HEARTBEAT:
            event_type = EventType.HMI_MESSAGE_HEARTBEAT
        elif message_type == HMIMessageType.DISCONNECT:
            event_type = EventType.HMI_MESSAGE_DISCONNECT
        elif message_type == HMIMessageType.CONTROL_ADD:
            event_type = EventType.HMI_MESSAGE_CONTROL_ADD
        elif message_type == HMIMessageType.CONTROL_REMOVE:
            event_type = EventType.HMI_MESSAGE_CONTROL_REMOVE
        else:
            event_type = EventType.HMI_MESSAGE_HEARTBEAT  # fallback

        event = create_hmi_event(
            event_type=event_type,
            source_service="hardware",
            message_type=message_type,
            data=data,
        )
        await self.event_bus.publish(event)

    async def _scan_control_chain_devices(self):
        """Scan for connected Control Chain devices"""
        try:
            if not self.control_chain:
                return

            self.logger.info("Scanning for Control Chain devices...")

            # ControlChainDeviceListener handles device discovery automatically
            # Just wait for it to initialize
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self.control_chain.wait_initialized(lambda: None)
            )

            # Devices are reported via callbacks, so check the internal state
            device_count = len(getattr(self.control_chain, "hw_versions", {}))
            self.logger.info(f"Control Chain initialized with {device_count} devices")

        except Exception as e:
            self.logger.error(f"Failed to scan Control Chain devices: {e}")

    def _hmi_callback(self, msg_type: str, data: Any):
        """Handle HMI messages and publish events"""
        self.logger.debug(f"HMI message: {msg_type} - {data}")
        self.hardware_state.last_heartbeat = datetime.now()

        # Process different HMI message types
        if msg_type == "heartbeat":
            self.hardware_state.device_connected = True
            # Publish heartbeat event
            asyncio.create_task(
                self.publish_hmi_event(HMIMessageType.HEARTBEAT, {"status": "alive"})
            )
        elif msg_type == "disconnect":
            self.hardware_state.device_connected = False
            # Publish disconnect event
            asyncio.create_task(
                self.publish_hmi_event(
                    HMIMessageType.DISCONNECT, {"reason": "device_disconnected"}
                )
            )
        elif msg_type == "control_add":
            # Publish control added event
            asyncio.create_task(
                self.publish_hmi_event(HMIMessageType.CONTROL_ADD, data)
            )
        elif msg_type == "control_remove":
            # Publish control removed event
            asyncio.create_task(
                self.publish_hmi_event(HMIMessageType.CONTROL_REMOVE, data)
            )

        # Publish status update
        asyncio.create_task(self.publish_hardware_status())

    def _msg_callback(self, msg: str):
        """Handle general hardware messages"""
        self.logger.debug(f"Hardware message: {msg}")

        # Publish generic message event
        try:
            parsed_msg = json.loads(msg) if msg.startswith("{") else {"message": msg}
            asyncio.create_task(
                self.publish_hmi_event(HMIMessageType.MESSAGE, parsed_msg)
            )
        except Exception as e:
            self.logger.debug(f"Could not parse message as JSON: {e}")
            asyncio.create_task(
                self.publish_hmi_event(HMIMessageType.MESSAGE, {"message": msg})
            )

    def _hw_added_callback(self, dev_id, dev_uri, label, labelsuffix, version):
        """Handle Control Chain hardware added"""
        device_name = f"{label}{labelsuffix}"
        self.logger.info(
            f"Control Chain device added: {device_name} (v{version}) - {dev_uri}"
        )

        # Publish device added event
        asyncio.create_task(
            self.publish_control_chain_event(
                device_id=str(dev_id),
                status=ControlChainDeviceStatus.ADDED,
                device_type=label,
                name=device_name,
            )
        )

    def _hw_removed_callback(self, dev_id, dev_uri, label, version):
        """Handle Control Chain hardware removed"""
        self.logger.info(
            f"Control Chain device removed: {label} (v{version}) - {dev_uri}"
        )

        # Publish device removed event
        asyncio.create_task(
            self.publish_control_chain_event(
                device_id=str(dev_id),
                status=ControlChainDeviceStatus.REMOVED,
                device_type=label,
                name=label,
            )
        )

    def _hw_connected_callback(self, label, version):
        """Handle Control Chain hardware connected"""
        self.logger.info(f"Control Chain device connected: {label} (v{version})")

        # Publish device connected event
        asyncio.create_task(
            self.publish_control_chain_event(
                device_id=label,  # Use label as ID if dev_id not available
                status=ControlChainDeviceStatus.CONNECTED,
                device_type=label,
                name=label,
            )
        )

    def _hw_disconnected_callback(self, label, version):
        """Handle Control Chain hardware disconnected"""
        self.logger.info(f"Control Chain device disconnected: {label} (v{version})")

        # Publish device disconnected event
        asyncio.create_task(
            self.publish_control_chain_event(
                device_id=label,  # Use label as ID if dev_id not available
                status=ControlChainDeviceStatus.DISCONNECTED,
                device_type=label,
                name=label,
            )
        )

    def _act_added_callback(self, dev_id, actuator_id, metadata):
        """Handle Control Chain actuator added"""
        self.logger.debug(
            f"Control Chain actuator added: {metadata['name']} - {metadata['uri']}"
        )

        # Publish actuator added event
        asyncio.create_task(
            self.publish_control_chain_event(
                device_id=str(dev_id),
                status=ControlChainDeviceStatus.ACTUATOR_ADDED,
                device_type="actuator",
                name=metadata.get("name", "Unknown Actuator"),
            )
        )

    async def get_hardware_state(self) -> Dict[str, Any]:
        """Get current hardware state"""
        return {
            "device_connected": self.hardware_state.device_connected,
            "device_type": self.hardware_state.device_type,
            "serial_port": self.hardware_state.serial_port,
            "hmi_version": self.hardware_state.hmi_version,
            "control_chain_devices": self.hardware_state.control_chain_devices,
            "last_heartbeat": self.hardware_state.last_heartbeat.isoformat(),
        }

    async def send_hmi_command(self, command: str, data: Any = None) -> Dict[str, Any]:
        """Send command to HMI"""
        try:
            if not self.hmi or not self.hardware_state.device_connected:
                raise ValueError("HMI not available")

            self.logger.debug(f"Sending HMI command: {command} - {data}")

            # Send command via HMI
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: getattr(self.hmi, "send_command", lambda c, d: None)(
                    command, data
                ),
            )

            return {"success": True, "result": result}

        except Exception as e:
            self.logger.error(f"Failed to send HMI command: {e}")
            return {"success": False, "error": str(e)}

    async def get_system_info(self) -> Dict[str, Any]:
        """Get hardware system information"""
        try:
            system_info = {
                "hardware_state": await self.get_hardware_state(),
                "serial_ports": [],
                "system_resources": await self._get_system_resources(),
            }

            # Add available serial ports
            ports = serial.tools.list_ports.comports()
            port_list = []
            for port in ports:
                port_list.append(
                    {
                        "device": port.device,
                        "description": port.description,
                        "hwid": port.hwid,
                    }
                )
            system_info["serial_ports"] = port_list

            return system_info

        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {"error": str(e)}

    async def _get_system_resources(self) -> Dict[str, Any]:
        """Get system resource information"""
        try:
            # Basic system info without psutil for now
            return {
                "cpu_percent": 0.0,  # Would need psutil or read /proc/stat
                "memory": {
                    "total": 0,
                    "available": 0,
                    "percent": 0.0,
                },
                "disk": {
                    "total": 0,
                    "free": 0,
                    "percent": 0.0,
                },
            }
        except Exception as e:
            self.logger.error(f"Failed to get system resources: {e}")
            return {}

    async def shutdown(self):
        """Shutdown the hardware service"""
        self.logger.info("Shutting down hardware service...")
        self.running = False

        try:
            if self.control_chain:
                # ControlChainDeviceListener doesn't have explicit stop method
                self.control_chain.crashed = True
                self.control_chain = None
            if self.hmi:
                await asyncio.get_event_loop().run_in_executor(None, self.hmi.stop)
            if self.serial_port:
                self.serial_port.close()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

        self.logger.info("Hardware service shutdown complete")

    async def start_monitoring(self):
        """Start the hardware service monitoring."""
        self.running = True
        self.logger.info("Hardware service monitoring started")

        # Publish initial status
        await self.publish_hardware_status()


# Global service instance
hardware_service: Optional[HardwareService] = None


async def hardware_monitoring_loop():
    """Background monitoring loop for hardware service."""
    global hardware_service

    if not hardware_service:
        return

    logger = logging.getLogger(__name__)
    logger.info("Starting hardware monitoring loop...")

    try:
        while hardware_service.running:
            # Monitor hardware state
            if hardware_service.hardware_state.device_connected:
                # Check heartbeat timeout
                heartbeat_age = (
                    datetime.now() - hardware_service.hardware_state.last_heartbeat
                ).total_seconds()
                if heartbeat_age > 30:  # 30 second timeout
                    logger.warning(
                        "Hardware heartbeat timeout, marking as disconnected"
                    )
                    hardware_service.hardware_state.device_connected = False
                    await hardware_service.publish_hardware_status()

            # Periodically rescan for devices if not connected
            if not hardware_service.hardware_state.device_connected:
                await hardware_service._detect_devices()
                if hardware_service.hardware_state.device_connected:
                    await hardware_service._initialize_hmi()
                    await hardware_service._initialize_control_chain()
                    await hardware_service.publish_hardware_status()

            await asyncio.sleep(5)  # Check every 5 seconds

    except asyncio.CancelledError:
        logger.info("Hardware monitoring loop cancelled")
    except Exception as e:
        logger.error(f"Hardware monitoring loop error: {e}")
    finally:
        logger.info("Hardware monitoring loop stopped")


# FastAPI application for standalone hardware service
app = FastAPI(
    title="MOD Hardware Service",
    description="Standalone hardware communication service for MOD devices",
    version="2.0.0",
)


@app.on_event("startup")
async def startup_event():
    """Initialize hardware service on startup."""
    global hardware_service

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting MOD Hardware Service...")

    # Create and initialize hardware service
    hardware_service = HardwareService()

    try:
        # Setup event bus connection
        await hardware_service.setup_event_bus()

        # Initialize hardware
        await hardware_service.initialize()

        # Start monitoring
        await hardware_service.start_monitoring()

        # Start background monitoring task (but don't await it)
        asyncio.create_task(hardware_monitoring_loop())

        logger.info("Hardware service started successfully")

    except Exception as e:
        logger.error(f"Failed to start hardware service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global hardware_service

    logger = logging.getLogger(__name__)
    logger.info("Shutting down hardware service...")

    if hardware_service:
        await hardware_service.shutdown()
        await hardware_service.cleanup_event_bus()

    logger.info("Hardware service shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not hardware_service:
        return {"status": "error", "message": "Service not initialized"}

    return {
        "status": "healthy",
        "device_connected": hardware_service.hardware_state.device_connected,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/hardware/status")
async def get_hardware_status():
    """Get current hardware status."""
    if not hardware_service:
        return {"error": "Service not initialized"}

    return await hardware_service.get_hardware_state()


@app.post("/hardware/hmi/command")
async def send_hmi_command(command: str, data: Optional[Dict[str, Any]] = None):
    """Send HMI command to device."""
    if not hardware_service:
        return {"error": "Service not initialized"}

    return await hardware_service.send_hmi_command(command, data)


async def standalone_main():
    """Main entry point for standalone execution."""

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger = logging.getLogger(__name__)
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start FastAPI server
    config = uvicorn.Config(
        app,
        host=os.getenv("HARDWARE_SERVICE_HOST", "0.0.0.0"),
        port=int(os.getenv("HARDWARE_SERVICE_PORT", "8002")),
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(standalone_main())
