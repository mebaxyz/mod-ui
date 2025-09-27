"""
Effects Router for WebUI Gateway
Provides FastAPI endpoints that communicate with the Effects Service via Redis pub/sub
"""

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from mod_ui.common import ServiceClient, ServiceResponse
from mod_ui.common.config import get_redis_url_from_env

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/effect", tags=["effects"])


class EffectAddRequestBody(BaseModel):
    """Request body for adding an effect"""

    uri: str
    x: float = 0.0
    y: float = 0.0


class EffectParameterSetBody(BaseModel):
    """Request body for setting effect parameters"""

    symbol: str
    value: float


@router.get("/add/{instance:path}")
async def add_effect(
    instance: str = Path(..., description="Effect instance path"),
    uri: str = Query(..., description="Plugin URI"),
    x: float = Query(0.0, description="X position"),
    y: float = Query(0.0, description="Y position"),
):
    """Add an effect to the pedalboard"""
    try:
        # Communicate with effects service
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {"instance": instance, "uri": uri, "x": x, "y": y}

        response: ServiceResponse = await service_client.make_request(
            "effect_add", request_data, "effects_service"
        )

        if response.success:
            return response.data
        else:
            raise HTTPException(
                status_code=400, detail=response.data.get("error", "Add effect failed")
            )

    except Exception as e:
        logger.error(f"Add effect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/remove/{instance:path}")
async def remove_effect(instance: str = Path(..., description="Effect instance path")):
    """Remove an effect from the pedalboard"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {"instance": instance}

        response: ServiceResponse = await service_client.make_request(
            "effect_remove", request_data, "effects_service"
        )

        if response.success:
            return response.data.get("success", True)
        else:
            raise HTTPException(
                status_code=400,
                detail=response.data.get("error", "Remove effect failed"),
            )

    except Exception as e:
        logger.error(f"Remove effect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_effects():
    """List all available effects"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {}

        response: ServiceResponse = await service_client.make_request(
            "effect_list", request_data, "effects_service"
        )

        if response.success:
            return response.data.get("plugins", [])
        else:
            raise HTTPException(
                status_code=500,
                detail=response.data.get("error", "Failed to list effects"),
            )

    except Exception as e:
        logger.error(f"List effects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get")
async def get_effect(uri: str = Query(..., description="Plugin URI")):
    """Get effect information (cached)"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {"uri": uri, "cached": True}

        response: ServiceResponse = await service_client.make_request(
            "effect_get", request_data, "effects_service"
        )

        if response.success:
            return response.data.get("plugin_data", {})
        else:
            raise HTTPException(
                status_code=404, detail=response.data.get("error", "Plugin not found")
            )

    except Exception as e:
        logger.error(f"Get effect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_non_cached")
async def get_effect_non_cached(uri: str = Query(..., description="Plugin URI")):
    """Get effect information (non-cached)"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {"uri": uri, "cached": False}

        response: ServiceResponse = await service_client.make_request(
            "effect_get", request_data, "effects_service"
        )

        if response.success:
            return response.data.get("plugin_data", {})
        else:
            raise HTTPException(
                status_code=404, detail=response.data.get("error", "Plugin not found")
            )

    except Exception as e:
        logger.error(f"Get effect non-cached error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connect/{port_from}/{port_to}")
async def connect_effects(
    port_from: str = Path(..., description="Source port"),
    port_to: str = Path(..., description="Destination port"),
):
    """Connect effect ports"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {"port_from": port_from, "port_to": port_to}

        response: ServiceResponse = await service_client.make_request(
            "effect_connect", request_data, "effects_service"
        )

        if response.success:
            return response.data.get("success", True)
        else:
            raise HTTPException(
                status_code=400, detail=response.data.get("error", "Connection failed")
            )

    except Exception as e:
        logger.error(f"Connect effects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/disconnect/{port_from}/{port_to}")
async def disconnect_effects(
    port_from: str = Path(..., description="Source port"),
    port_to: str = Path(..., description="Destination port"),
):
    """Disconnect effect ports"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {"port_from": port_from, "port_to": port_to}

        response: ServiceResponse = await service_client.make_request(
            "effect_disconnect", request_data, "effects_service"
        )

        if response.success:
            return response.data.get("success", True)
        else:
            raise HTTPException(
                status_code=400,
                detail=response.data.get("error", "Disconnection failed"),
            )

    except Exception as e:
        logger.error(f"Disconnect effects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parameter/set")
async def set_effect_parameter(
    instance: str = Query(..., description="Effect instance"),
    body: EffectParameterSetBody = None,
):
    """Set effect parameter value"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {
            "instance": instance,
            "symbol": body.symbol,
            "value": body.value,
        }

        response: ServiceResponse = await service_client.make_request(
            "effect_parameter_set", request_data, "effects_service"
        )

        if response.success:
            return response.data.get("success", True)
        else:
            raise HTTPException(
                status_code=400,
                detail=response.data.get("error", "Parameter set failed"),
            )

    except Exception as e:
        logger.error(f"Set effect parameter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameter/address/{instance:path}")
async def address_effect_parameter(
    instance: str = Path(..., description="Effect instance path")
):
    """Address effect parameter"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {
            "instance": instance,
            "symbol": "",  # TODO: Extract from request
            "addressing_data": {},  # TODO: Extract from request
        }

        response: ServiceResponse = await service_client.make_request(
            "effect_parameter_address", request_data, "effects_service"
        )

        if response.success:
            return response.data.get("addressing_data", {})
        else:
            raise HTTPException(
                status_code=400,
                detail=response.data.get("error", "Parameter addressing failed"),
            )

    except Exception as e:
        logger.error(f"Address effect parameter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preset/load/{instance:path}")
