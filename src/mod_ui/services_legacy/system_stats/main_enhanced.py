"""
System Statistics Service - ENHANCED with Auto-Reconnecting ServiceBus

This provides exactly what you wanted:
1. Define connection once ✅
2. Define topics and handlers ✅
3. Everything else automatic ✅
"""

import asyncio
import logging
import os
import platform
import signal
import subprocess
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

# Import ServiceBus components
import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError
from servicebus import CommConfig, Service, ServiceEvent, get_config, set_config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResilientServiceBus:
    """
    ENHANCED Auto-Reconnecting ServiceBus Wrapper

    This provides exactly what you wanted:
    1. Define connection once ✅
    2. Define topics and handlers ✅
    3. Everything else automatic (reconnection, health monitoring, etc.) ✅
    """

    def __init__(self, service_name: str, redis_url: str = None):
        self.service_name = service_name
        self.redis_url = redis_url or self._get_redis_url()
        self.service: Optional[Service] = None
        self.methods: Dict[str, Callable] = {}
        self.events: Dict[str, Callable] = {}
        self.is_running = False
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 60.0
        self.health_check_interval = 30.0
        self.last_health_check = 0
        self._redis_client: Optional[redis.Redis] = None
        self._shutdown_event = asyncio.Event()

    def _get_redis_url(self) -> str:
        """Get Redis URL from environment"""
        host = os.getenv("REDIS_HOST", "localhost")
        port = os.getenv("REDIS_PORT", "6379")
        db = os.getenv("REDIS_DB", "0")
        return f"redis://{host}:{port}/{db}"

    def register_method(self, method_name: str, handler: Callable):
        """Register a method handler"""
        self.methods[method_name] = handler
        logger.info(f"Registered method '{method_name}'")

    def subscribe_to_event(self, event_name: str, handler: Callable):
        """Subscribe to an event"""
        self.events[event_name] = handler
        logger.info(f"Subscribed to event '{event_name}'")

    async def _create_redis_client(self) -> redis.Redis:
        """Create Redis client with connection pooling"""
        return redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            max_connections=10,
        )

    async def _test_redis_connection(self) -> bool:
        """Test if Redis connection is working"""
        try:
            if not self._redis_client:
                self._redis_client = await self._create_redis_client()

            await self._redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection test failed: {e}")
            # Clean up failed client
            if self._redis_client:
                try:
                    await self._redis_client.aclose()
                except:
                    pass
                self._redis_client = None
            return False

    async def _connect_to_servicebus(self) -> bool:
        """Connect to ServiceBus with error handling"""
        try:
            # Configure ServiceBus
            config = CommConfig(redis_url=self.redis_url)
            set_config(config)

            # Create service
            self.service = Service(self.service_name)

            # Register all methods
            for method_name, handler in self.methods.items():
                self.service.register_handler(method_name, handler)

            # Subscribe to all events
            for event_name, handler in self.events.items():
                self.service.subscribe(event_name, handler)

            return True

        except Exception as e:
            logger.error(f"Failed to connect to ServiceBus: {e}")
            self.service = None
            return False

    async def _reconnect_to_redis(self):
        """Handle Redis reconnection with exponential backoff"""
        while not self._shutdown_event.is_set() and self.is_running:
            try:
                logger.info(
                    f"Attempting to reconnect ServiceBus for '{self.service_name}'..."
                )

                # Test Redis connection first
                if await self._test_redis_connection():
                    # Try to reconnect ServiceBus
                    if await self._connect_to_servicebus():
                        logger.info(
                            f"ServiceBus connection established for '{self.service_name}'"
                        )
                        logger.info(
                            f"Reconnection successful for '{self.service_name}'"
                        )
                        self.reconnect_delay = 1.0  # Reset delay on success
                        return

                # Exponential backoff
                logger.warning(
                    f"Reconnection failed, retrying in {self.reconnect_delay}s..."
                )
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(
                    self.reconnect_delay * 2, self.max_reconnect_delay
                )

            except Exception as e:
                logger.error(f"Reconnection error: {e}")
                await asyncio.sleep(self.reconnect_delay)

    async def _health_monitor(self):
        """Monitor ServiceBus health and trigger reconnection if needed"""
        while not self._shutdown_event.is_set() and self.is_running:
            try:
                await asyncio.sleep(self.health_check_interval)

                current_time = time.time()

                # Only check if enough time has passed
                if current_time - self.last_health_check < self.health_check_interval:
                    continue

                self.last_health_check = current_time

                # Test Redis connection
                if not await self._test_redis_connection():
                    logger.warning(
                        f"Health check failed for '{self.service_name}', triggering reconnection..."
                    )
                    await self._reconnect_to_redis()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)  # Brief pause before continuing

    async def start(self):
        """Start the enhanced ServiceBus with auto-reconnection"""
        self.is_running = True

        # Initial connection
        if await self._test_redis_connection() and await self._connect_to_servicebus():
            logger.info(f"ServiceBus connection established for '{self.service_name}'")
            logger.info(f"Reconnection successful for '{self.service_name}'")
        else:
            logger.warning(
                f"Initial connection failed, starting reconnection process..."
            )
            asyncio.create_task(self._reconnect_to_redis())

        # Start health monitoring
        asyncio.create_task(self._health_monitor())

        # Start the service if connected
        if self.service:
            await self.service.start()

    async def stop(self):
        """Stop the ServiceBus gracefully"""
        self.is_running = False
        self._shutdown_event.set()

        if self.service:
            await self.service.stop()

        if self._redis_client:
            await self._redis_client.aclose()

    async def publish_event(self, event_name: str, data: Any):
        """Publish an event through the ServiceBus"""
        if self.service:
            await self.service.publish_event(event_name, data)


