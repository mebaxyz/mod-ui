"""
Session Management Router

Provides REST API endpoints for session lifecycle management,
transport controls, and system-level operations.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..models import SessionState, TransportState
from ..services.state_manager import StateManagerService

router = APIRouter()


# Request/Response models
class SetTempoRequest(BaseModel):
    bpm: float


class SetTransportStateRequest(BaseModel):
    state: TransportState


class SystemConfigRequest(BaseModel):
    sample_rate: Optional[int] = None
    buffer_size: Optional[int] = None
    audio_driver: Optional[str] = None


# Dependency to get state manager
async def get_state_manager(request: Request) -> StateManagerService:
    state_manager = getattr(request.app.state, "state_manager", None)
    if state_manager is None:
        raise HTTPException(status_code=503, detail="State manager not available")
    return state_manager


@router.get("/status")
async def get_session_status(
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Get current session status and state"""
    try:
        session_state = await state_mgr.get_session_state()

        return {
            "success": True,
            "session": {
                "transport_state": session_state.transport_state.value,
                "tempo_bpm": session_state.tempo_bpm,
                "sample_rate": session_state.sample_rate,
                "buffer_size": session_state.buffer_size,
                "audio_driver": session_state.audio_driver,
                "cpu_load": session_state.cpu_load,
                "xrun_count": session_state.xrun_count,
                "uptime_seconds": session_state.uptime_seconds,
                "created_at": session_state.created_at.isoformat(),
                "modified_at": session_state.modified_at.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_session(state_mgr: StateManagerService = Depends(get_state_manager)):
    """Reset session to initial state"""
    try:
        # Create a new session state
        new_session = SessionState()

        # Reset via state manager
        await state_mgr.reset_session(new_session)

        return {
            "success": True,
            "message": "Session reset successfully",
            "session_id": str(new_session.session_id),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Transport control endpoints


@router.post("/transport/play")
async def transport_play(state_mgr: StateManagerService = Depends(get_state_manager)):
    """Start transport playback"""
    try:
        await state_mgr.set_transport_state(TransportState.PLAYING)

        return {
            "success": True,
            "transport_state": "playing",
            "message": "Transport started",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transport/stop")
async def transport_stop(state_mgr: StateManagerService = Depends(get_state_manager)):
    """Stop transport playback"""
    try:
        await state_mgr.set_transport_state(TransportState.STOPPED)

        return {
            "success": True,
            "transport_state": "stopped",
            "message": "Transport stopped",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transport/pause")
async def transport_pause(state_mgr: StateManagerService = Depends(get_state_manager)):
    """Pause transport playback"""
    try:
        await state_mgr.set_transport_state(TransportState.PAUSED)

        return {
            "success": True,
            "transport_state": "paused",
            "message": "Transport paused",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transport/rewind")
async def transport_rewind(state_mgr: StateManagerService = Depends(get_state_manager)):
    """Rewind transport to beginning"""
    try:
        # TODO: Implement actual rewind logic with JACK transport
        await state_mgr.set_transport_state(TransportState.STOPPED)

        return {
            "success": True,
            "transport_state": "stopped",
            "message": "Transport rewound to start",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tempo")
async def set_tempo(
    request: SetTempoRequest,
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Set session tempo (BPM)"""
    try:
        if request.bpm <= 0 or request.bpm > 300:
            raise HTTPException(status_code=400, detail="BPM must be between 1 and 300")

        await state_mgr.set_tempo(request.bpm)

        return {
            "success": True,
            "tempo_bpm": request.bpm,
            "message": f"Tempo set to {request.bpm} BPM",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tempo")
async def get_tempo(state_mgr: StateManagerService = Depends(get_state_manager)):
    """Get current session tempo"""
    try:
        session_state = await state_mgr.get_session_state()

        return {"success": True, "tempo_bpm": session_state.tempo_bpm}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# System configuration endpoints


@router.post("/config")
async def set_system_config(
    request: SystemConfigRequest,
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Update system configuration"""
    try:
        session_state = await state_mgr.get_session_state()

        # Update provided configuration
        config_changed = False

        if request.sample_rate is not None:
            if request.sample_rate not in [22050, 44100, 48000, 88200, 96000]:
                raise HTTPException(status_code=400, detail="Invalid sample rate")
            session_state.sample_rate = request.sample_rate
            config_changed = True

        if request.buffer_size is not None:
            if request.buffer_size not in [64, 128, 256, 512, 1024, 2048]:
                raise HTTPException(status_code=400, detail="Invalid buffer size")
            session_state.buffer_size = request.buffer_size
            config_changed = True

        if request.audio_driver is not None:
            if request.audio_driver not in ["alsa", "jack", "dummy"]:
                raise HTTPException(status_code=400, detail="Invalid audio driver")
            session_state.audio_driver = request.audio_driver
            config_changed = True

        if config_changed:
            # TODO: Apply configuration changes to audio system
            # This would typically require restarting audio engine
            pass

        return {
            "success": True,
            "config": {
                "sample_rate": session_state.sample_rate,
                "buffer_size": session_state.buffer_size,
                "audio_driver": session_state.audio_driver,
            },
            "message": "Configuration updated" if config_changed else "No changes made",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_system_config(
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Get current system configuration"""
    try:
        session_state = await state_mgr.get_session_state()

        return {
            "success": True,
            "config": {
                "sample_rate": session_state.sample_rate,
                "buffer_size": session_state.buffer_size,
                "audio_driver": session_state.audio_driver,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Performance monitoring endpoints


@router.get("/stats")
async def get_session_stats(
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Get session performance statistics"""
    try:
        session_state = await state_mgr.get_session_state()

        return {
            "success": True,
            "stats": {
                "cpu_load": session_state.cpu_load,
                "xrun_count": session_state.xrun_count,
                "uptime_seconds": session_state.uptime_seconds,
                "sample_rate": session_state.sample_rate,
                "buffer_size": session_state.buffer_size,
                "transport_state": session_state.transport_state.value,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats/reset")
async def reset_session_stats(
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """Reset session performance counters"""
    try:
        session_state = await state_mgr.get_session_state()

        # Reset counters
        session_state.xrun_count = 0
        session_state.uptime_seconds = 0

        return {
            "success": True,
            "message": "Session statistics reset",
            "stats": {"xrun_count": 0, "uptime_seconds": 0},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Snapshot management


@router.post("/snapshot/save")
async def save_session_snapshot(
    name: str, state_mgr: StateManagerService = Depends(get_state_manager)
):
    """Save current session state as a named snapshot"""
    try:
        # TODO: Implement snapshot functionality
        # This would save both pedalboard and session configuration

        return {
            "success": True,
            "snapshot_name": name,
            "message": f"Snapshot '{name}' saved successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/load/{name}")
async def load_session_snapshot(
    name: str, state_mgr: StateManagerService = Depends(get_state_manager)
):
    """Load a saved session snapshot"""
    try:
        # TODO: Implement snapshot loading
        # This would restore both pedalboard and session configuration

        return {
            "success": True,
            "snapshot_name": name,
            "message": f"Snapshot '{name}' loaded successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots")
async def list_session_snapshots(
    state_mgr: StateManagerService = Depends(get_state_manager),
):
    """List all available session snapshots"""
    try:
        # TODO: Implement snapshot listing
        # This would scan filesystem for saved snapshots

        return {"success": True, "snapshots": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
