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

from servicebus import CommConfig, ServiceClient, set_config


# Get Redis URL from environment and configure ServiceBus
def get_configured_service_client() -> ServiceClient:
    """Get configured service client"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    config = CommConfig(redis_url=redis_url)
    set_config(config)

    return ServiceClient("webui_gateway")


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
        service_client = get_configured_service_client()

        request_data = {"instance": instance, "uri": uri, "x": x, "y": y}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_add",
            data=request_data,
        )

        if response is not None:
            return response
        else:
            raise HTTPException(status_code=400, detail="Add effect failed")

    except Exception as e:
        logger.error(f"Add effect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/remove/{instance:path}")
async def remove_effect(instance: str = Path(..., description="Effect instance path")):
    """Remove an effect from the pedalboard"""
    try:
        service_client = get_configured_service_client()

        request_data = {"instance": instance}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_remove",
            data=request_data,
        )

        if response is not None:
            return response
        else:
            raise HTTPException(
                status_code=400,
                detail="Remove effect failed",
            )

    except Exception as e:
        logger.error(f"Remove effect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_effects():
    """List all available effects"""
    try:
        service_client = get_configured_service_client()

        request_data = {}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_list",
            data=request_data,
        )

        if response is not None:
            return response.get(
                "plugins", response if isinstance(response, list) else []
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to list effects",
            )

    except Exception as e:
        logger.error(f"List effects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get")
async def get_effect(uri: str = Query(..., description="Plugin URI")):
    """Get effect information (cached)"""
    try:
        service_client = get_configured_service_client()

        request_data = {"uri": uri, "cached": True}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_get",
            data=request_data,
        )

        if response is not None:
            return response.get("plugin_data", response)
        else:
            raise HTTPException(status_code=404, detail="Plugin not found")

    except Exception as e:
        logger.error(f"Get effect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connect/{instance_output:path}/{instance_input:path}")
async def connect_effects(
    instance_output: str = Path(..., description="Output instance path"),
    instance_input: str = Path(..., description="Input instance path"),
):
    """Connect two effects"""
    try:
        service_client = get_configured_service_client()

        request_data = {
            "instance_output": instance_output,
            "instance_input": instance_input,
        }

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_connect",
            data=request_data,
        )

        if response is not None:
            return response
        else:
            raise HTTPException(
                status_code=400,
                detail="Connect effects failed",
            )

    except Exception as e:
        logger.error(f"Connect effects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/disconnect/{instance_output:path}/{instance_input:path}")
async def disconnect_effects(
    instance_output: str = Path(..., description="Output instance path"),
    instance_input: str = Path(..., description="Input instance path"),
):
    """Disconnect two effects"""
    try:
        service_client = get_configured_service_client()

        request_data = {
            "instance_output": instance_output,
            "instance_input": instance_input,
        }

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_disconnect",
            data=request_data,
        )

        if response is not None:
            return response
        else:
            raise HTTPException(
                status_code=400,
                detail="Disconnect effects failed",
            )

    except Exception as e:
        logger.error(f"Disconnect effects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameter/set/{instance:path}")
async def set_effect_parameter(
    instance: str = Path(..., description="Effect instance path"),
    symbol: str = Query(..., description="Parameter symbol"),
    value: float = Query(..., description="Parameter value"),
):
    """Set an effect parameter"""
    try:
        service_client = get_configured_service_client()

        request_data = {"instance": instance, "symbol": symbol, "value": value}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_parameter_set",
            data=request_data,
        )

        if response is not None:
            return response
        else:
            raise HTTPException(
                status_code=400,
                detail="Set parameter failed",
            )

    except Exception as e:
        logger.error(f"Set parameter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parameter/set/{instance:path}")
async def set_effect_parameter_post(instance: str, body: EffectParameterSetBody):
    """Set an effect parameter via POST"""
    return await set_effect_parameter(instance, body.symbol, body.value)


@router.get("/parameter/address/{instance:path}")
async def address_effect_parameter(
    instance: str = Path(..., description="Effect instance path"),
    symbol: str = Query(..., description="Parameter symbol"),
    address: str = Query(..., description="Address URI"),
):
    """Address an effect parameter (MIDI, CV, etc.)"""
    try:
        service_client = get_configured_service_client()

        request_data = {"instance": instance, "symbol": symbol, "address": address}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_parameter_address",
            data=request_data,
        )

        if response is not None:
            return response
        else:
            raise HTTPException(
                status_code=400,
                detail="Address parameter failed",
            )

    except Exception as e:
        logger.error(f"Address parameter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preset/load/{instance:path}")
async def load_effect_preset(
    instance: str = Path(..., description="Effect instance path"),
    preset_uri: str = Query(..., description="Preset URI"),
):
    """Load a preset for an effect"""
    try:
        service_client = get_configured_service_client()

        request_data = {"instance": instance, "preset_uri": preset_uri}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_preset_load",
            data=request_data,
        )

        if response is not None:
            return response
        else:
            raise HTTPException(
                status_code=400,
                detail="Load preset failed",
            )

    except Exception as e:
        logger.error(f"Load preset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preset/save/{instance:path}")
async def save_effect_preset(
    instance: str = Path(..., description="Effect instance path"),
    name: str = Query(..., description="Preset name"),
):
    """Save a preset for an effect"""
    try:
        service_client = get_configured_service_client()

        request_data = {"instance": instance, "name": name}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_preset_save",
            data=request_data,
        )

        if response is not None:
            return response
        else:
            raise HTTPException(
                status_code=400,
                detail="Save preset failed",
            )

    except Exception as e:
        logger.error(f"Save preset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preset/delete/{instance:path}")
async def delete_effect_preset(
    instance: str = Path(..., description="Effect instance path"),
    preset_uri: str = Query(..., description="Preset URI"),
):
    """Delete a preset for an effect"""
    try:
        service_client = get_configured_service_client()

        request_data = {"instance": instance, "preset_uri": preset_uri}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_preset_delete",
            data=request_data,
        )

        if response is not None:
            return response
        else:
            raise HTTPException(
                status_code=400,
                detail="Delete preset failed",
            )

    except Exception as e:
        logger.error(f"Delete preset error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image/{uri:path}")
async def get_effect_image(
    uri: str = Path(..., description="Plugin URI"),
    version: int = Query(1, description="Image version"),
):
    """Get effect image/icon"""
    try:
        service_client = get_configured_service_client()

        request_data = {"uri": uri, "version": version}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_image",
            data=request_data,
        )

        if response is not None:
            image_path = response.get("image_path")
            if image_path and os.path.exists(image_path):
                return FileResponse(image_path)
            else:
                raise HTTPException(status_code=404, detail="Image not found")
        else:
            raise HTTPException(status_code=400, detail="Get image failed")

    except Exception as e:
        logger.error(f"Get effect image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{uri:path}")
async def get_effect_file(
    uri: str = Path(..., description="Plugin URI"),
    filename: str = Query(..., description="File name"),
):
    """Get effect file"""
    try:
        service_client = get_configured_service_client()

        request_data = {"uri": uri, "filename": filename}

        response = await service_client.call(
            target_service="effects_service",
            request_type="effect_file",
            data=request_data,
        )

        if response is not None:
            file_path = response.get("file_path")
            if file_path and os.path.exists(file_path):
                return FileResponse(file_path)
            else:
                raise HTTPException(status_code=404, detail="File not found")
        else:
            raise HTTPException(status_code=400, detail="Get file failed")

    except Exception as e:
        logger.error(f"Get effect file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))