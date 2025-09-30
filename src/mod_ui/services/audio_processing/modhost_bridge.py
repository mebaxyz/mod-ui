"""
MOD UI - Audio Processing Service - ModHost Bridge

Manages the mod-host process and provides an interface for plugin operations.
"""

import asyncio
import logging
import os
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ModHostBridge:
    """Bridge to communicate with mod-host process"""

    def __init__(self, simulate: bool = None):
        self.simulate = (
            simulate
            if simulate is not None
            else os.getenv("SIMULATE_MODHOST", "false").lower() == "true"
        )
        self.port = int(os.getenv("MOD_HOST_PORT", "5555"))
        self.mod_host_path = os.getenv(
            "MOD_HOST_PATH",
            os.path.join(os.path.dirname(__file__), "../mod-host/mod-host"),
        )
        self.sample_rate = int(os.getenv("JACK_SAMPLE_RATE", "48000"))
        self.buffer_size = int(os.getenv("JACK_BUFFER_SIZE", "256"))

        self.process: Optional[subprocess.Popen] = None
        self._connected = False
        self._lock = asyncio.Lock()

    async def start(self) -> bool:
        """Start mod-host process"""
        async with self._lock:
            if self._connected:
                return True

            if self.simulate:
                logger.info("Starting mod-host in simulation mode")
                await asyncio.sleep(0.1)  # Simulate startup time
                self._connected = True
                return True

            try:
                if not os.path.exists(self.mod_host_path):
                    logger.error("mod-host binary not found at %s", self.mod_host_path)
                    return False

                # Start mod-host process
                cmd = [
                    self.mod_host_path,
                    "-p",
                    str(self.port),
                    "-f",
                    str(self.sample_rate),
                    "-b",
                    str(self.buffer_size),
                ]

                logger.info("Starting mod-host: %s", " ".join(cmd))

                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )

                # Wait for mod-host to be ready
                for attempt in range(30):  # 3 seconds timeout
                    await asyncio.sleep(0.1)
                    if self.process.poll() is not None:
                        # Process died
                        stdout, stderr = self.process.communicate()
                        logger.error(
                            "mod-host process died: stdout=%s, stderr=%s",
                            stdout,
                            stderr,
                        )
                        return False

                    # Test connection
                    if await self._test_connection():
                        self._connected = True
                        logger.info(
                            "mod-host started successfully on port %s", self.port
                        )
                        return True

                logger.error("mod-host failed to become ready within timeout")
                await self.stop()
                return False

            except Exception as e:
                logger.error("Error starting mod-host: %s", e)
                return False

    async def stop(self):
        """Stop mod-host process"""
        async with self._lock:
            self._connected = False

            if self.simulate:
                logger.info("Stopping mod-host simulation")
                return

            if self.process:
                try:
                    self.process.terminate()
                    # Wait for graceful shutdown
                    for _ in range(10):  # 1 second timeout
                        if self.process.poll() is not None:
                            break
                        await asyncio.sleep(0.1)

                    # Force kill if still running
                    if self.process.poll() is None:
                        self.process.kill()
                        await asyncio.sleep(0.1)

                    self.process = None
                    logger.info("mod-host stopped")

                except Exception as e:
                    logger.error("Error stopping mod-host: %s", e)

    def is_connected(self) -> bool:
        """Check if mod-host is connected"""
        return self._connected

    async def ping(self) -> bool:
        """Ping mod-host to check if it's responsive"""
        if self.simulate:
            return self._connected

        if not self._connected:
            return False

        try:
            response = await self._send_command("help")
            return response is not None
        except Exception:
            return False

    async def _test_connection(self) -> bool:
        """Test if we can connect to mod-host"""
        if self.simulate:
            return True

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("localhost", self.port), timeout=1.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _send_command(self, command: str) -> Optional[str]:
        """Send command to mod-host and get response"""
        if self.simulate:
            # Simulate command responses
            await asyncio.sleep(0.01)  # Simulate network delay
            if command.startswith("add "):
                return "resp 0"
            elif command.startswith("remove "):
                return "resp 0"
            elif command.startswith("param_set "):
                return "resp 0"
            elif command.startswith("param_get "):
                return "resp 0.5"  # Simulate parameter value
            elif command.startswith("connect "):
                return "resp 0"
            elif command.startswith("disconnect "):
                return "resp 0"
            elif command == "help":
                return "resp help available"
            else:
                return "resp 0"

        if not self._connected:
            raise RuntimeError("mod-host not connected")

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("localhost", self.port), timeout=5.0
            )

            # Send command
            writer.write(f"{command}\n".encode())
            await writer.drain()

            # Read response
            response = await asyncio.wait_for(reader.readline(), timeout=5.0)
            response = response.decode().strip()

            writer.close()
            await writer.wait_closed()

            return response

        except Exception as e:
            logger.error("Error sending command to mod-host: %s", e)
            return None

    async def add_plugin(self, plugin_uri: str, instance_id: str) -> bool:
        """Add plugin to mod-host"""
        command = f"add {plugin_uri} {instance_id}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Added plugin %s as %s", plugin_uri, instance_id)
        else:
            logger.error("Failed to add plugin %s: %s", plugin_uri, response)

        return success

    async def remove_plugin(self, instance_id: str) -> bool:
        """Remove plugin from mod-host"""
        command = f"remove {instance_id}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Removed plugin %s", instance_id)
        else:
            logger.error("Failed to remove plugin %s: %s", instance_id, response)

        return success

    async def set_parameter(
        self, instance_id: str, parameter: str, value: float
    ) -> bool:
        """Set plugin parameter"""
        command = f"param_set {instance_id} {parameter} {value}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.debug("Set parameter %s.%s = %s", instance_id, parameter, value)
        else:
            logger.error(
                "Failed to set parameter %s.%s: %s", instance_id, parameter, response
            )

        return success

    async def get_parameter(self, instance_id: str, parameter: str) -> Optional[float]:
        """Get plugin parameter value"""
        command = f"param_get {instance_id} {parameter}"
        response = await self._send_command(command)

        if response and response.startswith("resp "):
            try:
                value = float(response.split()[1])
                logger.debug("Got parameter %s.%s = %s", instance_id, parameter, value)
                return value
            except (IndexError, ValueError) as e:
                logger.error("Failed to parse parameter value: %s (%s)", response, e)
        else:
            logger.error(
                "Failed to get parameter %s.%s: %s", instance_id, parameter, response
            )

        return None

    async def connect_ports(self, source: str, target: str) -> bool:
        """Connect audio ports"""
        command = f"connect {source} {target}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Connected %s -> %s", source, target)
        else:
            logger.error("Failed to connect %s -> %s: %s", source, target, response)

        return success

    async def disconnect_ports(self, source: str, target: str) -> bool:
        """Disconnect audio ports"""
        command = f"disconnect {source} {target}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Disconnected %s -> %s", source, target)
        else:
            logger.error("Failed to disconnect %s -> %s: %s", source, target, response)

        return success

    def get_status(self) -> Dict[str, Any]:
        """Get mod-host status"""
        return {
            "connected": self._connected,
            "simulate": self.simulate,
            "port": self.port,
            "sample_rate": self.sample_rate,
            "buffer_size": self.buffer_size,
            "process_running": (
                self.process is not None and self.process.poll() is None
                if self.process
                else False
            ),
        }
