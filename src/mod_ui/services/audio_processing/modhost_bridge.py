"""
MOD UI - Audio Processing Service - ModHost Bridge

Manages the mod-host process and provides an interface for plugin operations.
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

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
        self.feedback_port = int(os.getenv("MOD_HOST_FEEDBACK_PORT", "5556"))
        self.mod_host_path = os.getenv(
            "MOD_HOST_PATH",
            os.path.join(os.path.dirname(__file__), "../mod-host/mod-host"),
        )
        self.sample_rate = int(os.getenv("JACK_SAMPLE_RATE", "48000"))
        self.buffer_size = int(os.getenv("JACK_BUFFER_SIZE", "256"))

        self.process: Optional[subprocess.Popen] = None
        self._connected = False
        self._lock = asyncio.Lock()
        # Feedback port handling
        self._feedback_reader = None
        self._feedback_writer = None
        self._feedback_task = None
        self._feedback_callbacks = {}
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

            # Auto-detect an already-running external mod-host by default.
            # This allows the service to attach to a mod-host started outside
            # of this process (e.g. container or host instance). To force
            # starting the local mod-host binary instead, set
            # MODHOST_FORCE_LOCAL=true in the environment.
            force_local = os.getenv("MODHOST_FORCE_LOCAL", "false").lower() in (
                "1",
                "true",
                "yes",
            )

            if not force_local:
                try:
                    if await self._test_connection():
                        self._connected = True
                        self._start_time = datetime.now()
                        logger.info(
                            "Connected to existing mod-host on port %s", self.port
                        )
                        # Connect to feedback port
                        await self._start_feedback_listener()
                        # No process to monitor when connecting to external host
                        return True
                except Exception:
                    # If the connection attempt fails, continue to try to start
                    # a local mod-host binary (existing behavior).
                    pass

            try:
                if not os.path.exists(self.mod_host_path):
                    logger.error("mod-host binary not found at %s", self.mod_host_path)
                    return False

                # Start mod-host process
                cmd = [
                    self.mod_host_path,
                    "-n",  # no fork
                    "-p",  # socket port
                    str(self.port),
                    "-f",  # feedback port
                    str(self.feedback_port),
                    "-v",  # verbose
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
                        # Connect to feedback port
                        await self._start_feedback_listener()
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

        # Stop feedback listener
        await self._stop_feedback_listener()

    async def _start_feedback_listener(self):
        """Start listening to mod-host feedback port"""
        if self.simulate:
            logger.info(
                "SIMULATED: Started feedback listener on port %s", self.feedback_port
            )
            return

        try:
            self._feedback_reader, self._feedback_writer = (
                await asyncio.open_connection("localhost", self.feedback_port)
            )
            logger.info("Connected to mod-host feedback port %s", self.feedback_port)

            # Start feedback message handler task
            self._feedback_task = asyncio.create_task(self._handle_feedback_messages())

        except Exception as e:
            logger.warning(
                "Failed to connect to feedback port %s: %s", self.feedback_port, e
            )

    async def _stop_feedback_listener(self):
        """Stop feedback listener"""
        if self._feedback_task and not self._feedback_task.done():
            self._feedback_task.cancel()
            try:
                await self._feedback_task
            except asyncio.CancelledError:
                pass

        if self._feedback_writer:
            self._feedback_writer.close()
            try:
                await self._feedback_writer.wait_closed()
            except Exception:
                pass
            self._feedback_writer = None
            self._feedback_reader = None

        logger.info("Feedback listener stopped")

    async def _handle_feedback_messages(self):
        """Handle incoming feedback messages from mod-host"""
        try:
            while self._feedback_reader:
                try:
                    # Read a line from feedback port
                    data = await self._feedback_reader.readline()
                    if not data:
                        break

                    message = data.decode().strip()
                    if message:
                        await self._process_feedback_message(message)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error reading feedback message: %s", e)
                    await asyncio.sleep(0.1)  # Brief pause on error

        except Exception as e:
            logger.error("Feedback handler error: %s", e)
        finally:
            logger.debug("Feedback message handler stopped")

    async def _process_feedback_message(self, message: str):
        """Process a feedback message from mod-host"""
        logger.debug("Feedback: %s", message)

        # Parse feedback message and call appropriate callbacks
        try:
            # Examples of feedback messages:
            # param_output <instance_number> <param_symbol> <value>
            # audio_levels <port_name> <peak> <rms>
            # midi_cc <channel> <cc> <value>
            # midi_program <channel> <program>

            parts = message.split()
            if len(parts) < 2:
                return

            message_type = parts[0]

            # Call registered callbacks for this message type
            callbacks = self._feedback_callbacks.get(message_type, [])
            for callback in callbacks:
                try:
                    await callback(message_type, parts[1:])
                except Exception as e:
                    logger.error("Error in feedback callback: %s", e)

        except Exception as e:
            logger.error("Error processing feedback message '%s': %s", message, e)

    def register_feedback_callback(self, message_type: str, callback):
        """Register a callback for feedback messages of a specific type"""
        if message_type not in self._feedback_callbacks:
            self._feedback_callbacks[message_type] = []
        self._feedback_callbacks[message_type].append(callback)

    def unregister_feedback_callback(self, message_type: str, callback):
        """Unregister a feedback callback"""
        if message_type in self._feedback_callbacks:
            try:
                self._feedback_callbacks[message_type].remove(callback)
            except ValueError:
                pass

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

    # Phase 1 Critical Commands - Essential for plugin lifecycle and performance

    async def activate_plugin(self, instance_number: int) -> bool:
        """Activate a loaded plugin instance"""
        if self.simulate:
            logger.info("SIMULATED: Activating plugin instance %d", instance_number)
            return True

        command = f"activate {instance_number}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Activated plugin instance %d", instance_number)
        else:
            logger.error(
                "Failed to activate plugin instance %d: %s", instance_number, response
            )

        return success

    async def preload_plugin(self, lv2_uri: str) -> bool:
        """Preload plugin to reduce instantiation time"""
        if self.simulate:
            logger.info("SIMULATED: Preloading plugin %s", lv2_uri)
            return True

        command = f"preload {lv2_uri}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Preloaded plugin %s", lv2_uri)
        else:
            logger.error("Failed to preload plugin %s: %s", lv2_uri, response)

        return success

    async def bypass_plugin(self, instance_number: int, bypass: bool = True) -> bool:
        """Bypass/enable a plugin (True=bypassed, False=enabled)"""
        if self.simulate:
            state = "bypassed" if bypass else "enabled"
            logger.info("SIMULATED: Plugin instance %d %s", instance_number, state)
            return True

        bypass_value = 1 if bypass else 0
        command = f"bypass {instance_number} {bypass_value}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            state = "bypassed" if bypass else "enabled"
            logger.info("Plugin instance %d %s", instance_number, state)
        else:
            logger.error(
                "Failed to bypass plugin instance %d: %s", instance_number, response
            )

        return success

    async def disconnect_all_ports(self) -> bool:
        """Disconnect all audio connections"""
        if self.simulate:
            logger.info("SIMULATED: Disconnecting all audio ports")
            return True

        command = "disconnect_all"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Disconnected all audio ports")
        else:
            logger.error("Failed to disconnect all ports: %s", response)

        return success

    async def get_cpu_load(self) -> float:
        """Get current CPU load percentage"""
        if self.simulate:
            import random

            cpu_load = random.uniform(5.0, 25.0)  # Simulate reasonable CPU load
            logger.info("SIMULATED: CPU load: %.1f%%", cpu_load)
            return cpu_load

        command = "cpu_load"
        response = await self._send_command(command)

        if response and response.startswith("resp "):
            try:
                # Response format: "resp <cpu_load_percentage>"
                cpu_load = float(response.split()[1])
                logger.debug("CPU load: %.1f%%", cpu_load)
                return cpu_load
            except (IndexError, ValueError) as e:
                logger.error("Failed to parse CPU load: %s (%s)", response, e)
        else:
            logger.error("Failed to get CPU load: %s", response)

        return 0.0

    async def get_max_cpu_load(self) -> float:
        """Get maximum CPU load since last check"""
        if self.simulate:
            import random

            max_cpu_load = random.uniform(15.0, 45.0)  # Simulate peak CPU load
            logger.info("SIMULATED: Max CPU load: %.1f%%", max_cpu_load)
            return max_cpu_load

        command = "max_cpu_load"
        response = await self._send_command(command)

        if response and response.startswith("resp "):
            try:
                # Response format: "resp <max_cpu_load_percentage>"
                max_cpu_load = float(response.split()[1])
                logger.debug("Max CPU load: %.1f%%", max_cpu_load)
                return max_cpu_load
            except (IndexError, ValueError) as e:
                logger.error("Failed to parse max CPU load: %s (%s)", response, e)
        else:
            logger.error("Failed to get max CPU load: %s", response)

        return 0.0

    # Phase 2 Preset Management - Critical for user experience

    async def load_preset(self, instance_number: int, preset_uri: str) -> bool:
        """Load a preset for a plugin instance"""
        if self.simulate:
            logger.info(
                "SIMULATED: Loading preset %s for instance %d",
                preset_uri,
                instance_number,
            )
            return True

        command = f"preset_load {instance_number} {preset_uri}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Loaded preset %s for instance %d", preset_uri, instance_number)
        else:
            logger.error(
                "Failed to load preset %s for instance %d: %s",
                preset_uri,
                instance_number,
                response,
            )

        return success

    async def save_preset(
        self, instance_number: int, preset_name: str, directory: str, filename: str
    ) -> bool:
        """Save current plugin state as preset"""
        if self.simulate:
            logger.info(
                "SIMULATED: Saving preset %s for instance %d to %s/%s",
                preset_name,
                instance_number,
                directory,
                filename,
            )
            return True

        command = f"preset_save {instance_number} {preset_name} {directory} {filename}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info(
                "Saved preset %s for instance %d to %s/%s",
                preset_name,
                instance_number,
                directory,
                filename,
            )
        else:
            logger.error(
                "Failed to save preset %s for instance %d: %s",
                preset_name,
                instance_number,
                response,
            )

        return success

    async def show_presets(self, instance_number: int) -> list:
        """Show available presets for plugin"""
        if self.simulate:
            # Simulate some preset names
            fake_presets = ["Default", "Rock", "Jazz", "Clean", "Distorted"]
            logger.info(
                "SIMULATED: Available presets for instance %d: %s",
                instance_number,
                fake_presets,
            )
            return fake_presets

        command = f"preset_show {instance_number}"
        response = await self._send_command(command)

        if response and response.startswith("resp "):
            try:
                # Response format: "resp <preset1> <preset2> ..." or "resp" if none
                parts = response.split()[1:]  # Skip "resp"
                presets = parts if parts else []
                logger.debug(
                    "Available presets for instance %d: %s", instance_number, presets
                )
                return presets
            except (IndexError, ValueError) as e:
                logger.error("Failed to parse presets list: %s (%s)", response, e)
        else:
            logger.error(
                "Failed to get presets for instance %d: %s", instance_number, response
            )

        return []

    # Phase 3 Monitoring - Parameter observation and audio monitoring

    async def monitor_parameter(
        self, instance_number: int, param_symbol: str, condition: str, value: float
    ) -> bool:
        """Monitor parameter changes with conditions (>, <, =, etc.)"""
        if self.simulate:
            logger.info(
                "SIMULATED: Monitoring parameter %s.%s %s %f",
                instance_number,
                param_symbol,
                condition,
                value,
            )
            return True

        command = f"param_monitor {instance_number} {param_symbol} {condition} {value}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info(
                "Started monitoring parameter %s.%s %s %f",
                instance_number,
                param_symbol,
                condition,
                value,
            )
        else:
            logger.error(
                "Failed to monitor parameter %s.%s: %s",
                instance_number,
                param_symbol,
                response,
            )

        return success

    async def monitor_output(self, output_port: str, enable: bool = True) -> bool:
        """Monitor audio output levels"""
        if self.simulate:
            state = "enabled" if enable else "disabled"
            logger.info(
                "SIMULATED: Output monitoring %s for port %s", state, output_port
            )
            return True

        enable_val = 1 if enable else 0
        command = f"monitor {output_port} {enable_val}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            state = "enabled" if enable else "disabled"
            logger.info("Output monitoring %s for port %s", state, output_port)
        else:
            logger.error(
                "Failed to set output monitoring for port %s: %s", output_port, response
            )

        return success

    async def get_audio_levels(self) -> Dict[str, float]:
        """Get current audio level meters"""
        if self.simulate:
            import random

            # Simulate some audio levels
            levels = {
                "system:playback_1": random.uniform(-60.0, 0.0),
                "system:playback_2": random.uniform(-60.0, 0.0),
                "system:capture_1": random.uniform(-80.0, -20.0),
                "system:capture_2": random.uniform(-80.0, -20.0),
            }
            logger.info("SIMULATED: Audio levels: %s", levels)
            return levels

        command = "monitor_audio_levels"
        response = await self._send_command(command)

        if response and response.startswith("resp "):
            try:
                # Response format: "resp port1:level1 port2:level2 ..."
                parts = response.split()[1:]  # Skip "resp"
                levels = {}
                for part in parts:
                    if ":" in part:
                        port, level = part.split(":", 1)
                        levels[port] = float(level)
                logger.debug("Audio levels: %s", levels)
                return levels
            except (IndexError, ValueError) as e:
                logger.error("Failed to parse audio levels: %s (%s)", response, e)
        else:
            logger.error("Failed to get audio levels: %s", response)

        return {}

    async def flush_parameters(self) -> bool:
        """Flush all parameter changes"""
        if self.simulate:
            logger.info("SIMULATED: Flushing all parameter changes")
            return True

        command = "params_flush"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Flushed all parameter changes")
        else:
            logger.error("Failed to flush parameters: %s", response)

        return success

    # Phase 4 Patch Management - Advanced property and patch management

    async def set_patch_property(
        self, instance_number: int, property_uri: str, value: str
    ) -> bool:
        """Set plugin property/patch value"""
        if self.simulate:
            logger.info(
                "SIMULATED: Setting patch property %s.%s = %s",
                instance_number,
                property_uri,
                value,
            )
            return True

        command = f"patch_set {instance_number} {property_uri} {value}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info(
                "Set patch property %s.%s = %s", instance_number, property_uri, value
            )
        else:
            logger.error(
                "Failed to set patch property %s.%s: %s",
                instance_number,
                property_uri,
                response,
            )

        return success

    async def get_patch_property(self, instance_number: int, property_uri: str) -> str:
        """Get plugin property/patch value"""
        if self.simulate:
            fake_value = f"simulated_value_for_{property_uri}"
            logger.info(
                "SIMULATED: Getting patch property %s.%s = %s",
                instance_number,
                property_uri,
                fake_value,
            )
            return fake_value

        command = f"patch_get {instance_number} {property_uri}"
        response = await self._send_command(command)

        if response and response.startswith("resp "):
            try:
                # Response format: "resp <property_value>"
                value = response.split(" ", 1)[1]  # Split only on first space
                logger.debug(
                    "Got patch property %s.%s = %s",
                    instance_number,
                    property_uri,
                    value,
                )
                return value
            except (IndexError, ValueError) as e:
                logger.error(
                    "Failed to parse patch property value: %s (%s)", response, e
                )
        else:
            logger.error(
                "Failed to get patch property %s.%s: %s",
                instance_number,
                property_uri,
                response,
            )

        return ""

    # Phase 5 Bundle Management - Plugin bundle management

    async def add_bundle(self, bundle_path: str) -> bool:
        """Add plugin bundle to available plugins"""
        if self.simulate:
            logger.info("SIMULATED: Adding bundle %s", bundle_path)
            return True

        command = f"bundle_add {bundle_path}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Added bundle %s", bundle_path)
        else:
            logger.error("Failed to add bundle %s: %s", bundle_path, response)

        return success

    async def remove_bundle(self, bundle_path: str) -> bool:
        """Remove plugin bundle"""
        if self.simulate:
            logger.info("SIMULATED: Removing bundle %s", bundle_path)
            return True

        command = f"bundle_remove {bundle_path}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Removed bundle %s", bundle_path)
        else:
            logger.error("Failed to remove bundle %s: %s", bundle_path, response)

        return success

    # Phase 6 MIDI Control - MIDI learning and mapping

    async def midi_learn_parameter(
        self, instance_number: int, param_symbol: str, min_val: float, max_val: float
    ) -> bool:
        """Enable MIDI learning for parameter"""
        if self.simulate:
            logger.info(
                "SIMULATED: MIDI learning for %s.%s range [%f, %f]",
                instance_number,
                param_symbol,
                min_val,
                max_val,
            )
            return True

        command = f"midi_learn {instance_number} {param_symbol} {min_val} {max_val}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info(
                "MIDI learning enabled for %s.%s range [%f, %f]",
                instance_number,
                param_symbol,
                min_val,
                max_val,
            )
        else:
            logger.error(
                "Failed to enable MIDI learning for %s.%s: %s",
                instance_number,
                param_symbol,
                response,
            )

        return success

    async def midi_map_parameter(
        self,
        instance_number: int,
        param_symbol: str,
        channel: int,
        cc: int,
        min_val: float,
        max_val: float,
    ) -> bool:
        """Map MIDI CC to parameter"""
        if self.simulate:
            logger.info(
                "SIMULATED: MIDI mapping %s.%s to CH%d CC%d range [%f, %f]",
                instance_number,
                param_symbol,
                channel,
                cc,
                min_val,
                max_val,
            )
            return True

        command = f"midi_map {instance_number} {param_symbol} {channel} {cc} {min_val} {max_val}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info(
                "MIDI mapped %s.%s to CH%d CC%d range [%f, %f]",
                instance_number,
                param_symbol,
                channel,
                cc,
                min_val,
                max_val,
            )
        else:
            logger.error(
                "Failed to MIDI map %s.%s: %s", instance_number, param_symbol, response
            )

        return success

    async def midi_unmap_parameter(
        self, instance_number: int, param_symbol: str
    ) -> bool:
        """Remove MIDI mapping from parameter"""
        if self.simulate:
            logger.info(
                "SIMULATED: MIDI unmapping %s.%s", instance_number, param_symbol
            )
            return True

        command = f"midi_unmap {instance_number} {param_symbol}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("MIDI unmapped %s.%s", instance_number, param_symbol)
        else:
            logger.error(
                "Failed to MIDI unmap %s.%s: %s",
                instance_number,
                param_symbol,
                response,
            )

        return success

    # Phase 7 Hardware Control - Control Chain and CV mapping

    async def cc_map_parameter(
        self,
        device_id: int,
        actuator_id: int,
        instance_number: int,
        param_symbol: str,
        min_val: float,
        max_val: float,
    ) -> bool:
        """Map Control Chain actuator to parameter"""
        if self.simulate:
            logger.info(
                "SIMULATED: CC mapping device %d actuator %d to %s.%s range [%f, %f]",
                device_id,
                actuator_id,
                instance_number,
                param_symbol,
                min_val,
                max_val,
            )
            return True

        command = f"cc_map {device_id} {actuator_id} {instance_number} {param_symbol} {min_val} {max_val}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info(
                "CC mapped device %d actuator %d to %s.%s range [%f, %f]",
                device_id,
                actuator_id,
                instance_number,
                param_symbol,
                min_val,
                max_val,
            )
        else:
            logger.error(
                "Failed to CC map device %d actuator %d to %s.%s: %s",
                device_id,
                actuator_id,
                instance_number,
                param_symbol,
                response,
            )

        return success

    async def cc_unmap_parameter(self, device_id: int, actuator_id: int) -> bool:
        """Remove Control Chain mapping"""
        if self.simulate:
            logger.info(
                "SIMULATED: CC unmapping device %d actuator %d", device_id, actuator_id
            )
            return True

        command = f"cc_unmap {device_id} {actuator_id}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("CC unmapped device %d actuator %d", device_id, actuator_id)
        else:
            logger.error(
                "Failed to CC unmap device %d actuator %d: %s",
                device_id,
                actuator_id,
                response,
            )

        return success

    async def cc_value_set(
        self, device_id: int, actuator_id: int, value: float
    ) -> bool:
        """Set Control Chain actuator value"""
        if self.simulate:
            logger.info(
                "SIMULATED: CC setting device %d actuator %d = %f",
                device_id,
                actuator_id,
                value,
            )
            return True

        command = f"cc_value_set {device_id} {actuator_id} {value}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info(
                "CC set device %d actuator %d = %f", device_id, actuator_id, value
            )
        else:
            logger.error(
                "Failed to CC set device %d actuator %d: %s",
                device_id,
                actuator_id,
                response,
            )

        return success

    async def cv_map_parameter(
        self, instance_number: int, param_symbol: str, min_val: float, max_val: float
    ) -> bool:
        """Map CV input to parameter"""
        if self.simulate:
            logger.info(
                "SIMULATED: CV mapping to %s.%s range [%f, %f]",
                instance_number,
                param_symbol,
                min_val,
                max_val,
            )
            return True

        command = f"cv_map {instance_number} {param_symbol} {min_val} {max_val}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info(
                "CV mapped to %s.%s range [%f, %f]",
                instance_number,
                param_symbol,
                min_val,
                max_val,
            )
        else:
            logger.error(
                "Failed to CV map to %s.%s: %s", instance_number, param_symbol, response
            )

        return success

    async def cv_unmap_parameter(self, instance_number: int, param_symbol: str) -> bool:
        """Remove CV mapping from parameter"""
        if self.simulate:
            logger.info("SIMULATED: CV unmapping %s.%s", instance_number, param_symbol)
            return True

        command = f"cv_unmap {instance_number} {param_symbol}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("CV unmapped %s.%s", instance_number, param_symbol)
        else:
            logger.error(
                "Failed to CV unmap %s.%s: %s", instance_number, param_symbol, response
            )

        return success

    # Phase 8 Transport Control - Transport and tempo synchronization

    async def set_bpm(self, bpm: float) -> bool:
        """Set transport BPM"""
        if self.simulate:
            logger.info("SIMULATED: Setting BPM to %f", bpm)
            return True

        command = f"set_bpm {bpm}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Set BPM to %f", bpm)
        else:
            logger.error("Failed to set BPM to %f: %s", bpm, response)

        return success

    async def set_beats_per_bar(self, beats_per_bar: int) -> bool:
        """Set beats per bar"""
        if self.simulate:
            logger.info("SIMULATED: Setting beats per bar to %d", beats_per_bar)
            return True

        command = f"set_bpb {beats_per_bar}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Set beats per bar to %d", beats_per_bar)
        else:
            logger.error(
                "Failed to set beats per bar to %d: %s", beats_per_bar, response
            )

        return success

    async def set_transport(
        self, rolling: bool, beats_per_bar: int, beat_type: int
    ) -> bool:
        """Control transport state"""
        if self.simulate:
            state = "rolling" if rolling else "stopped"
            logger.info(
                "SIMULATED: Setting transport %s, %d/%d time",
                state,
                beats_per_bar,
                beat_type,
            )
            return True

        rolling_val = 1 if rolling else 0
        command = f"transport {rolling_val} {beats_per_bar} {beat_type}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            state = "rolling" if rolling else "stopped"
            logger.info(
                "Transport set to %s, %d/%d time", state, beats_per_bar, beat_type
            )
        else:
            logger.error("Failed to set transport: %s", response)

        return success

    async def transport_sync(self, sync_mode: str) -> bool:
        """Set transport sync mode"""
        if self.simulate:
            logger.info("SIMULATED: Setting transport sync mode to %s", sync_mode)
            return True

        command = f"transport_sync {sync_mode}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Transport sync mode set to %s", sync_mode)
        else:
            logger.error("Failed to set transport sync mode: %s", response)

        return success

    # Feedback Port Monitoring Commands - Using port 5556

    async def monitor_output(
        self, instance_number: int, param_symbol: str, enable: bool = True
    ) -> bool:
        """Monitor an output control port (sends data to feedback port)"""
        if self.simulate:
            action = "enabled" if enable else "disabled"
            logger.info(
                "SIMULATED: Output monitoring %s for %s.%s",
                action,
                instance_number,
                param_symbol,
            )
            return True

        if enable:
            command = f"monitor_output {instance_number} {param_symbol}"
        else:
            command = f"monitor_output_off {instance_number} {param_symbol}"

        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            action = "enabled" if enable else "disabled"
            logger.info(
                "Output monitoring %s for %s.%s", action, instance_number, param_symbol
            )
        else:
            logger.error(
                "Failed to set output monitoring for %s.%s: %s",
                instance_number,
                param_symbol,
                response,
            )

        return success

    async def monitor_audio_levels(self, port_name: str, enable: bool = True) -> bool:
        """Monitor audio levels for a JACK port (sends data to feedback port)"""
        if self.simulate:
            action = "enabled" if enable else "disabled"
            logger.info(
                "SIMULATED: Audio level monitoring %s for %s", action, port_name
            )
            return True

        enable_val = 1 if enable else 0
        command = f"monitor_audio_levels {port_name} {enable_val}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            action = "enabled" if enable else "disabled"
            logger.info("Audio level monitoring %s for %s", action, port_name)
        else:
            logger.error(
                "Failed to set audio level monitoring for %s: %s", port_name, response
            )

        return success

    async def monitor_midi_control(
        self, midi_channel: int, enable: bool = True
    ) -> bool:
        """Monitor MIDI control change messages (sends data to feedback port)"""
        if self.simulate:
            action = "enabled" if enable else "disabled"
            logger.info(
                "SIMULATED: MIDI control monitoring %s for channel %d",
                action,
                midi_channel,
            )
            return True

        enable_val = 1 if enable else 0
        command = f"monitor_midi_control {midi_channel} {enable_val}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            action = "enabled" if enable else "disabled"
            logger.info(
                "MIDI control monitoring %s for channel %d", action, midi_channel
            )
        else:
            logger.error(
                "Failed to set MIDI control monitoring for channel %d: %s",
                midi_channel,
                response,
            )

        return success

    async def monitor_midi_program(
        self, midi_channel: int, enable: bool = True
    ) -> bool:
        """Monitor MIDI program change messages (sends data to feedback port)"""
        if self.simulate:
            action = "enabled" if enable else "disabled"
            logger.info(
                "SIMULATED: MIDI program monitoring %s for channel %d",
                action,
                midi_channel,
            )
            return True

        enable_val = 1 if enable else 0
        command = f"monitor_midi_program {midi_channel} {enable_val}"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            action = "enabled" if enable else "disabled"
            logger.info(
                "MIDI program monitoring %s for channel %d", action, midi_channel
            )
        else:
            logger.error(
                "Failed to set MIDI program monitoring for channel %d: %s",
                midi_channel,
                response,
            )

        return success

    # Session Control Methods
    async def reset_host(self) -> bool:
        """Reset the entire mod-host state, removing all plugins and connections"""
        if self.simulate:
            logger.info("SIMULATED: Resetting mod-host state")
            return True

        # Remove all plugins and connections
        command = "remove -1"
        response = await self._send_command(command)
        success = response == "resp 0" if response else False

        if success:
            logger.info("Successfully reset mod-host state")
        else:
            logger.error("Failed to reset mod-host state: %s", response)

        return success

    async def mute_output(self) -> bool:
        """Mute system audio output by disconnecting monitor outputs"""
        if self.simulate:
            logger.info("SIMULATED: Muting system audio output")
            return True

        success = True
        # Disconnect monitor outputs from system playback
        disconnect_commands = [
            "disconnect mod-monitor:out_1 system:playback_1",
            "disconnect mod-monitor:out_2 system:playback_2",
            "disconnect mod-monitor:out_1 mod-peakmeter:in_3",
            "disconnect mod-monitor:out_2 mod-peakmeter:in_4",
        ]

        for command in disconnect_commands:
            response = await self._send_command(command)
            if response != "resp 0":
                success = False
                logger.warning(
                    "Failed to execute mute command: %s -> %s", command, response
                )

        if success:
            logger.info("Successfully muted system audio output")
        else:
            logger.error("Some mute operations failed")

        return success

    async def unmute_output(self) -> bool:
        """Unmute system audio output by reconnecting monitor outputs"""
        if self.simulate:
            logger.info("SIMULATED: Unmuting system audio output")
            return True

        success = True
        # Reconnect monitor outputs to system playback
        connect_commands = [
            "connect mod-monitor:out_1 system:playback_1",
            "connect mod-monitor:out_2 system:playback_2",
            "connect mod-monitor:out_1 mod-peakmeter:in_3",
            "connect mod-monitor:out_2 mod-peakmeter:in_4",
        ]

        for command in connect_commands:
            response = await self._send_command(command)
            if response != "resp 0":
                success = False
                logger.warning(
                    "Failed to execute unmute command: %s -> %s", command, response
                )

        if success:
            logger.info("Successfully unmuted system audio output")
        else:
            logger.error("Some unmute operations failed")

        return success

    async def get_system_state(self) -> Dict[str, Any]:
        """Get current system state information"""
        if self.simulate:
            return {
                "cpu_load": 12.5,
                "xruns": 0,
                "sample_rate": self.sample_rate,
                "buffer_size": self.buffer_size,
                "connected": True,
                "simulated": True,
            }

        state = {}

        # Get CPU load
        cpu_load = await self.get_cpu_load()
        state["cpu_load"] = cpu_load if cpu_load is not None else 0.0

        # Get basic system info
        state.update(
            {
                "sample_rate": self.sample_rate,
                "buffer_size": self.buffer_size,
                "connected": self._connected,
                "feedback_connected": self._feedback_reader is not None,
                "simulated": False,
            }
        )

        return state

    # JACK Integration Methods
    async def get_jack_ports(self) -> List[str]:
        """Get list of available JACK ports"""
        if self.simulate:
            return [
                "system:capture_1",
                "system:capture_2",
                "system:playback_1",
                "system:playback_2",
                "mod-monitor:in_1",
                "mod-monitor:in_2",
                "mod-monitor:out_1",
                "mod-monitor:out_2",
            ]

        # In a real implementation, this would query JACK
        # For now, return basic system ports
        return []

    async def set_buffer_size(self, buffer_size: int) -> bool:
        """Set JACK buffer size"""
        if self.simulate:
            logger.info("SIMULATED: Setting JACK buffer size to %d", buffer_size)
            self.buffer_size = buffer_size
            return True

        # This would typically be handled by JACK directly
        # mod-host doesn't have a direct command for this
        logger.warning("Buffer size changes must be handled by JACK server")
        return False

    async def handle_port_appeared(
        self, port_name: str, is_output: bool
    ) -> Dict[str, Any]:
        """Handle JACK port appearance event"""
        port_info = {
            "name": port_name,
            "type": "audio",  # Default assumption
            "is_output": is_output,
            "timestamp": datetime.now().isoformat(),
        }

        # Determine port type from name
        if "midi" in port_name.lower():
            port_info["type"] = "midi"
        elif "cv" in port_name.lower():
            port_info["type"] = "cv"

        logger.info(
            "JACK port appeared: %s (%s, %s)",
            port_name,
            port_info["type"],
            "output" if is_output else "input",
        )

        return port_info

    async def handle_port_deleted(self, port_name: str) -> Dict[str, Any]:
        """Handle JACK port deletion event"""
        port_info = {"name": port_name, "timestamp": datetime.now().isoformat()}

        logger.info("JACK port deleted: %s", port_name)
        return port_info

    async def handle_buffer_size_changed(self, new_buffer_size: int) -> Dict[str, Any]:
        """Handle JACK buffer size change event"""
        old_buffer_size = self.buffer_size
        self.buffer_size = new_buffer_size

        buffer_info = {
            "old_buffer_size": old_buffer_size,
            "new_buffer_size": new_buffer_size,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            "JACK buffer size changed: %d -> %d", old_buffer_size, new_buffer_size
        )
        return buffer_info

    def get_status(self) -> Dict[str, Any]:
        """Get mod-host status"""
        return {
            "connected": self._connected,
            "simulate": self.simulate,
            "port": self.port,
            "feedback_port": self.feedback_port,
            "feedback_connected": self._feedback_reader is not None,
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
