"""
Configuration API Router for WebUI Gateway

This router handles configuration-related HTTP requests and communicates with
the Configuration Service via Redis pub/sub.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from servicebus import ServiceClient

router = APIRouter()

# Service client for communicating with config service
config_service_client: Optional[ServiceClient] = None


def inject_service_client(client: ServiceClient):
    """Inject the service client for config communication"""
    global config_service_client
    config_service_client = client


@router.get("/")
async def get_config_overview() -> Dict[str, Any]:
    """Get an overview of available configuration endpoints"""
    return {
        "endpoints": [
            "/api/config/settings",
            "/api/config/settings/{section}",
            "/api/config/settings/{section}/{key}",
            "/api/config/reload",
        ],
        "description": "MOD UI Configuration Service endpoints",
    }


@router.get("/settings")
async def get_all_settings() -> Dict[str, Any]:
    """Get all configuration settings"""
    if not config_service_client:
        raise HTTPException(status_code=500, detail="Config service not available")

    try:
        response = await config_service_client.call(
            target_service="config",
            request_type="get_all_config",
            data={},
        )

        if response is not None:
            return {
                "ok": True,
                **response,
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to get config",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/{section}")
async def get_settings_section(section: str) -> Dict[str, Any]:
    """Get a specific configuration section"""
    if not config_service_client:
        raise HTTPException(status_code=500, detail="Config service not available")

    try:
        response = await config_service_client.call(
            target_service="config",
            request_type="get_config_section",
            data={"section": section},
        )

        if response is not None:
            return {
                "ok": True,
                "section": section,
                **response,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to get config section")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/{section}/{key}")
async def get_setting_by_key(section: str, key: str) -> Dict[str, Any]:
    """Get a specific configuration setting by section and key"""
    if not config_service_client:
        raise HTTPException(status_code=500, detail="Config service not available")

    try:
        response = await config_service_client.call(
            target_service="config",
            request_type="get_config_value",
            data={"section": section, "key": key},
        )

        if response is not None:
            return {
                "ok": True,
                "section": section,
                "key": key,
                "value": response,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to get config value")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/{section}/{key}")
async def set_setting_by_key(section: str, key: str, value: Any) -> Dict[str, Any]:
    """Set a specific configuration setting by section and key"""
    if not config_service_client:
        raise HTTPException(status_code=500, detail="Config service not available")

    try:
        response = await config_service_client.call(
            target_service="config",
            request_type="set_config_value",
            data={"section": section, "key": key, "value": value},
        )

        if response is not None:
            return {
                "ok": True,
                "message": "Configuration updated",
                "section": section,
                "key": key,
                "value": value,
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to set config value",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_config() -> Dict[str, Any]:
    """Reload configuration from file"""
    if not config_service_client:
        raise HTTPException(status_code=500, detail="Config service not available")

    try:
        response = await config_service_client.call(
            target_service="config",
            request_type="reload_config",
            data={},
        )

        if response is not None:
            return {
                "ok": True,
                "message": "Configuration reloaded",
                "config": response,
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to reload config",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def config_health_check() -> Dict[str, Any]:
    """Health check for the configuration service"""
    if not config_service_client:
        return {
            "status": "unhealthy",
            "service": "config-service",
            "error": "Service client not available",
        }

    try:
        # Try to get all settings to verify service is working
        response = await config_service_client.call(
            target_service="config",
            request_type="get_all_config",
            data={},
        )

        if response is not None:
            return {
                "status": "healthy",
                "service": "config-service",
                "settings_loaded": True,
            }
        else:
            return {
                "status": "unhealthy",
                "service": "config-service",
                "settings_loaded": False,
                "error": "Unknown error",
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "config-service",
            "settings_loaded": False,
            "error": str(e),
        }
