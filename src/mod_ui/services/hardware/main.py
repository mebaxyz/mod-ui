"""
FastAPI Hardware Service - Manages MOD device hardware interfaces

This service replaces the hardware-specific functionality from the original
Tornado-based application, providing async hardware communication with
the MOD Duo device via serial and HMI protocols.
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import json
import serial
import serial.tools.list_ports

from mod.hmi import HMI
from mod.control_chain import ControlChain


@dataclass
class HardwareState:
    """Current hardware state"""
    device_connected: bool = False
    device_type: Optional[str] = None
    serial_port: Optional[str] = None
    hmi_version: Optional[str] = None
    control_chain_devices: List[Dict[str, Any]] = field(default_factory=list)
    last_heartbeat: datetime = field(default_factory=datetime.now)


class HardwareService:
    """
    Modern async hardware service managing MOD device communication
    
    This service handles:
    - Serial communication with MOD devices
    - HMI (Human Machine Interface) protocol
    - Control Chain device management
    - Hardware monitoring and diagnostics
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.hardware_state = HardwareState()
        self.hmi: Optional[HMI] = None
        self.control_chain: Optional[ControlChain] = None
        self.serial_connection: Optional[serial.Serial] = None
        self.running = False
        
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
                    self.logger.info(f"Found MOD device: {self.hardware_state.device_type} on {port.device}")
                    break
            
            if not self.hardware_state.device_connected:
                self.logger.warning("No MOD devices detected")
                
        except Exception as e:
            self.logger.error(f"Device detection failed: {e}")
    
    def _is_mod_device(self, port) -> bool:
        """Check if the port is a MOD device"""
        try:
            # Check vendor ID and product ID for MOD devices
            if hasattr(port, 'vid') and hasattr(port, 'pid'):
                # MOD Devices vendor/product IDs (these would be the actual values)
                mod_devices = [
                    (0x0525, 0xa4a2),  # Example MOD Duo
                    (0x0525, 0xa4a3),  # Example MOD Duo X
                ]
                
                for vid, pid in mod_devices:
                    if port.vid == vid and port.pid == pid:
                        return True
            
            # Alternative: Check device description
            if hasattr(port, 'description'):
                mod_descriptions = ['MOD', 'Audio Injector']
                for desc in mod_descriptions:
                    if desc.lower() in port.description.lower():
                        return True
                        
        except Exception as e:
            self.logger.debug(f"Error checking device {port.device}: {e}")
        
        return False
    
    def _detect_device_type(self, port) -> str:
        """Detect specific MOD device type"""
        try:
            if hasattr(port, 'pid'):
                if port.pid == 0xa4a2:
                    return "MOD Duo"
                elif port.pid == 0xa4a3:
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
                host_callback=self._hmi_callback,
                msg_callback=self._msg_callback
            )
            
            # Start HMI in executor for backward compatibility
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.hmi.start)
            
            # Get HMI version
            self.hardware_state.hmi_version = await self._get_hmi_version()
            
            self.logger.info(f"HMI initialized, version: {self.hardware_state.hmi_version}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize HMI: {e}")
            raise
    
    async def _initialize_control_chain(self):
        """Initialize Control Chain communication"""
        try:
            self.logger.info("Initializing Control Chain...")
            
            self.control_chain = ControlChain()
            
            # Start Control Chain
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.control_chain.start)
            
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
                    None, 
                    lambda: getattr(self.hmi, 'get_version', lambda: None)()
                )
                return version_info
        except Exception as e:
            self.logger.error(f"Failed to get HMI version: {e}")
        
        return None
    
    async def _scan_control_chain_devices(self):
        """Scan for connected Control Chain devices"""
        try:
            if not self.control_chain:
                return
            
            self.logger.info("Scanning for Control Chain devices...")
            
            # Get list of Control Chain devices
            loop = asyncio.get_event_loop()
            devices = await loop.run_in_executor(
                None,
                lambda: getattr(self.control_chain, 'get_devices', lambda: [])()
            )
            
            self.hardware_state.control_chain_devices = devices
            self.logger.info(f"Found {len(devices)} Control Chain devices")
            
        except Exception as e:
            self.logger.error(f"Failed to scan Control Chain devices: {e}")
    
    def _hmi_callback(self, msg_type: str, data: Any):
        """Handle HMI messages"""
        self.logger.debug(f"HMI message: {msg_type} - {data}")
        self.hardware_state.last_heartbeat = datetime.now()
        
        # Process different HMI message types
        if msg_type == "heartbeat":
            self.hardware_state.device_connected = True
        elif msg_type == "disconnect":
            self.hardware_state.device_connected = False
        
        # TODO: Broadcast to session service or API clients
    
    def _msg_callback(self, msg: str):
        """Handle general hardware messages"""
        self.logger.debug(f"Hardware message: {msg}")
    
    async def get_hardware_state(self) -> Dict[str, Any]:
        """Get current hardware state"""
        return {
            "device_connected": self.hardware_state.device_connected,
            "device_type": self.hardware_state.device_type,
            "serial_port": self.hardware_state.serial_port,
            "hmi_version": self.hardware_state.hmi_version,
            "control_chain_devices": self.hardware_state.control_chain_devices,
            "last_heartbeat": self.hardware_state.last_heartbeat.isoformat()
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
                lambda: getattr(self.hmi, 'send_command', lambda c, d: None)(command, data)
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
                "system_resources": await self._get_system_resources()
            }
            
            # Add available serial ports
            ports = serial.tools.list_ports.comports()
            for port in ports:
                system_info["serial_ports"].append({
                    "device": port.device,
                    "description": port.description,
                    "hwid": port.hwid
                })
            
            return system_info
            
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {"error": str(e)}
    
    async def _get_system_resources(self) -> Dict[str, Any]:
        """Get system resource information"""
        try:
            import psutil
            
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent
                },
                "disk": {
                    "total": psutil.disk_usage('/').total,
                    "free": psutil.disk_usage('/').free,
                    "percent": psutil.disk_usage('/').percent
                }
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
                await asyncio.get_event_loop().run_in_executor(None, self.control_chain.stop)
            if self.hmi:
                await asyncio.get_event_loop().run_in_executor(None, self.hmi.stop)
            if self.serial_connection:
                self.serial_connection.close()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        
        self.logger.info("Hardware service shutdown complete")
    
    async def run(self):
        """Main service loop"""
        self.running = True
        self.logger.info("Hardware service running...")
        
        try:
            while self.running:
                # Monitor hardware state
                if self.hardware_state.device_connected:
                    # Check heartbeat timeout
                    heartbeat_age = (datetime.now() - self.hardware_state.last_heartbeat).total_seconds()
                    if heartbeat_age > 30:  # 30 second timeout
                        self.logger.warning("Hardware heartbeat timeout, marking as disconnected")
                        self.hardware_state.device_connected = False
                
                # Periodically rescan for devices if not connected
                if not self.hardware_state.device_connected:
                    await self._detect_devices()
                    if self.hardware_state.device_connected:
                        await self._initialize_hmi()
                        await self._initialize_control_chain()
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
        except asyncio.CancelledError:
            self.logger.info("Hardware service cancelled")
        except Exception as e:
            self.logger.error(f"Hardware service error: {e}")
        finally:
            await self.shutdown()


async def main():
    """Main entry point for the hardware service"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Create and initialize hardware service
    hardware_service = HardwareService()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        hardware_service.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await hardware_service.initialize()
        await hardware_service.run()
    except Exception as e:
        logger.error(f"Hardware service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())