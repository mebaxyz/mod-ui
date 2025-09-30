"""
MOD UI - System & Resource Management Service

Consolidated service handling system control, monitoring, file management, and resource management.
This service replaces the individual config_service, system_stats, and adds new file management capabilities.
"""

import asyncio
import json
import logging
import os
import platform
import shutil
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import psutil
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ...common.models import ServiceHealth, ServiceStatus
from ...common.resilient_service_bus import ResilientServiceBus

# Configuration
SERVICE_NAME = "system_resource_management"
SERVICE_PORT = int(os.getenv("SYSTEM_RESOURCE_PORT", "8081"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# File system paths
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
PEDALBOARDS_DIR = os.path.join(DATA_DIR, "pedalboards")
BANKS_FILE = os.path.join(DATA_DIR, "banks.json")
PREFS_FILE = os.path.join(DATA_DIR, "prefs.json")
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.json")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Request/Response Models
class SystemCommand(BaseModel):
    command: str
    args: Optional[List[str]] = None


class FileOperation(BaseModel):
    operation: str  # copy, move, delete, mkdir
    source: Optional[str] = None
    destination: Optional[str] = None
    path: Optional[str] = None


class PreferenceUpdate(BaseModel):
    category: str
    key: str
    value: Union[str, int, float, bool, dict, list]


class BankUpdate(BaseModel):
    bank_id: str
    name: str
    pedalboards: List[str]


class PedalboardMeta(BaseModel):
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    created_at: Optional[str] = None
    modified_at: Optional[str] = None


# Global instances
service_bus: Optional[ResilientServiceBus] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global service_bus

    # Startup
    logger.info(f"Starting {SERVICE_NAME} service on port {SERVICE_PORT}")

    # Initialize directories
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PEDALBOARDS_DIR, exist_ok=True)

    # Initialize service bus
    service_bus = ResilientServiceBus(SERVICE_NAME, REDIS_URL)
    await service_bus.start()

    # Register service endpoints
    await service_bus.register_service(SERVICE_NAME, f"http://localhost:{SERVICE_PORT}")

    # Initialize system monitoring
    asyncio.create_task(system_monitor())

    logger.info(f"{SERVICE_NAME} service started successfully")

    yield

    # Shutdown
    logger.info(f"Shutting down {SERVICE_NAME} service")
    if service_bus:
        await service_bus.stop()


# Create FastAPI app
app = FastAPI(
    title="MOD UI - System & Resource Management Service",
    description="Handles system control, monitoring, file management, and resource management",
    version="1.0.0",
    lifespan=lifespan,
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    disk_usage = shutil.disk_usage(DATA_DIR)
    return ServiceHealth(
        service=SERVICE_NAME,
        status=ServiceStatus.HEALTHY,
        details={
            "data_directory": DATA_DIR,
            "disk_free_gb": round(disk_usage.free / (1024**3), 2),
            "disk_total_gb": round(disk_usage.total / (1024**3), 2),
            "service_bus_connected": (
                service_bus.is_connected() if service_bus else False
            ),
        },
    )


# System Status and Monitoring
@app.get("/api/system/status")
async def get_system_status():
    """Get comprehensive system status"""
    try:
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()

        # Disk usage
        disk_usage = shutil.disk_usage(DATA_DIR)

        # System info
        system_info = {
            "platform": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

        # Audio system status (would be queried from audio service)
        audio_status = "running"  # Placeholder

        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "usage_percent": cpu_percent,
                "count": psutil.cpu_count(),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "usage_percent": memory.percent,
            },
            "disk": {
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round((disk_usage.total - disk_usage.free) / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "usage_percent": round(
                    ((disk_usage.total - disk_usage.free) / disk_usage.total) * 100, 1
                ),
            },
            "system": system_info,
            "audio_engine": {
                "status": audio_status,
                "sample_rate": 48000,  # Would be queried from audio service
                "buffer_size": 256,
                "xruns": 0,
            },
            "services": await get_services_status(),
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")


@app.get("/api/system/processes")
async def get_processes():
    """Get running processes"""
    try:
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent"]
        ):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Sort by CPU usage
        processes.sort(key=lambda x: x["cpu_percent"] or 0, reverse=True)
        return {"processes": processes[:20]}  # Top 20 processes
    except Exception as e:
        logger.error(f"Error getting processes: {e}")
        raise HTTPException(status_code=500, detail="Failed to get processes")


@app.post("/api/system/command")
async def execute_system_command(command: SystemCommand):
    """Execute system command (restricted for security)"""
    # Whitelist of allowed commands for security
    allowed_commands = [
        "systemctl",
        "journalctl",
        "df",
        "free",
        "top",
        "ps",
        "lsusb",
        "lsblk",
        "mount",
        "umount",
    ]

    if command.command not in allowed_commands:
        raise HTTPException(
            status_code=403, detail=f"Command '{command.command}' not allowed"
        )

    try:
        import subprocess

        args = [command.command] + (command.args or [])
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)

        return {
            "command": " ".join(args),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timeout")
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        raise HTTPException(status_code=500, detail="Command execution failed")


# File Management
@app.get("/api/files/pedalboards")
async def list_pedalboards():
    """List all pedalboards"""
    try:
        pedalboards = []
        if os.path.exists(PEDALBOARDS_DIR):
            for item in os.listdir(PEDALBOARDS_DIR):
                item_path = os.path.join(PEDALBOARDS_DIR, item)
                if os.path.isdir(item_path):
                    manifest_path = os.path.join(item_path, "manifest.ttl")
                    if os.path.exists(manifest_path):
                        stat = os.stat(item_path)
                        pedalboards.append(
                            {
                                "id": item,
                                "name": item.replace(".pedalboard", ""),
                                "path": item_path,
                                "created": datetime.fromtimestamp(
                                    stat.st_ctime
                                ).isoformat(),
                                "modified": datetime.fromtimestamp(
                                    stat.st_mtime
                                ).isoformat(),
                                "size": get_directory_size(item_path),
                            }
                        )

        return {"pedalboards": pedalboards}
    except Exception as e:
        logger.error(f"Error listing pedalboards: {e}")
        raise HTTPException(status_code=500, detail="Failed to list pedalboards")


@app.get("/api/files/pedalboards/{pedalboard_id}")
async def get_pedalboard_info(pedalboard_id: str):
    """Get detailed pedalboard information"""
    try:
        pedalboard_path = os.path.join(PEDALBOARDS_DIR, pedalboard_id)
        if not os.path.exists(pedalboard_path):
            raise HTTPException(status_code=404, detail="Pedalboard not found")

        manifest_path = os.path.join(pedalboard_path, "manifest.ttl")
        if not os.path.exists(manifest_path):
            raise HTTPException(status_code=404, detail="Pedalboard manifest not found")

        with open(manifest_path, "r") as f:
            manifest_content = f.read()

        stat = os.stat(pedalboard_path)
        files = os.listdir(pedalboard_path)

        return {
            "id": pedalboard_id,
            "name": pedalboard_id.replace(".pedalboard", ""),
            "path": pedalboard_path,
            "manifest": manifest_content,
            "files": files,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size": get_directory_size(pedalboard_path),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pedalboard info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pedalboard info")


@app.delete("/api/files/pedalboards/{pedalboard_id}")
async def delete_pedalboard_files(pedalboard_id: str):
    """Delete pedalboard files"""
    try:
        pedalboard_path = os.path.join(PEDALBOARDS_DIR, pedalboard_id)
        if not os.path.exists(pedalboard_path):
            raise HTTPException(status_code=404, detail="Pedalboard not found")

        shutil.rmtree(pedalboard_path)

        return {"message": f"Pedalboard {pedalboard_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pedalboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete pedalboard")


@app.post("/api/files/operations")
async def file_operation(operation: FileOperation):
    """Perform file operations"""
    try:
        if operation.operation == "copy" and operation.source and operation.destination:
            if os.path.isfile(operation.source):
                shutil.copy2(operation.source, operation.destination)
            else:
                shutil.copytree(operation.source, operation.destination)
            return {"message": "File copied successfully"}

        elif (
            operation.operation == "move" and operation.source and operation.destination
        ):
            shutil.move(operation.source, operation.destination)
            return {"message": "File moved successfully"}

        elif operation.operation == "delete" and operation.path:
            if os.path.isfile(operation.path):
                os.remove(operation.path)
            else:
                shutil.rmtree(operation.path)
            return {"message": "File deleted successfully"}

        elif operation.operation == "mkdir" and operation.path:
            os.makedirs(operation.path, exist_ok=True)
            return {"message": "Directory created successfully"}

        else:
            raise HTTPException(
                status_code=400, detail="Invalid operation or missing parameters"
            )

    except Exception as e:
        logger.error(f"Error performing file operation: {e}")
        raise HTTPException(status_code=500, detail="File operation failed")


# Configuration Management
@app.get("/api/config/preferences")
async def get_preferences():
    """Get user preferences"""
    try:
        if os.path.exists(PREFS_FILE):
            with open(PREFS_FILE, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to get preferences")


@app.put("/api/config/preferences")
async def update_preference(pref_update: PreferenceUpdate):
    """Update user preference"""
    try:
        # Load existing preferences
        prefs = {}
        if os.path.exists(PREFS_FILE):
            with open(PREFS_FILE, "r") as f:
                prefs = json.load(f)

        # Update preference
        if pref_update.category not in prefs:
            prefs[pref_update.category] = {}
        prefs[pref_update.category][pref_update.key] = pref_update.value

        # Save preferences
        with open(PREFS_FILE, "w") as f:
            json.dump(prefs, f, indent=2)

        return {"message": "Preference updated successfully"}
    except Exception as e:
        logger.error(f"Error updating preference: {e}")
        raise HTTPException(status_code=500, detail="Failed to update preference")


@app.get("/api/config/banks")
async def get_banks():
    """Get bank configuration"""
    try:
        if os.path.exists(BANKS_FILE):
            with open(BANKS_FILE, "r") as f:
                return json.load(f)
        return {"banks": []}
    except Exception as e:
        logger.error(f"Error getting banks: {e}")
        raise HTTPException(status_code=500, detail="Failed to get banks")


@app.put("/api/config/banks")
async def update_bank(bank_update: BankUpdate):
    """Update bank configuration"""
    try:
        # Load existing banks
        banks_data = {}
        if os.path.exists(BANKS_FILE):
            with open(BANKS_FILE, "r") as f:
                banks_data = json.load(f)

        if "banks" not in banks_data:
            banks_data["banks"] = []

        # Update or add bank
        bank_found = False
        for i, bank in enumerate(banks_data["banks"]):
            if bank.get("id") == bank_update.bank_id:
                banks_data["banks"][i] = {
                    "id": bank_update.bank_id,
                    "name": bank_update.name,
                    "pedalboards": bank_update.pedalboards,
                }
                bank_found = True
                break

        if not bank_found:
            banks_data["banks"].append(
                {
                    "id": bank_update.bank_id,
                    "name": bank_update.name,
                    "pedalboards": bank_update.pedalboards,
                }
            )

        # Save banks
        with open(BANKS_FILE, "w") as f:
            json.dump(banks_data, f, indent=2)

        return {"message": "Bank updated successfully"}
    except Exception as e:
        logger.error(f"Error updating bank: {e}")
        raise HTTPException(status_code=500, detail="Failed to update bank")


# Utility functions
def get_directory_size(path: str) -> int:
    """Get total size of directory in bytes"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, FileNotFoundError):
                pass
    return total_size


async def get_services_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all services"""
    if not service_bus:
        return {}

    try:
        services = await service_bus.discover_services()
        status = {}

        for service_name, service_info in services.items():
            status[service_name] = {
                "status": "running",
                "url": service_info.get("url", "unknown"),
                "last_seen": service_info.get("last_seen", "unknown"),
            }

        return status
    except Exception as e:
        logger.error(f"Error getting services status: {e}")
        return {}


# Background tasks
async def system_monitor():
    """Monitor system resources and publish updates"""
    while True:
        try:
            await asyncio.sleep(30)  # Every 30 seconds

            if service_bus:
                # Get current system status
                status = await get_system_status()

                # Publish system status update
                await service_bus.publish("system_status_update", status)

                # Check for critical conditions
                cpu_usage = status["cpu"]["usage_percent"]
                memory_usage = status["memory"]["usage_percent"]
                disk_usage = status["disk"]["usage_percent"]

                if cpu_usage > 90:
                    await service_bus.publish(
                        "system_alert",
                        {"type": "high_cpu", "value": cpu_usage, "threshold": 90},
                    )

                if memory_usage > 85:
                    await service_bus.publish(
                        "system_alert",
                        {"type": "high_memory", "value": memory_usage, "threshold": 85},
                    )

                if disk_usage > 95:
                    await service_bus.publish(
                        "system_alert",
                        {"type": "high_disk", "value": disk_usage, "threshold": 95},
                    )

        except Exception as e:
            logger.error(f"Error in system monitor: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=SERVICE_PORT, reload=False, log_level="info"
    )
