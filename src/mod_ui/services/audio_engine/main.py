"""
Audio Engine Service FastAPI Application

Provides HTTP endpoints for audio engine operations.
"""

import logging
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException

from .models import (
    AddPluginCommand,
    AudioConnection,
    AudioEngineState,
    BypassPluginCommand,
    ConnectPortsCommand,
    DisconnectPortsCommand,
    LoadPresetCommand,
    PluginInstance,
    RemovePluginCommand,
    SetParameterCommand,
    SetTransportCommand,
    TransportState,
)
from .service import AudioEngineService

logger = logging.getLogger(__name__)

# Global service instance
audio_engine_service = AudioEngineService()

app = FastAPI(
    title="Audio Engine Service",
    description="Service for managing mod-host audio engine operations",
    version="1.0.0",
)


async def get_audio_service() -> AudioEngineService:
    """Dependency to get the audio engine service"""
    return audio_engine_service


@app.on_event("startup")
async def startup_event():
    """Start the audio engine service"""
    success = await audio_engine_service.start()
    if not success:
        logger.error("Failed to start audio engine service")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the audio engine service"""
    await audio_engine_service.stop()


# Health Check
@app.get("/health")
async def health_check(service: AudioEngineService = Depends(get_audio_service)):
    """Check service health and connection status"""
    return {
        "status": "healthy" if service.is_connected else "unhealthy",
        "connected": service.is_connected,
        "connection_status": service.connection.status.value,
    }


# State Management
@app.get("/state", response_model=AudioEngineState)
async def get_state(service: AudioEngineService = Depends(get_audio_service)):
    """Get current audio engine state"""
    return await service.get_state()


# Plugin Management
@app.post("/plugins", response_model=PluginInstance)
async def add_plugin(
    command: AddPluginCommand, service: AudioEngineService = Depends(get_audio_service)
):
    """Add a plugin instance to the audio engine"""
    return await service.add_plugin(command)


@app.delete("/plugins/{instance_id}")
async def remove_plugin(
    instance_id: str, service: AudioEngineService = Depends(get_audio_service)
):
    """Remove a plugin instance from the audio engine"""
    command = RemovePluginCommand(instance_id=instance_id)
    success = await service.remove_plugin(command)
    return {"success": success}


@app.get("/plugins", response_model=Dict[str, PluginInstance])
async def get_plugins(service: AudioEngineService = Depends(get_audio_service)):
    """Get all plugin instances"""
    state = await service.get_state()
    return state.plugins


@app.get("/plugins/{instance_id}", response_model=PluginInstance)
async def get_plugin(
    instance_id: str, service: AudioEngineService = Depends(get_audio_service)
):
    """Get a specific plugin instance"""
    state = await service.get_state()
    if instance_id not in state.plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return state.plugins[instance_id]


@app.post("/plugins/{instance_id}/bypass")
async def bypass_plugin(
    instance_id: str,
    bypass: bool,
    service: AudioEngineService = Depends(get_audio_service),
):
    """Bypass or enable a plugin"""
    command = BypassPluginCommand(instance_id=instance_id, bypass=bypass)
    success = await service.bypass_plugin(command)
    return {"success": success}


# Parameter Management
@app.post("/plugins/{instance_id}/parameters/{port_symbol}")
async def set_parameter(
    instance_id: str,
    port_symbol: str,
    value: float,
    service: AudioEngineService = Depends(get_audio_service),
):
    """Set a plugin parameter value"""
    command = SetParameterCommand(
        instance_id=instance_id, port_symbol=port_symbol, value=value
    )
    success = await service.set_parameter(command)
    return {"success": success}


@app.get("/plugins/{instance_id}/parameters")
async def get_plugin_parameters(
    instance_id: str, service: AudioEngineService = Depends(get_audio_service)
):
    """Get all parameter values for a plugin"""
    state = await service.get_state()
    if instance_id not in state.plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return state.plugins[instance_id].ports


# Preset Management
@app.post("/plugins/{instance_id}/presets")
async def load_preset(
    instance_id: str,
    preset_uri: str,
    service: AudioEngineService = Depends(get_audio_service),
):
    """Load a preset for a plugin"""
    command = LoadPresetCommand(instance_id=instance_id, preset_uri=preset_uri)
    success = await service.load_preset(command)
    return {"success": success}


# Audio Routing
@app.post("/connections", response_model=AudioConnection)
async def connect_ports(
    command: ConnectPortsCommand,
    service: AudioEngineService = Depends(get_audio_service),
):
    """Connect two audio ports"""
    return await service.connect_ports(command)


@app.delete("/connections")
async def disconnect_ports(
    from_port: str,
    to_port: str,
    service: AudioEngineService = Depends(get_audio_service),
):
    """Disconnect two audio ports"""
    command = DisconnectPortsCommand(from_port=from_port, to_port=to_port)
    success = await service.disconnect_ports(command)
    return {"success": success}


@app.get("/connections", response_model=List[AudioConnection])
async def get_connections(service: AudioEngineService = Depends(get_audio_service)):
    """Get all audio connections"""
    state = await service.get_state()
    return state.connections


# Transport Control
@app.get("/transport", response_model=TransportState)
async def get_transport(service: AudioEngineService = Depends(get_audio_service)):
    """Get current transport state"""
    return await service.get_transport()


@app.post("/transport", response_model=TransportState)
async def set_transport(
    command: SetTransportCommand,
    service: AudioEngineService = Depends(get_audio_service),
):
    """Set transport state"""
    return await service.set_transport(command)


@app.post("/transport/play")
async def play_transport(service: AudioEngineService = Depends(get_audio_service)):
    """Start transport playback"""
    command = SetTransportCommand(rolling=True)
    return await service.set_transport(command)


@app.post("/transport/stop")
async def stop_transport(service: AudioEngineService = Depends(get_audio_service)):
    """Stop transport playback"""
    command = SetTransportCommand(rolling=False)
    return await service.set_transport(command)


@app.post("/transport/bpm")
async def set_bpm(bpm: float, service: AudioEngineService = Depends(get_audio_service)):
    """Set transport BPM"""
    command = SetTransportCommand(bpm=bpm)
    return await service.set_transport(command)


@app.post("/transport/bpb")
async def set_bpb(bpb: float, service: AudioEngineService = Depends(get_audio_service)):
    """Set transport beats per bar"""
    command = SetTransportCommand(bpb=bpb)
    return await service.set_transport(command)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")