# Global enhanced ServiceBus instance
resilient_servicebus: Optional[ResilientServiceBus] = None


async def setup_enhanced_servicebus():
    """Setup the enhanced ServiceBus with all handlers"""
    global resilient_servicebus

    # Step 1: Define connection once ✅
    resilient_servicebus = ResilientServiceBus("system-stats-service")

    # Step 2: Define topics and handlers ✅
    resilient_servicebus.register_method("get_system_info", get_system_info)
    resilient_servicebus.register_method("get_system_stats", get_system_stats)

    # Step 3: Everything else automatic ✅ (reconnection, health monitoring, etc.)

    logger.info("Enhanced ServiceBus setup complete for System Stats Service")


# System Info and Stats Handlers
async def get_system_info(request) -> Dict[str, Any]:
    """Get comprehensive system information"""
    try:
        # Get basic system info
        uname = platform.uname()

        # Get Python version
        python_version = platform.python_version()

        # Try to get more detailed hardware info
        architecture = platform.machine()

        # Default system info
        system_info = {
            "hwname": _get_hardware_name(),
            "architecture": architecture,
            "cpu": _get_cpu_info(),
            "platform": _get_platform_name(),
            "bin_compat": _get_binary_compatibility(),
            "model": _get_device_model(),
            "sysdate": datetime.now().strftime("%Y-%m-%d"),
            "python": {"version": python_version},
            "uname": {
                "machine": uname.machine,
                "release": uname.release,
                "sysname": uname.system,
                "version": uname.version,
            },
        }

        return system_info

    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        # Return fallback info
        return {
            "hwname": "MOD Device",
            "architecture": "unknown",
            "cpu": "Unknown CPU",
            "platform": "mod",
            "bin_compat": "unknown",
            "model": "mod",
            "sysdate": datetime.now().strftime("%Y-%m-%d"),
            "python": {"version": platform.python_version()},
            "uname": {
                "machine": "unknown",
                "release": "unknown",
                "sysname": "Linux",
                "version": "unknown",
            },
        }


async def get_system_stats(request) -> Dict[str, Any]:
    """Get current system statistics"""
    try:
        stats = {
            "cpu_load": _read_cpu_load(),
            "mem_usage": _read_memory_usage(),
            "cpu_frequency": _read_cpu_frequency(),
            "cpu_temperature": _read_cpu_temperature(),
            "uptime": _get_uptime(),
            "disk_usage": _get_disk_usage(),
            "timestamp": datetime.now().isoformat(),
        }

        return stats

    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {
            "cpu_load": 0.0,
            "mem_usage": 0.0,
            "cpu_frequency": "0",
            "cpu_temperature": "0",
            "uptime": "0",
            "disk_usage": 0.0,
            "timestamp": datetime.now().isoformat(),
        }


# System utility functions (unchanged from original)
def _get_hardware_name() -> str:
    """Get hardware name"""
    try:
        # Try to read device tree model
        if os.path.exists("/proc/device-tree/model"):
            with open("/proc/device-tree/model", "r") as f:
                return f.read().strip().replace("\x00", "")

        # Fallback to generic names based on architecture
        arch = platform.machine()
        if "arm" in arch.lower():
            return "MOD Device"
        else:
            return "MOD Development Device"
    except:
        return "MOD Device"


def _get_cpu_info() -> str:
    """Get CPU information"""
    try:
        # Try to read from /proc/cpuinfo
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
                    elif line.startswith("Hardware"):
                        return line.split(":", 1)[1].strip()

        # Fallback
        return platform.processor() or "Unknown CPU"
    except:
        return "Unknown CPU"


def _get_platform_name() -> str:
    """Get platform name"""
    # This would be customized based on the actual MOD hardware
    return "modduo"  # or "modduox", "moddwarf", etc.


def _get_binary_compatibility() -> str:
    """Get binary compatibility string"""
    arch = platform.machine()
    if "arm" in arch.lower():
        return "arm-linux-gnueabihf"
    elif "x86_64" in arch.lower():
        return "x86_64-linux-gnu"
    else:
        return f"{arch}-linux-gnu"


def _get_device_model() -> str:
    """Get device model"""
    # This would be determined based on actual hardware detection
    return "modduo"  # Default model


def _read_cpu_load() -> float:
    """Read CPU load from /proc/loadavg"""
    try:
        with open("/proc/loadavg", "r") as f:
            load_avg = float(f.read().strip().split()[0])
            # Convert load average to percentage (approximation)
            return min(load_avg * 100, 100.0)
    except Exception as e:
        logger.warning(f"Failed to read CPU load: {e}")
        return 0.0


