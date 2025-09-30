"""
Pedalboard Management Router

Provides REST API endpoints for pedalboard CRUD operations,
plugin management, and connections.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..models import ConnectionModel, PedalboardMetadata, PedalboardModel, PluginModel
from ..services.state_manager import StateManagerService

router = APIRouter()


# Request/Response models
class CreatePedalboardRequest(BaseModel):
    title: str
    description: Optional[str] = None


class SavePedalboardRequest(BaseModel):
    title: Optional[str] = None
    bundle_path: Optional[str] = None


class AddPluginRequest(BaseModel):
    instance_id: str
    plugin_uri: str
    x: float
    y: float
    enabled: bool = True


class MovePluginRequest(BaseModel):
    x: float
    y: float


class SetParameterRequest(BaseModel):
    value: float


class AddConnectionRequest(BaseModel):
    source_port: str
    destination_port: str


# Dependency to get state manager
async def get_state_manager(request: Request) -> StateManagerService:
    state_manager = getattr(request.app.state, "state_manager", None)
    if state_manager is None:
        raise HTTPException(status_code=503, detail="State manager not available")
    return state_manager


@router.get("/list")
async def list_pedalboards(state_mgr: StateManagerService = Depends(get_state_manager)):
    """List all available pedalboards"""
    try:
        pedalboards = await state_mgr.list_pedalboards()
        return {"success": True, "pedalboards": pedalboards, "count": len(pedalboards)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_pedalboard(
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Get currently loaded pedalboard"""
    try:
        pedalboard = await state_mgr.get_current_pedalboard()
        if pedalboard is None:
            return {"success": True, "pedalboard": None}

        return {
            "success": True,
            "pedalboard": {
                "bundle_path": pedalboard.bundle_path,
                "metadata": pedalboard.metadata.dict(),
                "plugins": {k: v.dict() for k, v in pedalboard.plugins.items()},
                "connections": [conn.dict() for conn in pedalboard.connections],
                "created_at": pedalboard.created_at.isoformat(),
                "modified_at": pedalboard.modified_at.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_pedalboard(
    request: CreatePedalboardRequest,
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Create a new empty pedalboard"""
    try:
        pedalboard = await state_mgr.create_new_pedalboard(
            title=request.title, description=request.description
        )

        return {
            "success": True,
            "bundle_path": pedalboard.bundle_path,
            "title": pedalboard.metadata.title,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load/{bundle_path:path}")
async def load_pedalboard(
    bundle_path: str, state_mgr: StateManagerService = Depends(get_state_manager)
):
    """Load a pedalboard from file system"""
    try:
        pedalboard = await state_mgr.load_pedalboard(bundle_path)

        return {
            "success": True,
            "pedalboard": {
                "bundle_path": pedalboard.bundle_path,
                "title": pedalboard.metadata.title,
                "plugin_count": len(pedalboard.plugins),
                "connection_count": len(pedalboard.connections),
            },
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pedalboard not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_pedalboard(
    request: SavePedalboardRequest,
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Save current pedalboard"""
    try:
        current_pedalboard = await state_mgr.get_current_pedalboard()
        if current_pedalboard is None:
            raise HTTPException(status_code=400, detail="No current pedalboard to save")

        # Update title if provided
        if request.title:
            current_pedalboard.metadata.title = request.title

        bundle_path = await state_mgr.save_pedalboard(
            current_pedalboard, request.bundle_path
        )

        return {
            "success": True,
            "bundle_path": bundle_path,
            "title": current_pedalboard.metadata.title,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Plugin management endpoints


@router.post("/plugin/add")
async def add_plugin(
    request: AddPluginRequest,
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Add a plugin to the current pedalboard"""
    try:
        plugin = PluginModel(
            instance_id=request.instance_id,
            plugin_uri=request.plugin_uri,
            x=request.x,
            y=request.y,
            enabled=request.enabled,
        )

        await state_mgr.add_plugin(plugin)

        return {
            "success": True,
            "instance_id": plugin.instance_id,
            "plugin_uri": plugin.plugin_uri,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/plugin/{instance_id}")
async def remove_plugin(
    instance_id: str, state_mgr: StateManagerService = Depends(get_state_manager)
):
    """Remove a plugin from the current pedalboard"""
    try:
        success = await state_mgr.remove_plugin(instance_id)

        if not success:
            raise HTTPException(status_code=404, detail="Plugin not found")

        return {"success": True, "instance_id": instance_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/plugin/{instance_id}/move")
async def move_plugin(
    instance_id: str,
    request: MovePluginRequest,
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Move a plugin on the pedalboard canvas"""
    try:
        current_pedalboard = await state_mgr.get_current_pedalboard()
        if current_pedalboard is None:
            raise HTTPException(status_code=400, detail="No current pedalboard")

        plugin = current_pedalboard.get_plugin(instance_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")

        plugin.x = request.x
        plugin.y = request.y
        current_pedalboard.modified_at = datetime.now()

        return {
            "success": True,
            "instance_id": instance_id,
            "x": plugin.x,
            "y": plugin.y,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/plugin/{instance_id}/parameter/{parameter_symbol}")
async def set_plugin_parameter(
    instance_id: str,
    parameter_symbol: str,
    request: SetParameterRequest,
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Set a plugin parameter value"""
    try:
        await state_mgr.set_plugin_parameter(
            instance_id, parameter_symbol, request.value
        )

        return {
            "success": True,
            "instance_id": instance_id,
            "parameter": parameter_symbol,
            "value": request.value,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/plugin/{instance_id}/enable")
async def enable_plugin(
    instance_id: str, state_mgr: StateManagerService = Depends(get_state_manager)
):
    """Enable a plugin (remove bypass)"""
    try:
        current_pedalboard = await state_mgr.get_current_pedalboard()
        if current_pedalboard is None:
            raise HTTPException(status_code=400, detail="No current pedalboard")

        plugin = current_pedalboard.get_plugin(instance_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")

        plugin.enabled = True
        current_pedalboard.modified_at = datetime.now()

        return {"success": True, "instance_id": instance_id, "enabled": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/plugin/{instance_id}/disable")
async def disable_plugin(
    instance_id: str, state_mgr: StateManagerService = Depends(get_state_manager)
):
    """Disable a plugin (bypass)"""
    try:
        current_pedalboard = await state_mgr.get_current_pedalboard()
        if current_pedalboard is None:
            raise HTTPException(status_code=400, detail="No current pedalboard")

        plugin = current_pedalboard.get_plugin(instance_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")

        plugin.enabled = False
        current_pedalboard.modified_at = datetime.now()

        return {"success": True, "instance_id": instance_id, "enabled": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Connection management endpoints


@router.post("/connection/add")
async def add_connection(
    request: AddConnectionRequest,
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Add a connection between plugin ports"""
    try:
        connection = ConnectionModel(
            source_port=request.source_port, destination_port=request.destination_port
        )

        await state_mgr.add_connection(connection)

        return {
            "success": True,
            "connection_id": connection.connection_id,
            "source_port": connection.source_port,
            "destination_port": connection.destination_port,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connection/remove")
async def remove_connection(
    source_port: str,
    destination_port: str,
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Remove a connection between plugin ports"""
    try:
        success = await state_mgr.remove_connection(source_port, destination_port)

        if not success:
            raise HTTPException(status_code=404, detail="Connection not found")

        return {
            "success": True,
            "source_port": source_port,
            "destination_port": destination_port,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections")
async def list_connections(state_mgr: StateManagerService = Depends(get_state_manager)):
    """List all connections in current pedalboard"""
    try:
        current_pedalboard = await state_mgr.get_current_pedalboard()
        if current_pedalboard is None:
            return {"success": True, "connections": [], "count": 0}

        connections = [conn.dict() for conn in current_pedalboard.connections]

        return {"success": True, "connections": connections, "count": len(connections)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
