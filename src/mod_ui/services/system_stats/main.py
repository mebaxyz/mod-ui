"""
System Statistics Service

This service provides system information and statistics using the simplified
service communication package. It handles requests for system info and stats
from other services like the WebSocket Gateway.
"""

import asyncio
import logging
import os
import platform
import subprocess
from datetime import datetime
from typing import Any, Dict

from mod_ui.common import RequestType, SimpleService, service_handler

# Create the service instance with Redis URL from environment
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_db = os.getenv("REDIS_DB", "0")
redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

service = SimpleService("system-stats-service", redis_url=redis_url)


@service.enum_handler(RequestType.GET_SYSTEM_INFO)
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
        logging.error(f"Error getting system info: {e}")
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


@service.handler("get_system_stats")
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
        logging.error(f"Error getting system stats: {e}")
        return {
            "cpu_load": 0.0,
            "mem_usage": 0.0,
            "cpu_frequency": "0",
            "cpu_temperature": "0",
            "uptime": "0",
            "disk_usage": 0.0,
            "timestamp": datetime.now().isoformat(),
        }


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
        logging.warning(f"Failed to read CPU load: {e}")
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
        logging.warning(f"Failed to read memory usage: {e}")
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
        logging.warning(f"Failed to read CPU frequency: {e}")
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
        logging.warning(f"Failed to read CPU temperature: {e}")
        return "0"


def _get_uptime() -> str:
    """Get system uptime in seconds"""
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.read().strip().split()[0])
            return str(int(uptime_seconds))
    except Exception as e:
        logging.warning(f"Failed to read uptime: {e}")
        return "0"


def _get_disk_usage() -> float:
    """Get disk usage percentage for root filesystem"""
    try:
        import shutil

        total, used, free = shutil.disk_usage("/")
        return (used / total) * 100.0
    except Exception as e:
        logging.warning(f"Failed to read disk usage: {e}")
        return 0.0


async def main():
    """Main entry point for the system stats service"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting System Stats Service...")

    try:
        # Start the service (this will handle requests)
        await service.start()

        logger.info("System Stats Service started successfully")

        # Keep the service running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Service error: {e}")
        raise
    finally:
        await service.stop()
        logger.info("System Stats Service stopped")


if __name__ == "__main__":
    asyncio.run(main())
