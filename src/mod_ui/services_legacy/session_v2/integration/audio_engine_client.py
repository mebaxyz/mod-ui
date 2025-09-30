"""
Audio Engine ServiceBus Client

Client for communicating with the audio engine service through Redis pub/sub
instead of HTTP calls. This maintains the pure pub/sub architecture.
"""

import logging
from typing import Any, Dict, Optional

from servicebus import ServiceClient

logger = logging.getLogger(__name__)


class SessionPluginService:
    """ServiceBus client for audio engine operations from session service"""

    def __init__(self, servicebus_client: ServiceClient):
        self.client = servicebus_client

    async def add_plugin(
        self, instance_id: str, plugin_uri: str, x: float = 0.0, y: float = 0.0
    ) -> Dict[str, Any]:
        """Add a plugin through ServiceBus"""
        try:
            response = await self.client.call(
                "audio-engine",
                "add_plugin",
                {"instance_id": instance_id, "plugin_uri": plugin_uri, "x": x, "y": y},
            )
            return response
        except Exception as e:
            logger.error("Failed to add plugin via ServiceBus: %s", e)
            raise

    async def remove_plugin(self, instance_id: str) -> Dict[str, Any]:
        """Remove a plugin through ServiceBus"""
        try:
            response = await self.client.call(
                "audio-engine", "remove_plugin", {"instance_id": instance_id}
            )
            return response
        except Exception as e:
            logger.error("Failed to remove plugin via ServiceBus: %s", e)
            raise

    async def set_parameter(
        self, instance_id: str, port_symbol: str, value: float
    ) -> Dict[str, Any]:
        """Set plugin parameter through ServiceBus"""
        try:
            response = await self.client.call(
                "audio-engine",
                "set_parameter",
                {
                    "instance_id": instance_id,
                    "port_symbol": port_symbol,
                    "value": value,
                },
            )
            return response
        except Exception as e:
            logger.error("Failed to set parameter via ServiceBus: %s", e)
            raise

    async def connect_ports(self, from_port: str, to_port: str) -> Dict[str, Any]:
        """Connect audio ports through ServiceBus"""
        try:
            response = await self.client.call(
                "audio-engine",
                "connect_ports",
                {"from_port": from_port, "to_port": to_port},
            )
            return response
        except Exception as e:
            logger.error("Failed to connect ports via ServiceBus: %s", e)
            raise

    async def disconnect_ports(self, from_port: str, to_port: str) -> Dict[str, Any]:
        """Disconnect audio ports through ServiceBus"""
        try:
            response = await self.client.call(
                "audio-engine",
                "disconnect_ports",
                {"from_port": from_port, "to_port": to_port},
            )
            return response
        except Exception as e:
            logger.error("Failed to disconnect ports via ServiceBus: %s", e)
            raise

    async def set_transport(
        self,
        rolling: Optional[bool] = None,
        bpm: Optional[float] = None,
        bpb: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Set transport state through ServiceBus"""
        try:
            params = {}
            if rolling is not None:
                params["rolling"] = rolling
            if bpm is not None:
                params["bpm"] = bpm
            if bpb is not None:
                params["bpb"] = bpb

            response = await self.client.call("audio-engine", "set_transport", params)
            return response
        except Exception as e:
            logger.error("Failed to set transport via ServiceBus: %s", e)
            raise

    async def get_state(self) -> Dict[str, Any]:
        """Get audio engine state through ServiceBus"""
        try:
            response = await self.client.call("audio-engine", "get_state", {})
            return response
        except Exception as e:
            logger.error("Failed to get state via ServiceBus: %s", e)
            raise

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()

    async def add_plugin(
        self, instance_id: str, plugin_uri: str, x: float = 0.0, y: float = 0.0
    ):
        """Add a plugin to the current session"""
        try:
            response = await self.http_client.post(
                f"{self.audio_engine_url}/plugins",
                json={
                    "instance_id": instance_id,
                    "plugin_uri": plugin_uri,
                    "x": x,
                    "y": y,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to add plugin %s: %s", instance_id, e)
            raise HTTPException(status_code=500, detail=f"Failed to add plugin: {e}")

    async def remove_plugin(self, instance_id: str):
        """Remove a plugin from the current session"""
        try:
            response = await self.http_client.delete(
                f"{self.audio_engine_url}/plugins/{instance_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to remove plugin %s: %s", instance_id, e)
            raise HTTPException(status_code=500, detail=f"Failed to remove plugin: {e}")

    async def set_parameter(self, instance_id: str, port_symbol: str, value: float):
        """Set a plugin parameter value"""
        try:
            response = await self.http_client.post(
                f"{self.audio_engine_url}/plugins/{instance_id}/parameters/{port_symbol}",
                params={"value": value},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to set parameter %s:%s = %f: %s",
                instance_id,
                port_symbol,
                value,
                e,
            )
            raise HTTPException(status_code=500, detail=f"Failed to set parameter: {e}")

    async def connect_ports(self, from_port: str, to_port: str):
        """Connect two audio/CV ports"""
        try:
            response = await self.http_client.post(
                f"{self.audio_engine_url}/connections",
                json={"from_port": from_port, "to_port": to_port},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to connect %s -> %s: %s", from_port, to_port, e)
            raise HTTPException(status_code=500, detail=f"Failed to connect ports: {e}")

    async def disconnect_ports(self, from_port: str, to_port: str):
        """Disconnect two audio/CV ports"""
        try:
            response = await self.http_client.delete(
                f"{self.audio_engine_url}/connections",
                params={"from_port": from_port, "to_port": to_port},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to disconnect %s -> %s: %s", from_port, to_port, e)
            raise HTTPException(
                status_code=500, detail=f"Failed to disconnect ports: {e}"
            )

    async def load_preset(self, instance_id: str, preset_uri: str):
        """Load a preset for a plugin"""
        try:
            response = await self.http_client.post(
                f"{self.audio_engine_url}/plugins/{instance_id}/presets",
                params={"preset_uri": preset_uri},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to load preset %s for plugin %s: %s", preset_uri, instance_id, e
            )
            raise HTTPException(status_code=500, detail=f"Failed to load preset: {e}")

    async def bypass_plugin(self, instance_id: str, bypass: bool):
        """Bypass or enable a plugin"""
        try:
            response = await self.http_client.post(
                f"{self.audio_engine_url}/plugins/{instance_id}/bypass",
                params={"bypass": bypass},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to bypass plugin %s: %s", instance_id, e)
            raise HTTPException(status_code=500, detail=f"Failed to bypass plugin: {e}")

    async def get_plugin_state(self, instance_id: str):
        """Get current state of a plugin"""
        try:
            response = await self.http_client.get(
                f"{self.audio_engine_url}/plugins/{instance_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to get plugin state %s: %s", instance_id, e)
            raise HTTPException(
                status_code=500, detail=f"Failed to get plugin state: {e}"
            )

    async def get_all_plugins(self):
        """Get state of all plugins"""
        try:
            response = await self.http_client.get(f"{self.audio_engine_url}/plugins")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to get all plugins: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to get plugins: {e}")

    async def get_connections(self):
        """Get all audio connections"""
        try:
            response = await self.http_client.get(
                f"{self.audio_engine_url}/connections"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to get connections: %s", e)
            raise HTTPException(
                status_code=500, detail=f"Failed to get connections: {e}"
            )

    async def get_transport_state(self):
        """Get current transport state"""
        try:
            response = await self.http_client.get(f"{self.audio_engine_url}/transport")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to get transport state: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to get transport: {e}")

    async def set_transport_bpm(self, bpm: float):
        """Set transport BPM"""
        try:
            response = await self.http_client.post(
                f"{self.audio_engine_url}/transport/bpm", params={"bpm": bpm}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to set BPM to %f: %s", bpm, e)
            raise HTTPException(status_code=500, detail=f"Failed to set BPM: {e}")

    async def set_transport_bpb(self, bpb: float):
        """Set transport beats per bar"""
        try:
            response = await self.http_client.post(
                f"{self.audio_engine_url}/transport/bpb", params={"bpb": bpb}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to set BPB to %f: %s", bpb, e)
            raise HTTPException(status_code=500, detail=f"Failed to set BPB: {e}")

    async def play_transport(self):
        """Start transport playback"""
        try:
            response = await self.http_client.post(
                f"{self.audio_engine_url}/transport/play"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to start transport: %s", e)
            raise HTTPException(
                status_code=500, detail=f"Failed to start transport: {e}"
            )

    async def stop_transport(self):
        """Stop transport playback"""
        try:
            response = await self.http_client.post(
                f"{self.audio_engine_url}/transport/stop"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Failed to stop transport: %s", e)
            raise HTTPException(
                status_code=500, detail=f"Failed to stop transport: {e}"
            )

    async def get_audio_engine_health(self):
        """Check audio engine service health"""
        try:
            response = await self.http_client.get(f"{self.audio_engine_url}/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("Audio engine health check failed: %s", e)
            return {"status": "unhealthy", "error": str(e)}
