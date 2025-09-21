"""
FastAPI Session Service - Manages MOD device session state and coordination

This service replaces the session management functionality from the original
Tornado-based mod/session.py, providing async session coordination between
the various MOD UI components.
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from mod.session import Session as LegacySession
from mod.host import Host
from mod.hmi import HMI


@dataclass
class SessionState:
    """Current session state"""
    host_connected: bool = False
    hmi_connected: bool = False
    websocket_clients: int = 0
    current_pedalboard: Optional[str] = None
    last_activity: datetime = field(default_factory=datetime.now)
    system_stats: Dict[str, Any] = field(default_factory=dict)


class SessionService:
    """
    Modern async session service managing MOD UI state coordination
    
    This service acts as the central coordinator between:
    - Host (JACK audio engine)
    - HMI (hardware interface)
    - WebSocket clients
    - API services
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session_state = SessionState()
        self.legacy_session: Optional[LegacySession] = None
        self.host: Optional[Host] = None
        self.hmi: Optional[HMI] = None
        self.running = False
        
    async def initialize(self):
        """Initialize the session service and legacy components"""
        try:
            self.logger.info("Initializing session service...")
            
            # Initialize legacy session for backward compatibility
            self.legacy_session = LegacySession()
            
            # Initialize host connection
            self.host = Host(hmi_callback=self._hmi_callback,
                           msg_callback=self._msg_callback)
            
            # Initialize HMI
            self.hmi = HMI(host_callback=self._host_callback,
                          msg_callback=self._msg_callback)
            
            # Start host and HMI
            await self._start_host()
            await self._start_hmi()
            
            self.logger.info("Session service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize session service: {e}")
            raise
    
    async def _start_host(self):
        """Start the host connection"""
        try:
            self.logger.info("Starting host connection...")
            if self.host:
                # Start host in a separate thread for backward compatibility
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.host.start)
                self.session_state.host_connected = True
                self.logger.info("Host connection established")
        except Exception as e:
            self.logger.error(f"Failed to start host: {e}")
            self.session_state.host_connected = False
    
    async def _start_hmi(self):
        """Start the HMI connection"""
        try:
            self.logger.info("Starting HMI connection...")
            if self.hmi:
                # Start HMI in a separate thread for backward compatibility
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.hmi.start)
                self.session_state.hmi_connected = True
                self.logger.info("HMI connection established")
        except Exception as e:
            self.logger.error(f"Failed to start HMI: {e}")
            self.session_state.hmi_connected = False
    
    def _hmi_callback(self, msg_type: str, data: Any):
        """Handle HMI messages"""
        self.logger.debug(f"HMI message: {msg_type} - {data}")
        self.session_state.last_activity = datetime.now()
        
        # Process HMI messages and update state
        if msg_type == "hw_connected":
            self.session_state.hmi_connected = True
        elif msg_type == "hw_disconnected":
            self.session_state.hmi_connected = False
    
    def _host_callback(self, msg_type: str, data: Any):
        """Handle host messages"""
        self.logger.debug(f"Host message: {msg_type} - {data}")
        self.session_state.last_activity = datetime.now()
        
        # Process host messages and update state
        if msg_type == "host_connected":
            self.session_state.host_connected = True
        elif msg_type == "host_disconnected":
            self.session_state.host_connected = False
        elif msg_type == "pedalboard_changed":
            self.session_state.current_pedalboard = data.get("bundle_path")
    
    def _msg_callback(self, msg: str):
        """Handle general messages"""
        self.logger.debug(f"Session message: {msg}")
        self.session_state.last_activity = datetime.now()
    
    async def get_session_state(self) -> Dict[str, Any]:
        """Get current session state"""
        return {
            "host_connected": self.session_state.host_connected,
            "hmi_connected": self.session_state.hmi_connected,
            "websocket_clients": self.session_state.websocket_clients,
            "current_pedalboard": self.session_state.current_pedalboard,
            "last_activity": self.session_state.last_activity.isoformat(),
            "system_stats": self.session_state.system_stats
        }
    
    async def update_websocket_clients(self, count: int):
        """Update WebSocket client count"""
        self.session_state.websocket_clients = count
        self.logger.debug(f"WebSocket clients updated: {count}")
    
    async def broadcast_message(self, msg_type: str, data: Any):
        """Broadcast message to all connected clients"""
        message = {
            "type": msg_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.debug(f"Broadcasting message: {message}")
        # TODO: Implement actual broadcasting to WebSocket clients
    
    async def shutdown(self):
        """Shutdown the session service"""
        self.logger.info("Shutting down session service...")
        self.running = False
        
        try:
            if self.hmi:
                await asyncio.get_event_loop().run_in_executor(None, self.hmi.stop)
            if self.host:
                await asyncio.get_event_loop().run_in_executor(None, self.host.stop)
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        
        self.logger.info("Session service shutdown complete")
    
    async def run(self):
        """Main service loop"""
        self.running = True
        self.logger.info("Session service running...")
        
        try:
            while self.running:
                # Update system stats periodically
                self.session_state.system_stats = await self._collect_system_stats()
                await asyncio.sleep(10)  # Update every 10 seconds
                
        except asyncio.CancelledError:
            self.logger.info("Session service cancelled")
        except Exception as e:
            self.logger.error(f"Session service error: {e}")
        finally:
            await self.shutdown()
    
    async def _collect_system_stats(self) -> Dict[str, Any]:
        """Collect system statistics"""
        import psutil
        
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to collect system stats: {e}")
            return {}


async def main():
    """Main entry point for the session service"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Create and initialize session service
    session_service = SessionService()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        session_service.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await session_service.initialize()
        await session_service.run()
    except Exception as e:
        logger.error(f"Session service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())