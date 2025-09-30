"""
MOD UI - Audio Processing Service - ModHost Bridge

Manages the mod-host process and provides an interface for plugin operations.
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Localized pylint - monitor loops and restart handling intentionally use broad excepts
# pylint: disable=broad-except,unused-variable


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
        # Supervision / restart bookkeeping
        self.restart_count = 0
        self.last_error = None
        self._start_time = None
        self._monitor_task = None
        # Restart policy (configurable via env)
        # If max_restarts is 0, treat as unlimited restarts (keep trying until available)
        self.max_restarts = int(os.getenv("MODHOST_MAX_RESTARTS", "0"))
        self.backoff_base = float(os.getenv("MODHOST_RESTART_BACKOFF_BASE", "0.5"))

    async def start(self) -> bool:
        """Start mod-host process"""
        async with self._lock:
            if self._connected:
                return True

            if self.simulate:
                logger.info("Starting mod-host in simulation mode")
                await asyncio.sleep(0.1)  # Simulate startup time
                self._connected = True
                self._start_time = datetime.now()
                # No monitor task for simulation mode
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
                        self._start_time = datetime.now()
                        logger.info(
                            "mod-host started successfully on port %s", self.port
                        )
                        # Start monitor task to supervise the process
                        if self._monitor_task is None or self._monitor_task.done():
                            self._monitor_task = asyncio.create_task(
                                self._monitor_process()
                            )
                        # reset last_error on successful start
                        self.last_error = None
                        return True

                logger.error("mod-host failed to become ready within timeout")
                await self.stop()
                return False

            except Exception as e:
                logger.error("Error starting mod-host: %s", e)
                self.last_error = str(e)
                return False

    async def stop(self):
        """Stop mod-host process"""
        async with self._lock:
            self._connected = False

            if self.simulate:
                logger.info("Stopping mod-host simulation")
                return
            # Cancel monitor task if running
            if self._monitor_task:
                try:
                    self._monitor_task.cancel()
                    # allow it to cancel gracefully
                    await asyncio.sleep(0)
                except Exception:
                    pass
                self._monitor_task = None

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
                    self.last_error = str(e)

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

    async def wait_until_ready(self, timeout: Optional[float] = None) -> bool:
        """Wait until mod-host is connected.

        This method does NOT call `start()` for you; call `start()` first to trigger
        the process startup. This only waits for `self._connected` to become True.

        Args:
            timeout: number of seconds to wait, or None to wait indefinitely.

        Returns:
            True if connected, False if the timeout elapsed.
        """

        async def _wait():
            while not self._connected:
                await asyncio.sleep(0.02)

        if timeout is None:
            await _wait()
            return True

        try:
            await asyncio.wait_for(_wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def start_and_wait(self, timeout: Optional[float] = None) -> bool:
        """Start the mod-host and wait until it's ready.

        Convenience wrapper that calls `start()` and then `wait_until_ready()`.
        Returns True if started and became ready within timeout, else False.
        """
        started = await self.start()
        if not started:
            return False
        return await self.wait_until_ready(timeout=timeout)

    async def _monitor_process(self):
        """Background task that monitors the mod-host process and attempts restarts.

        This task is only active for real (non-simulated) mod-host processes.
        It will apply an exponential backoff between restart attempts and respect
        the configured max_restarts.
        """
        try:
            while True:
                await asyncio.sleep(0.5)

                if not self.process:
                    break

                code = self.process.poll()
                if code is None:
                    # still running
                    continue

                # Process exited
                try:
                    stdout, stderr = self.process.communicate(timeout=0.1)
                except Exception:
                    stdout, stderr = ("", "")

                self._connected = False
                self.restart_count += 1
                self.last_error = (
                    f"mod-host exited with code {code}; stderr={stderr}".strip()
                )
                logger.warning(
                    "mod-host exited (code=%s). restart_count=%s",
                    code,
                    self.restart_count,
                )

                if self.max_restarts and self.restart_count > self.max_restarts:
                    logger.error(
                        "Exceeded max restarts (%s); not attempting further restarts",
                        self.max_restarts,
                    )
                    break

                # Exponential backoff
                backoff = min(self.backoff_base * (2 ** (self.restart_count - 1)), 30.0)
                logger.info("Waiting %s seconds before attempting restart", backoff)
                await asyncio.sleep(backoff)

                # Attempt to restart the process using existing start path
                try:
                    await self.start()
                except Exception as e:
                    logger.error("Restart attempt failed: %s", e)
                    self.last_error = str(e)
                    # loop will continue and potentially try again

        except asyncio.CancelledError:
            # Monitor task cancelled during shutdown
            return
        except Exception as e:
            logger.error("Unexpected error in mod-host monitor: %s", e)
            self.last_error = str(e)

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
            raw = await asyncio.wait_for(reader.readline(), timeout=5.0)
            response = raw.decode().strip()

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
            "restart_count": self.restart_count,
            "last_error": self.last_error,
            "uptime": (
                (datetime.now() - self._start_time).total_seconds()
                if self._start_time
                else 0
            ),
        }
