"""
System Statistics Service for Session System

Collects system statistics (CPU load, memory usage, etc.)
and publishes them to the event bus for distribution.
"""

import asyncio
import logging
import os
from typing import Optional

from ..models.events import EventType, create_system_stats_event
from ..utils.event_bus import EventBus


class SystemStatsService:
    """
    Service for collecting and publishing system statistics

    This service collects system stats and publishes them to the event bus.
    The WebSocket Gateway Service will receive these events and broadcast
    them to connected clients in the appropriate format.
    """

    def __init__(self, event_bus: EventBus, broadcast_interval: float = 1.0):
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus
        self.broadcast_interval = broadcast_interval
        self.running = False
        self.stats_task: Optional[asyncio.Task] = None
        self.sys_stats_task: Optional[asyncio.Task] = None

        # Stats counters
        self.data_ready_counter = 0
        self.cpu_load = 0.0
        self.xruns = 0
        self.mem_usage = 0.0

        # CPU frequency and temperature files (MOD device specific)
        self.cpu_freq_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
        self.cpu_temp_file = "/sys/class/thermal/thermal_zone0/temp"

        self.logger.info("SystemStatsService initialized")

    async def initialize(self) -> None:
        """Initialize the system stats service"""
        try:
            self.logger.info("System Stats Service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize System Stats Service: {e}")
            raise

    async def start(self) -> None:
        """Start the periodic stats broadcasting"""
        if self.running:
            return

        self.running = True
        self.logger.info("Starting system stats broadcasting")

        # Start stats broadcasting tasks
        self.stats_task = asyncio.create_task(self._stats_broadcast_loop())
        self.sys_stats_task = asyncio.create_task(self._sys_stats_broadcast_loop())

    async def stop(self) -> None:
        """Stop the stats broadcasting"""
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping system stats broadcasting")

        # Cancel tasks
        if self.stats_task:
            self.stats_task.cancel()
            try:
                await self.stats_task
            except asyncio.CancelledError:
                pass
            self.stats_task = None

        if self.sys_stats_task:
            self.sys_stats_task.cancel()
            try:
                await self.sys_stats_task
            except asyncio.CancelledError:
                pass
            self.sys_stats_task = None

    async def _stats_broadcast_loop(self) -> None:
        """Main loop for broadcasting stats messages"""
        try:
            while self.running:
                await self._collect_and_send_stats()
                await asyncio.sleep(self.broadcast_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error in stats broadcast loop: {e}")

    async def _sys_stats_broadcast_loop(self) -> None:
        """Main loop for broadcasting system stats messages (less frequently)"""
        try:
            while self.running:
                await self._collect_and_send_sys_stats()
                await asyncio.sleep(self.broadcast_interval * 5)  # Every 5 seconds
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error in sys stats broadcast loop: {e}")

    async def _collect_and_send_stats(self) -> None:
        """Collect CPU load and xruns data and publish event"""
        try:
            # Get CPU load percentage from /proc/loadavg (simple approach)
            cpu_load = self._read_cpu_load()

            # For now, we'll simulate xruns as 0 since we don't have JACK integration yet
            # TODO: Integrate with actual JACK audio system to get real xruns
            xruns = 0

            # Update internal state
            self.cpu_load = cpu_load
            self.xruns = xruns

            # Publish stats event to event bus
            event = create_system_stats_event(
                "system_stats_service",
                data={
                    "type": "stats",
                    "cpu_load": cpu_load,
                    "xruns": xruns,
                }
            )
            await self.event_bus.publish(event)

            self.logger.debug(
                f"Published stats event: CPU {cpu_load:.1f}%, xruns {xruns}"
            )

        except Exception as e:
            self.logger.error(f"Error collecting stats: {e}")

    async def _collect_and_send_sys_stats(self) -> None:
        """Collect system statistics and publish event"""
        try:
            # Get memory usage percentage from /proc/meminfo
            mem_usage = self._read_memory_usage()

            # Get CPU frequency (MOD device specific)
            cpu_freq = self._read_cpu_frequency()

            # Get CPU temperature (MOD device specific)
            cpu_temp = self._read_cpu_temperature()

            # Update internal state
            self.mem_usage = mem_usage

            # Publish sys_stats event to event bus
            event = create_system_stats_event(
                "system_stats_service",
                data={
                    "type": "sys_stats",
                    "memory_percent": mem_usage,
                    "cpu_frequency": cpu_freq,
                    "cpu_temperature": cpu_temp,
                }
            )
            await self.event_bus.publish(event)

            self.logger.debug(
                f"Published sys_stats event: MEM {mem_usage:.1f}%, freq {cpu_freq}, temp {cpu_temp}"
            )

        except Exception as e:
            self.logger.error(f"Error collecting system stats: {e}")

    def _read_cpu_load(self) -> float:
        """Read CPU load from /proc/loadavg"""
        try:
            with open("/proc/loadavg", "r") as f:
                load_avg = float(f.read().strip().split()[0])
                # Convert load average to percentage (approximation)
                # This is a rough estimate, real CPU percentage would need more complex calculation
                return min(load_avg * 100, 100.0)
        except Exception:
            return 0.0

    def _read_memory_usage(self) -> float:
        """Read memory usage from /proc/meminfo"""
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()

            mem_info = {}
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    mem_info[key.strip()] = int(value.strip().split()[0])

            total = mem_info.get("MemTotal", 0)
            available = mem_info.get("MemAvailable", 0)

            if total > 0:
                used = total - available
                return (used / total) * 100.0
            return 0.0
        except Exception:
            return 0.0

    def _read_cpu_frequency(self) -> str:
        """Read CPU frequency from system file"""
        try:
            if os.path.exists(self.cpu_freq_file):
                with open(self.cpu_freq_file, "r") as f:
                    freq_khz = int(f.read().strip())
                    return str(
                        freq_khz * 1000
                    )  # Convert to Hz for legacy compatibility
            return "0"
        except Exception:
            return "0"

    def _read_cpu_temperature(self) -> str:
        """Read CPU temperature from system file"""
        try:
            if os.path.exists(self.cpu_temp_file):
                with open(self.cpu_temp_file, "r") as f:
                    temp_millicelsius = int(f.read().strip())
                    return str(
                        temp_millicelsius
                    )  # Already in millicelsius for legacy compatibility
            return "0"
        except Exception:
            return "0"

    async def send_data_ready(self) -> None:
        """Publish data_ready event"""
        self.data_ready_counter += 1
        event = create_system_stats_event(
            "system_stats_service",
            data={
                "type": "data_ready",
                "counter": self.data_ready_counter,
            }
        )
        await self.event_bus.publish(event)
        self.logger.debug(f"Published data_ready event: {self.data_ready_counter}")

    async def send_ping(self) -> None:
        """Publish ping event"""
        event = create_system_stats_event(
            "system_stats_service",
            data={
                "type": "ping",
            }
        )
        await self.event_bus.publish(event)
        self.logger.debug("Published ping event")

    def get_current_stats(self) -> dict:
        """Get current statistics as a dictionary"""
        return {
            "cpu_load": self.cpu_load,
            "xruns": self.xruns,
            "mem_usage": self.mem_usage,
            "data_ready_counter": self.data_ready_counter,
        }

    async def close(self) -> None:
        """Close the system stats service"""
        await self.stop()
        self.logger.info("System Stats Service closed")
