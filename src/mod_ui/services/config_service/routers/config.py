"""
Configuration Router

Provides REST API endpoints for serving MOD UI configuration settings.
Serves the settings.json file from the mod directory as structured JSON responses.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException

# Path to the settings JSON file
SETTINGS_JSON_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "mod" / "settings.json"

logger = logging.getLogger(__name__)

# Cache for settings data
_settings_cache: Optional[Dict[str, Any]] = None
_settings_loaded = False

def load_settings() -> Dict[str, Any]:
    """Load settings from JSON file"""
    global _settings_cache, _settings_loaded

    if _settings_cache is not None:
        return _settings_cache

    try:
        if not SETTINGS_JSON_PATH.exists():
            raise FileNotFoundError(f"Settings file not found: {SETTINGS_JSON_PATH}")

        with open(SETTINGS_JSON_PATH, 'r') as f:
            _settings_cache = json.load(f)
            _settings_loaded = True
            logger.info(f"Successfully loaded settings from {SETTINGS_JSON_PATH}")
            return _settings_cache

    except Exception as e:
        logger.error(f"Failed to load settings from {SETTINGS_JSON_PATH}: {e}")
        _settings_loaded = False
        raise

router = APIRouter(prefix="/api/v1/config", tags=["configuration"])

@router.get("/")
async def get_config_overview():
    """
    Get an overview of available configuration endpoints.
    """
    return {
        "endpoints": [
            "/api/v1/config/settings",
            "/api/v1/config/settings/{section}",
            "/api/v1/config/settings/{section}/{key}",
            "/api/v1/config/health"
        ],
        "description": "MOD UI Configuration Service endpoints"
    }

@router.get("/settings")
async def get_all_settings() -> Dict[str, Any]:
    """
    Get all configuration settings from settings.json as a JSON object.
    """
    try:
        return load_settings()
    except Exception as e:
        logger.error(f"Failed to retrieve settings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve settings: {str(e)}"
        )

@router.get("/settings/{section}")
async def get_settings_section(section: str) -> Dict[str, Any]:
    """
    Get a specific configuration section from settings.json.
    """
    try:
        settings = load_settings()
        if section not in settings:
            raise HTTPException(
                status_code=404,
                detail=f"Settings section '{section}' not found"
            )
        return settings[section]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve settings section '{section}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve settings section '{section}': {str(e)}"
        )

@router.get("/settings/{section}/{key}")
async def get_setting_by_key(section: str, key: str) -> Any:
    """
    Get a specific configuration setting by section and key.
    """
    try:
        settings = load_settings()
        if section not in settings:
            raise HTTPException(
                status_code=404,
                detail=f"Settings section '{section}' not found"
            )

        section_data = settings[section]
        if key not in section_data:
            raise HTTPException(
                status_code=404,
                detail=f"Setting '{key}' not found in section '{section}'"
            )

        return section_data[key]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve setting '{section}.{key}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve setting '{section}.{key}': {str(e)}"
        )

@router.get("/health")
async def config_health_check():
    """
    Health check for the configuration service.
    """
    health_status = {
        "status": "healthy" if _settings_loaded else "unhealthy",
        "service": "config-service",
        "settings_loaded": _settings_loaded
    }

    if not _settings_loaded:
        health_status["error"] = "Failed to load settings file"

    return health_status
