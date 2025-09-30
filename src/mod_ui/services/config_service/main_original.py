"""
Configuration Service for MOD UI

Serves configuration settings from the centralized config directory.
It serves the settings.json file from the config directory to other services.
"""

import asyncio
import json
import logging
import os
import signal
from pathlib import Path
from typing import Any, Dict, Optional

# Import common service infrastructure
from servicebus import Service
from servicebus.config import CommConfig, set_config

# Global service instances
service: Optional[Service] = None
settings_cache: Optional[Dict[str, Any]] = None

# Path to the settings JSON file
SETTINGS_JSON_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "config" / "settings.json"
)


def get_template_variables() -> Dict[str, Any]:
    """Generate current template variables"""
    import time

    # Version variable
    version_arg = "1"
    try:
        # Try to read version from MOD release file
        version_file = "/etc/mod-release/release"
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                image_version = f.read().strip()
                if image_version and len(image_version) > 1:
                    # Strip initial 'v' from version if present
                    version_arg = (
                        image_version[1:] if image_version[0] == "v" else image_version
                    )
                else:
                    version_arg = str(int(time.time()))
        else:
            # Use timestamp as fallback
            version_arg = str(int(time.time()))
    except Exception as e:
        logging.error(f"Error reading version: {e}")
        version_arg = str(int(time.time()))

    # Desktop mode variable
    desktop_mode = bool(int(os.environ.get("MOD_DESKTOP", "0")))

    return {
        "version": version_arg,
        "using_desktop": "true" if desktop_mode else "false",
        "cloud_url": "https://cloud.moddevices.com",
        "cloud_labs_url": "https://cloud.moddevices.com/labs",
        "plugins_url": "https://cloud.moddevices.com/plugins",
        "pedalboards_url": "https://cloud.moddevices.com/pedalboards",
        "pedalboards_labs_url": "https://cloud.moddevices.com/labs/pedalboards",
        "controlchain_url": "https://wiki.moddevices.com/wiki/Control_Chain",
        "using_mod": "false",  # Will be determined by hardware detection later
        "dev_api_class": (
            "dev_api" if os.environ.get("DEV_API", "").lower() == "true" else ""
        ),
    }


def load_settings() -> Dict[str, Any]:
    """Load settings from JSON file"""
    global settings_cache

    try:
        if not SETTINGS_JSON_PATH.exists():
            # Create default settings if file doesn't exist
            default_settings = {
                "audio": {"sample_rate": 48000, "buffer_size": 256, "driver": "jack"},
                "device": {"name": "MOD Device", "model": "modduo", "version": "1.0.0"},
                "ui": {"theme": "dark", "language": "en"},
            }

            # Ensure directory exists
            SETTINGS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

            with open(SETTINGS_JSON_PATH, "w") as f:
                json.dump(default_settings, f, indent=2)

            settings_cache = default_settings
            logging.info(f"Created default settings at {SETTINGS_JSON_PATH}")
        else:
            with open(SETTINGS_JSON_PATH, "r") as f:
                settings_cache = json.load(f)
            logging.info(f"Loaded settings from {SETTINGS_JSON_PATH}")

        return settings_cache

    except Exception as e:
        logging.error(f"Failed to load settings: {e}")
        # Return minimal default settings on error
        return {
            "audio": {"sample_rate": 48000, "buffer_size": 256, "driver": "jack"},
            "device": {"name": "MOD Device", "model": "modduo", "version": "1.0.0"},
        }


def save_settings(settings: Dict[str, Any]) -> bool:
    """Save settings to JSON file"""
    global settings_cache

    try:
        # Ensure directory exists
        SETTINGS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(SETTINGS_JSON_PATH, "w") as f:
            json.dump(settings, f, indent=2)

        settings_cache = settings
        logging.info(f"Saved settings to {SETTINGS_JSON_PATH}")
        return True

    except Exception as e:
        logging.error(f"Failed to save settings: {e}")
        return False