async def load_effect_preset(
    instance: str = Path(..., description="Effect instance path"),
    uri: str = Query(..., description="Preset URI"),
    bundle: str = Query(..., description="Preset bundle"),
):
    """Load effect preset"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {"instance": instance, "uri": uri, "bundle": bundle}

        response: ServiceResponse = await service_client.make_request(
            "effect_preset_load", request_data, "effects_service"
        )

        if response.success:
            return response.data.get("success", True)
        else:
            raise HTTPException(
                status_code=400, detail=response.data.get("error", "Preset load failed")
            )

    except Exception as e:
        logger.error(f"Load effect preset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preset/save_new/{instance:path}")
async def save_new_effect_preset(
    instance: str = Path(..., description="Effect instance path"),
    uri: str = Query(..., description="Preset URI"),
    bundle: str = Query(..., description="Preset bundle"),
    label: str = Query(..., description="Preset label"),
):
    """Save new effect preset"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {
            "instance": instance,
            "uri": uri,
            "bundle": bundle,
            "label": label,
            "replace": False,
        }

        response: ServiceResponse = await service_client.make_request(
            "effect_preset_save", request_data, "effects_service"
        )

        if response.success:
            return response.data
        else:
            raise HTTPException(
                status_code=400, detail=response.data.get("error", "Preset save failed")
            )

    except Exception as e:
        logger.error(f"Save new effect preset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preset/save_replace/{instance:path}")
async def save_replace_effect_preset(
    instance: str = Path(..., description="Effect instance path"),
    uri: str = Query(..., description="Preset URI"),
    bundle: str = Query(..., description="Preset bundle"),
    label: str = Query(..., description="Preset label"),
):
    """Save/replace effect preset"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {
            "instance": instance,
            "uri": uri,
            "bundle": bundle,
            "label": label,
            "replace": True,
        }

        response: ServiceResponse = await service_client.make_request(
            "effect_preset_save", request_data, "effects_service"
        )

        if response.success:
            return response.data
        else:
            raise HTTPException(
                status_code=400, detail=response.data.get("error", "Preset save failed")
            )

    except Exception as e:
        logger.error(f"Save/replace effect preset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preset/delete/{instance:path}")
async def delete_effect_preset(
    instance: str = Path(..., description="Effect instance path"),
    uri: str = Query(..., description="Preset URI"),
    bundle: str = Query(..., description="Preset bundle"),
):
    """Delete effect preset"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {"instance": instance, "uri": uri, "bundle": bundle}

        response: ServiceResponse = await service_client.make_request(
            "effect_preset_delete", request_data, "effects_service"
        )

        if response.success:
            return response.data.get("success", True)
        else:
            raise HTTPException(
                status_code=400,
                detail=response.data.get("error", "Preset delete failed"),
            )

    except Exception as e:
        logger.error(f"Delete effect preset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image/{image_type}.png")
async def get_effect_image(
    image_type: str = Path(..., description="Image type (screenshot or thumbnail)"),
    uri: str = Query(..., description="Plugin URI"),
):
    """Get effect image (screenshot or thumbnail)"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {"uri": uri, "image_type": image_type}

        response: ServiceResponse = await service_client.make_request(
            "effect_image", request_data, "effects_service"
        )

        if response.success:
            image_path = response.data.get("image_path")
            content_type = response.data.get("content_type", "image/png")

            if image_path and os.path.exists(image_path):
                return FileResponse(
                    image_path, media_type=content_type, filename=f"{image_type}.png"
                )
            else:
                raise HTTPException(status_code=404, detail="Image not found")
        else:
            raise HTTPException(
                status_code=404, detail=response.data.get("error", "Image not found")
            )

    except Exception as e:
        logger.error(f"Get effect image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{filename:path}")
async def get_effect_file(
    filename: str = Path(..., description="Filename"),
    uri: str = Query(..., description="Plugin URI"),
):
    """Get effect file"""
    try:
        redis_url = get_redis_url_from_env()
        service_client = ServiceClient(redis_url=redis_url)

        request_data = {"uri": uri, "filename": filename}

        response: ServiceResponse = await service_client.make_request(
            "effect_file", request_data, "effects_service"
        )

        if response.success:
            file_path = response.data.get("file_path")
            content_type = response.data.get("content_type", "text/plain")

            if file_path and os.path.exists(file_path):
                return FileResponse(
                    file_path,
                    media_type=content_type,
                    filename=os.path.basename(filename),
                )
            else:
                raise HTTPException(status_code=404, detail="File not found")
        else:
            raise HTTPException(
                status_code=404, detail=response.data.get("error", "File not found")
            )

    except Exception as e:
        logger.error(f"Get effect file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
