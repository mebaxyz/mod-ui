"""
Standalone System Statistics Service

This service runs independently from the main session service and requires
privileged access to system resources (/proc, /sys, etc.) to collect
accurate system statistics.

It publishes system statistics events to the Redis event bus for consumption
by other services, particularly the WebSocket hub for legacy client support.
"""

import asyncio
import logging
import os
import sys
from typing import Optional

import redis.asyncio as redis
from pydantic import BaseModel

from mod_ui.services.session_v2.models.events import (
    EventType,
    create_system_stats_event,
)
from mod_ui.services.session_v2.utils.event_bus import RedisEventBus


class SystemStatsConfig(BaseModel):
    """Configuration for the system stats service"""

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    broadcast_interval: float = 5.0  # Broadcast every 5 seconds
    cpu_freq_file: str = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
    cpu_temp_file: str = "/sys/class/thermal/thermal_zone0/temp"


class StandaloneSystemStatsService:
    """
    Standalone service for collecting and publishing system statistics

    This service runs independently and requires privileged access to:
    - /proc/loadavg (CPU load)
    - /proc/meminfo (memory usage)
    - /sys/devices/system/cpu/*/cpufreq/scaling_cur_freq (CPU frequency)
    - /sys/class/thermal/thermal_zone*/temp (CPU temperature)
    """

    def __init__(self, config: SystemStatsConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.stats_task: Optional[asyncio.Task] = None
        self.event_bus: Optional[RedisEventBus] = None

        # Current stats
        self.cpu_load = 0.0
        self.mem_usage = 0.0
        self.xruns = 0  # Not available in standalone mode, defaults to 0

        self.logger.info("StandaloneSystemStatsService initialized")

    async def initialize(self) -> None:
        """Initialize the system stats service and event bus connection"""
        try:
            # Initialize Redis event bus
            redis_url = f"redis://{self.config.redis_host}:{self.config.redis_port}/{self.config.redis_db}"

            self.event_bus = RedisEventBus(redis_url)
            await self.event_bus.initialize()

            # Verify system access
            self._verify_system_access()

            self.logger.info("Standalone System Stats Service initialized successfully")

        except Exception as e:
            self.logger.error(
                f"Failed to initialize Standalone System Stats Service: {e}"
            )
            raise

    def _verify_system_access(self) -> None:
        """Verify that we have access to required system files"""
        required_files = ["/proc/loadavg", "/proc/meminfo"]
        optional_files = [self.config.cpu_freq_file, self.config.cpu_temp_file]

        for file_path in required_files:
            if not os.path.exists(file_path):
                raise RuntimeError(f"Required system file not accessible: {file_path}")
            if not os.access(file_path, os.R_OK):
                raise RuntimeError(f"No read permission for required file: {file_path}")

        for file_path in optional_files:
            if os.path.exists(file_path) and not os.access(file_path, os.R_OK):
                self.logger.warning(
                    f"No read permission for optional file: {file_path}"
                )

        self.logger.info("System access verification completed")

    async def start(self) -> None:
        """Start the periodic stats broadcasting"""
        if self.running:
            return

        self.running = True
        self.logger.info("Starting standalone system stats broadcasting")

        # Start stats broadcasting task
        self.stats_task = asyncio.create_task(self._stats_broadcast_loop())

    async def stop(self) -> None:
        """Stop the stats broadcasting"""
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping standalone system stats broadcasting")

        # Cancel task
        if self.stats_task:
            self.stats_task.cancel()
            try:
                await self.stats_task
            except asyncio.CancelledError:
                pass
            self.stats_task = None

    async def _stats_broadcast_loop(self) -> None:
        """Main loop for broadcasting system stats events"""
        try:
            while self.running:
                await self._collect_and_publish_stats()
                await asyncio.sleep(self.config.broadcast_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error in stats broadcast loop: {e}")

    async def _collect_and_publish_stats(self) -> None:
        """Collect system statistics and publish to event bus"""
        try:
            # Collect all stats
            cpu_load = self._read_cpu_load()
            mem_usage = self._read_memory_usage()
            cpu_freq = self._read_cpu_frequency()
            cpu_temp = self._read_cpu_temperature()

            # Update internal state
            self.cpu_load = cpu_load
            self.mem_usage = mem_usage

            # Publish system stats event to the event bus
            if self.event_bus:
                event = create_system_stats_event(
                    event_type=EventType.SYSTEM_STATS_UPDATED,
                    source_service="system_stats_standalone",
                    cpu_percent=cpu_load,
                    memory_percent=mem_usage,
                    cpu_frequency=cpu_freq,
                    cpu_temperature=cpu_temp,
                    xruns=self.xruns,
                )
                await self.event_bus.publish(event)

                self.logger.info(
                    f"Published system stats event: CPU {cpu_load:.1f}%, MEM {mem_usage:.1f}%, freq {cpu_freq}Hz, temp {cpu_temp}°C"
                )
            else:
                self.logger.warning(
                    "Event bus not available, skipping stats publication"
                )

        except Exception as e:
            self.logger.error(f"Error collecting and publishing system stats: {e}")

    def _read_cpu_load(self) -> float:
        """Read CPU load from /proc/loadavg"""
        try:
            with open("/proc/loadavg", "r") as f:
                load_avg = float(f.read().strip().split()[0])
                # Convert load average to percentage (approximation)
                # This is a rough estimate based on single-core load
                return min(load_avg * 100, 100.0)
        except Exception as e:
            self.logger.warning(f"Failed to read CPU load: {e}")
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
        except Exception as e:
            self.logger.warning(f"Failed to read memory usage: {e}")
            return 0.0

    def _read_cpu_frequency(self) -> str:
        """Read CPU frequency from system file"""
        try:
            if os.path.exists(self.config.cpu_freq_file):
                with open(self.config.cpu_freq_file, "r") as f:
                    freq_khz = int(f.read().strip())
                    return str(
                        freq_khz * 1000
                    )  # Convert to Hz for legacy compatibility
            return "0"
        except Exception as e:
            self.logger.warning(f"Failed to read CPU frequency: {e}")
            return "0"

    def _read_cpu_temperature(self) -> str:
        """Read CPU temperature from system file"""
        try:
            if os.path.exists(self.config.cpu_temp_file):
                with open(self.config.cpu_temp_file, "r") as f:
                    temp_millicelsius = int(f.read().strip())
                    return str(
                        temp_millicelsius
                    )  # Keep in millicelsius for legacy compatibility
            return "0"
        except Exception as e:
            self.logger.warning(f"Failed to read CPU temperature: {e}")
            return "0"

    def get_current_stats(self) -> dict:
        """Get current statistics as a dictionary"""
        return {
            "cpu_load": self.cpu_load,
            "mem_usage": self.mem_usage,
            "xruns": self.xruns,
        }

    async def close(self) -> None:
        """Close the system stats service"""
        await self.stop()
        if self.event_bus:
            await self.event_bus.close()
        self.logger.info("Standalone System Stats Service closed")


async def main():
    """Main entry point for the standalone system stats service"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load configuration from environment variables
    config = SystemStatsConfig(
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_db=int(os.getenv("REDIS_DB", "0")),
        broadcast_interval=float(os.getenv("STATS_BROADCAST_INTERVAL", "5.0")),
    )

    # Create and start the service
    service = StandaloneSystemStatsService(config)

    try:
        await service.initialize()
        await service.start()

        logger = logging.getLogger(__name__)
        logger.info("Standalone System Stats Service started successfully")

        # Keep the service running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Service error: {e}")
        raise
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