def _read_memory_usage() -> float:
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
        logger.warning(f"Failed to read memory usage: {e}")
        return 0.0


def _read_cpu_frequency() -> str:
    """Read CPU frequency from system file"""
    try:
        cpu_freq_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
        if os.path.exists(cpu_freq_file):
            with open(cpu_freq_file, "r") as f:
                freq_khz = int(f.read().strip())
                return str(freq_khz * 1000)  # Convert to Hz
        return "0"
    except Exception as e:
        logger.warning(f"Failed to read CPU frequency: {e}")
        return "0"


def _read_cpu_temperature() -> str:
    """Read CPU temperature from system file"""
    try:
        cpu_temp_file = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(cpu_temp_file):
            with open(cpu_temp_file, "r") as f:
                temp_millicelsius = int(f.read().strip())
                return str(temp_millicelsius)  # Keep in millicelsius
        return "0"
    except Exception as e:
        logger.warning(f"Failed to read CPU temperature: {e}")
        return "0"


def _get_uptime() -> str:
    """Get system uptime in seconds"""
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().strip().split()[0])
            return str(int(uptime_seconds))
    except Exception as e:
        logger.warning(f"Failed to read uptime: {e}")
        return "0"


def _get_disk_usage() -> float:
    """Get disk usage percentage for root filesystem"""
    try:
        import shutil

        total, used, free = shutil.disk_usage("/")
        return (used / total) * 100.0
    except Exception as e:
        logger.warning(f"Failed to read disk usage: {e}")
        return 0.0


async def broadcast_stats_periodic():
    """Background task to broadcast system stats via WebSocket"""
    global resilient_servicebus

    while resilient_servicebus and resilient_servicebus.is_running:
        try:
            # Get current system stats
            cpu_load = _read_cpu_load()
            xruns = 0  # TODO: Get actual xruns from audio engine

            mem_usage = _read_memory_usage()
            cpu_freq = _read_cpu_frequency()
            cpu_temp = _read_cpu_temperature()

            # Send legacy WebSocket messages that the frontend expects
            # Format: "stats CPU_LOAD XRUNS"
            stats_message = f"stats {cpu_load:.1f} {xruns}"

            # Format: "sys_stats MEM_LOAD CPU_FREQ CPU_TEMP"
            sys_stats_message = f"sys_stats {mem_usage:.1f} {cpu_freq} {cpu_temp}"

            # Send both messages to webui-gateway via ServiceBus events
            try:
                # Publish stats message event
                await resilient_servicebus.publish_event(
                    "websocket_broadcast",
                    {
                        "type": "legacy_websocket",
                        "content": stats_message,
                        "message_type": "system_stats",
                        "cpu_load": cpu_load,
                        "xruns": xruns,
                    },
                )
                logger.debug(f"Published stats message event: {stats_message}")

                # Publish sys_stats message event
                await resilient_servicebus.publish_event(
                    "websocket_broadcast",
                    {
                        "type": "legacy_websocket",
                        "content": sys_stats_message,
                        "message_type": "system_stats_detailed",
                        "memory_usage": mem_usage,
                        "cpu_frequency": cpu_freq,
                        "cpu_temp": cpu_temp,
                    },
                )
                logger.debug(f"Published sys_stats message event: {sys_stats_message}")

            except Exception as e:
                logger.warning(f"Failed to publish stats events: {e}")

        except Exception as e:
            logger.error(f"Error in stats broadcasting: {e}")

        # Wait 2 seconds before next update (matches original MOD UI frequency)
        await asyncio.sleep(2)


async def main():
    """Main entry point for the Enhanced System Stats Service"""

    # Setup signal handlers for graceful shutdown
    def signal_handler():
        logger.info("Received shutdown signal")
        if resilient_servicebus:
            asyncio.create_task(resilient_servicebus.stop())

    if os.name != "nt":  # Unix systems
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())

    logger.info("Starting System Stats Service with Enhanced ServiceBus...")

    try:
        # Setup enhanced ServiceBus with all handlers
        await setup_enhanced_servicebus()

        # Start the enhanced ServiceBus (Step 3: Everything else automatic ✅)
        await resilient_servicebus.start()

        logger.info(
            "System Stats Service with Enhanced ServiceBus started successfully"
        )

        # Start background stats broadcasting task
        stats_task = asyncio.create_task(broadcast_stats_periodic())
        logger.info("System stats broadcasting started")

        try:
            # Keep the service running
            while resilient_servicebus and resilient_servicebus.is_running:
                await asyncio.sleep(1)
        finally:
            # Cancel background task on shutdown
            stats_task.cancel()
            try:
                await stats_task
            except asyncio.CancelledError:
                pass

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"System Stats Service error: {e}")
        raise
    finally:
        if resilient_servicebus:
            await resilient_servicebus.stop()

    logger.info("System Stats Service stopped")


if __name__ == "__main__":
    asyncio.run(main())