async def initialize_services():
    """Initialize all services"""
    global service

    logger = logging.getLogger(__name__)
    logger.info("Starting Config Service v2...")

    try:
        # Load initial configuration
        load_settings()

        # Initialize Service for Redis pub/sub communication
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # Configure ServiceBus with Docker environment
        config = CommConfig(redis_url=redis_url)
        set_config(config)

        logger.info("Using Redis URL: %s", redis_url)

        service = Service("config")

        # Register config handlers
        service.register_handler("GET_ALL_CONFIG", handle_get_all_config)
        service.register_handler("GET_CONFIG_SECTION", handle_get_config_section)
        service.register_handler("GET_CONFIG_VALUE", handle_get_config_value)
        service.register_handler("SET_CONFIG_VALUE", handle_set_config_value)
        service.register_handler("RELOAD_CONFIG", handle_reload_config)

        await service.start()
        logger.info("Service started for Redis pub/sub communication")

        logger.info("Config Service v2 startup complete")

    except Exception as e:
        logger.error(f"Failed to start Config Service v2: {e}")
        raise


async def shutdown_services():
    """Shutdown all services gracefully"""
    global service

    logger = logging.getLogger(__name__)
    logger.info("Shutting down Config Service v2...")

    if service:
        await service.stop()
        logger.info("Service stopped")

    logger.info("Config Service v2 shutdown complete")


# ServiceServer request handlers for Redis pub/sub communication
async def handle_get_all_config(data) -> dict:
    """Handler for getting all configuration settings"""
    try:
        settings = load_settings()
        return {"success": True, "config": settings}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_get_config_section(data) -> dict:
    """Handler for getting a specific configuration section"""
    try:
        section = data.get("section")

        if not section:
            return {"success": False, "error": "Section parameter required"}

        settings = load_settings()

        if section not in settings:
            return {"success": False, "error": f"Section '{section}' not found"}

        return {"success": True, "section": section, "config": settings[section]}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_get_config_value(data) -> dict:
    """Handler for getting a specific configuration value"""
    try:
        section = data.get("section")
        key = data.get("key")

        if not section or not key:
            return {"success": False, "error": "Section and key parameters required"}

        settings = load_settings()

        if section not in settings:
            return {"success": False, "error": f"Section '{section}' not found"}

        section_data = settings[section]
        if key not in section_data:
            return {
                "success": False,
                "error": f"Key '{key}' not found in section '{section}'",
            }

        return {
            "success": True,
            "section": section,
            "key": key,
            "value": section_data[key],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_set_config_value(data) -> dict:
    """Handler for setting a configuration value"""
    try:
        section = data.get("section")
        key = data.get("key")
        value = data.get("value")

        if not section or not key:
            return {"success": False, "error": "Section and key parameters required"}

        settings = load_settings()

        # Create section if it doesn't exist
        if section not in settings:
            settings[section] = {}

        # Set the value
        settings[section][key] = value

        # Save settings
        if save_settings(settings):
            return {
                "success": True,
                "message": f"Set {section}.{key} = {value}",
                "section": section,
                "key": key,
                "value": value,
            }
        else:
            return {"success": False, "error": "Failed to save settings"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_reload_config(data) -> dict:
    """Handler for reloading configuration from file"""
    global settings_cache
    try:
        # Clear cache to force reload
        settings_cache = None
        settings = load_settings()

        return {
            "success": True,
            "message": "Configuration reloaded successfully",
            "config": settings,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def main():
    """Main entry point for the service"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, _frame):
        logger.info("Received signal %d, shutting down...", signum)
        asyncio.get_event_loop().stop()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Initialize services
        await initialize_services()

        logger.info("Config Service v2 is running - Press Ctrl+C to shutdown")

        # Keep the service running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Service error: %s", str(e))
        raise
    finally:
        # Shutdown services
        await shutdown_services()


if __name__ == "__main__":
    asyncio.run(main())
