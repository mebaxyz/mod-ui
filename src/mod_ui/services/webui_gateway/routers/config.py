"""
Configuration API Router for WebUI Gateway

This router handles configuration-related HTTP requests and communicates with
the Configuration Service via Redis pub/sub.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from mod_ui.common import RequestType, ServiceClient

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
        response = await config_service_client.make_request(
            service_name="config",
            request_type=RequestType.GET_ALL_CONFIG,
            data={},
        )

        if response.data.get("success"):
            return {
                "ok": True,
                **response.data.get("config", {}),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=response.data.get("error", "Failed to get config"),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/{section}")
async def get_settings_section(section: str) -> Dict[str, Any]:
    """Get a specific configuration section"""
    if not config_service_client:
        raise HTTPException(status_code=500, detail="Config service not available")

    try:
        response = await config_service_client.make_request(
            service_name="config",
            request_type=RequestType.GET_CONFIG_SECTION,
            data={"section": section},
        )

        if response.data.get("success"):
            return {
                "ok": True,
                "section": response.data.get("section"),
                **response.data.get("config", {}),
            }
        else:
            error_msg = response.data.get("error", "Failed to get config section")
            if "not found" in error_msg:
                raise HTTPException(status_code=404, detail=error_msg)
            else:
                raise HTTPException(status_code=500, detail=error_msg)

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
        response = await config_service_client.make_request(
            service_name="config",
            request_type=RequestType.GET_CONFIG_VALUE,
            data={"section": section, "key": key},
        )

        if response.data.get("success"):
            return {
                "ok": True,
                "section": response.data.get("section"),
                "key": response.data.get("key"),
                "value": response.data.get("value"),
            }
        else:
            error_msg = response.data.get("error", "Failed to get config value")
            if "not found" in error_msg:
                raise HTTPException(status_code=404, detail=error_msg)
            else:
                raise HTTPException(status_code=500, detail=error_msg)

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
        response = await config_service_client.make_request(
            service_name="config",
            request_type=RequestType.SET_CONFIG_VALUE,
            data={"section": section, "key": key, "value": value},
        )

        if response.data.get("success"):
            return {
                "ok": True,
                "message": response.data.get("message", "Configuration updated"),
                "section": response.data.get("section"),
                "key": response.data.get("key"),
                "value": response.data.get("value"),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=response.data.get("error", "Failed to set config value"),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_config() -> Dict[str, Any]:
    """Reload configuration from file"""
    if not config_service_client:
        raise HTTPException(status_code=500, detail="Config service not available")

    try:
        response = await config_service_client.make_request(
            service_name="config",
            request_type=RequestType.RELOAD_CONFIG,
            data={},
        )

        if response.data.get("success"):
            return {
                "ok": True,
                "message": response.data.get("message", "Configuration reloaded"),
                "config": response.data.get("config", {}),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=response.data.get("error", "Failed to reload config"),
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
        response = await config_service_client.make_request(
            service_name="config",
            request_type=RequestType.GET_ALL_CONFIG,
            data={},
        )

        if response.data.get("success"):
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
                "error": response.data.get("error", "Unknown error"),
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "config-service",
            "settings_loaded": False,
            "error": str(e),
        }
